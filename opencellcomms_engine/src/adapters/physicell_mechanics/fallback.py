"""
NumPy fallback for cell mechanics when the C++ extension is not built.

Functionally equivalent to mechanics.cpp but slower (O(N²) brute force
instead of uniform grid neighbor search).  Used for:
- Development machines without a C++ compiler
- CI environments where the extension hasn't been built yet
- Verification: running both paths and comparing results

Matches the PhysiCell formulas exactly:
    repulsion = (1 - d/R)^2 * sqrt(cr_i * cr_j)       when d < R
    adhesion  = (1 - d/S)^2 * sqrt(ca_i * ca_j)       when d < S
    velocity  = (repulsion - adhesion) / d * (r_i - r_j)
"""

from __future__ import annotations

import numpy as np

SIMPLE_PRESSURE_SCALE = 0.027288820670331  # 12 * (1 - sqrt(pi/(2*sqrt(3))))^2


def update_velocities_numpy(
    positions: np.ndarray,
    radii: np.ndarray,
    alive: np.ndarray,
    repulsion: np.ndarray,
    adhesion: np.ndarray,
    max_adh_distance: np.ndarray,
    velocities: np.ndarray,
    pressures: np.ndarray,
) -> None:
    """
    Brute-force O(N²) velocity calculation. Matches mechanics.cpp semantics.

    Modifies `velocities` and `pressures` in place.
    """
    N = positions.shape[0]
    velocities[...] = 0.0
    pressures[...] = 0.0

    alive_idx = np.where(alive)[0]
    if len(alive_idx) < 2:
        return

    pos_a = positions[alive_idx]
    R_a = radii[alive_idx]
    cr_a = repulsion[alive_idx]
    ca_a = adhesion[alive_idx]
    S_a = max_adh_distance[alive_idx]
    M = len(alive_idx)

    # Pairwise displacements: (M, M, 3)
    disp = pos_a[:, np.newaxis, :] - pos_a[np.newaxis, :, :]
    d2 = np.sum(disp * disp, axis=2)
    d = np.sqrt(d2)
    np.fill_diagonal(d, 1.0)  # avoid div by zero on diagonal
    d = np.maximum(d, 1e-5)

    # Sum of radii (M, M)
    R_sum = R_a[:, np.newaxis] + R_a[np.newaxis, :]
    S_sum = S_a[:, np.newaxis] + S_a[np.newaxis, :]

    # Repulsion
    rep_active = d < R_sum
    u_r = np.where(rep_active, 1.0 - d / R_sum, 0.0)
    temp_r = u_r * u_r
    # Pressure contribution (before multiplying by eff_rep)
    pressure_contrib = temp_r / SIMPLE_PRESSURE_SCALE
    np.fill_diagonal(pressure_contrib, 0.0)
    pressures[alive_idx] = np.sum(pressure_contrib, axis=1)

    eff_rep = np.sqrt(cr_a[:, np.newaxis] * cr_a[np.newaxis, :])
    temp_r = temp_r * eff_rep

    # Adhesion
    adh_active = d < S_sum
    u_a = np.where(adh_active, 1.0 - d / S_sum, 0.0)
    temp_a = u_a * u_a
    eff_adh = np.sqrt(ca_a[:, np.newaxis] * ca_a[np.newaxis, :])
    temp_a = temp_a * eff_adh

    # Net force magnitude per pair (M, M)
    temp_net = temp_r - temp_a
    np.fill_diagonal(temp_net, 0.0)
    # Scale by 1/d
    factor = temp_net / d
    # Zero out diagonal again (self)
    np.fill_diagonal(factor, 0.0)

    # Sum forces: vel[i] = sum_j factor[i,j] * disp[i,j]
    # disp has shape (M, M, 3), factor (M, M)
    vel_a = np.sum(factor[:, :, np.newaxis] * disp, axis=1)
    velocities[alive_idx] = vel_a


def update_positions_numpy(
    positions: np.ndarray,
    velocities: np.ndarray,
    velocities_prev: np.ndarray,
    alive: np.ndarray,
    dt: float,
    x_min: float, y_min: float, z_min: float,
    x_max: float, y_max: float, z_max: float,
    use_2D: bool,
) -> None:
    """Adams-Bashforth 2nd-order integration. Modifies positions in place."""
    mask = alive.astype(bool)
    new_v = velocities[mask]
    old_v = velocities_prev[mask]
    delta = dt * (1.5 * new_v - 0.5 * old_v)
    if use_2D:
        delta[:, 2] = 0.0
    positions[mask] += delta
    velocities_prev[mask] = new_v

    # Clamp to domain
    np.clip(positions[:, 0], x_min, x_max, out=positions[:, 0])
    np.clip(positions[:, 1], y_min, y_max, out=positions[:, 1])
    if not use_2D:
        np.clip(positions[:, 2], z_min, z_max, out=positions[:, 2])


def update_mechanics_numpy(
    positions: np.ndarray,
    radii: np.ndarray,
    alive: np.ndarray,
    repulsion: np.ndarray,
    adhesion: np.ndarray,
    max_adh_distance: np.ndarray,
    velocities: np.ndarray,
    velocities_prev: np.ndarray,
    pressures: np.ndarray,
    dt: float,
    x_min: float, y_min: float, z_min: float,
    x_max: float, y_max: float, z_max: float,
    use_2D: bool,
) -> None:
    """Combined velocity + position update (NumPy fallback)."""
    update_velocities_numpy(positions, radii, alive, repulsion, adhesion,
                            max_adh_distance, velocities, pressures)
    update_positions_numpy(positions, velocities, velocities_prev, alive, dt,
                           x_min, y_min, z_min, x_max, y_max, z_max, use_2D)
