"""Dissect the first-step explosion of BM cell #65 in mechano t=0."""
import os
import sys
import numpy as np
import scipy.io

HERE = os.path.dirname(os.path.abspath(__file__))
EXT_DIR = os.path.normpath(os.path.join(HERE, "..", "src", "adapters", "physicell_mechanics"))
sys.path.insert(0, HERE)
sys.path.insert(0, EXT_DIR)
import _physicell_mechanics as m  # type: ignore
import xml.etree.ElementTree as ET


def _parse_labels(xml_path):
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


OUT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "PhysiBoSS-master", "output"))
lbls = _parse_labels(os.path.join(OUT, "output00000000.xml"))
cells = scipy.io.loadmat(os.path.join(OUT, "output00000000_cells.mat"))["cells"]


def col(k):
    return cells[lbls[k]].astype(np.float64)


pos = np.column_stack([col("position_x"), col("position_y"), col("position_z")])
vol = col("total_volume")
radii = ((3.0 * vol) / (4.0 * np.pi)) ** (1.0 / 3.0)
cr = col("cell_cell_repulsion_strength")
ca = col("cell_cell_adhesion_strength")
rel_max = col("relative_maximum_adhesion_distance")
max_adh = radii * rel_max
ctype = col("cell_type").astype(int)
N = pos.shape[0]

print(f"Total cells: {N}")
target = 65
print(f"\nCell #{target} ({'BM' if ctype[target]==1 else 'cancer'}): "
      f"pos={pos[target]}  R={radii[target]:.3f}  "
      f"cr={cr[target]:.1f}  ca={ca[target]:.1f}  max_adh={max_adh[target]:.3f}  "
      f"rel_max={rel_max[target]:.3f}")

# Distance to all other cells
d = np.linalg.norm(pos - pos[target], axis=1)
d[target] = np.inf
# Interaction cutoff = max(Rsum, max_adh[i]+max_adh[j])
R_i = radii[target]
max_i = max_adh[target]
Rsum = R_i + radii
cutoff = np.maximum(Rsum, max_i + max_adh)
interacting = np.where(d < cutoff)[0]
print(f"\nNeighbors within interaction cutoff: {len(interacting)}")
print(f"{'idx':>4}  {'type':>4}  {'dx':>8}  {'dy':>8}  {'dz':>8}  "
      f"{'d':>8}  {'Rsum':>8}  {'max_adh_sum':>10}  {'cr_j':>6}  {'ca_j':>6}")
for j in interacting[np.argsort(d[interacting])]:
    dv = pos[j] - pos[target]
    print(f"{j:>4}  {ctype[j]:>4}  {dv[0]:>8.3f}  {dv[1]:>8.3f}  {dv[2]:>8.3f}  "
          f"{d[j]:>8.3f}  {Rsum[j]:>8.3f}  {max_i+max_adh[j]:>10.3f}  "
          f"{cr[j]:>6.1f}  {ca[j]:>6.1f}")

# Per-neighbor force from the PhysiCell formula
# repulsion vector = -(sqrt(cr_i*cr_j)) * (1 - d/Rsum)^2 * r_hat   for d < Rsum
# adhesion  vector = +(sqrt(ca_i*ca_j)) * (1 - d/S)^2   * r_hat   for d < S
print("\n--- Per-neighbor contribution to velocity (PhysiCell formula, net outward>0) ---")
total = np.zeros(3)
for j in interacting:
    dv = pos[j] - pos[target]
    dist = d[j]
    r_hat = dv / dist
    Rs = Rsum[j]
    S = max_i + max_adh[j]
    rep = 0.0
    adh = 0.0
    if dist < Rs:
        rep = np.sqrt(cr[target] * cr[j]) * (1 - dist / Rs) ** 2
    if dist < S:
        adh = np.sqrt(ca[target] * ca[j]) * (1 - dist / S) ** 2
    # PhysiCell convention: net = adhesion_pull (toward j, +r_hat) - repulsion_push (-r_hat away from j)
    # v = F/eta with eta=1:  v_contrib = (-rep + adh) * r_hat
    v_contrib = (-rep + adh) * r_hat
    total += v_contrib
    print(f"  j={j} type={ctype[j]} d={dist:.4f} Rsum={Rs:.4f}  "
          f"rep={rep:.3f}  adh={adh:.3f}  |v_contrib|={np.linalg.norm(v_contrib):.3f}")

print(f"\nNet velocity on cell #{target}: {total}")
print(f"|v| = {np.linalg.norm(total):.3f} µm/min")
print(f"AB2 first step disp = 1.5 * dt * |v| = {1.5 * 0.1 * np.linalg.norm(total):.3f} µm  (dt=0.1)")
