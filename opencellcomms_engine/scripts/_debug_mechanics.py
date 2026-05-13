"""Diagnostic: probe the C++ mechanics kernel in the stiff regime (cr=100)
and at equilibrium spacing, which is the mechano initial condition.

Scenarios:
  A) 2 cells at d = Rsum exactly, cr=10          — expect zero motion
  B) 2 cells at d = Rsum exactly, cr=100         — expect zero motion
  C) 2 cells at d = 0.99*Rsum, cr=10             — small stable separation
  D) 2 cells at d = 0.99*Rsum, cr=100            — stable? or oscillation?
  E) 3x3 hex grid of BM cells (cr=100) at Rsum   — stability over 600 steps
"""
import sys, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXT_DIR = os.path.normpath(os.path.join(HERE, "..", "src", "adapters", "physicell_mechanics"))
sys.path.insert(0, HERE)          # for sibling script imports
sys.path.insert(0, EXT_DIR)       # for the compiled extension
import _physicell_mechanics as m  # type: ignore


def run(pos, radii, cr, ca, max_adh, dt, n_steps, use_2D=True):
    N = pos.shape[0]
    alive = np.ones(N, dtype=bool)
    vel = np.zeros((N, 3), dtype=np.float64)
    vp = np.zeros((N, 3), dtype=np.float64)
    pr = np.zeros(N, dtype=np.float64)
    traj = [pos.copy()]
    for _ in range(n_steps):
        m.update_mechanics(pos, radii, alive, cr, ca, max_adh,
                           vel, vp, pr, dt,
                           -500, -500, -50, 500, 500, 50,
                           float(max_adh.max()) + 1e-6, use_2D)
        traj.append(pos.copy())
    return traj, vel, pr


def two_cell(label, d0, cr_val, dt=0.1, n_steps=600):
    R = 8.413
    pos = np.array([[-d0 / 2, 0, 0], [d0 / 2, 0, 0]], dtype=np.float64)
    radii = np.array([R, R])
    cr = np.array([cr_val, cr_val])
    ca = np.zeros(2)
    max_adh = np.array([1.25 * R, 1.25 * R])
    traj, vel, pr = run(pos, radii, cr, ca, max_adh, dt, n_steps)
    d_final = float(np.linalg.norm(traj[-1][1] - traj[-1][0]))
    # Peak intermediate distance (detect overshoots)
    dists = np.array([np.linalg.norm(t[1] - t[0]) for t in traj])
    print(f"{label:40s}  d0={d0:6.3f}  d_final={d_final:6.3f}  "
          f"max_d={dists.max():6.3f}  min_d={dists.min():6.3f}  "
          f"|v_final|={np.linalg.norm(vel[0]):.3e}")


def hex_grid(cr_val, dt=0.1, n_steps=600):
    R = 8.413
    Rsum = 2 * R
    pts = []
    for i in range(3):
        for j in range(3):
            pts.append([i * Rsum, j * Rsum * np.sqrt(3) / 2
                        + (0.5 * Rsum if i % 2 else 0), 0])
    pos = np.array(pts, dtype=np.float64)
    pos -= pos.mean(axis=0)
    radii = np.full(9, R)
    cr = np.full(9, cr_val)
    ca = np.zeros(9)
    max_adh = np.full(9, 1.25 * R)
    init = pos.copy()
    traj, vel, pr = run(pos, radii, cr, ca, max_adh, dt, n_steps)
    disp = np.linalg.norm(traj[-1] - init, axis=1)
    max_step = 0.0
    for k in range(1, len(traj)):
        step = np.linalg.norm(traj[k] - traj[k - 1], axis=1).max()
        max_step = max(max_step, step)
    print(f"hex9_cr={cr_val:<5.0f}  max_disp={disp.max():7.3f}  "
          f"mean_disp={disp.mean():7.3f}  max_single_step={max_step:.3e}  "
          f"mean_pressure={pr.mean():.3f}")


def mechano_real_replay(n_steps_list=(1, 10, 100, 600), dt=0.1):
    """Replay real mechano t=0 initial condition (from .mat) for N steps.

    Records where the kernel first produces non-trivial motion, so we can
    distinguish first-step instability from long-run drift.
    """
    import scipy.io
    import xml.etree.ElementTree as ET
    from compare_native_physiboss import _parse_labels

    out_dir = os.path.normpath(os.path.join(
        HERE, "..", "..", "..", "PhysiBoSS-master", "output"))
    xml = os.path.join(out_dir, "output00000000.xml")
    mat = os.path.join(out_dir, "output00000000_cells.mat")
    lbls = _parse_labels(xml)
    cells = scipy.io.loadmat(mat)["cells"]

    def pick(k):
        return cells[lbls[k]].astype(np.float64)

    N = cells.shape[1]
    pos0 = np.column_stack([pick("position_x"), pick("position_y"),
                            pick("position_z")]).astype(np.float64)
    vol = pick("total_volume")
    radii = ((3.0 * vol) / (4.0 * np.pi)) ** (1.0 / 3.0)
    cr = pick("cell_cell_repulsion_strength")
    ca = pick("cell_cell_adhesion_strength")
    max_adh = radii * pick("relative_maximum_adhesion_distance")
    ctype = pick("cell_type").astype(int)

    for n_steps in n_steps_list:
        pos = pos0.copy()
        traj, vel, pr = run(pos, radii, cr, ca, max_adh, dt, n_steps, use_2D=False)
        disp = np.linalg.norm(traj[-1] - pos0, axis=1)
        step_sizes = [np.linalg.norm(traj[k] - traj[k - 1], axis=1)
                      for k in range(1, len(traj))]
        max_step_global = max(s.max() for s in step_sizes) if step_sizes else 0.0
        # Which cell and on which step was the worst motion?
        worst_cell = int(np.argmax(disp))
        print(f"n={n_steps:4d}  N_cells={N}  max_disp={disp.max():8.3f}  "
              f"p99={np.percentile(disp, 99):7.3f}  max_single_step={max_step_global:.3e}  "
              f"worst_cell={worst_cell} type={ctype[worst_cell]} cr={cr[worst_cell]:.0f}")
        if max_step_global > 5.0:
            # Show when the big jump happened
            for k, s in enumerate(step_sizes):
                if s.max() > 5.0:
                    i_bad = int(np.argmax(s))
                    neighbors_at_step_start = (np.linalg.norm(traj[k] - traj[k][i_bad], axis=1) < 25.0).sum()
                    print(f"    -> first big jump at step {k+1}: cell #{i_bad} "
                          f"type={ctype[i_bad]} cr={cr[i_bad]:.0f} "
                          f"moved {s[i_bad]:.3f} µm  "
                          f"({neighbors_at_step_start-1} neighbors within 25 µm)")
                    break


def main():
    R = 8.413
    Rsum = 2 * R
    print("─── Two-cell diagnostics (600 steps, dt=0.1) ───")
    two_cell("A) d=Rsum exactly,       cr=10",  Rsum,        10.0)
    two_cell("B) d=Rsum exactly,       cr=100", Rsum,        100.0)
    two_cell("C) d=0.99*Rsum,          cr=10",  0.99 * Rsum, 10.0)
    two_cell("D) d=0.99*Rsum,          cr=100", 0.99 * Rsum, 100.0)
    two_cell("E) d=0.95*Rsum,          cr=100", 0.95 * Rsum, 100.0)
    two_cell("F) d=0.9*Rsum,           cr=100", 0.9  * Rsum, 100.0)

    print("\n─── 3x3 hex grid diagnostics ───")
    hex_grid(10.0)
    hex_grid(100.0)

    print("\n─── Mechano real t=0 replay (all 548 cells) ───")
    mechano_real_replay()


if __name__ == "__main__":
    main()
