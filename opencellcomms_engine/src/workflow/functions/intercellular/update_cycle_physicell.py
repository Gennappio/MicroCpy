"""
PhysiCell-faithful cell cycle advance (live_cells_cycle_model by default).

Vectorized implementation of PhysiCell_phenotype.cpp ::
Cycle_Model::advance_model for the simplest and most common cycle models:

- ``live`` (code=5): single phase "Live", stochastic self-loop with
  ``division_at_exit=True``. Matches the prostate LNCaP XML.
- ``ki67_basic`` (code=1): two phases Ki67- / Ki67+. Ki67- -> Ki67+ is
  stochastic, Ki67+ -> Ki67- is fixed-duration with division_at_exit.

Advances every living cell's ``cycle_phase_idx`` and ``cycle_elapsed``
columns and sets the ``flagged_for_division`` bool column when a phase
whose ``division_at_exit`` is True fires a transition. The division
kernel then acts on that flag.

For cells already in a death process (``death_phase_idx`` != -1) the
cycle is skipped, matching PhysiCell's short-circuit when the death
cycle model takes over.
"""

from typing import Any, Dict, Optional

import numpy as np

from src.workflow.decorators import register_function
from src.workflow.logging import log

# PhysiCell live-cells default rate = 0.0432 / 60 ~= 7.2e-4 1/min
# Prostate LNCaP uses 0.0003155 1/min (≈52h cycle)
_DEFAULT_LIVE_RATE = 0.0003155


@register_function(
    display_name="Update Cycle (PhysiCell)",
    description=(
        "Advance per-cell cycle phase (live_cells or ki67_basic). "
        "Flags cells for division when their phase exits. Skips cells in "
        "a death process."
    ),
    category="INTERCELLULAR",
    parameters=[
        {"name": "dt", "type": "FLOAT",
         "description": "Time step (minutes). If <=0, use context['dt'].",
         "default": 0.0, "min_value": 0.0, "max_value": 60.0},
        {"name": "model", "type": "STRING",
         "description": "Cycle model: 'live' (single phase) or 'ki67_basic'.",
         "default": "live", "options": ["live", "ki67_basic"]},
        {"name": "live_rate", "type": "FLOAT",
         "description": "Live -> Live transition rate (1/min). LNCaP default.",
         "default": _DEFAULT_LIVE_RATE, "min_value": 0.0, "max_value": 1.0},
        {"name": "ki67_minus_rate", "type": "FLOAT",
         "description": "Ki67- -> Ki67+ stochastic rate (1/min).",
         "default": 1.0 / (4.59 * 60.0), "min_value": 0.0, "max_value": 1.0},
        {"name": "ki67_plus_duration", "type": "FLOAT",
         "description": "Ki67+ fixed duration (minutes).",
         "default": 15.5 * 60.0, "min_value": 0.0, "max_value": 1e6},
        {"name": "verbose", "type": "BOOL",
         "description": "Enable detailed logging.",
         "default": None},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def update_cycle_physicell(
    context: Dict[str, Any],
    dt: float = 0.0,
    model: str = "live",
    live_rate: float = _DEFAULT_LIVE_RATE,
    ki67_minus_rate: float = 1.0 / (4.59 * 60.0),
    ki67_plus_duration: float = 15.5 * 60.0,
    verbose: Optional[bool] = None,
    **kwargs,
) -> bool:
    from src.biology.cell_container import CellContainer

    container = context.get("cell_container")
    if not isinstance(container, CellContainer):
        log(context, "update_cycle_physicell requires context['cell_container']",
            prefix="[Cyc]", node_verbose=verbose)
        return False

    N = container.count
    if N == 0:
        return True

    step_dt = dt if dt > 0 else float(context.get("dt", 6.0))

    phase_idx = _ensure_float(container, "cycle_phase_idx", 0.0)
    elapsed = _ensure_float(container, "cycle_elapsed", 0.0)
    flag_div = _ensure_bool(container, "flagged_for_division", False)
    death_phase = _ensure_float(container, "death_phase_idx", -1.0)

    alive = container.alive[:N]
    dying = death_phase[:N] >= 0.0
    active = alive & (~dying)

    # Advance elapsed clock on active cells
    elapsed[:N] = np.where(active, elapsed[:N] + step_dt, elapsed[:N])

    # Reset division flag for cells not currently in an exit
    flag_div[:N] = np.where(active, False, flag_div[:N])

    n_div = 0
    if model == "live":
        # single phase, stochastic self-loop, division_at_exit
        prob = 1.0 - np.exp(-live_rate * step_dt)
        draw = np.random.random(N)
        transition = active & (draw < prob)
        flag_div[:N] = flag_div[:N] | transition
        # reset elapsed on transition
        elapsed[:N] = np.where(transition, 0.0, elapsed[:N])
        n_div = int(transition.sum())
    elif model == "ki67_basic":
        cur = phase_idx[:N].astype(np.int32)
        # Phase 0 -> 1 stochastic, no division
        prob_m = 1.0 - np.exp(-ki67_minus_rate * step_dt)
        in_minus = active & (cur == 0)
        t_m = in_minus & (np.random.random(N) < prob_m)
        # Phase 1 -> 0 fixed duration, division at exit
        in_plus = active & (cur == 1)
        t_p = in_plus & (elapsed[:N] >= ki67_plus_duration - 0.5 * step_dt)
        phase_idx[:N] = np.where(t_m, 1.0, phase_idx[:N])
        phase_idx[:N] = np.where(t_p, 0.0, phase_idx[:N])
        flag_div[:N] = flag_div[:N] | t_p
        elapsed[:N] = np.where(t_m | t_p, 0.0, elapsed[:N])
        n_div = int(t_p.sum())
    else:
        log(context, f"unknown cycle model '{model}', skipping", prefix="[Cyc]", node_verbose=verbose)
        return False

    log(context, f"cycle step: N={N}, dt={step_dt:.2f}, model={model}, flagged={n_div}",
        prefix="[Cyc]", node_verbose=verbose)
    return True


def _ensure_float(container, name: str, default: float) -> np.ndarray:
    if not container.has_column(name):
        return container.add_float_column(name, default=default)
    return container.get_float(name)


def _ensure_bool(container, name: str, default: bool) -> np.ndarray:
    if name not in container._bool_columns:
        return container.add_bool_column(name, default=default)
    return container.get_bool(name)
