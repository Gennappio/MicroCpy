"""
PhysiCell-faithful cell mechanics update (Hertzian repulsion + adhesion).

Computes per-cell velocities from pairwise cell-cell forces and integrates
positions with a 2nd-order Adams-Bashforth scheme. Uses a C++/pybind11
kernel when available; falls back to a pure NumPy implementation otherwise.

Operates on the CellContainer SoA layout (context['cell_container']).
Reserved columns on the container (created lazily):
    repulsion_strength  : float — cr_i in PhysiCell (default 10.0)
    adhesion_strength   : float — ca_i in PhysiCell (default 0.4)
    max_adh_distance    : float — S_i in PhysiCell (default 1.25 * radius)
    pressure            : float — accumulated simple pressure

Mechanics state (velocities, velocities_prev) is kept in context['mechanics']
to avoid embedding 2D arrays in the container.
"""

from typing import Any, Dict, Optional

import numpy as np

from src.workflow.decorators import register_function
from src.workflow.logging import log


@register_function(
    display_name="Update Mechanics (PhysiCell)",
    description=(
        "Compute Hertzian repulsion + adhesion forces between cells and "
        "integrate positions with Adams-Bashforth. Requires CellContainer."
    ),
    category="INTERCELLULAR",
    parameters=[
        {"name": "dt", "type": "FLOAT",
         "description": "Mechanics sub-step (minutes). If <=0, use context['dt'].",
         "default": 0.1, "min_value": 0.0, "max_value": 10.0},
        {"name": "repulsion_strength", "type": "FLOAT",
         "description": "Default repulsion coefficient (cr) applied when column absent.",
         "default": 10.0, "min_value": 0.0, "max_value": 1000.0},
        {"name": "adhesion_strength", "type": "FLOAT",
         "description": "Default adhesion coefficient (ca) applied when column absent.",
         "default": 0.4, "min_value": 0.0, "max_value": 1000.0},
        {"name": "max_adh_distance_factor", "type": "FLOAT",
         "description": "Adhesion range as multiple of the cell radius (S_i = factor * R_i).",
         "default": 1.25, "min_value": 1.0, "max_value": 5.0},
        {"name": "max_cell_radius", "type": "FLOAT",
         "description": "Max expected cell radius (µm) — used for neighbor-search cell size.",
         "default": 8.5, "min_value": 1.0, "max_value": 100.0},
        {"name": "use_fallback", "type": "BOOL",
         "description": "Force NumPy fallback instead of the C++ extension.",
         "default": False},
        {"name": "verbose", "type": "BOOL",
         "description": "Enable detailed logging.",
         "default": None},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def update_mechanics_physicell(
    context: Dict[str, Any],
    dt: float = 0.1,
    repulsion_strength: float = 10.0,
    adhesion_strength: float = 0.4,
    max_adh_distance_factor: float = 1.25,
    max_cell_radius: float = 8.5,
    use_fallback: bool = False,
    verbose: Optional[bool] = None,
    **kwargs,
) -> bool:
    from src.biology.cell_container import CellContainer

    container = context.get("cell_container")
    if not isinstance(container, CellContainer):
        log(context, "update_mechanics_physicell requires context['cell_container']",
            prefix="[Mech]", node_verbose=verbose)
        return False

    N = container.count
    if N == 0:
        return True

    # ── Resolve time step ────────────────────────────────────────────────
    step_dt = dt if dt > 0 else float(context.get("dt", 0.1))

    # ── Resolve domain bounds (centered at origin, µm) ───────────────────
    x_min, y_min, z_min, x_max, y_max, z_max, use_2D = _resolve_domain(context)

    # ── Per-cell parameter arrays (lazy column init) ─────────────────────
    rep_arr = _ensure_float_col(container, "repulsion_strength", repulsion_strength)
    adh_arr = _ensure_float_col(container, "adhesion_strength", adhesion_strength)
    max_adh = _ensure_float_col(container, "max_adh_distance", 0.0)
    pressure = _ensure_float_col(container, "pressure", 0.0)

    # If max_adh_distance was never set explicitly, derive from radius
    needs_derive = max_adh[:N] <= 0.0
    if np.any(needs_derive):
        max_adh[:N][needs_derive] = container.radii[:N][needs_derive] * max_adh_distance_factor

    # ── Mechanics state (velocities, velocities_prev) ────────────────────
    mech = _ensure_mechanics_state(context, container.capacity, container.dims)
    velocities, velocities_prev = mech["velocities"], mech["velocities_prev"]
    if velocities.shape[0] < container.capacity:
        mech["velocities"] = _grow_2d(velocities, container.capacity)
        mech["velocities_prev"] = _grow_2d(velocities_prev, container.capacity)
        velocities, velocities_prev = mech["velocities"], mech["velocities_prev"]

    # ── Slice active arrays (views into SoA) ─────────────────────────────
    positions = container.positions
    radii = container.radii
    alive = container.alive

    # ── Dispatch: C++ or NumPy ───────────────────────────────────────────
    ext = None
    if not use_fallback:
        from src.adapters.physicell_mechanics import get_extension
        ext = get_extension()

    if ext is not None:
        ext.update_mechanics(
            positions, radii, alive,
            rep_arr, adh_arr, max_adh,
            velocities, velocities_prev, pressure,
            step_dt,
            x_min, y_min, z_min, x_max, y_max, z_max,
            max_cell_radius, use_2D,
        )
        backend = "cxx"
    else:
        from src.adapters.physicell_mechanics.fallback import update_mechanics_numpy
        update_mechanics_numpy(
            positions[:N], radii[:N], alive[:N],
            rep_arr[:N], adh_arr[:N], max_adh[:N],
            velocities[:N], velocities_prev[:N], pressure[:N],
            step_dt,
            x_min, y_min, z_min, x_max, y_max, z_max, use_2D,
        )
        backend = "numpy"

    log(context, f"mechanics step: {N} cells, dt={step_dt:.4f}, backend={backend}",
        prefix="[Mech]", node_verbose=verbose)
    return True


# ── Helpers ────────────────────────────────────────────────────────────────

def _ensure_float_col(container, name: str, default: float) -> np.ndarray:
    if not container.has_column(name):
        return container.add_float_column(name, default=default)
    return container.get_float(name)


def _ensure_mechanics_state(context: Dict[str, Any], capacity: int, dims: int) -> Dict[str, np.ndarray]:
    mech = context.get("mechanics")
    if mech is None or mech.get("velocities") is None:
        mech = {
            "velocities": np.zeros((capacity, 3), dtype=np.float64),
            "velocities_prev": np.zeros((capacity, 3), dtype=np.float64),
        }
        context["mechanics"] = mech
    return mech


def _grow_2d(arr: np.ndarray, new_rows: int) -> np.ndarray:
    new = np.zeros((new_rows, arr.shape[1]), dtype=arr.dtype)
    new[:arr.shape[0]] = arr
    return new


def _resolve_domain(context: Dict[str, Any]):
    """Return (x_min, y_min, z_min, x_max, y_max, z_max, use_2D)."""
    config = context.get("config")
    dims = context.get("dimensions", 3)
    if config is not None and getattr(config, "domain", None) is not None:
        dom = config.domain
        dims = getattr(dom, "dimensions", dims)
        sx = _micro(getattr(dom, "size_x", None), 500.0)
        sy = _micro(getattr(dom, "size_y", None), 500.0)
        sz = _micro(getattr(dom, "size_z", None), 500.0) if dims == 3 else 0.0
    else:
        sx = sy = sz = 500.0

    use_2D = (dims == 2)
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    return (-hx, -hy, -hz, hx, hy, hz, use_2D)


def _micro(length_like, default: float) -> float:
    if length_like is None:
        return default
    if hasattr(length_like, "micrometers"):
        return float(length_like.micrometers)
    try:
        return float(length_like)
    except Exception:
        return default
