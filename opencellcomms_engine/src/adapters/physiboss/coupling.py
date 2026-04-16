"""
PhysiBoss Substrate Coupling - Maps substance concentrations to MaBoSS inputs
and MaBoSS output nodes to cell phenotype rates.

This is the core adapter logic (~100 lines) that replaces the C++
MaBoSSIntracellular::update_inputs() and update_outputs() methods.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config_loader import InputMapping, OutputMapping


@dataclass
class PhysiBossSubstrateCoupling:
    """
    Bidirectional coupling between substance concentrations and MaBoSS nodes.

    Implements the same logic as PhysiBoss's MaBoSSIntracellular class:
    - compute_bn_inputs:  substance concentrations → boolean node states
    - apply_phenotype_outputs: MaBoSS node probabilities → cell fate rates
    """
    inputs: List[InputMapping] = field(default_factory=list)
    outputs: List[OutputMapping] = field(default_factory=list)

    def compute_bn_inputs(
        self, substance_concs: Dict[str, float]
    ) -> Dict[str, bool]:
        """
        Convert substance concentrations to boolean node states.

        For each input mapping:
        - activation: concentration >= threshold → True
        - inhibition: concentration >= threshold → False

        Smoothing (Hill function) is supported for continuous → discrete transitions.

        Args:
            substance_concs: Dict mapping substance name → concentration value.

        Returns:
            Dict mapping MaBoSS node name → boolean state.
        """
        bn_inputs: Dict[str, bool] = {}

        for inp in self.inputs:
            conc = substance_concs.get(inp.substance_name, 0.0)

            if inp.smoothing > 0:
                # Hill-function smoothing: sigmoid transition around threshold
                # P(ON) = conc^n / (conc^n + threshold^n) where n = smoothing
                n = inp.smoothing
                if inp.threshold > 0:
                    ratio = (conc / inp.threshold) ** n
                    prob = ratio / (1.0 + ratio)
                else:
                    prob = 1.0 if conc > 0 else 0.0
                active = prob >= 0.5
            else:
                # Simple threshold
                active = conc >= inp.threshold

            # Handle inactivation threshold (hysteresis)
            if inp.inact_threshold > 0 and conc < inp.inact_threshold:
                active = False

            # Apply action type
            if inp.action == "inhibition":
                active = not active

            bn_inputs[inp.node_name] = active

        return bn_inputs

    def apply_phenotype_outputs(
        self,
        bn_states: Dict[str, float],
        cell_rates: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Map MaBoSS output node probabilities to cell fate rates.

        For each output mapping:
        - If node is active (probability > 0.5): rate = value
        - If node is inactive: rate = base_value
        - Smoothing provides linear interpolation between base_value and value

        Args:
            bn_states: Dict mapping MaBoSS node name → probability [0,1].
            cell_rates: Current cell phenotype rates (modified in-place and returned).

        Returns:
            Updated cell_rates dict.
        """
        for out in self.outputs:
            prob = bn_states.get(out.node_name, 0.0)

            if out.smoothing > 0:
                # Linear interpolation: rate = base + prob * (value - base)
                rate = out.base_value + prob * (out.value - out.base_value)
            else:
                # Binary: use value if active, base_value otherwise
                if prob >= 0.5:
                    rate = out.value
                else:
                    rate = out.base_value

            # Apply action type
            if out.action == "inhibition":
                # Inhibition: node ON means LOWER rate
                rate = out.value + out.base_value - rate

            cell_rates[out.behaviour_name] = rate

        return cell_rates

    @classmethod
    def from_config(cls, coupling_config) -> "PhysiBossSubstrateCoupling":
        """Create from a CouplingConfig dataclass."""
        return cls(
            inputs=list(coupling_config.inputs),
            outputs=list(coupling_config.outputs),
        )


    # ── Vectorized (NumPy) interface ────────────────────────────────────

    def compute_bn_inputs_vectorized(
        self,
        substance_arrays: Dict[str, "np.ndarray"],
    ) -> Dict[str, "np.ndarray"]:
        """
        Vectorized: compute BN input states for ALL cells at once.

        Args:
            substance_arrays: {name: ndarray shape (N,)} — concentration per cell.

        Returns:
            {node_name: ndarray bool (N,)} — boolean input state per cell.
        """
        import numpy as np

        # Determine N from any array
        N = 0
        for arr in substance_arrays.values():
            N = len(arr)
            break

        bn_inputs: Dict[str, "np.ndarray"] = {}
        for inp in self.inputs:
            conc = substance_arrays.get(inp.substance_name, np.zeros(N))

            if inp.smoothing > 0:
                n = inp.smoothing
                if inp.threshold > 0:
                    ratio = (conc / inp.threshold) ** n
                    prob = ratio / (1.0 + ratio)
                else:
                    prob = np.where(conc > 0, 1.0, 0.0)
                active = prob >= 0.5
            else:
                active = conc >= inp.threshold

            if inp.inact_threshold > 0:
                active = active & (conc >= inp.inact_threshold)

            if inp.action == "inhibition":
                active = ~active

            bn_inputs[inp.node_name] = active

        return bn_inputs

    def apply_phenotype_outputs_vectorized(
        self,
        bn_probs: Dict[str, "np.ndarray"],
        N: int,
    ) -> Dict[str, "np.ndarray"]:
        """
        Vectorized: map BN output probabilities to cell fate rates for ALL cells.

        Args:
            bn_probs: {node_name: ndarray float64 (N,)} — per-cell node prob.
            N: Number of cells.

        Returns:
            {behaviour_name: ndarray float64 (N,)} — rate per cell.
        """
        import numpy as np

        cell_rates: Dict[str, "np.ndarray"] = {}
        for out in self.outputs:
            prob = bn_probs.get(out.node_name, np.zeros(N))

            if out.smoothing > 0:
                rate = out.base_value + prob * (out.value - out.base_value)
            else:
                rate = np.where(prob >= 0.5, out.value, out.base_value)

            if out.action == "inhibition":
                rate = out.value + out.base_value - rate

            cell_rates[out.behaviour_name] = rate

        return cell_rates