"""
PhysiBoss Phenotype Mapper - Translates MaBoSS output node probabilities
into OpenCellComms cell phenotype changes (apoptosis, necrosis, proliferation).

This module bridges between PhysiCell's rate-based phenotype model and
OpenCellComms' discrete phenotype states.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PhysiBossPhenotypeMapper:
    """
    Maps PhysiCell-style death/proliferation rates to OpenCellComms phenotypes.

    PhysiCell uses continuous rates (e.g. apoptosis_rate = 1e6 means almost certain
    death per dt).  OpenCellComms uses discrete phenotype strings.  This mapper
    converts rates into stochastic decisions.

    Attributes:
        dt_phenotype: Time step for phenotype updates (minutes).
    """
    dt_phenotype: float = 6.0

    def apply_rates(
        self,
        cell_rates: Dict[str, float],
        current_phenotype: str,
        dt: Optional[float] = None,
    ) -> str:
        """
        Apply phenotype rates to determine the cell's new phenotype.

        Decision priority (matching PhysiCell):
        1. Necrosis (if necrosis rate > 0)
        2. Apoptosis (if apoptosis rate > 0)
        3. Proliferation (if cycle entry rate > 0 and not dying)

        Each decision is stochastic: probability = 1 - exp(-rate * dt).

        Args:
            cell_rates: Dict of behaviour_name → rate value.
            current_phenotype: Current phenotype string.
            dt: Time step in minutes. Uses self.dt_phenotype if not specified.

        Returns:
            New phenotype string.
        """
        if dt is None:
            dt = self.dt_phenotype

        # Don't change phenotype of already-dead cells
        if current_phenotype in ("apoptotic", "necrotic", "dead"):
            return current_phenotype

        # 1. Check necrosis
        necrosis_rate = cell_rates.get("necrosis", 0.0)
        if necrosis_rate > 0:
            prob = 1.0 - _safe_exp(-necrosis_rate * dt)
            if random.random() < prob:
                return "necrotic"

        # 2. Check apoptosis
        apoptosis_rate = cell_rates.get("apoptosis", 0.0)
        if apoptosis_rate > 0:
            prob = 1.0 - _safe_exp(-apoptosis_rate * dt)
            if random.random() < prob:
                return "apoptotic"

        # 3. Check proliferation (cycle entry)
        # PhysiCell uses transition rates between cycle phases.
        # For simplicity, we check if any proliferation-related rate is set.
        proliferation_rate = cell_rates.get("proliferation", 0.0)
        if proliferation_rate <= 0:
            proliferation_rate = cell_rates.get("cycle_entry", 0.0)
        if proliferation_rate > 0:
            prob = 1.0 - _safe_exp(-proliferation_rate * dt)
            if random.random() < prob:
                return "Proliferation"

        # No fate change
        return current_phenotype

    # ── Vectorized interface ────────────────────────────────────────────

    def apply_rates_vectorized(
        self,
        cell_rates: "Dict[str, np.ndarray]",
        current_phenotype_ids: "np.ndarray",
        dt: "Optional[float]" = None,
    ) -> "np.ndarray":
        """
        Vectorized stochastic fate decisions for all cells at once.

        Args:
            cell_rates: {behaviour_name: ndarray float64 (N,)} — rates per cell.
            current_phenotype_ids: ndarray int32 (N,) — current phenotype IDs.
            dt: Time step. Uses self.dt_phenotype if not specified.

        Returns:
            ndarray int32 (N,) — new phenotype IDs.
        """
        import numpy as np
        from src.biology.cell_container import phenotype_id

        if dt is None:
            dt = self.dt_phenotype

        N = len(current_phenotype_ids)
        new_phenos = current_phenotype_ids.copy()
        rng = np.random.random(N)

        # Dead cells mask — don't change these
        apoptotic_id = phenotype_id("apoptotic")
        necrotic_id = phenotype_id("necrotic")
        dead_id = phenotype_id("dead")
        removed_id = phenotype_id("removed")
        dead_mask = (
            (current_phenotype_ids == apoptotic_id) |
            (current_phenotype_ids == necrotic_id) |
            (current_phenotype_ids == dead_id) |
            (current_phenotype_ids == removed_id)
        )
        alive_mask = ~dead_mask

        # 1. Necrosis (highest priority)
        necrosis_rate = cell_rates.get("necrosis", np.zeros(N))
        necrosis_prob = 1.0 - np.exp(np.clip(-necrosis_rate * dt, -700, 0))
        necrosis_trigger = alive_mask & (rng < necrosis_prob)
        new_phenos[necrosis_trigger] = necrotic_id

        # Update alive_mask (cells that triggered necrosis can't also trigger apoptosis)
        alive_mask = alive_mask & ~necrosis_trigger
        rng2 = np.random.random(N)

        # 2. Apoptosis
        apoptosis_rate = cell_rates.get("apoptosis", np.zeros(N))
        apoptosis_prob = 1.0 - np.exp(np.clip(-apoptosis_rate * dt, -700, 0))
        apoptosis_trigger = alive_mask & (rng2 < apoptosis_prob)
        new_phenos[apoptosis_trigger] = apoptotic_id

        alive_mask = alive_mask & ~apoptosis_trigger
        rng3 = np.random.random(N)

        # 3. Proliferation
        prolif_rate = cell_rates.get("proliferation", np.zeros(N))
        if np.all(prolif_rate == 0):
            prolif_rate = cell_rates.get("cycle_entry", np.zeros(N))
        prolif_prob = 1.0 - np.exp(np.clip(-prolif_rate * dt, -700, 0))
        prolif_trigger = alive_mask & (rng3 < prolif_prob)
        new_phenos[prolif_trigger] = phenotype_id("Proliferation")

        return new_phenos


def _safe_exp(x: float) -> float:
    """Compute exp(x) clamping to prevent overflow."""
    if x < -700:
        return 0.0
    if x > 700:
        return float("inf")
    import math
    return math.exp(x)