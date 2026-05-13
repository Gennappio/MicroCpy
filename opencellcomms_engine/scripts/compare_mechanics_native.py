#!/usr/bin/env python3
"""
Pure-mechanics validation: OpenCellComms C++ kernel vs native PhysiBoSS `mechano`.

Loads the native t=0 snapshot (548 cells, multi-type), replays only the cell-cell
mechanics in the engine for one native save interval (60 min = 600 steps of
dt=0.1), then matches by `ID` to the native t=60 snapshot and reports positional
and pressure deviation.

This isolates the Hertzian repulsion + adhesion + Adams-Bashforth integration
from the cycle / death / diffusion machinery that the native run also exercises
and which the engine does not yet fully implement.

Usage:
    python scripts/compare_mechanics_native.py \
        [--native-dir PhysiBoSS-master/output] \
        [--dt 0.1] [--duration 60] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

import numpy as np
import scipy.io

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from scripts.compare_native_physiboss import _parse_labels  # noqa: E402


def _load_snapshot(native_dir: Path, idx: int):
    xml = native_dir / f"output{idx:08d}.xml"
    mat = native_dir / f"output{idx:08d}_cells.mat"
    if not xml.exists() or not mat.exists():
        raise FileNotFoundError(f"Missing native snapshot at index {idx}")
    import xml.etree.ElementTree as ET
    labels = _parse_labels(xml)
    cells = scipy.io.loadmat(mat)["cells"]  # (rows, N)
    t = float(ET.parse(xml).getroot().find("metadata/current_time").text)
    return t, labels, cells


def _extract_fields(labels: dict, cells: np.ndarray):
    pick = lambda k: cells[labels[k]]
    return {
        "id": pick("ID").astype(np.int64),
        "cell_type": pick("cell_type").astype(np.int64),
        "pos": np.stack([pick("position_x"), pick("position_y"),
                         pick("position_z")], axis=1).astype(np.float64),
        "vol": pick("total_volume").astype(np.float64),
        "rep": pick("cell_cell_repulsion_strength").astype(np.float64),
        "adh": pick("cell_cell_adhesion_strength").astype(np.float64),
        "max_adh_rel": pick("relative_maximum_adhesion_distance").astype(np.float64),
        "dead": pick("dead").astype(bool),
    }


def _run_engine(init: dict, dt: float, duration: float,
                domain: Tuple[float, float, float, float, float, float]):
    from src.adapters.physicell_mechanics import get_extension
    ext = get_extension()
    if ext is None:
        raise RuntimeError("C++ mechanics extension not built; run setup.py build_ext --inplace")

    N = init["pos"].shape[0]
    # Deep copy — `ascontiguousarray` returns the same array if already contiguous,
    # which would cause the kernel to mutate ``init["pos"]`` in place.
    pos = np.array(init["pos"], dtype=np.float64, copy=True, order="C")
    radii = ((3.0 * init["vol"]) / (4.0 * np.pi)) ** (1.0 / 3.0)
    alive = np.ones(N, dtype=bool)
    rep = init["rep"].copy()
    adh = init["adh"].copy()
    max_adh = radii * init["max_adh_rel"]
    vel = np.zeros((N, 3), dtype=np.float64)
    vel_prev = np.zeros((N, 3), dtype=np.float64)
    pressure = np.zeros(N, dtype=np.float64)

    x_min, y_min, z_min, x_max, y_max, z_max = domain
    # Bin size must cover the worst-case interaction range (adhesion cutoff).
    max_cell_radius = float(max_adh.max()) + 1e-6
    n_steps = int(round(duration / dt))
    for _ in range(n_steps):
        ext.update_mechanics(pos, radii, alive, rep, adh, max_adh,
                             vel, vel_prev, pressure, dt,
                             x_min, y_min, z_min, x_max, y_max, z_max,
                             max_cell_radius, False)  # 3D (z ≈ 0 throughout)
    return {"pos": pos, "pressure": pressure, "radii": radii}


def _dist_stats(dist: np.ndarray) -> dict:
    return {
        "mean": float(dist.mean()),
        "rms": float(np.sqrt(np.mean(dist ** 2))),
        "p50": float(np.percentile(dist, 50)),
        "p90": float(np.percentile(dist, 90)),
        "p99": float(np.percentile(dist, 99)),
        "max": float(dist.max()),
    }


def _compare(engine: dict, t0: dict, native: dict) -> dict:
    """Match by ID; report position error globally and by cell type."""
    id0, id_n = t0["id"], native["id"]
    common, i0, i_n = np.intersect1d(id0, id_n, return_indices=True)
    if common.size == 0:
        raise RuntimeError("No common cell IDs between initial and final snapshots")

    eng_pos = engine["pos"][i0]
    native_pos = native["pos"][i_n]
    init_pos = t0["pos"][i0]
    ctype = t0["cell_type"][i0]

    err = np.linalg.norm(eng_pos - native_pos, axis=1)          # engine vs native
    native_mot = np.linalg.norm(native_pos - init_pos, axis=1)  # native motion
    engine_mot = np.linalg.norm(eng_pos - init_pos, axis=1)     # engine motion
    mean_diam = float(2.0 * engine["radii"].mean())

    metrics = {
        "n_cells_t0": int(id0.size),
        "n_cells_native_final": int(id_n.size),
        "n_matched": int(common.size),
        "n_daughters_native": int(id_n.size - common.size),
        "mean_diameter_um": mean_diam,
        "error_vs_native_um": _dist_stats(err),
        "native_displacement_um": _dist_stats(native_mot),
        "engine_displacement_um": _dist_stats(engine_mot),
        "error_rel_diameter_rms": float(np.sqrt(np.mean(err ** 2)) / mean_diam),
        "error_rel_native_motion_mean": float(err.mean() / max(native_mot.mean(), 1e-9)),
    }
    # Per-type breakdown (type 0 = cancer, type 1 = BM in the mechano project)
    by_type = {}
    for t in np.unique(ctype):
        mask = ctype == t
        by_type[f"type_{int(t)}"] = {
            "n": int(mask.sum()),
            "err": _dist_stats(err[mask]),
            "native_mot": _dist_stats(native_mot[mask]),
        }
    metrics["by_type"] = by_type
    return metrics


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--native-dir", type=Path,
                   default=_HERE.parents[2] / "PhysiBoSS-master" / "output")
    p.add_argument("--dt", type=float, default=0.1)
    p.add_argument("--duration", type=float, default=60.0)
    p.add_argument("--idx-initial", type=int, default=0)
    p.add_argument("--idx-final", type=int, default=1)
    p.add_argument("--domain", type=float, nargs=6,
                   metavar=("XMIN", "YMIN", "ZMIN", "XMAX", "YMAX", "ZMAX"),
                   default=[-500, -500, -10, 500, 500, 10])
    args = p.parse_args()

    _, lab0, cells0 = _load_snapshot(args.native_dir, args.idx_initial)
    t_final, lab1, cells1 = _load_snapshot(args.native_dir, args.idx_final)
    init = _extract_fields(lab0, cells0)
    native = _extract_fields(lab1, cells1)

    print(f"Native initial snapshot (idx={args.idx_initial}): {init['pos'].shape[0]} cells")
    print(f"Native final   snapshot (idx={args.idx_final}, t={t_final:.0f} min): "
          f"{native['pos'].shape[0]} cells")
    print(f"Replaying {args.duration:.1f} min of mechanics (dt={args.dt}) in engine...")

    engine = _run_engine(init, args.dt, args.duration, tuple(args.domain))
    m = _compare(engine, init, native)

    def _fmt_stats(s: dict, indent: str = "    ") -> str:
        return (f"{indent}mean={s['mean']:7.3f}  rms={s['rms']:7.3f}  "
                f"p50={s['p50']:7.3f}  p90={s['p90']:7.3f}  "
                f"p99={s['p99']:7.3f}  max={s['max']:7.3f}")

    print("\n── Comparison metrics ──────────────────────────────────────────")
    print(f"  cells: t0={m['n_cells_t0']}  native_final={m['n_cells_native_final']}  "
          f"matched={m['n_matched']}  daughters(native-only)={m['n_daughters_native']}")
    print(f"  mean_diameter: {m['mean_diameter_um']:.3f} µm")
    print(f"  Position error (engine vs native), µm:")
    print(_fmt_stats(m["error_vs_native_um"]))
    print(f"  Native displacement over window, µm:")
    print(_fmt_stats(m["native_displacement_um"]))
    print(f"  Engine displacement over window, µm:")
    print(_fmt_stats(m["engine_displacement_um"]))
    print(f"\n  error_rms / diameter       = {m['error_rel_diameter_rms']:.4f}")
    print(f"  error_mean / native_motion = {m['error_rel_native_motion_mean']:.4f}")
    print("\n  By cell type:")
    for tag, d in m["by_type"].items():
        print(f"    {tag} (N={d['n']}):")
        print(f"      error:        {_fmt_stats(d['err'], '')}")
        print(f"      native motion:{_fmt_stats(d['native_mot'], '')}")

    rel = m["error_rel_diameter_rms"]
    tol = 0.25  # RMS position error < 25% of cell diameter
    status = "PASS" if rel < tol else "FAIL"
    print(f"\nMechanics fidelity: {status} (rms/diam = {rel:.3f}, tol {tol})")
    return 0 if rel < tol else 1


if __name__ == "__main__":
    sys.exit(main())
