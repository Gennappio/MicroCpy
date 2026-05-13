"""Prostate MaBoSS step — generic coupling + anti_<target> overrides.

Behaves like the engine's generic ``run_physiboss_step`` (substance conc ->
BN inputs via coupling -> per-cell MaBoSS run -> bn_prob_<node> columns),
but also forces the anti_<target> input nodes from
``context['prostate_anti_istates']`` populated by
``apply_drug_sensitivity_inputs``.

This mirrors the native C++ flow where ``pre_update_intracellular`` writes
drug-sensitivity boolean overrides that take effect in the next MaBoSS
propagation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from src.workflow.decorators import register_function
from src.workflow.logging import log


@register_function(
    display_name="Prostate: Run PhysiBoSS Step",
    description=(
        "Run one MaBoSS step per cell. Applies generic PhysiBoss coupling "
        "for substrate inputs AND forces anti_<target> BN nodes previously "
        "set by 'Prostate: Drug Sensitivity -> anti_* BN inputs'."
    ),
    category="INTRACELLULAR",
    parameters=[
        {"name": "verbose", "type": "BOOL",
         "description": "Enable per-step logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def run_prostate_physiboss_step(
    context: Dict[str, Any],
    verbose: Optional[bool] = False,
    **kwargs,
) -> None:
    from src.biology.cell_container import CellContainer, phenotype_id

    container = context.get("cell_container")
    if not isinstance(container, CellContainer):
        return

    maboss_sim = context.get("maboss_sim")
    if maboss_sim is None:
        return

    coupling = context.get("physiboss_coupling")
    simulator = context.get("simulator")
    N = container.count
    if N == 0:
        return

    dead_ids = {phenotype_id(p) for p in ("apoptotic", "necrotic", "dead", "removed")}
    alive = container.alive[:N].copy()
    for did in dead_ids:
        alive &= (container.phenotype_ids[:N] != did)
    alive_idx = np.where(alive)[0]
    if len(alive_idx) == 0:
        return

    positions = container.positions[alive_idx]
    substance_arrays = _sample_concentrations(simulator, positions)
    if coupling is not None:
        bn_input_arrays = coupling.compute_bn_inputs_vectorized(substance_arrays)
    else:
        bn_input_arrays = {}

    # Prostate anti_<target> overrides (already aligned with full container range).
    anti_istates: Dict[str, np.ndarray] = context.get("prostate_anti_istates", {}) or {}

    node_names = list(maboss_sim.network.keys())
    for node in node_names:
        col_prob = f"bn_prob_{node}"
        col_state = f"bn_state_{node}"
        if not container.has_column(col_prob):
            container.add_float_column(col_prob, default=0.0)
        if not container.has_column(col_state):
            container.add_bool_column(col_state, default=False)

    cells_done = 0
    for local_i, global_i in enumerate(alive_idx):
        # Generic coupling inputs.
        for node_name, state_arr in bn_input_arrays.items():
            if node_name in maboss_sim.network:
                state = bool(state_arr[local_i])
                maboss_sim.network.set_istate(
                    node_name, [0.0, 1.0] if state else [1.0, 0.0]
                )
        # Prostate drug-sensitivity overrides (take priority).
        for node_name, full_arr in anti_istates.items():
            if node_name in maboss_sim.network:
                state = bool(full_arr[global_i])
                maboss_sim.network.set_istate(
                    node_name, [0.0, 1.0] if state else [1.0, 0.0]
                )

        result = maboss_sim.run()
        probs = _extract_node_probabilities(result, node_names)
        for node, prob in probs.items():
            container.get_float(f"bn_prob_{node}")[global_i] = prob
            container.get_bool(f"bn_state_{node}")[global_i] = (prob >= 0.5)
        cells_done += 1

    if cells_done > 0 and verbose:
        log(context, f"Prostate MaBoSS: {cells_done} cells updated",
            prefix="[Prostate]", node_verbose=verbose)


def _sample_concentrations(simulator, positions: np.ndarray) -> Dict[str, np.ndarray]:
    result: Dict[str, np.ndarray] = {}
    if simulator is None:
        return result
    try:
        if hasattr(simulator, "sample_at"):
            return simulator.sample_at(positions)
        if hasattr(simulator, "get_concentrations_at_positions"):
            return simulator.get_concentrations_at_positions(positions)
        if hasattr(simulator, "substances"):
            N = positions.shape[0]
            for name in simulator.substances:
                arr = np.zeros(N, dtype=np.float64)
                for i in range(N):
                    arr[i] = simulator.get_substance_concentration(
                        name, positions[i, 0], positions[i, 1]
                    )
                result[name] = arr
    except Exception:
        pass
    return result


def _extract_node_probabilities(result, node_names) -> Dict[str, float]:
    probs: Dict[str, float] = {}
    try:
        last = result.get_last_nodes_probtraj()
        if hasattr(last, "iloc"):
            row = last.iloc[-1]
            for node in node_names:
                probs[node] = float(row.get(node, 0.0))
        else:
            for node in node_names:
                probs[node] = float(last.get(node, 0.0))
        return probs
    except Exception:
        pass
    try:
        final = result.get_last_states_probtraj()
        row = final.iloc[-1].to_dict() if hasattr(final, "iloc") else dict(final)
        for node in node_names:
            p = 0.0
            for state_str, state_prob in row.items():
                if state_str == "Time":
                    continue
                active = set(state_str.replace(" ", "").split("--"))
                if node in active:
                    p += float(state_prob)
            probs[node] = p
    except Exception:
        for node in node_names:
            probs[node] = 0.0
    return probs
