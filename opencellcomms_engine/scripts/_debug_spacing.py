"""Inspect pairwise distances in the mechano cells.csv initial condition."""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
csv = os.path.normpath(os.path.join(
    HERE, "..", "..", "..", "PhysiBoSS-master", "output", "cells.csv"))
data = np.loadtxt(csv, delimiter=",")
print(f"Total cells: {data.shape[0]}   columns: {data.shape[1]}")
print(f"Cell types: {np.unique(data[:, 3])}")
for t in np.unique(data[:, 3]):
    sub = data[data[:, 3] == t]
    print(f"\n── Type {int(t)}: {sub.shape[0]} cells ──")
    xyz = sub[:, :3]
    # Pairwise distances (brute force, OK for ~300 cells)
    diff = xyz[:, None, :] - xyz[None, :, :]
    dist = np.linalg.norm(diff, axis=2)
    np.fill_diagonal(dist, np.inf)
    min_dist_per_cell = dist.min(axis=1)
    # Count pairs with d < Rsum (=16.83 for R=8.413)
    Rsum = 2 * 8.413
    n_close = int(((dist < Rsum) & (dist > 0)).sum() // 2)
    print(f"  min pairwise distance: {dist.min():.3f} µm")
    print(f"  5th percentile of min-dist-per-cell: {np.percentile(min_dist_per_cell, 5):.3f}")
    print(f"  median min-dist-per-cell: {np.median(min_dist_per_cell):.3f}")
    print(f"  # pairs with d < Rsum (={Rsum:.2f}): {n_close}")
    # Show the 5 most compressed cells
    idx_worst = np.argsort(min_dist_per_cell)[:5]
    print(f"  5 most compressed cells (idx, (x,y,z), min_neighbor_d):")
    for i in idx_worst:
        print(f"    #{i}: ({xyz[i,0]:8.2f}, {xyz[i,1]:8.2f}, {xyz[i,2]:.2f})  "
              f"min_d={min_dist_per_cell[i]:.3f}")
