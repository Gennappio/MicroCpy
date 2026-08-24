"""
TRANSIENT growth-factor diffusion solve — linear kinetics, one implicit step.

The transient counterpart of run_growth_factor_solver. Per the reference
model the signalling substances obey, per cell:

    consumption   R_S = γ_S,C · C_S · fate_weight     (first order in conc.)
    production    R_S = γ_S,P · fate_weight           (where the substance's
                                                       gene node is ON)

with γ taken from each substance's uptake_rate / production_rate in its
resource configuration (same collection helper as the steady node — shared,
not copied). Each scheduler step advances the fields by ONE implicit
(backward) Euler step of

    ∂C/∂t = ∇·(D∇C) − k(x)·C + P(x),   k(x) = Σ_cells γ_S,C · fate_weight / V_mesh

over the timestep owned by the Setup Simulation node (dt hours × 3600 s).
Production is explicit at the gene states set upstream by gene_update;
uptake is folded into the matrix as an implicit sink, so the step is
unconditionally positivity-preserving (no clamp needed) and the matrix is
nonsingular for any boundary type — the TransientTerm additionally puts
V/dt on the diagonal, so even the zero-flux TGFA/FGF/GI fields that made
the steady coupled solve singular are unconditionally well-posed here.

Pair with Run Diffusion Solver (TRANSIENT Metabolic), which advances the
metabolic substances over the same dt.
"""

from typing import Dict, Any, Optional

from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always
from src.workflow.functions.diffusion.run_diffusion_solver_coupled import (
    _add_growth_factor_reactions,
)
from src.workflow.functions.initialization.setup_simulation import get_simulation_dt_hours


@register_function(
    requires=['population', 'simulator'],
    typed_env_exempt=True,
    display_name="Run Growth Factor Solver (TRANSIENT)",
    description="TRANSIENT solve of the growth-factor/signalling substances "
                "(default TGFA,FGF,HGF,GI): one implicit (backward) Euler step "
                "of ∂C/∂t = ∇·(D∇C) − k(x)·C + P(x) per scheduler step over dt "
                "from the Setup Simulation node. Per-cell production γ_P where "
                "the substance's gene node is ON (explicit, at the gene states "
                "set by the previous gene_update); first-order uptake γ_C·C "
                "folded into the matrix as an implicit sink — positivity-"
                "preserving. Rates from each substance's uptake_rate/"
                "production_rate in its Resources configuration. Pair with Run "
                "Diffusion Solver (TRANSIENT Metabolic).",
    category="DIFFUSION",
    parameters=[
        {
            "name": "substances",
            "type": "STRING",
            "description": "Comma-separated growth-factor substances to solve",
            "default": "TGFA,FGF,HGF,GI"
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
def run_diffusion_solver_transient_growth_factors(
    context: Dict[str, Any],
    substances: str = "TGFA,FGF,HGF,GI",
    verbose: Optional[bool] = None,
    **kwargs
) -> None:
    """Advance the growth-factor fields by one implicit Euler dt step.

    See the module docstring for the equations and the explicit/implicit
    split of production vs uptake.
    """
    simulator = context.get('simulator')
    population = context.get('population')

    if simulator is None:
        log_always("[run_diffusion_solver_transient_growth_factors] No simulator in context - cannot run.")
        return
    if population is None:
        log_always("[run_diffusion_solver_transient_growth_factors] No population - nothing produces or consumes; skipping.")
        return

    requested = [s.strip() for s in substances.split(',') if s.strip()]
    names = [s for s in requested if s in simulator.state.substances]
    missing = set(requested) - set(names)
    if missing:
        log_always(f"[run_diffusion_solver_transient_growth_factors] Substances not registered, skipping: {sorted(missing)}")
    if not names:
        log_always("[run_diffusion_solver_transient_growth_factors] No requested substance is registered - nothing to solve.")
        return

    dt_hours = get_simulation_dt_hours(context)
    dt_seconds = dt_hours * 3600.0
    # R1.5: announce the effective law once per run, unconditionally (per-step
    # repeats stay behind the verbosity gate below).
    if not context.get('_transient_gf_logged'):
        context['_transient_gf_logged'] = True
        log_always(f"[TRANSIENT-GF] TRANSIENT implicit Euler: dt = {dt_hours:g} h "
                   f"({dt_seconds:g} s) from Setup Simulation (config.time.dt); "
                   f"substances = {names}; production explicit at current gene "
                   f"states, uptake implicit in the matrix")
    else:
        log(context,
            f"TRANSIENT implicit Euler step: dt = {dt_hours:g} h ({dt_seconds:g} s); "
            f"substances = {names}",
            prefix="[TRANSIENT-GF]", node_verbose=verbose)

    # Production (explicit source) and uptake coefficients (implicit sink)
    production_reactions: Dict = {}
    implicit_sinks: Dict = {}
    _add_growth_factor_reactions(production_reactions, population, simulator, context,
                                 verbose=verbose, implicit_uptake_out=implicit_sinks,
                                 substance_names=names)

    simulator.update(production_reactions, implicit_sinks=implicit_sinks,
                     substance_filter=names, transient_dt=dt_seconds)

    for name in names:
        field = simulator.state.substances[name].concentrations
        log(context, f"{name}: min={field.min():.3e} max={field.max():.3e} mM",
            prefix="[TRANSIENT-GF]", node_verbose=verbose)
