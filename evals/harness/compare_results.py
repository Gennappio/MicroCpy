"""Compare simulation *results* — the second comparator the harness needs.

This is a model-agnostic generalization of ``tools/migration/microc_golden.py``
(whose ``snapshot`` is hardwired to the MicroC-shaped context). It keeps that
file's hard-won determinism discipline verbatim — the three footguns are not
optional:

  1. ``workflow.seed`` only fixes ENTITY ITERATION ORDER; the biology draws from
     the global ``random`` / ``numpy.random`` streams, so we seed those too.
  2. Division daughters get non-seedable ``uuid4`` ids -> cells are keyed by
     POSITION, never id.
  3. Global RNG state carries across in-process runs -> every ``run`` is a fresh
     process (the ``run`` subcommand is the unit; ``compare`` / ``determinism``
     spawn one process per run).

Two comparison regimes, deliberately distinct (plan, Behavior axis):
  * **determinism / regression** — same code, same seed -> identical snapshot.
    EXACT (rtol=atol=0). This reuses the full snapshot depth (fields + per-cell
    state + aggregates).
  * **observable agreement** — a *regenerated* model will NOT match the benchmark
    bit-exact (a different node decomposition draws RNG in a different order), so
    cross-implementation comparison is aggregate/trajectory-level, checked against
    the plain-language Observables in MODEL.md. Never bit-exact across
    implementations.

CLI:
    python -m evals.harness.compare_results run --workflow W --seed S --steps N --out DIR
    python -m evals.harness.compare_results compare REF NEW [--field-rtol R --field-atol A]
    python -m evals.harness.compare_results determinism --workflow W --seed S --steps N
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
from typing import Any, Dict, List, Optional

import numpy as np

from evals.harness import _engine as E

# Per-cell state fields compared exactly (present-only; absent on a model is fine).
_DEFAULT_STATE_FIELDS = ("phenotype", "gene_states", "gene_network", "division_count", "metabolic_state")


# ------------------------------------------------------------------------- snapshot
def snapshot(context: Dict[str, Any]) -> Dict[str, Any]:
    """Extract comparable state from a finished run, defensively — any model.

    Captures substance fields (if a simulator is present), per-cell state keyed
    by position (phenotype / gene states / gene network / ABM ``metabolic_state``
    traits, whichever exist), population + substance aggregates, and the
    ``env.record`` time-series buffer."""
    snap: Dict[str, Any] = {"substances": {}, "cells": {}, "records": {},
                            "population_stats": {}, "substance_stats": {}, "meta": {}}

    snap["substances"] = _extract_fields(context)
    snap["cells"], snap["population_stats"] = _extract_cells(context)

    sim = context.get("simulator")
    if sim is not None:
        try:
            snap["substance_stats"] = sim.get_summary_statistics()
        except Exception:
            pass

    snap["records"] = context.get("_records", {}) or {}
    snap["meta"] = {"n_cells": len(snap["cells"]), "n_substances": len(snap["substances"])}
    return snap


def _extract_fields(context: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """Substance/resource fields from either representation: the legacy simulator
    (``simulator.state.substances``, MicroC) or the ABM domain
    (``domain.resources()``, SUGARSCAPE)."""
    fields: Dict[str, np.ndarray] = {}
    sim = context.get("simulator")
    if sim is not None and getattr(sim, "state", None) is not None:
        for n, s in (getattr(sim.state, "substances", {}) or {}).items():
            if hasattr(s, "concentrations"):
                fields[n] = np.asarray(s.concentrations, dtype=float).copy()
    dom = context.get("domain")
    if dom is not None and hasattr(dom, "resources"):
        for r in dom.resources():
            arr = _field_array(r)
            if arr is not None:
                fields.setdefault(getattr(r, "name", f"resource_{len(fields)}"), arr)
    return fields


def _field_array(resource) -> Optional[np.ndarray]:
    """The 2D field of an ABM Resource, tolerant of ``values`` being a property or
    a method across Resource variants."""
    for attr in ("values", "_values", "concentrations"):
        v = getattr(resource, attr, None)
        if v is None:
            continue
        if callable(v):
            try:
                v = v()
            except Exception:
                continue
        try:
            return np.asarray(v, dtype=float).copy()
        except (TypeError, ValueError):
            continue
    return None


def _cellpop(context: Dict[str, Any]):
    """The CellPopulation, from the raw key (MicroC) or wrapped in the ABM
    Population (SUGARSCAPE: ``abm_population.cellpop``)."""
    pop = context.get("population")
    if pop is not None and getattr(pop, "state", None) is not None:
        return pop
    ap = context.get("abm_population")
    cp = getattr(ap, "cellpop", None)
    if cp is not None and getattr(cp, "state", None) is not None:
        return cp
    return None


def _extract_cells(context: Dict[str, Any]):
    """Per-cell state keyed by position, from whichever population representation
    exists. Returns ``(cells, population_stats)``."""
    cells: Dict[str, Any] = {}
    pop = _cellpop(context)
    if pop is None:
        return cells, {}
    nets = context.get("gene_networks", {}) or {}
    for cid, c in pop.state.cells.items():
        st = c.state
        key = ",".join(str(int(v)) for v in st.position)  # "x,y" — JSON-safe, id-free
        net = nets.get(cid)
        cells[key] = {
            "position": [int(v) for v in st.position],
            "phenotype": getattr(st, "phenotype", None),
            "gene_states": {k: bool(v) for k, v in dict(getattr(st, "gene_states", {}) or {}).items()},
            "gene_network": (None if net is None
                             else {k: bool(v) for k, v in net.get_all_states().items()}),
            "division_count": int(getattr(st, "division_count", 0) or 0),
            "metabolic_state": _scalar_only(getattr(st, "metabolic_state", {}) or {}),
        }
    stats = {}
    try:
        stats = pop.get_population_statistics()
    except Exception:
        pass
    return cells, stats


def _scalar_only(d: dict) -> dict:
    """Keep JSON-safe scalar traits (sugar, vision, metabolism); drop objects and
    the private ``_kind`` / ``_dead`` bookkeeping keys used by the ABM layer."""
    out = {}
    for k, v in d.items():
        if k.startswith("_"):
            continue
        if isinstance(v, (int, float, bool, str)) or v is None:
            out[k] = v
        elif isinstance(v, (np.integer, np.floating)):
            out[k] = float(v)
    return out


# ------------------------------------------------------------------------- persistence
def save_snapshot(snap: Dict[str, Any], out_dir) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_dir / "substances.npz", **snap["substances"])
    payload = {k: snap[k] for k in ("cells", "records", "population_stats", "substance_stats", "meta")}
    with gzip.open(out_dir / "snapshot.json.gz", "wt", encoding="utf-8") as f:
        json.dump(payload, f, sort_keys=True, default=_json_default)


def load_snapshot(in_dir) -> Dict[str, Any]:
    in_dir = Path(in_dir)
    with np.load(in_dir / "substances.npz") as z:
        substances = {k: z[k] for k in z.files}
    with gzip.open(in_dir / "snapshot.json.gz", "rt", encoding="utf-8") as f:
        rest = json.load(f)
    rest["substances"] = substances
    return rest


def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# ------------------------------------------------------------------------- compare
def compare(ref: Dict[str, Any], new: Dict[str, Any],
            field_rtol: float = 0.0, field_atol: float = 0.0,
            state_fields=_DEFAULT_STATE_FIELDS) -> Dict[str, Any]:
    """Four-level diff: substance fields (numeric, tolerant), cells (exact, by
    position, over ``state_fields``), aggregates, records/trajectories. Returns a
    report dict with ``ok``. Default tolerance is EXACT (determinism); loosen for
    cross-implementation comparison."""
    report: Dict[str, Any] = {"ok": True, "fields": {}, "cells": {}, "aggregates": {}, "records": {}}

    # --- substance fields ---
    ref_s, new_s = ref.get("substances", {}), new.get("substances", {})
    if set(ref_s) != set(new_s):
        report["ok"] = False
        report["fields"]["substance_set_mismatch"] = {"ref": sorted(ref_s), "new": sorted(new_s)}
    for name in sorted(set(ref_s) & set(new_s)):
        a, b = np.asarray(ref_s[name], float), np.asarray(new_s[name], float)
        if a.shape != b.shape:
            report["ok"] = False
            report["fields"][name] = {"ok": False, "reason": "shape",
                                      "ref_shape": list(a.shape), "new_shape": list(b.shape)}
            continue
        absd = np.abs(a - b)
        denom = np.maximum(np.abs(a), np.abs(b))
        reld = np.divide(absd, denom, out=np.zeros_like(absd), where=denom > 0)
        ok = bool(np.allclose(a, b, rtol=field_rtol, atol=field_atol))
        report["fields"][name] = {"ok": ok, "max_abs": float(absd.max()), "max_rel": float(reld.max())}
        report["ok"] &= ok

    # --- cells (exact, by position) ---
    ref_c, new_c = ref.get("cells", {}), new.get("cells", {})
    only_ref = sorted(set(ref_c) - set(new_c))
    only_new = sorted(set(new_c) - set(ref_c))
    diffs = []
    for key in sorted(set(ref_c) & set(new_c)):
        r, n = ref_c[key], new_c[key]
        for field in state_fields:
            if r.get(field) != n.get(field):
                diffs.append({"pos": key, "field": field})
                break
    cells_ok = not (only_ref or only_new or diffs)
    report["cells"] = {"ok": cells_ok, "n_ref": len(ref_c), "n_new": len(new_c),
                       "only_in_ref": len(only_ref), "only_in_new": len(only_new),
                       "state_diffs": len(diffs), "sample_diffs": diffs[:5],
                       "sample_only_ref": only_ref[:5], "sample_only_new": only_new[:5]}
    report["ok"] &= cells_ok

    # --- aggregates (phenotype counts) ---
    rp = (ref.get("population_stats") or {}).get("phenotype_counts")
    npc = (new.get("population_stats") or {}).get("phenotype_counts")
    report["aggregates"] = {"ok": rp == npc, "ref_phenotype_counts": rp, "new_phenotype_counts": npc}
    report["ok"] &= (rp == npc)

    # --- records / trajectories (final value per key; tolerant) ---
    ref_r, new_r = ref.get("records", {}), new.get("records", {})
    for key in sorted(set(ref_r) | set(new_r)):
        rv = _final(ref_r.get(key)), _final(new_r.get(key))
        if rv[0] is None or rv[1] is None:
            report["records"][key] = {"ok": False, "reason": "missing", "ref": rv[0], "new": rv[1]}
            report["ok"] = False
        else:
            ok = bool(np.isclose(rv[0], rv[1], rtol=max(field_rtol, 1e-9), atol=field_atol))
            report["records"][key] = {"ok": ok, "ref_final": rv[0], "new_final": rv[1]}
            report["ok"] &= ok
    return report


def _final(series: Optional[List[dict]]):
    if not series:
        return None
    try:
        return float(series[-1]["value"])
    except (KeyError, TypeError, ValueError):
        return None


# ------------------------------------------------------------------------- observables
def check_observables(snap: Dict[str, Any], observables: List[dict]) -> List[dict]:
    """Evaluate the plain-language Observables recorded in MODEL.md against a run.

    Only the mechanical checks are decided here (population extinction, a field
    reaching non-trivial values, a record's monotonic-then-flat "steady state"
    shape). Genuinely semantic observables carry ``verdict: "needs_llm"`` with the
    evidence attached, for the reviewer / LLM judge — the harness never silently
    passes what it can't actually check."""
    results = []
    for obs in observables:
        kind = obs.get("check")
        target = obs.get("target")
        r = {"observable": obs.get("text", obs), "check": kind, "target": target, "verdict": "needs_llm"}
        if kind == "population_survives":
            n = snap.get("meta", {}).get("n_cells", 0)
            r.update(verdict="pass" if n > 0 else "fail", evidence=f"n_cells={n}")
        elif kind == "population_extinct":
            n = snap.get("meta", {}).get("n_cells", 0)
            r.update(verdict="pass" if n == 0 else "fail", evidence=f"n_cells={n}")
        elif kind == "field_nontrivial" and target in snap.get("substances", {}):
            arr = np.asarray(snap["substances"][target], float)
            spread = float(arr.max() - arr.min())
            r.update(verdict="pass" if spread > 0 else "fail",
                     evidence=f"{target} range={spread:.3g}")
        elif kind == "record_steady_state" and target in snap.get("records", {}):
            r.update(_steady_state(snap["records"][target]))
        results.append(r)
    return results


def _steady_state(series: List[dict]) -> dict:
    """Heuristic: rises (or moves) then flattens — the common 'reaches steady
    state' observable. A weak signal by design; a borderline call is left to the
    LLM judge rather than asserted."""
    vals = [e.get("value") for e in (series or []) if isinstance(e.get("value"), (int, float))]
    if len(vals) < 4:
        return {"verdict": "needs_llm", "evidence": f"too few points ({len(vals)})"}
    tail = vals[-max(2, len(vals) // 5):]
    spread = (max(vals) - min(vals)) or 1.0
    tail_var = (max(tail) - min(tail)) / spread
    return {"verdict": "pass" if tail_var < 0.05 else "needs_llm",
            "evidence": f"tail_variation={tail_var:.3f} over {len(vals)} points"}


# ------------------------------------------------------------------------- run
def run_workflow_snapshot(workflow_path: str, seed: int, steps: int) -> Dict[str, Any]:
    """Run a workflow in-process (seed the globals!) and snapshot the final
    context. MUST be called in a fresh process for determinism (footgun 3)."""
    random.seed(seed)
    np.random.seed(seed)
    from src.workflow.loader import WorkflowLoader
    from src.workflow.executor import WorkflowExecutor

    wf = WorkflowLoader.load(workflow_path)
    wf.seed = seed
    for call in wf.subworkflows["main"].subworkflow_calls:
        if call.subworkflow_name == "__scheduler__":
            call.iterations = int(steps)
    executor = WorkflowExecutor(wf, workflow_file=str(workflow_path), observability_enabled=False)
    context = {"workflow_file": str(Path(workflow_path).absolute())}
    return executor.execute_main(context, entry_subworkflow="main")


# ------------------------------------------------------------------------- CLI
def _cmd_run(args) -> int:
    t0 = time.time()
    # Absolutize BEFORE chdir — the run below chdirs into a temp dir to contain
    # the workflow's incidental outputs, which would break a relative path.
    workflow_abs = str(Path(args.workflow).resolve())
    out_abs = str(Path(args.out).resolve())
    work = Path(tempfile.mkdtemp(prefix="occ_run_"))
    cwd = os.getcwd()
    try:
        os.chdir(work)
        ctx = run_workflow_snapshot(workflow_abs, args.seed, args.steps)
        snap = snapshot(ctx)
    finally:
        os.chdir(cwd)
    save_snapshot(snap, Path(out_abs))
    print(f"[results] {Path(args.workflow).name} seed={args.seed} steps={args.steps} "
          f"cells={snap['meta']['n_cells']} subs={snap['meta']['n_substances']} "
          f"-> {args.out}  ({time.time()-t0:.0f}s)")
    return 0


def _run_subprocess(out_dir, workflow, seed, steps, hash_seed=None) -> None:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if hash_seed is not None:
        env["PYTHONHASHSEED"] = str(hash_seed)
    subprocess.run([sys.executable, "-m", "evals.harness.compare_results", "run",
                    "--workflow", str(Path(workflow).resolve()), "--seed", str(seed),
                    "--steps", str(steps), "--out", str(Path(out_dir).resolve())],
                   check=True, env=env, cwd=str(E.REPO_ROOT))


def _print_report(rep: Dict[str, Any]) -> None:
    print(f"\n[results] OVERALL: {'MATCH' if rep['ok'] else 'DIVERGENCE'}")
    for name, d in rep["fields"].items():
        if "max_abs" in d:
            print(f"  field {name}: ok={d['ok']} max_abs={d['max_abs']:.3g} max_rel={d['max_rel']:.3g}")
        else:
            print(f"  field {name}: {d}")
    c = rep["cells"]
    print(f"  cells: ok={c['ok']} n_ref={c['n_ref']} n_new={c['n_new']} "
          f"only_ref={c['only_in_ref']} only_new={c['only_in_new']} diffs={c['state_diffs']}")
    if c["sample_diffs"]:
        print(f"    sample: {c['sample_diffs']}")
    print(f"  aggregates: ok={rep['aggregates']['ok']}")
    for k, d in rep["records"].items():
        print(f"  record {k}: {d}")


def _cmd_compare(args) -> int:
    rep = compare(load_snapshot(args.ref), load_snapshot(args.new),
                  field_rtol=args.field_rtol, field_atol=args.field_atol)
    _print_report(rep)
    return 0 if rep["ok"] else 1


def _cmd_determinism(args) -> int:
    base = Path(tempfile.mkdtemp(prefix="occ_determinism_"))
    a, b = base / "a", base / "b"
    print(f"[results] determinism: two fresh runs of {Path(args.workflow).name} "
          f"seed={args.seed} steps={args.steps}, DIFFERENT hash seeds")
    _run_subprocess(a, args.workflow, args.seed, args.steps, hash_seed=1)
    _run_subprocess(b, args.workflow, args.seed, args.steps, hash_seed=2)
    rep = compare(load_snapshot(a), load_snapshot(b))  # EXACT
    _print_report(rep)
    print(f"\n[results] snapshots: {a}  |  {b}")
    return 0 if rep["ok"] else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Compare simulation results (any workflow).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run")
    pr.add_argument("--workflow", required=True)
    pr.add_argument("--seed", type=int, default=123)
    pr.add_argument("--steps", type=int, default=3)
    pr.add_argument("--out", required=True)
    pr.set_defaults(func=_cmd_run)

    pc = sub.add_parser("compare")
    pc.add_argument("ref")
    pc.add_argument("new")
    pc.add_argument("--field-rtol", dest="field_rtol", type=float, default=0.0)
    pc.add_argument("--field-atol", dest="field_atol", type=float, default=0.0)
    pc.set_defaults(func=_cmd_compare)

    pd = sub.add_parser("determinism")
    pd.add_argument("--workflow", required=True)
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
