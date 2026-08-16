"""
Growth-factor diffusion solve — linear kinetics, one implicit pass.

One of the two halves of the split diffusion step (the other is
run_diffusion_solver_metabolic). Per the reference model the signalling
substances obey, per cell:

    consumption   R_S = γ_S,C · C_S · fate_weight     (first order in conc.)
    production    R_S = γ_S,P · fate_weight           (where the substance's
                                                       gene node is ON)

with fate_weight = 1 (normal/proliferating), 0.5 (growth-arrest),
0 (necrotic), and γ taken from each substance's uptake_rate /
production_rate in its resource configuration.

THE EQUATION. The uptake is folded into the PDE matrix as an implicit sink
(same mechanism as decay_rate); production is the explicit source:

    ∇·(D∇C) − k(x)·C = −P(x),   k(x) = Σ_cells γ_S,C · fate_weight / V_mesh

Putting the uptake in the matrix matters: with zero-flux (Neumann)
boundaries and net production — TGFA, FGF, GI here — the explicit form
∇·(D∇C) = −(P − γ_C·C_prev) is singular and has no steady state, so the
solver either froze the fields at 0 or dumped the imbalance into an
arbitrary constant. The implicit form is nonsingular whenever any cell
takes the substance up, and its steady state is the meaningful
production/uptake balance.

WHY NO PICARD LOOP. Given the gene states (set upstream by gene_update),
this system is LINEAR in C — one direct sparse-LU solve per substance is
exact. That is why growth factors get their own node instead of riding
along inside the metabolic node's coupling iterations.
"""

from typing import Dict, Any, Optional

from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always
from src.workflow.functions.diffusion.run_diffusion_solver_coupled import (
    _add_growth_factor_reactions,
)


@register_function(
    requires=['population', 'simulator'],
    typed_env_exempt=True,
    display_name="Run Growth Factor Solver",
    description="Steady-state solve of the growth-factor/signalling substances "
                "(default TGFA,FGF,HGF,GI): per-cell production γ_P where the "
                "substance's gene node is ON, first-order uptake γ_C·C folded "
                "into the PDE matrix as an implicit sink. Linear given the gene "
                "states, so a single direct solve — no coupling iterations. "
                "Pair with Run Diffusion Solver (Metabolic).",
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
def run_growth_factor_solver(
    context: Dict[str, Any],
    substances: str = "TGFA,FGF,HGF,GI",
    verbose: Optional[bool] = None,
    **kwargs
) -> None:
    """Solve the growth-factor fields once, with implicit first-order uptake.

    See the module docstring for the equations and why this is separate from
    the metabolic Picard solve.
    """
    simulator = context.get('simulator')
    population = context.get('population')

    if simulator is None:
        log_always("[run_growth_factor_solver] No simulator in context - cannot run.")
        return
    if population is None:
        log_always("[run_growth_factor_solver] No population - nothing produces or consumes; skipping.")
        return

    requested = [s.strip() for s in substances.split(',') if s.strip()]
    names = [s for s in requested if s in simulator.state.substances]
    missing = set(requested) - set(names)
    if missing:
        log_always(f"[run_growth_factor_solver] Substances not registered, skipping: {sorted(missing)}")
    if not names:
        log_always("[run_growth_factor_solver] No requested substance is registered - nothing to solve.")
        return

    # Production (explicit source) and uptake coefficients (implicit sink)
    production_reactions: Dict = {}
    implicit_sinks: Dict = {}
    _add_growth_factor_reactions(production_reactions, population, simulator, context,
                                 verbose=verbose, implicit_uptake_out=implicit_sinks,
                                 substance_names=names)

    simulator.update(production_reactions, implicit_sinks=implicit_sinks,
                     substance_filter=names)

    for name in names:
        field = simulator.state.substances[name].concentrations
        log(context, f"{name}: min={field.min():.3e} max={field.max():.3e} mM",
            prefix="[GROWTH-FACTOR]", node_verbose=verbose)
