"""
PhysiCell-faithful volume dynamics (standard_volume_update_function).

Vectorized NumPy reimplementation of PhysiCell_standard_models.cpp :: 
standard_volume_update_function. Evolves per-cell fluid, cytoplasmic solid
and nuclear solid volumes toward their targets with the three rate
constants, then updates derived volumes, total, fluid_fraction, and the
cell radius.

Operates on the CellContainer SoA layout. Lazily creates the columns it
needs with PhysiCell MCF-7 / prostate LNCaP defaults.
"""

from typing import Any, Dict, Optional

import numpy as np

from src.workflow.decorators import register_function
from src.workflow.logging import log


# PhysiCell MCF-7 reference values (also matches prostate LNCaP XML)
_DEF_TOTAL = 2494.0
_DEF_NUCLEAR = 540.0
_DEF_FLUID_FRAC = 0.75
_DEF_FLUID_RATE = 0.05          # 1/min
_DEF_CYTO_RATE = 0.0045         # 1/min
_DEF_NUC_RATE = 0.0055          # 1/min
_DEF_RELATIVE_RUPTURE = 2.0


@register_function(
    display_name="Update Volume (PhysiCell)",
    description=(
        "Evolve per-cell fluid, nuclear solid and cytoplasmic solid "
        "volumes toward their targets using PhysiCell's standard volume "
        "update function. Updates total volume, fluid fraction and radius."
    ),
    category="INTRACELLULAR",
    parameters=[
        {"name": "dt", "type": "FLOAT",
         "description": "Time step (minutes). If <=0, use context['dt'].",
         "default": 0.0, "min_value": 0.0, "max_value": 60.0},
        {"name": "verbose", "type": "BOOL",
         "description": "Enable detailed logging.",
         "default": None},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def update_volume_physicell(
    context: Dict[str, Any],
    dt: float = 0.0,
    verbose: Optional[bool] = None,
    **kwargs,
) -> bool:
    from src.biology.cell_container import CellContainer

    container = context.get("cell_container")
    if not isinstance(container, CellContainer):
        log(context, "update_volume_physicell requires context['cell_container']",
            prefix="[Vol]", node_verbose=verbose)
        return False

    N = container.count
    if N == 0:
        return True

    step_dt = dt if dt > 0 else float(context.get("dt", 6.0))

    # Lazily create per-cell state columns (defaults match PhysiCell MCF-7)
    fluid = _ensure_col(container, "volume_fluid", _DEF_FLUID_FRAC * _DEF_TOTAL)
    nuc_solid = _ensure_col(container, "volume_nuclear_solid",
                            (1.0 - _DEF_FLUID_FRAC) * _DEF_NUCLEAR)
    cyto_solid = _ensure_col(container, "volume_cytoplasmic_solid",
                             (1.0 - _DEF_FLUID_FRAC) * (_DEF_TOTAL - _DEF_NUCLEAR))
    nuclear = _ensure_col(container, "volume_nuclear", _DEF_NUCLEAR)
    # Targets
    tgt_fluid_frac = _ensure_col(container, "volume_target_fluid_fraction", _DEF_FLUID_FRAC)
    tgt_nuc_solid = _ensure_col(container, "volume_target_solid_nuclear",
                                (1.0 - _DEF_FLUID_FRAC) * _DEF_NUCLEAR)
    tgt_cyto_solid = _ensure_col(container, "volume_target_solid_cytoplasmic",
                                 (1.0 - _DEF_FLUID_FRAC) * (_DEF_TOTAL - _DEF_NUCLEAR))
    tgt_ratio = _ensure_col(container, "volume_target_cyto_to_nuclear_ratio",
                            (_DEF_TOTAL - _DEF_NUCLEAR) / max(_DEF_NUCLEAR, 1e-16))
    # Per-cell rates (overridable via setup)
    r_fluid = _ensure_col(container, "volume_fluid_change_rate", _DEF_FLUID_RATE)
    r_cyto = _ensure_col(container, "volume_cytoplasmic_biomass_rate", _DEF_CYTO_RATE)
    r_nuc = _ensure_col(container, "volume_nuclear_biomass_rate", _DEF_NUC_RATE)
    calcified_frac = _ensure_col(container, "volume_calcified_fraction", 0.0)
    r_calc = _ensure_col(container, "volume_calcification_rate", 0.0)

    alive = container.alive[:N]
    total = container.volumes[:N]
    f = fluid[:N]; ns = nuc_solid[:N]; cs = cyto_solid[:N]; nu = nuclear[:N]

    # Fluid
    f_new = f + step_dt * r_fluid[:N] * (tgt_fluid_frac[:N] * total - f)
    np.clip(f_new, 0.0, None, out=f_new)
    # Split fluid by nuclear/total ratio
    nuclear_fluid = (nu / (total + 1e-16)) * f_new
    cytoplasmic_fluid = f_new - nuclear_fluid

    # Solids progress toward targets
    ns_new = ns + step_dt * r_nuc[:N] * (tgt_nuc_solid[:N] - ns)
    np.clip(ns_new, 0.0, None, out=ns_new)

    # Cytoplasmic target follows nucleus by ratio
    tgt_cyto_solid[:N] = tgt_ratio[:N] * tgt_nuc_solid[:N]
    cs_new = cs + step_dt * r_cyto[:N] * (tgt_cyto_solid[:N] - cs)
    np.clip(cs_new, 0.0, None, out=cs_new)

    # Recompose
    nuclear_new = ns_new + nuclear_fluid
    cytoplasmic_new = cs_new + cytoplasmic_fluid
    total_new = nuclear_new + cytoplasmic_new

    calcified_frac[:N] = calcified_frac[:N] + step_dt * r_calc[:N] * (1.0 - calcified_frac[:N])

    # Write back
    f[:] = np.where(alive, f_new, f)
    ns[:] = np.where(alive, ns_new, ns)
    cs[:] = np.where(alive, cs_new, cs)
    nu[:] = np.where(alive, nuclear_new, nu)
    total[:] = np.where(alive, total_new, total)
    # Radius from total (sphere)
    r = (3.0 * np.maximum(total, 1e-16) / (4.0 * np.pi)) ** (1.0 / 3.0)
    container.radii[:N] = np.where(alive, r, container.radii[:N])

    log(context, f"volume step: N={N}, dt={step_dt:.3f} min, "
        f"mean total={float(total.mean()):.1f} µm³",
        prefix="[Vol]", node_verbose=verbose)
    return True


def _ensure_col(container, name: str, default: float) -> np.ndarray:
    if not container.has_column(name):
        return container.add_float_column(name, default=default)
    return container.get_float(name)
