"""Prostate BN -> cell-phenotype effects (post_update_intracellular port).

Python port of PhysiBoSS prostate boolean_model_interface.cpp::
    post_update_intracellular -> from_nodes_to_cell

Reads per-cell ``bn_prob_Apoptosis`` / ``bn_prob_Proliferation`` /
``bn_prob_Migration`` stored by the MaBoSS runner and updates cell state:

* ``Apoptosis`` ON  -> apoptosis rate  =
  ``base_apoptosis_rate * apoptosis_rate_multiplier``
* ``Proliferation`` ON -> proliferation rate =
  ``base_transition_rate * transition_rate_multiplier``
  (else ``base_transition_rate``)
* ``Migration``   ON  -> cell motile (speed / bias / persistence from params)

Rate decisions are stochastic (1 - exp(-rate * dt)); motility is a
deterministic switch on per-cell boolean columns.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from src.workflow.decorators import register_function
from src.workflow.logging import log


@register_function(
    display_name="Prostate: Apply BN -> Phenotype effects",
    description=(
        "Map Apoptosis / Proliferation / Migration BN outputs to "
        "OpenCellComms cell fate rates and motility state. Mirrors "
        "PhysiBoSS prostate/from_nodes_to_cell."
    ),
    category="INTERCELLULAR",
    parameters=[
        {"name": "verbose", "type": "BOOL",
         "description": "Log fate change counts", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def apply_prostate_boolean_effects(
    context: Dict[str, Any],
    verbose: Optional[bool] = False,
    **kwargs,
) -> None:
    from src.biology.cell_container import CellContainer, phenotype_id, phenotype_name

    container = context.get("cell_container")
    if not isinstance(container, CellContainer):
        return

    params: Dict[str, float] = context.get("prostate_params", {}) or {}
    base_apop = float(params.get("base_apoptosis_rate", 5.31667e-05))
    apop_mult = float(params.get("apoptosis_rate_multiplier", 5.0))
    base_transition = float(params.get("base_transition_rate", 0.0003155))
    transition_mult = float(params.get("transition_rate_multiplier", 2.0))

    mapper = context.get("physiboss_phenotype_mapper")
    pb_config = context.get("physiboss_config")
    dt = pb_config.timing.dt_phenotype if pb_config is not None else 6.0

    N = container.count
    if N == 0 or mapper is None:
        return

    # ── BN probability columns (default to zeros if the MaBoSS runner didn't fill them) ──
    def _prob(col: str) -> np.ndarray:
        if container.has_column(col):
            return container.get_float(col)[:N]
        return np.zeros(N, dtype=np.float64)

    apop_prob = _prob("bn_prob_Apoptosis")
    prolif_prob = _prob("bn_prob_Proliferation")
    mig_prob = _prob("bn_prob_Migration")

    # ── Rates (prostate switch implementation) ───────────────────────────
    apop_rate = np.where(apop_prob >= 0.5, base_apop * apop_mult, base_apop)
    prolif_rate = np.where(
        prolif_prob >= 0.5, base_transition * transition_mult, base_transition
    )

    cell_rates: Dict[str, np.ndarray] = {
        "apoptosis": apop_rate,
        "proliferation": prolif_rate,
        "necrosis": np.zeros(N, dtype=np.float64),
    }

    # ── Vectorized stochastic fate ───────────────────────────────────────
    old_phenos = container.phenotype_ids[:N].copy()
    new_phenos = mapper.apply_rates_vectorized(cell_rates, old_phenos, dt)
    container.phenotype_ids[:N] = new_phenos

    # ── Motility switch (Migration node) ─────────────────────────────────
    mig_on = mig_prob >= 0.5
    if container.has_column("motility_enabled"):
        container.get_bool("motility_enabled")[:N] = mig_on
    else:
        container.add_bool_column("motility_enabled", default=False)
        container.get_bool("motility_enabled")[:N] = mig_on

    mig_speed = float(params.get("migration_speed", 0.35))
    mig_bias = float(params.get("migration_bias", 0.0))
    mig_persistence = float(params.get("persistence", 2.0))
    if container.has_column("migration_speed"):
        container.get_float("migration_speed")[:N] = np.where(mig_on, mig_speed, 0.0)
    else:
        container.add_float_column("migration_speed", default=0.0)
        container.get_float("migration_speed")[:N] = np.where(mig_on, mig_speed, 0.0)
    if container.has_column("migration_bias"):
        container.get_float("migration_bias")[:N] = np.where(mig_on, mig_bias, 0.0)
    if container.has_column("persistence_time"):
        container.get_float("persistence_time")[:N] = np.where(mig_on, mig_persistence, 0.0)

    # ── Logging ──────────────────────────────────────────────────────────
    if verbose:
        changed = old_phenos != new_phenos
        if int(changed.sum()) > 0:
            counts: Dict[str, int] = {}
            for pid in np.unique(new_phenos[changed]):
                counts[phenotype_name(int(pid))] = int(
                    (new_phenos[changed] == pid).sum()
                )
            parts = ", ".join(f"{k}: {v}" for k, v in counts.items())
            log(context, f"Prostate phenotype changes: {parts}; "
                         f"motile: {int(mig_on.sum())}/{N}",
                prefix="[Prostate]", node_verbose=verbose)
