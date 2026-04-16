#!/usr/bin/env python3
"""
Phase 3.5–3.7 — Native PhysiBoSS vs OpenCellComms comparison.

Parses the native PhysiBoSS output directory (``output*.xml`` + ``*_cells.mat``),
replays the same initial condition in the OpenCellComms PhysiBoss adapter,
and prints / plots alive / apoptotic / necrotic trajectories side by side.

Usage:
    python scripts/compare_native_physiboss.py \
        [--native-dir PhysiBoSS-master/output] \
        [--xml  PhysiBoSS-master/output/1_Long_TNF.xml] \
        [--cells-csv  PhysiBoSS-master/sample_projects_intracellular/\
                      boolean/tutorial/config/simple_tnf/cells.csv] \
        [--save-csv compare.csv] [--save-plot compare.png] \
        [--tolerance 0.10] [--checkpoints 0,2500,5000,7500,10000]
"""
from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import scipy.io

# Make the engine src importable without installing the package
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from src.adapters.physiboss.config_loader import (  # noqa: E402
    InputMapping,
    OutputMapping,
    PhysiBossConfigLoader,
)
from src.adapters.physiboss.coupling import PhysiBossSubstrateCoupling  # noqa: E402
from src.adapters.physiboss.phenotype_mapper import (  # noqa: E402
    PhysiBossPhenotypeMapper,
)
from src.biology.cell_container import CellContainer  # noqa: E402

# PhysiCell death-model codes (from core/PhysiCell_constants.cpp)
APOPTOSIS_DEATH_MODEL = 100
NECROSIS_DEATH_MODEL = 101


# ─── Native-output parsing ──────────────────────────────────────────────────

def _parse_labels(xml_path: Path) -> dict:
    """Return {attribute_name: row_index} mapping for the cells.mat matrix."""
    root = ET.parse(xml_path).getroot()
    node = root.find("cellular_information").find("cell_populations").find(
        "cell_population").find("custom")
    for child in node.findall("simplified_data"):
        if child.get("source") == "PhysiCell":
            node = child
            break
    labels = {}
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
    """Return (time, total, alive, apoptotic, necrotic) for one snapshot."""
    labels = _parse_labels(xml_path)
    root = ET.parse(xml_path).getroot()
    t = float(root.find("metadata/current_time").text)
    mat_name = xml_path.with_name(xml_path.stem + "_cells.mat")
    cells = scipy.io.loadmat(mat_name)["cells"]  # shape: (rows, n_cells)
    total = cells.shape[1]
    cycle = cells[labels["cycle_model"]].astype(int)
    dead = cells[labels["dead"]].astype(bool)
    apop = int((dead & (cycle == APOPTOSIS_DEATH_MODEL)).sum())
    necro = int((dead & (cycle == NECROSIS_DEATH_MODEL)).sum())
    alive = int((~dead).sum())
    return t, total, alive, apop, necro


def parse_native_trajectory(output_dir: Path) -> pd.DataFrame:
    """Parse all output*.xml in `output_dir` and return a time-series DataFrame."""
    xmls = sorted(output_dir.glob("output*.xml"))
    if not xmls:
        raise FileNotFoundError(f"No output*.xml files in {output_dir}")
    rows = []
    for x in xmls:
        t, total, alive, apop, necro = _classify_snapshot(x)
        rows.append({
            "time_min": t,
            "n_total": total,
            "n_alive": alive,
            "n_apoptotic": apop,
            "n_necrotic": necro,
        })
    return pd.DataFrame(rows).sort_values("time_min").reset_index(drop=True)


# ─── cells.csv loader ───────────────────────────────────────────────────────

def load_cells_csv(csv_path: Path) -> np.ndarray:
    """Return (N, 2) array of initial (x, y) positions from a PhysiCell cells.csv."""
    df = pd.read_csv(csv_path)
    # Accept both formats: with or without header
    if "x" in df.columns and "y" in df.columns:
        return df[["x", "y"]].to_numpy(dtype=np.float64)
    # Headerless: assume first three columns are x, y, z
    arr = np.loadtxt(csv_path, delimiter=",", skiprows=0, dtype=np.float64)
    return arr[:, :2]


# ─── Engine replay ──────────────────────────────────────────────────────────

def _simulate_tnf_boolean_mock(tnf_on: np.ndarray, dt_min: float,
                                rng: np.random.Generator,
                                apop_per_day: float = 0.35,
                                nonacd_per_day: float = 0.65
                                ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Per-cell binary surrogate for the MaBoSS TNF cellfate model.

    The native `cellfate.bnd` cascade (TNF -> IKK -> NFkB -> ... -> Apoptosis /
    NonACD, `intracellular_dt=1440 min`) is replaced here with a per-step
    Bernoulli draw: while TNF is ON, each cell turns the `Apoptosis` or
    `NonACD` output node ON with a per-day probability calibrated so the
    aggregate kill dynamics approximate the reference 1_Long_TNF trajectory
    (~65 %% NonACD / ~35 %% Apoptosis under sustained TNF bath).

    Once an output node turns ON, the coupling -> mapper pipeline converts it
    into ``rate = 1e6`` for the matching phenotype behaviour (apoptosis /
    necrosis), which effectively kills the cell on the next phenotype step.

    Returns (bn_apop, bn_nonacd) arrays of length N containing 0.0/1.0.
    """
    N = tnf_on.shape[0]
    # Convert per-day probabilities to per-step probabilities (Poisson).
    p_apop_step = 1.0 - np.exp(-apop_per_day * dt_min / 1440.0)
    p_nonacd_step = 1.0 - np.exp(-nonacd_per_day * dt_min / 1440.0)
    draw = rng.random((2, N))
    bn_apop = np.where(tnf_on & (draw[0] < p_apop_step), 1.0, 0.0)
    bn_nonacd = np.where(tnf_on & (draw[1] < p_nonacd_step), 1.0, 0.0)
    return bn_apop, bn_nonacd



def run_engine_trajectory(xml_path: Path, cells_csv: Path,
                          max_time: float, save_interval: float,
                          seed: int = 0) -> pd.DataFrame:
    """
    Replay the same scenario in the OpenCellComms PhysiBoss adapter.

    TNF is modelled as a constant bath matching the XML's Dirichlet BC
    (the boundary value dominates the interior concentration since the
    domain is small and `decay_rate` is applied uniformly).
    """
    cfg = PhysiBossConfigLoader(str(xml_path)).load()
    dt_pheno = cfg.timing.dt_phenotype or 6.0
    tnf_sub = next((s for s in cfg.substrates if s.name.upper() == "TNF"), None)
    tnf_bath = (tnf_sub.dirichlet.value
                if tnf_sub and tnf_sub.dirichlet and tnf_sub.dirichlet.enabled
                else 10.0)

    positions = load_cells_csv(cells_csv)
    n_cells = positions.shape[0]

    container = CellContainer(capacity=max(n_cells * 4, 1024), dimensions=2)
    container.add_cells(positions, phenotype="Quiescent")
    container.add_float_column("bn_prob_Apoptosis", default=0.0)
    container.add_float_column("bn_prob_NonACD", default=0.0)

    coupling = PhysiBossSubstrateCoupling(
        inputs=[InputMapping(substance_name="TNF", node_name="TNF",
                             threshold=1.0, action="activation")],
        outputs=[
            OutputMapping(node_name="Apoptosis", behaviour_name="apoptosis",
                          value=1e6, base_value=0.0, action="activation"),
            OutputMapping(node_name="NonACD", behaviour_name="necrosis",
                          value=1e6, base_value=0.0, action="activation"),
        ],
    )
    mapper = PhysiBossPhenotypeMapper(dt_phenotype=dt_pheno)
    rng = np.random.default_rng(seed)

    from src.workflow.functions.intercellular.apply_physiboss_phenotype import (
        apply_physiboss_phenotype,
    )
    from src.adapters.physiboss.config_loader import (
        PhysiBossConfig, TimingConfig,
    )

    ctx = {
        "cell_container": container,
        "physiboss_coupling": coupling,
        "physiboss_phenotype_mapper": mapper,
        "physiboss_config": PhysiBossConfig(timing=TimingConfig(dt_phenotype=dt_pheno)),
        "dt": dt_pheno,
        "dimensions": 2,
    }

    rows = [_record_engine_row(container, 0.0)]
    t = 0.0
    next_save = save_interval
    while t < max_time - 1e-9:
        N = container.count
        if N == 0:
            break
        tnf_arr = np.full(N, tnf_bath, dtype=np.float64)
        bn_inputs = coupling.compute_bn_inputs_vectorized({"TNF": tnf_arr})
        tnf_on = bn_inputs.get("TNF", np.zeros(N, dtype=np.bool_))
        p_apop, p_nonacd = _simulate_tnf_boolean_mock(tnf_on, dt_pheno, rng)
        container.get_float("bn_prob_Apoptosis")[:N] = p_apop
        container.get_float("bn_prob_NonACD")[:N] = p_nonacd

        apply_physiboss_phenotype(ctx)

        t += dt_pheno
        if t + 1e-9 >= next_save:
            rows.append(_record_engine_row(container, t))
            next_save += save_interval

    return pd.DataFrame(rows)


def _record_engine_row(container: CellContainer, t: float) -> dict:
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


# ─── Comparison / reporting ─────────────────────────────────────────────────

def compare_trajectories(native: pd.DataFrame, engine: pd.DataFrame,
                         checkpoints: List[float]) -> pd.DataFrame:
    """Interpolate both trajectories onto `checkpoints` and return the diff."""
    rows = []
    for t in checkpoints:
        n_row = _interp_row(native, t)
        e_row = _interp_row(engine, t)
        rows.append({
            "t_min": t,
            **{f"native_{k}": n_row[k] for k in ("n_alive", "n_apoptotic", "n_necrotic")},
            **{f"engine_{k}": e_row[k] for k in ("n_alive", "n_apoptotic", "n_necrotic")},
            "alive_pct_err":   _pct_err(n_row["n_alive"],     e_row["n_alive"]),
            "apop_pct_err":    _pct_err(n_row["n_apoptotic"], e_row["n_apoptotic"]),
            "necro_pct_err":   _pct_err(n_row["n_necrotic"],  e_row["n_necrotic"]),
        })
    return pd.DataFrame(rows)


def _interp_row(df: pd.DataFrame, t: float) -> dict:
    ts = df["time_min"].to_numpy()
    if t <= ts[0]:
        return df.iloc[0].to_dict()
    if t >= ts[-1]:
        return df.iloc[-1].to_dict()
    out = {"time_min": t}
    for col in ("n_total", "n_alive", "n_apoptotic", "n_necrotic"):
        out[col] = float(np.interp(t, ts, df[col].to_numpy()))
    return out


def _pct_err(native: float, engine: float) -> float:
    return 100.0 * abs(engine - native) / max(native, 1.0)



def _format_comparison_table(cmp: pd.DataFrame, tol_pct: float) -> str:
    lines = []
    header = (f"{'t_min':>7} | "
              f"{'alive (N/E)':>20} {'apop (N/E)':>20} {'necro (N/E)':>20} | "
              f"{'alive%':>7} {'apop%':>7} {'necro%':>7}")
    lines.append(header)
    lines.append("-" * len(header))
    for _, r in cmp.iterrows():
        mark = "  OK " if max(r["alive_pct_err"], r["apop_pct_err"],
                              r["necro_pct_err"]) <= tol_pct * 100 else " FAIL"
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
    for ax, col, title in zip(
        axes, ("n_alive", "n_apoptotic", "n_necrotic"),
        ("Alive cells", "Apoptotic cells", "Necrotic cells"),
    ):
        ax.plot(native["time_min"], native[col], label="native", lw=2)
        ax.plot(engine["time_min"], engine[col], label="engine", lw=2, ls="--")
        ax.set_xlabel("time (min)")
        ax.set_title(title)
        ax.grid(alpha=0.3)
        ax.legend()
    fig.suptitle("PhysiBoSS native vs OpenCellComms engine - 1_Long_TNF")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    print(f"Plot saved to {out_path}")


def main() -> int:
    default_root = _HERE.resolve().parents[2]
    default_native = default_root / "PhysiBoSS-master" / "output"
    default_xml = default_native / "1_Long_TNF.xml"
    default_csv = (default_root / "PhysiBoSS-master" /
                   "sample_projects_intracellular" / "boolean" / "tutorial" /
                   "config" / "simple_tnf" / "cells.csv")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-dir", type=Path, default=default_native)
    p.add_argument("--xml", type=Path, default=default_xml)
    p.add_argument("--cells-csv", type=Path, default=default_csv)
    p.add_argument("--save-csv", type=Path, default=None)
    p.add_argument("--save-plot", type=Path, default=None)
    p.add_argument("--tolerance", type=float, default=0.10,
                   help="Per-metric tolerance as a fraction (default 0.10 = 10%%)")
    p.add_argument("--checkpoints", type=str,
                   default="0,500,1000,2000,5000,7500,10000")
    p.add_argument("--save-interval", type=float, default=30.0)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    if not args.native_dir.exists():
        print(f"ERROR: --native-dir does not exist: {args.native_dir}", file=sys.stderr)
        return 1
    if not args.xml.exists():
        print(f"ERROR: --xml does not exist: {args.xml}", file=sys.stderr)
        return 1
    if not args.cells_csv.exists():
        print(f"ERROR: --cells-csv does not exist: {args.cells_csv}", file=sys.stderr)
        return 1

    print(f"[1/3] Parsing native trajectory from {args.native_dir} ...")
    native = parse_native_trajectory(args.native_dir)
    print(f"      {len(native)} snapshots, t=[{native['time_min'].min():.0f},"
          f"{native['time_min'].max():.0f}] min")

    max_time = float(native["time_min"].max())
    print(f"[2/3] Running engine replay for {max_time:.0f} min "
          f"(initial cells from {args.cells_csv.name}) ...")
    engine = run_engine_trajectory(args.xml, args.cells_csv,
                                   max_time=max_time,
                                   save_interval=args.save_interval,
                                   seed=args.seed)
    print(f"      {len(engine)} snapshots recorded")

    print("[3/3] Comparing trajectories at checkpoints ...")
    checkpoints = [float(x) for x in args.checkpoints.split(",") if x.strip()]
    cmp = compare_trajectories(native, engine, checkpoints)
    print()
    print(_format_comparison_table(cmp, args.tolerance))

    worst = max(cmp[["alive_pct_err", "apop_pct_err", "necro_pct_err"]].max())
    print()
    print(f"Worst-case error: {worst:.1f}% "
          f"(tolerance: {args.tolerance * 100:.0f}%)")
    status = "PASS" if worst <= args.tolerance * 100 else "FAIL"
    print(f"Overall: {status}")

    print()
    print("Known fidelity gaps (mock MaBoSS + missing mechanisms):")
    print("  * Mock BN only drives Apoptosis / NonACD, not Proliferation or")
    print("    NFkB survival -> engine shows no regrowth of TNF-resistant cells.")
    print("  * Dead cells are not phagocytosed in the engine -> apoptotic /")
    print("    necrotic counts monotonically accumulate instead of plateauing.")
    print("  * No TNF-resistance heredity / no cell division triggered by the")
    print("    BN -> late-time populations diverge strongly from native.")
    print("  To close these gaps: plug in pyMaBoSS, add phagocytosis, and map")
    print("  the BN's Proliferation node through update_cell_division.")

    if args.save_csv:
        native["source"] = "native"
        engine["source"] = "engine"
        pd.concat([native, engine], ignore_index=True).to_csv(args.save_csv, index=False)
        print(f"Trajectories saved to {args.save_csv}")
    if args.save_plot:
        _maybe_plot(native, engine, args.save_plot)

    return 0 if worst <= args.tolerance * 100 else 2


if __name__ == "__main__":
    sys.exit(main())
