"""
PhysiCell-faithful death process kernel (apoptosis + necrosis).

Vectorized implementation of the death cycle models defined in
PhysiCell_standard_models.cpp. Handles:

1. **Entry**: any living cell whose phenotype was set to ``apoptotic`` or
   ``necrotic`` by the upstream phenotype mapper is initialized into the
   matching death model (sets targets to zero, rewrites volume change
   rates per the XML's <death><model><parameters>).
2. **Apoptosis progression**: single fixed-duration phase; the cell
   shrinks until ``elapsed >= 1/transition_rate``, then is flagged for
   removal.
3. **Necrosis progression**: two-phase model — unlysed (swelling) until
   ``total >= rupture_volume``, then lysed (slow fluid loss) for a fixed
   duration, then flagged for removal.

Uses the volume columns populated by ``update_volume_physicell``.
"""

from typing import Any, Dict, Optional

import numpy as np

from src.workflow.decorators import register_function
from src.workflow.logging import log


# PhysiCell codes
APOPTOSIS = 100
NECROSIS_UNLYSED = 101
NECROSIS_LYSED = 102
# Death phase codes stored in `death_phase_idx`: -1 = alive, 100 apop,
# 101 necrotic unlysed, 102 necrotic lysed.

# Prostate LNCaP XML defaults (unlysed/lysed fluid, nuc/cyto biomass)
_APOPTOSIS_FIXED_RATE = 0.00193798  # 1/min (~8.6h to removal)
_NECROSIS_LYSE_RATE = 1.15741e-5   # 1/min (unlysed -> lysed, fixed, ~24h)
_APOP_UNLYSED_FLUID_RATE = 0.05
_APOP_LYSED_FLUID_RATE = 0.0
_APOP_CYTO_BIOMASS_RATE = 1.66667e-02
_APOP_NUC_BIOMASS_RATE = 5.83333e-03
_NECRO_UNLYSED_FLUID_RATE = 0.05
_NECRO_LYSED_FLUID_RATE = 0.0
_NECRO_CYTO_BIOMASS_RATE = 1.66667e-02
_NECRO_NUC_BIOMASS_RATE = 5.83333e-03
_RELATIVE_RUPTURE = 2.0


@register_function(
    display_name="Update Death (PhysiCell)",
    description=(
        "Advance apoptotic and necrotic cells through PhysiCell death "
        "phases (swelling / lysis). Flags cells for removal when the "
        "death phase exits. Also initializes death-entry state the first "
        "time a cell becomes apoptotic/necrotic."
    ),
    category="INTERCELLULAR",
    parameters=[
        {"name": "dt", "type": "FLOAT",
         "description": "Time step (minutes). If <=0, use context['dt'].",
         "default": 0.0, "min_value": 0.0, "max_value": 60.0},
        {"name": "apoptosis_duration_rate", "type": "FLOAT",
         "description": "Apoptosis fixed-duration transition rate (1/min).",
         "default": _APOPTOSIS_FIXED_RATE, "min_value": 0.0, "max_value": 1.0},
        {"name": "necrosis_lyse_rate", "type": "FLOAT",
         "description": "Necrotic lysed -> removed rate (1/min, fixed).",
         "default": _NECROSIS_LYSE_RATE, "min_value": 0.0, "max_value": 1.0},
        {"name": "relative_rupture", "type": "FLOAT",
         "description": "Necrotic rupture volume as multiple of entry volume.",
         "default": _RELATIVE_RUPTURE, "min_value": 1.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL",
         "description": "Enable detailed logging.",
         "default": None},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def update_death_physicell(
    context: Dict[str, Any],
    dt: float = 0.0,
    apoptosis_duration_rate: float = _APOPTOSIS_FIXED_RATE,
    necrosis_lyse_rate: float = _NECROSIS_LYSE_RATE,
    relative_rupture: float = _RELATIVE_RUPTURE,
    verbose: Optional[bool] = None,
    **kwargs,
) -> bool:
    from src.biology.cell_container import CellContainer, phenotype_id

    container = context.get("cell_container")
    if not isinstance(container, CellContainer):
        log(context, "update_death_physicell requires context['cell_container']",
            prefix="[Death]", node_verbose=verbose)
        return False

    N = container.count
    if N == 0:
        return True
    step_dt = dt if dt > 0 else float(context.get("dt", 6.0))

    # Columns
    death_phase = _f(container, "death_phase_idx", -1.0)
    death_elapsed = _f(container, "death_elapsed", 0.0)
    flag_rem = _b(container, "flagged_for_removal", False)
    tgt_ff = _f(container, "volume_target_fluid_fraction", 0.75)
    tgt_ns = _f(container, "volume_target_solid_nuclear", 0.25 * 540.0)
    tgt_cs = _f(container, "volume_target_solid_cytoplasmic", 0.25 * 1954.0)
    tgt_ratio = _f(container, "volume_target_cyto_to_nuclear_ratio", 1954.0 / 540.0)
    r_fluid = _f(container, "volume_fluid_change_rate", 0.05)
    r_cyto = _f(container, "volume_cytoplasmic_biomass_rate", 0.0045)
    r_nuc = _f(container, "volume_nuclear_biomass_rate", 0.0055)
    rupture_vol = _f(container, "volume_rupture_volume", 0.0)

    alive = container.alive[:N]
    phenos = container.phenotype_ids[:N]
    apop_pid = phenotype_id("apoptotic")
    necro_pid = phenotype_id("necrotic")

    # ── 1. Entry: newly apoptotic / necrotic cells ────────────────────
    newly_apop = alive & (phenos == apop_pid) & (death_phase[:N] < 0.0)
    newly_necro = alive & (phenos == necro_pid) & (death_phase[:N] < 0.0)

    if np.any(newly_apop):
        death_phase[:N] = np.where(newly_apop, float(APOPTOSIS), death_phase[:N])
        death_elapsed[:N] = np.where(newly_apop, 0.0, death_elapsed[:N])
        tgt_ff[:N] = np.where(newly_apop, 0.0, tgt_ff[:N])
        tgt_ns[:N] = np.where(newly_apop, 0.0, tgt_ns[:N])
        tgt_cs[:N] = np.where(newly_apop, 0.0, tgt_cs[:N])
        tgt_ratio[:N] = np.where(newly_apop, 0.0, tgt_ratio[:N])
        r_fluid[:N] = np.where(newly_apop, _APOP_UNLYSED_FLUID_RATE, r_fluid[:N])
        r_cyto[:N] = np.where(newly_apop, _APOP_CYTO_BIOMASS_RATE, r_cyto[:N])
        r_nuc[:N] = np.where(newly_apop, _APOP_NUC_BIOMASS_RATE, r_nuc[:N])

    if np.any(newly_necro):
        death_phase[:N] = np.where(newly_necro, float(NECROSIS_UNLYSED), death_phase[:N])
        death_elapsed[:N] = np.where(newly_necro, 0.0, death_elapsed[:N])
        tgt_ff[:N] = np.where(newly_necro, 1.0, tgt_ff[:N])         # swell
        tgt_ns[:N] = np.where(newly_necro, 0.0, tgt_ns[:N])
        tgt_cs[:N] = np.where(newly_necro, 0.0, tgt_cs[:N])
        tgt_ratio[:N] = np.where(newly_necro, 0.0, tgt_ratio[:N])
        r_fluid[:N] = np.where(newly_necro, _NECRO_UNLYSED_FLUID_RATE, r_fluid[:N])
        r_cyto[:N] = np.where(newly_necro, _NECRO_CYTO_BIOMASS_RATE, r_cyto[:N])
        r_nuc[:N] = np.where(newly_necro, _NECRO_NUC_BIOMASS_RATE, r_nuc[:N])
        # rupture volume = relative * total at entry
        rupture_vol[:N] = np.where(
            newly_necro, relative_rupture * container.volumes[:N], rupture_vol[:N]
        )

    # ── 2. Progression ────────────────────────────────────────────────
    death_elapsed[:N] = np.where(death_phase[:N] >= 0.0,
                                 death_elapsed[:N] + step_dt, death_elapsed[:N])

    # Apoptosis: fixed duration -> remove
    apop_dur = 1.0 / max(apoptosis_duration_rate, 1e-30)
    in_apop = alive & (death_phase[:N] == APOPTOSIS)
    done_apop = in_apop & (death_elapsed[:N] >= apop_dur - 0.5 * step_dt)
    flag_rem[:N] = flag_rem[:N] | done_apop

    # Necrosis phase 0 (unlysed): swells until total >= rupture_vol
    total = container.volumes[:N]
    in_necro_u = alive & (death_phase[:N] == NECROSIS_UNLYSED)
    ruptured = in_necro_u & (total >= rupture_vol[:N]) & (rupture_vol[:N] > 0.0)
    if np.any(ruptured):
        # Transition to lysed: change fluid rate, reset elapsed
        death_phase[:N] = np.where(ruptured, float(NECROSIS_LYSED), death_phase[:N])
        death_elapsed[:N] = np.where(ruptured, 0.0, death_elapsed[:N])
        r_fluid[:N] = np.where(ruptured, _NECRO_LYSED_FLUID_RATE, r_fluid[:N])

    # Necrosis phase 1 (lysed): fixed-duration removal
    necro_lyse_dur = 1.0 / max(necrosis_lyse_rate, 1e-30)
    in_necro_l = alive & (death_phase[:N] == NECROSIS_LYSED)
    done_necro = in_necro_l & (death_elapsed[:N] >= necro_lyse_dur - 0.5 * step_dt)
    flag_rem[:N] = flag_rem[:N] | done_necro

    log(context,
        f"death step: N={N}, apop_in_flight={int(in_apop.sum())}, "
        f"necro_in_flight={int((in_necro_u | in_necro_l).sum())}, "
        f"to_remove={int((done_apop | done_necro).sum())}",
        prefix="[Death]", node_verbose=verbose)
    return True


def _f(container, name, default):
    if not container.has_column(name):
        return container.add_float_column(name, default=default)
    return container.get_float(name)


def _b(container, name, default):
    if name not in container._bool_columns:
        return container.add_bool_column(name, default=default)
    return container.get_bool(name)
