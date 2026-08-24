"""
ON-CHANGE steady-state solve for the growth-factor/signalling substances.

Event-driven variant of run_growth_factor_solver: the single implicit steady
solve (production explicit where the substance's gene node is ON, first-order
uptake folded into the matrix) runs ONLY when the discrete cell state it
depends on changed since the last solve; otherwise the previous solution is
kept — exact, because given that discrete state the system is linear with a
unique steady state.

WHAT TRIGGERS A RE-SOLVE (signature owned by _field_signature.py): per cell —
position/membership, phenotype (fate-weight stand-in), and the watched gene
nodes that gate production: each substance's own gene node (default
TGFA,FGF,HGF,GI, matching _add_growth_factor_reactions). Plus this node's own
parameters. Flips of any other gene never enter these PDEs and are ignored.

Pair with Run Diffusion Solver (Metabolic, ON-CHANGE Steady).
"""

from typing import Any, Dict, Optional

from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always
from src.workflow.functions.diffusion.run_diffusion_solver_coupled import (
    _add_growth_factor_reactions,
)
from src.workflow.functions.diffusion._field_signature import (
    collect_field_signature,
    describe_change,
)


@register_function(
    requires=['population', 'simulator'],
    typed_env_exempt=True,
    display_name="Run Growth Factor Solver (Steady, ON-CHANGE)",
    description="Steady-state solve of the growth-factor/signalling substances "
                "(default TGFA,FGF,HGF,GI; gene-gated production, implicit "
                "first-order uptake), re-run ONLY when the discrete state it "
                "depends on changed since the last solve: the watched genes "
                "gating production (default the substances' own gene nodes), "
                "any phenotype change, any cell added/removed/moved, or a "
                "parameter change. Otherwise the previous fields are kept — "
                "exact, since the steady state is unique given that discrete "
                "state. Every solve logs its trigger. Pair with Run Diffusion "
                "Solver (Metabolic, ON-CHANGE Steady).",
    category="DIFFUSION",
    parameters=[
        {
            "name": "substances",
            "type": "STRING",
            "description": "Comma-separated growth-factor substances to solve",
            "default": "TGFA,FGF,HGF,GI"
        },
        {
            "name": "watched_genes",
            "type": "STRING",
            "description": "Gene nodes whose flips change the production/uptake "
                           "pattern and therefore trigger a re-solve (each "
                           "substance's own gene node, per "
                           "_add_growth_factor_reactions). Flips of any other "
                           "gene are ignored by design.",
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
def run_growth_factor_solver_on_change(
    context: Dict[str, Any],
    substances: str = "TGFA,FGF,HGF,GI",
    watched_genes: str = "TGFA,FGF,HGF,GI",
    verbose: Optional[bool] = None,
    **kwargs
) -> None:
    """Steady growth-factor solve, skipped exactly while its fixed point is unchanged.

    See the module docstring for the trigger set.
    """
    simulator = context.get('simulator')
    population = context.get('population')

    if simulator is None:
        log_always("[run_growth_factor_solver_on_change] No simulator in context - cannot run.")
        return
    if population is None:
        log_always("[run_growth_factor_solver_on_change] No population - nothing produces or consumes; skipping.")
        return

    requested = [s.strip() for s in substances.split(',') if s.strip()]
    names = [s for s in requested if s in simulator.state.substances]
    missing = set(requested) - set(names)
    if missing:
        log_always(f"[run_growth_factor_solver_on_change] Substances not registered, skipping: {sorted(missing)}")
    if not names:
        log_always("[run_growth_factor_solver_on_change] No requested substance is registered - nothing to solve.")
        return
    watched = [g.strip() for g in watched_genes.split(',') if g.strip()]

    signature = collect_field_signature(
        population, watched, params=(tuple(names), tuple(watched)))

    store = context.setdefault('_steady_on_change', {})
    entry = store.get('growth_factors')
    if entry is None:
        # R1.5: announce the effective law once per run.
        log_always("[STEADY-ON-CHANGE] growth factors: steady-state fields are "
                   "re-equilibrated only when the field-relevant discrete state "
                   f"changes (watched genes: {watched}; plus phenotype, cell "
                   "membership/positions, parameters); otherwise the previous "
                   "solution is exact and kept")

    reason = describe_change(entry['signature'] if entry else None, signature)
    if reason is None:
        entry['skips'] += 1
        log(context,
            f"growth-factor fields kept — no field-relevant change "
            f"({entry['skips']} consecutive skip(s))",
            prefix="[STEADY-ON-CHANGE]", node_verbose=verbose)
        return

    skipped = entry['skips'] if entry else 0
    solves = (entry['solves'] if entry else 0) + 1
    after = f" (after {skipped} skipped step(s))" if skipped else ""
    log_always(f"[STEADY-ON-CHANGE] growth factors: re-solving — {reason}{after} "
               f"[solve #{solves}]")

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
            prefix="[STEADY-ON-CHANGE]", node_verbose=verbose)

    store['growth_factors'] = {'signature': signature, 'skips': 0, 'solves': solves}
