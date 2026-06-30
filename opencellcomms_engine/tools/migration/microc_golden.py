"""MicroC golden-reference harness — Stage 0 of the ABM migration.

Run MicroC in-process, seeded, for a few macro-steps, and snapshot the full
state (substance fields + per-cell state + aggregates) so that two runs — or a
pre/post-migration pair — can be compared to prove *behaviour preservation*.
This is the safety net the migration is gated on (see
docs/MICROC_ABM_MIGRATION_PLAN.md).

CLI
    python tools/migration/microc_golden.py run --seed 123 --steps 3 --out DIR
    python tools/migration/microc_golden.py compare REF_DIR NEW_DIR
    python tools/migration/microc_golden.py determinism --seed 123 --steps 3

Determinism notes (verified by investigation):
  * ``workflow.seed`` only fixes ENTITY ITERATION ORDER. The biology itself uses
    the GLOBAL ``random`` / ``numpy.random`` streams, which nothing in the MicroC
    path seeds — so we seed them here, before every run.
  * Daughter cells created by division get a non-seedable ``uuid4`` id. So we key
    cells by POSITION (unique per tile), never by id.
  * Global RNG state carries over between in-process runs, so every comparison
    run is executed in a FRESH PROCESS (the ``run`` subcommand is the unit; the
    ``determinism`` / ``compare`` drivers spawn one process per run).
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Dict

import numpy as np

# --- engine import wiring (engine uses both 'src.*' and bare 'simulation.*') ---
ENGINE = Path(__file__).resolve().parents[2]            # .../opencellcomms_engine
REPO = ENGINE.parent
WF = REPO / "opencellcomms_adapters" / "MicroC" / "workflows" / "microc.json"

# MicroC's logs print Unicode arrows; force UTF-8 so Windows cp1252 stdout does
# not raise mid-run.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ----------------------------------------------------------------------------- run
def run_microc(seed: int = 123, n_steps: int = 3) -> Dict[str, Any]:
    """Run MicroC in-process for ``n_steps`` macro-steps and return the final
    context. Seeds the global RNGs *and* ``workflow.seed`` for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)

    for p in (str(ENGINE), str(ENGINE / "src")):
        if p not in sys.path:
            sys.path.insert(0, p)

    from src.workflow.loader import WorkflowLoader
    from src.workflow.executor import WorkflowExecutor

    workflow = WorkflowLoader.load(WF)
    workflow.seed = seed
    for call in workflow.subworkflows["main"].subworkflow_calls:
        if call.subworkflow_name == "__scheduler__":
            call.iterations = int(n_steps)

    executor = WorkflowExecutor(workflow, workflow_file=str(WF), observability_enabled=False)
    context: Dict[str, Any] = {"workflow_file": str(WF.absolute())}
    return executor.execute_main(context, entry_subworkflow="main")


# ------------------------------------------------------------------------- snapshot
def snapshot(context: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the comparable state from a finished run."""
    sim = context["simulator"]
    pop = context["population"]
    nets = context.get("gene_networks", {})

    substances = {n: np.asarray(s.concentrations, dtype=float).copy()
                  for n, s in sim.state.substances.items()}

    # Keyed by position (a unique tile) so non-deterministic uuid4 daughter ids
    # never enter the comparison. id is recorded but not compared.
    cells: Dict[str, Any] = {}
    for cid, c in pop.state.cells.items():
        st = c.state
        net = nets.get(cid)
        key = ",".join(str(int(v)) for v in st.position)   # "x,y" — JSON-safe
        cells[key] = dict(
            position=[int(v) for v in st.position],
            phenotype=st.phenotype,
            gene_states={k: bool(v) for k, v in dict(st.gene_states).items()},
            gene_network=(None if net is None
                          else {k: bool(v) for k, v in net.get_all_states().items()}),
            age=float(st.age),
            division_count=int(st.division_count),
        )

    return dict(
        meta=dict(n_cells=len(cells)),
        substances=substances,
        cells=cells,
        population_stats=pop.get_population_statistics(),
        substance_stats=sim.get_summary_statistics(),
    )


def save_snapshot(snap: Dict[str, Any], out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_dir / "substances.npz", **snap["substances"])
    with gzip.open(out_dir / "cells.json.gz", "wt", encoding="utf-8") as f:
        json.dump(snap["cells"], f, sort_keys=True)   # ~35x smaller gzipped
    (out_dir / "aggregates.json").write_text(json.dumps(
        dict(meta=snap["meta"],
             population_stats=snap["population_stats"],
             substance_stats=snap["substance_stats"]),
        indent=2, sort_keys=True, default=_json_default))


def load_snapshot(in_dir: Path) -> Dict[str, Any]:
    in_dir = Path(in_dir)
    with np.load(in_dir / "substances.npz") as z:
        substances = {k: z[k] for k in z.files}
    with gzip.open(in_dir / "cells.json.gz", "rt", encoding="utf-8") as f:
        cells = json.load(f)
    agg = json.loads((in_dir / "aggregates.json").read_text())
    return dict(substances=substances, cells=cells,
                meta=agg["meta"], population_stats=agg["population_stats"],
                substance_stats=agg["substance_stats"])


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# -------------------------------------------------------------------------- compare
def compare(ref: Dict[str, Any], new: Dict[str, Any],
            field_rtol: float = 0.0, field_atol: float = 0.0) -> Dict[str, Any]:
    """Diff two snapshots at three levels: substance fields (numeric, with
    tolerance), cells (exact, keyed by position), aggregates. Returns a report
    dict with ``ok`` and per-level detail. Default tolerance is EXACT (for the
    determinism proof); loosen for cross-motor migration comparison."""
    report: Dict[str, Any] = {"ok": True, "fields": {}, "cells": {}, "aggregates": {}}

    # --- substance fields ---
    ref_subs, new_subs = ref["substances"], new["substances"]
    if set(ref_subs) != set(new_subs):
        report["ok"] = False
        report["fields"]["substance_set_mismatch"] = dict(
            ref=sorted(ref_subs), new=sorted(new_subs))
    for name in sorted(set(ref_subs) & set(new_subs)):
        a, b = np.asarray(ref_subs[name], float), np.asarray(new_subs[name], float)
        if a.shape != b.shape:
            report["ok"] = False
            report["fields"][name] = dict(ok=False, reason="shape",
                                          ref_shape=a.shape, new_shape=b.shape)
            continue
        absd = np.abs(a - b)
        denom = np.maximum(np.abs(a), np.abs(b))
        reld = np.divide(absd, denom, out=np.zeros_like(absd), where=denom > 0)
        ok = bool(np.allclose(a, b, rtol=field_rtol, atol=field_atol))
        report["fields"][name] = dict(ok=ok,
                                      max_abs=float(absd.max()),
                                      max_rel=float(reld.max()))
        report["ok"] &= ok

    # --- cells (exact, by position) ---
    ref_c, new_c = ref["cells"], new["cells"]
    only_ref = sorted(set(ref_c) - set(new_c))
    only_new = sorted(set(new_c) - set(ref_c))
    diffs = []
    for key in sorted(set(ref_c) & set(new_c)):
        r, n = ref_c[key], new_c[key]
        for field in ("phenotype", "gene_states", "gene_network", "division_count"):
            if r.get(field) != n.get(field):
                diffs.append(dict(pos=key, field=field))
                break
    cells_ok = not (only_ref or only_new or diffs)
    report["cells"] = dict(ok=cells_ok, n_ref=len(ref_c), n_new=len(new_c),
                           only_in_ref=len(only_ref), only_in_new=len(only_new),
                           state_diffs=len(diffs), sample_diffs=diffs[:5],
                           sample_only_ref=only_ref[:5], sample_only_new=only_new[:5])
    report["ok"] &= cells_ok

    # --- aggregates ---
    pc_ok = ref["population_stats"].get("phenotype_counts") == \
        new["population_stats"].get("phenotype_counts")
    report["aggregates"] = dict(
        ok=pc_ok,
        ref_phenotype_counts=ref["population_stats"].get("phenotype_counts"),
        new_phenotype_counts=new["population_stats"].get("phenotype_counts"))
    report["ok"] &= pc_ok
    return report


# ------------------------------------------------------------------------------ CLI
def _cmd_run(args) -> int:
    t0 = time.time()
    work = Path(tempfile.mkdtemp(prefix="microc_run_"))
    cwd = os.getcwd()
    try:
        os.chdir(work)                       # contain MicroC's incidental outputs
        ctx = run_microc(seed=args.seed, n_steps=args.steps)
        snap = snapshot(ctx)
    finally:
        os.chdir(cwd)
    save_snapshot(snap, Path(args.out))
    print(f"[golden] run seed={args.seed} steps={args.steps} "
          f"cells={snap['meta']['n_cells']} -> {args.out}  ({time.time()-t0:.0f}s)")
    return 0


def _run_subprocess(out_dir: Path, seed: int, steps: int, hash_seed=None) -> None:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if hash_seed is not None:
        # Set a SPECIFIC hash seed. The determinism check uses two different
        # values to prove the run no longer depends on set/dict iteration order.
        env["PYTHONHASHSEED"] = str(hash_seed)
    subprocess.run([sys.executable, str(Path(__file__).resolve()),
                    "run", "--seed", str(seed), "--steps", str(steps),
                    "--out", str(out_dir)], check=True, env=env)


def _print_report(rep: Dict[str, Any]) -> None:
    print(f"\n[golden] OVERALL: {'MATCH' if rep['ok'] else 'DIVERGENCE'}")
    print("  fields:")
    for name, d in rep["fields"].items():
        if "max_abs" in d:
            print(f"    {name}: ok={d['ok']} max_abs={d['max_abs']:.3g} "
                  f"max_rel={d['max_rel']:.3g}")
        else:
            print(f"    {name}: {d}")
    c = rep["cells"]
    print(f"  cells: ok={c['ok']} n_ref={c['n_ref']} n_new={c['n_new']} "
          f"only_ref={c['only_in_ref']} only_new={c['only_in_new']} "
          f"state_diffs={c['state_diffs']}")
    if c["sample_diffs"]:
        print(f"    sample diffs: {c['sample_diffs']}")
    a = rep["aggregates"]
    print(f"  aggregates: ok={a['ok']}")
    if not a["ok"]:
        print(f"    ref={a['ref_phenotype_counts']}\n    new={a['new_phenotype_counts']}")


def _cmd_compare(args) -> int:
    rep = compare(load_snapshot(Path(args.ref)), load_snapshot(Path(args.new)),
                  field_rtol=args.field_rtol, field_atol=args.field_atol)
    _print_report(rep)
    return 0 if rep["ok"] else 1


def _cmd_determinism(args) -> int:
    """Run MicroC twice (fresh process each) with the same seed and compare."""
    base = Path(tempfile.mkdtemp(prefix="microc_determinism_"))
    a, b = base / "run_a", base / "run_b"
    print(f"[golden] determinism: two fresh runs seed={args.seed} steps={args.steps} "
          f"with DIFFERENT hash seeds (proves order-independence)")
    _run_subprocess(a, args.seed, args.steps, hash_seed=1)
    _run_subprocess(b, args.seed, args.steps, hash_seed=2)
    rep = compare(load_snapshot(a), load_snapshot(b),
                  field_rtol=0.0, field_atol=0.0)          # EXACT for determinism
    _print_report(rep)
    print(f"\n[golden] snapshots: {a}  |  {b}")
    return 0 if rep["ok"] else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="MicroC golden-reference harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="run once and write a snapshot")
    pr.add_argument("--seed", type=int, default=123)
    pr.add_argument("--steps", type=int, default=3)
    pr.add_argument("--out", required=True)
    pr.set_defaults(func=_cmd_run)

    pc = sub.add_parser("compare", help="compare two snapshot dirs")
    pc.add_argument("ref")
    pc.add_argument("new")
    pc.add_argument("--field-rtol", dest="field_rtol", type=float, default=0.0)
    pc.add_argument("--field-atol", dest="field_atol", type=float, default=0.0)
    pc.set_defaults(func=_cmd_compare)

    pd = sub.add_parser("determinism", help="two fresh runs, same seed, exact compare")
    pd.add_argument("--seed", type=int, default=123)
    pd.add_argument("--steps", type=int, default=3)
    pd.set_defaults(func=_cmd_determinism)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except Exception:
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
