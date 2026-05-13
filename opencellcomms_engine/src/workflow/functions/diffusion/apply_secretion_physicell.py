"""
PhysiCell-faithful secretion / uptake from the CellContainer.

For each alive cell, reads per-substrate rates from container columns
(``uptake_rate_<sub>``, ``secretion_rate_<sub>``,
``saturation_density_<sub>``, ``net_export_rate_<sub>``) and the local
substrate concentration from the simulator, then builds the PhysiCell
source term

    dρ/dt = (V_cell / V_voxel) * (S*(ρ* - ρ) - U*ρ + E)

converted to ``mol/s/cell`` (the convention expected by
``MultiSubstanceSimulator._create_source_field_from_reactions``). The
result is stashed in ``context['container_substance_reactions']`` and
merged by the coupled diffusion solver's reaction-collection step.

Rate columns are created lazily from a ``substance_rates`` dict
parameter so the prostate adapter (and any other) can seed them from
XML without touching this kernel.
"""

from typing import Any, Dict, Optional

import numpy as np

from src.workflow.decorators import register_function
from src.workflow.logging import log


@register_function(
    display_name="Apply Secretion/Uptake (PhysiCell)",
    description=(
        "Build per-cell PhysiCell secretion/uptake source terms from the "
        "CellContainer and stash them for the diffusion solver. Reads "
        "substance rates from per-cell columns (auto-populated from the "
        "'substance_rates' dict parameter on first call)."
    ),
    category="DIFFUSION",
    parameters=[
        {
            "name": "substance_rates",
            "type": "DICT",
            "description": (
                "Per-substrate default rates, e.g. "
                "{'oxygen': {'uptake_rate': 10.0, 'secretion_rate': 0.0, "
                "'saturation_density': 38.0, 'net_export_rate': 0.0}}. "
                "Rates in 1/min; saturation_density in same units as the "
                "substrate field."
            ),
            "default": {},
        },
        {"name": "verbose", "type": "BOOL",
         "description": "Enable detailed logging.",
         "default": None},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def apply_secretion_physicell(
    context: Dict[str, Any],
    substance_rates: Optional[Dict[str, Dict[str, float]]] = None,
    verbose: Optional[bool] = None,
    **kwargs,
) -> bool:
    from src.biology.cell_container import CellContainer

    container = context.get("cell_container")
    simulator = context.get("simulator")
    if not isinstance(container, CellContainer) or simulator is None:
        context["container_substance_reactions"] = {}
        return True

    N = container.count
    if N == 0:
        context["container_substance_reactions"] = {}
        return True

    rates = substance_rates or context.get("physicell_substance_rates", {})
    substances = list(getattr(simulator.state, "substances", {}).keys())
    if not substances:
        context["container_substance_reactions"] = {}
        return True

    # Lazily create per-substrate rate columns
    for sub in substances:
        defaults = rates.get(sub, {}) if isinstance(rates, dict) else {}
        _ensure(container, f"uptake_rate_{sub}", defaults.get("uptake_rate", 0.0))
        _ensure(container, f"secretion_rate_{sub}", defaults.get("secretion_rate", 0.0))
        _ensure(container, f"saturation_density_{sub}", defaults.get("saturation_density", 0.0))
        _ensure(container, f"net_export_rate_{sub}", defaults.get("net_export_rate", 0.0))

    # Sample local concentration per cell, per substrate. Positions are
    # simulation-unit floats; get_concentration_at accepts them.
    alive = container.alive[:N]
    positions = container.positions[:N]
    volumes_um3 = container.volumes[:N]
    V_cell_m3 = volumes_um3 * 1e-18

    reactions: Dict = {}
    for sub in substances:
        U = container.get_float(f"uptake_rate_{sub}")[:N]
        S = container.get_float(f"secretion_rate_{sub}")[:N]
        sat = container.get_float(f"saturation_density_{sub}")[:N]
        E = container.get_float(f"net_export_rate_{sub}")[:N]
        state = simulator.state.substances[sub]
        # Per-cell local density
        rho = np.empty(N, dtype=np.float64)
        for i in range(N):
            if not alive[i]:
                rho[i] = 0.0
                continue
            rho[i] = state.get_concentration_at(tuple(positions[i]))
        # dρ/dt (density/min) = S*(sat-rho) - U*rho + E
        drho_per_min = S * (sat - rho) - U * rho + E
        # per-cell mol/s contribution: V_cell_m3 * (dρ/min) / 60 / 1000
        # (density->mol/m3: 1 mM = 1 mol/m³)
        rate_mol_per_s = V_cell_m3 * drho_per_min / 60000.0
        rate_mol_per_s = np.where(alive, rate_mol_per_s, 0.0)
        for i in np.nonzero(rate_mol_per_s != 0.0)[0]:
            key = tuple(float(v) for v in positions[i])
            reactions.setdefault(key, {})[sub] = reactions.get(key, {}).get(sub, 0.0) \
                + float(rate_mol_per_s[i])

    context["container_substance_reactions"] = reactions
    log(context,
        f"secretion: N={N}, substrates={len(substances)}, "
        f"positions_with_flux={len(reactions)}",
        prefix="[Secr]", node_verbose=verbose)
    return True


def _ensure(container, name: str, default: float):
    if not container.has_column(name):
        container.add_float_column(name, default=default)
