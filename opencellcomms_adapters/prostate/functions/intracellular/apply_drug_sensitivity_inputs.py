"""Prostate drug sensitivity -> anti_<target> BN inputs.

Python port of PhysiBoSS prostate boolean_model_interface.cpp::
    pre_update_intracellular -> set_input_nodes -> set_boolean_node

For every living cell, for every drug listed in ``context['prostate_drug_params']``:
  1. sample the drug concentration at the cell's position
  2. evaluate the two-parameter logistic dose-response curve
  3. draw a uniform random number; if it is <= inhibition (1 - viability),
     force the ``anti_<target>`` Boolean node ON for this cell's MaBoSS step.

Results are stored on the CellContainer as:
  * ``bn_state_anti_<target>`` - bool column (visible from the GUI)
  * ``bn_prob_anti_<target>``  - float column (inhibition probability)

and also copied into ``context['prostate_anti_istates']`` so that the
prostate MaBoSS runner can force the MaBoSS input states.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from src.workflow.decorators import register_function
from src.workflow.logging import log
from opencellcomms_adapters.prostate.drug_sensitivity import (
    DRUG_TARGETS,
    anti_target_node_name,
)


@register_function(
    display_name="Prostate: Drug Sensitivity -> anti_* BN inputs",
    description=(
        "Per cell, sample each prostate drug concentration, evaluate the "
        "GDSC two-parameter logistic dose-response, and stochastically set "
        "the matching anti_<target> BN input node. Mirrors "
        "PhysiBoSS prostate/pre_update_intracellular."
    ),
    category="INTRACELLULAR",
    parameters=[
        {"name": "verbose", "type": "BOOL",
         "description": "Log per-drug inhibition counts", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def apply_drug_sensitivity_inputs(
    context: Dict[str, Any],
    verbose: Optional[bool] = False,
    **kwargs,
) -> None:
    from src.biology.cell_container import CellContainer, phenotype_id

    container = context.get("cell_container")
    if not isinstance(container, CellContainer):
        return

    drug_params: Dict[str, Dict[str, float]] = context.get("prostate_drug_params", {}) or {}
    if not drug_params:
        return

    simulator = context.get("simulator")
    N = container.count
    if N == 0:
        return

    # Exclude dead cells from random draws (they don't re-enter BN).
    dead_ids = {phenotype_id(p) for p in ("apoptotic", "necrotic", "dead", "removed")}
    alive = container.alive[:N].copy()
    for did in dead_ids:
        alive &= (container.phenotype_ids[:N] != did)
    alive_idx = np.where(alive)[0]
    if len(alive_idx) == 0:
        return

    positions = container.positions[alive_idx]
    rng = np.random.default_rng()

    anti_istates: Dict[str, np.ndarray] = {}
    log_parts = []

    for drug_name, params in drug_params.items():
        node_name = anti_target_node_name(drug_name)
        if node_name is None:
            continue

        concs = _sample_drug_concentration(simulator, positions, drug_name)
        # Vectorized logistic: y_hat = 1 / (1 + exp((x - xmid) / scale)),
        # with x = log2(conc / max_conc) + 9, and viability = 1 when conc <= 0.
        max_conc = params["max_conc"]
        xmid = params["xmid"]
        scale = params["scale"]
        safe_conc = np.where(concs > 0, concs, np.nan)
        x = np.log2(safe_conc / max_conc) + 9.0
        viability = 1.0 / (1.0 + np.exp((x - xmid) / scale))
        viability = np.where(np.isnan(viability), 1.0, viability)
        inhibition = 1.0 - viability

        draw = rng.random(size=len(alive_idx))
        on = draw <= inhibition

        # Persist columns for GUI visibility / downstream inspection.
        bool_col = f"bn_state_{node_name}"
        prob_col = f"bn_prob_{node_name}"
        if not container.has_column(bool_col):
            container.add_bool_column(bool_col, default=False)
        if not container.has_column(prob_col):
            container.add_float_column(prob_col, default=0.0)
        container.get_bool(bool_col)[:N] = False
        container.get_float(prob_col)[:N] = 0.0
        container.get_bool(bool_col)[alive_idx] = on
        container.get_float(prob_col)[alive_idx] = inhibition

        # Per-cell bool array aligned with full container range -> drug runner.
        full = np.zeros(N, dtype=bool)
        full[alive_idx] = on
        anti_istates[node_name] = full

        log_parts.append(f"{drug_name}->{node_name}: {int(on.sum())}/{len(on)}")

    context["prostate_anti_istates"] = anti_istates
    if verbose and log_parts:
        log(context, "Prostate drug inhibition: " + "; ".join(log_parts),
            prefix="[Prostate]", node_verbose=verbose)


def _sample_drug_concentration(simulator, positions: np.ndarray, name: str) -> np.ndarray:
    """Return per-cell concentration of substance ``name``; 0 if unavailable."""
    N = positions.shape[0]
    if simulator is None:
        return np.zeros(N, dtype=np.float64)
    try:
        if hasattr(simulator, "sample_at"):
            arrs = simulator.sample_at(positions)
            if name in arrs:
                return np.asarray(arrs[name], dtype=np.float64)
        if hasattr(simulator, "get_concentrations_at_positions"):
            arrs = simulator.get_concentrations_at_positions(positions)
            if name in arrs:
                return np.asarray(arrs[name], dtype=np.float64)
        if hasattr(simulator, "get_substance_concentration"):
            out = np.zeros(N, dtype=np.float64)
            for i in range(N):
                out[i] = simulator.get_substance_concentration(
                    name, positions[i, 0], positions[i, 1]
                )
            return out
    except Exception:
        pass
    return np.zeros(N, dtype=np.float64)
