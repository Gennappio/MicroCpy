#!/usr/bin/env python3
"""Regenerate every MicroC seed file with an exactly centred spheroid.

Each ``initial_cells_<N>_center_<L>.csv`` is a packed spheroid of N cells on a
20 um bio-grid of an L um square (cube for the 3d files). Its coordinates are
centre-relative (``origin=center``) and its centre of mass sits EXACTLY on the
domain centre for the grid the file is named for: a cell centre on an odd grid
(1500 um / 20 um = 75 cells: centroid 0) or a cell corner on an even grid
(3000 um -> 150 cells, 10000 um -> 500 cells: centroid -0.5). Run from the
repository root:

    python opencellcomms_adapters/MicroC/data/regenerate_seeds.py

Phenotypes and gene columns follow csv_cell_generator's spheroid rule
(core within 2 cells Proliferation, the rest Growth_Arrest; random ATP genes,
seed 42). ``*_glyco.csv`` derivatives (every cell Quiescent, glycoATP ON,
mitoATP OFF) are rebuilt from their base file.
"""
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "opencellcomms_engine" / "tools"))
from csv_cell_generator import (  # noqa: E402
    assign_phenotypes_and_genes, generate_spheroid_pattern,
    generate_spheroid_pattern_3d, recenter_positions, symmetry_centre,
    write_csv_file)

DATA = Path(__file__).resolve().parent
CELL_UM = 20.0
SEEDS = [  # (cells, domain um, dims)
    *[(n, 1500.0, 2) for n in (100, 200, 500, 1000, 2000, 3000, 4000)],
    *[(n, 3000.0, 2) for n in (100, 200, 500, 1000, 2000, 3000, 4000, 5000,
                               6000, 7000, 8000, 9000, 10000)],
    *[(n, 10000.0, 2) for n in (50000, 100000)],
    *[(n, 750.0, 3) for n in (500, 1000, 2000)],
    (5000, 1500.0, 3),
]
GLYCO_DERIVATIVES = {  # base file -> (derivative, description)
    "initial_cells_1000_center_1500.csv": (
        "initial_cells_1000_center_1500_glyco.csv",
        "Same 1000-cell spheroid positions as initial_cells_1000_center_1500.csv "
        "with every cell Quiescent / glycoATP ON / mitoATP OFF (stability search "
        "start state; Growth_Arrest would halve consumption in the metabolism node)"),
}


def build(cells: int, domain_um: float, dims: int) -> Path:
    grid = int(domain_um / CELL_UM)
    centre = symmetry_centre(grid)
    np.random.seed(42)
    if dims == 3:
        positions = generate_spheroid_pattern_3d(centre, centre, centre, cells)
        name = f"initial_cells_3d_{cells}_center_{int(domain_um)}.csv"
        description = f"3D spheroid pattern with {cells} cells (centre of mass exactly at the domain centre)"
    else:
        positions = generate_spheroid_pattern(centre, centre, cells)
        name = f"initial_cells_{cells}_center_{int(domain_um)}.csv"
        description = f"Spheroid pattern with {cells} cells (centre of mass exactly at the domain centre)"
    positions = recenter_positions(positions, (grid // 2,) * dims)
    rows = assign_phenotypes_and_genes(positions, "spheroid")
    out = DATA / name
    write_csv_file(rows, out, CELL_UM, domain_um, description)
    xs = np.array([[r[a] for a in ("x", "y", "z")[:dims]] for r in rows], dtype=float)
    print(f"{name:42s} n={len(rows):6d} centroid={tuple(np.round(xs.mean(axis=0), 6))} "
          f"rmax={np.sqrt(((xs - xs.mean(axis=0)) ** 2).sum(axis=1)).max():.2f}")
    return out


def derive_glyco(base: Path, name: str, description: str) -> None:
    rows = [r for r in csv.DictReader(l for l in open(base) if not l.startswith("#"))]
    out = DATA / name
    with open(out, "w", newline="") as f:
        f.write(f'# origin=center, cell_size_um={CELL_UM}, domain_size_um=1500.0, description="{description}"\n')
        w = csv.writer(f)
        w.writerow(["x", "y", "phenotype", "gene_Proliferation", "gene_glycoATP", "gene_mitoATP"])
        for r in rows:
            w.writerow([r["x"], r["y"], "Quiescent", "false", "true", "false"])
    print(f"{name:42s} n={len(rows):6d} (derived from {base.name})")


if __name__ == "__main__":
    for cells, domain_um, dims in SEEDS:
        build(cells, domain_um, dims)
    for base, (name, description) in GLYCO_DERIVATIVES.items():
        derive_glyco(DATA / base, name, description)
