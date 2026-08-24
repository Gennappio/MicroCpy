"""
TRANSIENT diffusion solve for the METABOLIC substances only.

The transient counterpart of run_diffusion_solver_metabolic: instead of
iterating the PDE and the per-cell metabolism to a steady-state fixed point
(Picard loop), each scheduler step advances the fields by ONE implicit
(backward) Euler step of

    ∂c/∂t = ∇·(D∇c) + S(x)

over the timestep owned by the Setup Simulation node (dt hours × 3600 → the
seconds the SI-unit PDE integrates; D is m²/s, sources mM/s). The
Michaelis-Menten cell metabolism is evaluated ONCE per step at the
start-of-step concentrations — the PhysiCell/PhysiBoSS operator-splitting
scheme. There is deliberately NO coupling loop: a Picard "did the solution
stop moving" test is meaningless for a field that is supposed to move each
step, and for the small dt this scheme targets a single evaluation is the
standard splitting error.

The metabolism law itself lives in _recalculate_metabolism (which defers to
the canvas metabolism node via context['metabolism_fn'] when present), the
reaction collection in _collect_reactions_from_cells — both shared with the
steady-state nodes, never copied. Explicit consumption can overdraw a voxel
within one step; negatives are clamped to 0 afterwards, same safety net as
the steady solve.

Pair with Run Growth Factor Solver (TRANSIENT), which advances the
signalling substances over the same dt.
"""

from typing import Dict, Any, Optional

from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always
from src.workflow.functions.diffusion.run_diffusion_solver_coupled import (
    _recalculate_metabolism,
    _collect_reactions_from_cells,
    _clamp_negative_concentrations,
)
from src.workflow.functions.initialization.setup_simulation import get_simulation_dt_hours


@register_function(
    requires=['population', 'simulator'],
    typed_env_exempt=True,
    display_name="Run Diffusion Solver (TRANSIENT Metabolic)",
    description="TRANSIENT solve of the metabolic substances (default "
                "Oxygen,Glucose,Lactate,H): ONE implicit (backward) Euler step "
                "of ∂c/∂t = ∇·(D∇c) + S per scheduler step, advancing the "
                "fields by dt from the Setup Simulation node (dt hours × 3600 s). "
                "Michaelis-Menten cell metabolism is evaluated ONCE at "
                "start-of-step concentrations (PhysiCell operator splitting — "
                "no Picard loop); negatives from explicit overdraw are clamped "
                "to 0. Pair with Run Growth Factor Solver (TRANSIENT).",
    category="DIFFUSION",
    parameters=[
        {
            "name": "substances",
            "type": "STRING",
            "description": "Comma-separated metabolic substances to solve",
            "default": "Oxygen,Glucose,Lactate,H"
        },
        {
            "name": "oxygen_conversion_factor",
            "type": "FLOAT",
            "description": "Oxygen consumption conversion factor (multiplier)",
            "default": 1.0,
            "min_value": 0.0
        },
        {
            "name": "glucose_conversion_factor",
            "type": "FLOAT",
            "description": "Glucose consumption conversion factor (multiplier)",
            "default": 1.0,
            "min_value": 0.0
        },
        {
            "name": "lactate_conversion_factor",
            "type": "FLOAT",
            "description": "Lactate production conversion factor (multiplier)",
            "default": 1.0,
            "min_value": 0.0
        },
        {
            "name": "oxygen_consumption_multiplier",
            "type": "FLOAT",
            "description": "Multiplier for mitoATP oxygen consumption (replaces hardcoded 50x)",
            "default": 1.0,
            "min_value": 0.0
        },
        {
            "name": "verbose",
            "type": "BOOL",
            "description": "Enable detailed logging (None = use global setting)",
            "default": None
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def run_diffusion_solver_transient_metabolic(
    context: Dict[str, Any],
    substances: str = "Oxygen,Glucose,Lactate,H",
    oxygen_conversion_factor: float = 1.0,
    glucose_conversion_factor: float = 1.0,
    lactate_conversion_factor: float = 1.0,
    oxygen_consumption_multiplier: float = 1.0,
    verbose: Optional[bool] = None,
    **kwargs
) -> None:
    """Advance the metabolic fields by one implicit Euler dt step.

    See the module docstring for the scheme and why there is no Picard loop.
    """
    simulator = context.get('simulator')
    population = context.get('population')
    config = context.get('config')

    if simulator is None:
        log_always("[run_diffusion_solver_transient_metabolic] No simulator in context - cannot run.")
        return
    if population is None:
        log_always("[run_diffusion_solver_transient_metabolic] No population - nothing consumes or produces; skipping.")
        return

    substance_filter = [s.strip() for s in substances.split(',') if s.strip()]
    if not substance_filter:
        log_always("[run_diffusion_solver_transient_metabolic] Empty substance list - nothing to solve.")
        return

    dt_hours = get_simulation_dt_hours(context)
    dt_seconds = dt_hours * 3600.0
    # R1.5: announce the effective law once per run, unconditionally (per-step
    # repeats stay behind the verbosity gate below).
    if not context.get('_transient_metabolic_logged'):
        context['_transient_metabolic_logged'] = True
        log_always(f"[TRANSIENT-METABOLIC] TRANSIENT implicit Euler: dt = {dt_hours:g} h "
                   f"({dt_seconds:g} s) from Setup Simulation (config.time.dt); "
                   f"substances = {substance_filter}; metabolism evaluated once at "
                   f"start-of-step concentrations (no Picard loop)")
    else:
        log(context,
            f"TRANSIENT implicit Euler step: dt = {dt_hours:g} h ({dt_seconds:g} s); "
            f"substances = {substance_filter}",
            prefix="[TRANSIENT-METABOLIC]", node_verbose=verbose)

    # Metabolism at c^n, once (honours the canvas metabolism node via
    # context['metabolism_fn']).
    _recalculate_metabolism(
        context, simulator, population, config,
        oxygen_conversion_factor=oxygen_conversion_factor,
        glucose_conversion_factor=glucose_conversion_factor,
        lactate_conversion_factor=lactate_conversion_factor,
        oxygen_consumption_multiplier=oxygen_consumption_multiplier,
        verbose=verbose,
    )
    reactions = _collect_reactions_from_cells(
        population, simulator, context, verbose=verbose,
        include_growth_factors=False,
    )

    simulator.update(reactions, substance_filter=substance_filter,
                     transient_dt=dt_seconds)

    _clamp_negative_concentrations(simulator, context, verbose=verbose)

    for name in substance_filter:
        if name in simulator.state.substances:
            field = simulator.state.substances[name].concentrations
            log(context, f"{name}: min={field.min():.3e} max={field.max():.3e} mM",
                prefix="[TRANSIENT-METABOLIC]", node_verbose=verbose)
