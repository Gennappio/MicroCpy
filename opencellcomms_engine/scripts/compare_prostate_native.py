#!/usr/bin/env python3
"""Native PhysiBoSS prostate vs OpenCellComms engine comparison.

Parses the native output directory
(``output*.xml`` + ``*_cells.mat`` written by the running PhysiBoSS
prostate simulation), replays the same initial condition in the
OpenCellComms prostate adapter, and compares alive / apoptotic /
necrotic trajectories.

Intended to be run AFTER the native simulation finishes so that
``--native-dir`` contains the full output set.

Usage (defaults assume the standard layout of the repository):

    python scripts/compare_prostate_native.py \\
        [--native-dir PhysiBoSS-master/sample_projects_intracellular/\\
                      boolean/prostate/output] \\
        [--xml PhysiBoSS-master/sample_projects_intracellular/boolean/\\
                prostate/config/PhysiCell_settings_LNCaP.xml] \\
        [--save-csv compare_prostate.csv] \\
        [--save-plot compare_prostate.png] \\
        [--tolerance 0.15] \\
        [--checkpoints 0,1440,2880,5760,10080]
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import scipy.io

# Make the engine src importable without installing the package.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
# Make opencellcomms_adapters importable.
sys.path.insert(0, str(_HERE.parent.parent))

from src.adapters.physiboss.config_loader import (  # noqa: E402
    PhysiBossConfig, TimingConfig,
)
from src.adapters.physiboss.phenotype_mapper import (  # noqa: E402
    PhysiBossPhenotypeMapper,
)
from src.biology.cell_container import CellContainer  # noqa: E402
from opencellcomms_adapters.prostate.drug_sensitivity import (  # noqa: E402
    DRUG_TARGETS,
    anti_target_node_name,
)
from opencellcomms_adapters.prostate.functions.initialization.setup_prostate_params import (  # noqa: E402
    setup_prostate_params,
)
from opencellcomms_adapters.prostate.functions.intercellular.apply_prostate_boolean_effects import (  # noqa: E402
    apply_prostate_boolean_effects,
)
from src.workflow.functions.intercellular.update_cycle_physicell import (  # noqa: E402
    update_cycle_physicell,
)
from src.workflow.functions.intracellular.update_volume_physicell import (  # noqa: E402
    update_volume_physicell,
)
from src.workflow.functions.intercellular.update_death_physicell import (  # noqa: E402
    update_death_physicell,
)
from src.workflow.functions.diffusion.apply_secretion_physicell import (  # noqa: E402
    apply_secretion_physicell,
)
from src.workflow.functions.intercellular.physiboss_cell_division import (  # noqa: E402
    physiboss_cell_division,
)
from src.workflow.functions.intercellular.remove_flagged_cells import (  # noqa: E402
    remove_flagged_cells,
)
from opencellcomms_adapters.prostate.functions.intracellular.run_prostate_physiboss_step import (  # noqa: E402
    run_prostate_physiboss_step,
)

APOPTOSIS_DEATH_MODEL = 100
NECROSIS_DEATH_MODEL = 101


# ── Native output parsing ───────────────────────────────────────────────────

def _parse_labels(xml_path: Path) -> Dict[str, int]:
    root = ET.parse(xml_path).getroot()
    node = (root.find("cellular_information").find("cell_populations")
            .find("cell_population").find("custom"))
    for child in node.findall("simplified_data"):
        if child.get("source") == "PhysiCell":
            node = child
            break
    labels: Dict[str, int] = {}
    for lab in node.find("labels").findall("label"):
        name = lab.text.replace(" ", "_")
        size = int(lab.get("size"))
        idx = int(lab.get("index"))
        if size == 1:
            labels[name] = idx
        else:
            for i, sfx in enumerate(("_x", "_y", "_z")[:size]):
                labels[name + sfx] = idx + i
    return labels


def _classify_snapshot(xml_path: Path) -> Tuple[float, int, int, int, int]:
    labels = _parse_labels(xml_path)
    root = ET.parse(xml_path).getroot()
    t = float(root.find("metadata/current_time").text)
    mat_name = xml_path.with_name(xml_path.stem + "_cells.mat")
    cells = scipy.io.loadmat(mat_name)["cells"]
    total = cells.shape[1]
    cycle = cells[labels["cycle_model"]].astype(int)
    dead = cells[labels["dead"]].astype(bool)
    apop = int((dead & (cycle == APOPTOSIS_DEATH_MODEL)).sum())
    necro = int((dead & (cycle == NECROSIS_DEATH_MODEL)).sum())
    alive = int((~dead).sum())
    return t, total, alive, apop, necro


def parse_native_trajectory(output_dir: Path) -> pd.DataFrame:
    xmls = sorted(output_dir.glob("output*.xml"))
    if not xmls:
        raise FileNotFoundError(f"No output*.xml in {output_dir}")
    rows = []
    for x in xmls:
        t, total, alive, apop, necro = _classify_snapshot(x)
        rows.append({
            "time_min": t, "n_total": total,
            "n_alive": alive, "n_apoptotic": apop, "n_necrotic": necro,
        })
    return pd.DataFrame(rows).sort_values("time_min").reset_index(drop=True)


def load_initial_positions(output_dir: Path) -> np.ndarray:
    """Use the t=0 snapshot as initial condition (N, 2)."""
    xml0 = sorted(output_dir.glob("output*.xml"))[0]
    labels = _parse_labels(xml0)
    mat = scipy.io.loadmat(xml0.with_name(xml0.stem + "_cells.mat"))["cells"]
    x = mat[labels["position_x"]]
    y = mat[labels["position_y"]]
    return np.column_stack([x, y]).astype(np.float64)


# ── Engine replay ──────────────────────────────────────────────────────────

def _parse_drug_bath_from_xml(xml_path: Path,
                              drug_params: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Read <microenvironment_setup> to get the Dirichlet drug bath (absolute µM).

    Native code fetches a numeric concentration (or IC50 label) and applies it
    as a Dirichlet BC on the drug substance. We mirror the numeric branch.
    """
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    bath: Dict[str, float] = {}
    env = root.find(".//microenvironment_setup")
    if env is None:
        return bath
    for var in env.findall("variable"):
        name = var.get("name", "")
        if name == "oxygen" or name not in drug_params:
            continue
        dvec = var.find("./Dirichlet_boundary_condition")
        if dvec is not None and dvec.get("enabled", "false").lower() == "true":
            try:
                bath[name] = float(dvec.text.strip())
            except (TypeError, ValueError):
                bath[name] = 0.0
    return bath


def _prostate_mock_maboss(
    drug_bath: Dict[str, float],
    drug_params: Dict[str, Dict[str, float]],
    N: int, dt_min: float, rng: np.random.Generator,
) -> Dict[str, np.ndarray]:
    """Surrogate for the LNCaP MaBoSS cascade.

    The full Montagud 2022 network (150+ nodes) is replaced with a simple
    kernel: each step, for each cell, draw Bernoulli with probability
    proportional to the strongest drug inhibition present. The output
    probabilities are: Apoptosis (driven by any drug's inhibition),
    Proliferation (suppressed if any drug inhibits), Migration (unchanged).

    This is only an order-of-magnitude mock — for a faithful replica
    install pyMaBoSS and swap this for run_prostate_physiboss_step().
    """
    bn: Dict[str, np.ndarray] = {
        "Apoptosis": np.zeros(N),
        "Proliferation": np.ones(N),
        "Migration": np.zeros(N),
    }
    if not drug_bath:
        return bn
    max_inhibition = 0.0
    for drug, conc in drug_bath.items():
        if conc <= 0 or drug not in drug_params:
            continue
        p = drug_params[drug]
        x = np.log2(conc / p["max_conc"]) + 9.0
        viability = 1.0 / (1.0 + np.exp((x - p["xmid"]) / p["scale"]))
        max_inhibition = max(max_inhibition, float(1.0 - viability))
    p_apop_step = max_inhibition * (dt_min / 1440.0)
    bn["Apoptosis"] = (rng.random(N) < p_apop_step).astype(np.float64)
    bn["Proliferation"] = np.where(
        rng.random(N) < max_inhibition, 0.0, 1.0
    )
    return bn


def _load_maboss_sim_from_xml(xml_path: Path, sample_count: int = 1):
    """Load pyMaBoSS sim for the <intracellular> block of a PhysiCell XML."""
    import maboss
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    ic = root.find(".//intracellular")
    if ic is None:
        return None, None
    bnd_rel = ic.findtext("bnd_filename", "").strip()
    cfg_rel = ic.findtext("cfg_filename", "").strip()
    settings = ic.find("settings")
    intracellular_dt = 6.0
    scaling = 10.0
    if settings is not None:
        intracellular_dt = float(settings.findtext("intracellular_dt", "6.0"))
        scaling = float(settings.findtext("scaling", "10.0"))
    def _resolve(rel: str) -> Path:
        rel = rel.lstrip("./")
        # Native PhysiBoSS convention: paths are relative to the prostate
        # project root (one level up from the XML's config/ directory).
        candidates = [
            xml_path.parent.parent / rel,
            xml_path.parent / rel,
            Path(rel),
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
        return (xml_path.parent.parent / rel).resolve()

    bnd_path = _resolve(bnd_rel)
    cfg_path = _resolve(cfg_rel)
    if not bnd_path.exists() or not cfg_path.exists():
        raise FileNotFoundError(f"MaBoSS files not found: {bnd_path}, {cfg_path}")
    sim = maboss.load(str(bnd_path), str(cfg_path))
    sim.param["sample_count"] = sample_count
    sim.param["max_time"] = intracellular_dt / scaling
    sim.param["time_tick"] = sim.param["max_time"] / 10.0
    return sim, {"intracellular_dt": intracellular_dt, "scaling": scaling,
                 "bnd": str(bnd_path), "cfg": str(cfg_path)}


def run_engine_trajectory(xml_path: Path, initial_pos: np.ndarray,
                          max_time: float, save_interval: float,
                          seed: int = 0, use_real_maboss: bool = False,
                          maboss_sample_count: int = 1) -> pd.DataFrame:
    n_cells = initial_pos.shape[0]
    container = CellContainer(capacity=max(n_cells * 4, 1024), dimensions=2)
    container.add_cells(initial_pos, phenotype="Quiescent")
    for node in ("Apoptosis", "Proliferation", "Migration"):
        container.add_float_column(f"bn_prob_{node}", default=0.0)
        container.add_bool_column(f"bn_state_{node}", default=False)

    mapper = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
    ctx: Dict[str, object] = {
        "cell_container": container,
        "physiboss_phenotype_mapper": mapper,
        "physiboss_config": PhysiBossConfig(timing=TimingConfig(dt_phenotype=6.0)),
        "dimensions": 2,
        "current_step": 0,
    }
    setup_prostate_params(ctx, xml_path=str(xml_path))
    dt = ctx["physiboss_config"].timing.dt_phenotype or 6.0
    ctx["dt"] = dt
    drug_params = ctx.get("prostate_drug_params", {}) or {}
    drug_bath = _parse_drug_bath_from_xml(xml_path, drug_params)
    print(f"      drug bath (µM): {drug_bath or 'none'}")

    maboss_sim = None
    if use_real_maboss:
        maboss_sim, mb_info = _load_maboss_sim_from_xml(
            xml_path, sample_count=maboss_sample_count
        )
        if maboss_sim is None:
            print("      WARNING: <intracellular> block not found in XML; "
                  "falling back to mock MaBoSS.")
            use_real_maboss = False
        else:
            ctx["maboss_sim"] = maboss_sim
            print(f"      real MaBoSS: {Path(mb_info['bnd']).name} "
                  f"(dt={mb_info['intracellular_dt']} min, "
                  f"scaling={mb_info['scaling']}, "
                  f"sample_count={maboss_sample_count}, "
                  f"nodes={len(maboss_sim.network)})")

    rng = np.random.default_rng(seed)
    rows = [_record_row(container, 0.0)]
    t = 0.0
    next_save = save_interval
    step = 0
    while t < max_time - 1e-9:
        N = container.count
        if N == 0:
            break
        if use_real_maboss:
            run_prostate_physiboss_step(ctx)
        else:
            bn_out = _prostate_mock_maboss(drug_bath, drug_params, N, dt, rng)
            for node, arr in bn_out.items():
                container.get_float(f"bn_prob_{node}")[:N] = arr
                container.get_bool(f"bn_state_{node}")[:N] = arr >= 0.5
        apply_prostate_boolean_effects(ctx)
        # PhysiCell "Core Four" phenotype kernels
        update_cycle_physicell(ctx, dt=dt)
        update_volume_physicell(ctx, dt=dt)
        update_death_physicell(ctx, dt=dt)
        apply_secretion_physicell(ctx, dt=dt)
        # Division + cleanup of flagged cells
        physiboss_cell_division(ctx)
        remove_flagged_cells(ctx)
        step += 1
        ctx["current_step"] = step
        t += dt
        if t + 1e-9 >= next_save:
            rows.append(_record_row(container, t))
            next_save += save_interval
    return pd.DataFrame(rows)


def _record_row(container: CellContainer, t: float) -> Dict[str, float]:
    counts = container.phenotype_counts()
    apop = counts.get("apoptotic", 0)
    necro = counts.get("necrotic", 0)
    alive = sum(v for k, v in counts.items() if k not in ("apoptotic", "necrotic"))
    return {
        "time_min": t,
        "n_total": int(container.count),
        "n_alive": int(alive),
        "n_apoptotic": int(apop),
        "n_necrotic": int(necro),
    }


# ── Comparison / reporting ─────────────────────────────────────────────────

def compare_trajectories(native: pd.DataFrame, engine: pd.DataFrame,
                         checkpoints: List[float]) -> pd.DataFrame:
    rows = []
    for t in checkpoints:
        n = _interp_row(native, t)
        e = _interp_row(engine, t)
        rows.append({
            "t_min": t,
            **{f"native_{k}": n[k] for k in ("n_alive", "n_apoptotic", "n_necrotic")},
            **{f"engine_{k}": e[k] for k in ("n_alive", "n_apoptotic", "n_necrotic")},
            "alive_pct_err": _pct_err(n["n_alive"], e["n_alive"]),
            "apop_pct_err":  _pct_err(n["n_apoptotic"], e["n_apoptotic"]),
            "necro_pct_err": _pct_err(n["n_necrotic"], e["n_necrotic"]),
        })
    return pd.DataFrame(rows)


def _interp_row(df: pd.DataFrame, t: float) -> Dict[str, float]:
    ts = df["time_min"].to_numpy()
    if t <= ts[0]:
        return df.iloc[0].to_dict()
    if t >= ts[-1]:
        return df.iloc[-1].to_dict()
    out: Dict[str, float] = {"time_min": t}
    for col in ("n_total", "n_alive", "n_apoptotic", "n_necrotic"):
        out[col] = float(np.interp(t, ts, df[col].to_numpy()))
    return out


def _pct_err(native: float, engine: float) -> float:
    return 100.0 * abs(engine - native) / max(native, 1.0)


def _format_table(cmp: pd.DataFrame, tol_pct: float) -> str:
    lines = []
    header = (f"{'t_min':>7} | {'alive (N/E)':>20} {'apop (N/E)':>20} "
              f"{'necro (N/E)':>20} | {'alive%':>7} {'apop%':>7} {'necro%':>7}")
    lines.append(header)
    lines.append("-" * len(header))
    for _, r in cmp.iterrows():
        worst = max(r["alive_pct_err"], r["apop_pct_err"], r["necro_pct_err"])
        mark = "  OK " if worst <= tol_pct * 100 else " FAIL"
        lines.append(
            f"{r['t_min']:>7.0f} | "
            f"{int(r['native_n_alive']):>8d}/{int(r['engine_n_alive']):>8d}     "
            f"{int(r['native_n_apoptotic']):>8d}/{int(r['engine_n_apoptotic']):>8d}     "
            f"{int(r['native_n_necrotic']):>8d}/{int(r['engine_n_necrotic']):>8d}  | "
            f"{r['alive_pct_err']:>6.1f}  {r['apop_pct_err']:>6.1f}  "
            f"{r['necro_pct_err']:>6.1f}  {mark}"
        )
    return "\n".join(lines)


def _maybe_plot(native: pd.DataFrame, engine: pd.DataFrame, out_path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available - skipping plot.")
        return
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharex=True)
    for ax, col, title in zip(axes, ("n_alive", "n_apoptotic", "n_necrotic"),
                              ("Alive", "Apoptotic", "Necrotic")):
        ax.plot(native["time_min"], native[col], label="native", lw=2)
        ax.plot(engine["time_min"], engine[col], label="engine", lw=2, ls="--")
        ax.set_xlabel("time (min)")
        ax.set_title(title)
        ax.grid(alpha=0.3)
        ax.legend()
    fig.suptitle("PhysiBoSS prostate (native) vs OpenCellComms engine")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    print(f"Plot saved to {out_path}")


def main() -> int:
    default_root = _HERE.resolve().parents[2]
    default_native = (default_root / "PhysiBoSS-master"
                      / "sample_projects_intracellular" / "boolean"
                      / "prostate" / "output")
    default_xml = (default_root / "PhysiBoSS-master"
                   / "sample_projects_intracellular" / "boolean" / "prostate"
                   / "config" / "PhysiCell_settings_LNCaP.xml")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-dir", type=Path, default=default_native)
    p.add_argument("--xml", type=Path, default=default_xml)
    p.add_argument("--save-csv", type=Path, default=None)
    p.add_argument("--save-plot", type=Path, default=None)
    p.add_argument("--tolerance", type=float, default=0.15,
                   help="Per-metric tolerance as a fraction (default 0.15 = 15%%)")
    p.add_argument("--checkpoints", type=str,
                   default="0,1440,2880,5760,10080",
                   help="Checkpoints in minutes (default: 0,1d,2d,4d,7d)")
    p.add_argument("--save-interval", type=float, default=60.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--real-maboss", action="store_true",
                   help="Use pyMaBoSS with the full LNCaP BN instead of the mock surrogate.")
    p.add_argument("--maboss-sample-count", type=int, default=1,
                   help="MaBoSS sample_count per cell per step (default 1).")
    p.add_argument("--max-time", type=float, default=None,
                   help="Truncate engine replay to this duration in minutes "
                        "(default: use full native trajectory length).")
    args = p.parse_args()

    if not args.native_dir.exists():
        print(f"ERROR: --native-dir does not exist: {args.native_dir}", file=sys.stderr)
        return 1
    if not args.xml.exists():
        print(f"ERROR: --xml does not exist: {args.xml}", file=sys.stderr)
        return 1

    print(f"[1/3] Parsing native trajectory from {args.native_dir} ...")
    native = parse_native_trajectory(args.native_dir)
    print(f"      {len(native)} snapshots, t=[{native['time_min'].min():.0f},"
          f"{native['time_min'].max():.0f}] min; N0={int(native.iloc[0]['n_total'])}")

    initial_pos = load_initial_positions(args.native_dir)
    max_time = float(native["time_min"].max())
    if args.max_time is not None:
        max_time = min(max_time, float(args.max_time))
    print(f"[2/3] Engine replay for {max_time:.0f} min "
          f"({initial_pos.shape[0]} cells from native t=0 snapshot) "
          f"[BN: {'real MaBoSS' if args.real_maboss else 'mock'}] ...")
    engine = run_engine_trajectory(args.xml, initial_pos,
                                   max_time=max_time,
                                   save_interval=args.save_interval,
                                   seed=args.seed,
                                   use_real_maboss=args.real_maboss,
                                   maboss_sample_count=args.maboss_sample_count)
    print(f"      {len(engine)} snapshots recorded")

    print("[3/3] Comparing trajectories at checkpoints ...")
    checkpoints = [float(x) for x in args.checkpoints.split(",") if x.strip()]
    cmp = compare_trajectories(native, engine, checkpoints)
    print()
    print(_format_table(cmp, args.tolerance))

    worst = float(max(cmp[["alive_pct_err", "apop_pct_err", "necro_pct_err"]].max()))
    print()
    print(f"Worst-case error: {worst:.1f}%% (tolerance: {args.tolerance * 100:.0f}%%)")
    status = "PASS" if worst <= args.tolerance * 100 else "FAIL"
    print(f"Overall: {status}")

    print()
    print("Known fidelity gaps:")
    print("  * The LNCaP MaBoSS cascade (~150 nodes) is replaced here with a")
    print("    simple surrogate driven only by the strongest drug inhibition.")
    print("    For bit-parity, install pyMaBoSS and switch run_engine_trajectory")
    print("    to call run_prostate_physiboss_step() with the real .bnd/.cfg.")
    print("  * Cell division / migration trajectories are not modelled here")
    print("    (only fate counts). Migration node drives motility columns but")
    print("    positions don't evolve in this reduced replay.")
    print("  * Dirichlet drug bath is parsed from XML but drug decay/diffusion")
    print("    is not solved; drug concentration is taken constant.")

    if args.save_csv:
        native["source"] = "native"
        engine["source"] = "engine"
        pd.concat([native, engine], ignore_index=True).to_csv(
            args.save_csv, index=False
        )
        print(f"Trajectories saved to {args.save_csv}")
    if args.save_plot:
        _maybe_plot(native, engine, args.save_plot)

    return 0 if worst <= args.tolerance * 100 else 2


if __name__ == "__main__":
    sys.exit(main())
