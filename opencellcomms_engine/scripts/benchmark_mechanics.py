#!/usr/bin/env python3
"""
Mechanics performance benchmark (Phase 3.10).

Compares the C++ pybind11 kernel against the NumPy fallback
for update_mechanics_physicell across several population sizes.

Usage:
    python scripts/benchmark_mechanics.py
    python scripts/benchmark_mechanics.py --sizes 100,500,2000 --iters 50

Reports ms/step and C++/NumPy speedup.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from src.biology.cell_container import CellContainer
from src.workflow.functions.intercellular.update_mechanics_physicell import (
    update_mechanics_physicell,
)
from src.adapters.physicell_mechanics import get_extension


def _build_ctx(n_cells: int, dims: int = 3, seed: int = 0):
    """Random cells packed into a sphere/disc of radius 200 µm."""
    rng = np.random.default_rng(seed)
    container = CellContainer(capacity=n_cells * 2, dimensions=dims)
    # Uniform cube inside a sphere/disc of r=200
    r = 200.0
    pos = rng.uniform(-r, r, (n_cells, dims))
    # Keep only those inside the sphere to avoid edge clamping bias
    mask = (pos ** 2).sum(axis=1) < r ** 2
    pos = pos[mask]
    container.add_cells(pos, phenotype="Quiescent")
    return {
        "cell_container": container,
        "dt": 0.1,
        "dimensions": dims,
    }


def _bench(ctx: dict, iters: int, use_fallback: bool) -> float:
    """Return mean ms/step after a 2-iteration warmup."""
    for _ in range(2):
        update_mechanics_physicell(ctx, dt=0.1, use_fallback=use_fallback)
    t0 = time.perf_counter()
    for _ in range(iters):
        update_mechanics_physicell(ctx, dt=0.1, use_fallback=use_fallback)
    t1 = time.perf_counter()
    return (t1 - t0) * 1000.0 / iters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="100,500,2000,5000",
                    help="comma-separated cell counts")
    ap.add_argument("--iters", type=int, default=20,
                    help="timed iterations per (size, backend)")
    ap.add_argument("--dims", type=int, default=3, choices=(2, 3))
    args = ap.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]

    ext = get_extension()
    print(f"C++ extension available: {ext is not None}")
    print(f"Dims: {args.dims}D, iters/bench: {args.iters}")
    print()
    header = f"{'N':>8} {'NumPy (ms)':>14} {'C++ (ms)':>12} {'speedup':>10}"
    print(header)
    print("-" * len(header))

    for n in sizes:
        ctx_np = _build_ctx(n, dims=args.dims, seed=n)
        ms_np = _bench(ctx_np, args.iters, use_fallback=True)

        if ext is not None:
            ctx_cxx = _build_ctx(n, dims=args.dims, seed=n)
            ms_cxx = _bench(ctx_cxx, args.iters, use_fallback=False)
            speedup = ms_np / ms_cxx if ms_cxx > 0 else float("inf")
            print(f"{n:>8d} {ms_np:>14.3f} {ms_cxx:>12.3f} {speedup:>9.1f}x")
        else:
            print(f"{n:>8d} {ms_np:>14.3f} {'n/a':>12} {'n/a':>10}")


if __name__ == "__main__":
    main()
