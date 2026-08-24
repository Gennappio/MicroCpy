"""
ON-CHANGE steady-state solve for the METABOLIC substances.

Event-driven variant of run_diffusion_solver_metabolic: the Picard-coupled
steady solve runs ONLY when the discrete cell state it depends on has changed
since the last converged solve; otherwise the previous solution is kept —
which is EXACT, not an approximation, because the steady fixed point is fully
determined by that discrete state (the Michaelis-Menten concentration
dependence is part of the fixed point, not an extra input).

WHAT TRIGGERS A RE-SOLVE (the signature, owned by _field_signature.py):
per cell — position/membership (division, removal, movement), phenotype
(stand-in for the fate weight), and the watched gene nodes that gate the
metabolic reaction laws: mitoATP and glycoATP (calculate_cell_metabolism
switches every consumption/production branch on them). Plus this node's own
parameters. Flips of any OTHER gene node never enter these PDEs and are
deliberately ignored — with a MaBoSS gene update most flips per step are in
such nodes, and re-solving on them would erase the benefit.

The semantics are quasi-steady-state made event-driven: genes evolve under
piecewise-constant fields; whenever a watched bit flips the fields jump to
the new equilibrium. Justified here because the fields equilibrate in
seconds of simulated time while gene transitions happen on the
1/maboss_time_scale-hour scale.

When it does solve, the law is exactly run_diffusion_solver_metabolic's:
the shared _run_coupled Picard loop with under-relaxation, metabolism
re-evaluated per coupling iteration via the canvas metabolism node's hook.
Pair with Run Growth Factor Solver (Steady, ON-CHANGE).
"""

from typing import Any, Dict, Optional

from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always
from src.workflow.functions.diffusion.run_diffusion_solver_coupled import _run_coupled
from src.workflow.functions.diffusion._field_signature import (
    collect_field_signature,
    describe_change,
)


@register_function(
    requires=['population', 'simulator'],
    typed_env_exempt=True,
    display_name="Run Diffusion Solver (Metabolic, ON-CHANGE Steady)",
    description="Steady-state Picard solve of the metabolic substances "
                "(default Oxygen,Glucose,Lactate,H), re-run ONLY when the "
                "discrete state it depends on changed since the last solve: "
                "the watched genes that gate the metabolism (default "
                "mitoATP,glycoATP), any phenotype change, any cell "
                "added/removed/moved, or a parameter change. Otherwise the "
                "previous converged fields are kept — exact, since the steady "
                "fixed point is fully determined by that discrete state. "
                "Every solve logs its trigger. Pair with Run Growth Factor "
                "Solver (Steady, ON-CHANGE).",
    category="DIFFUSION",
    parameters=[
        {
            "name": "substances",
            "type": "STRING",
            "description": "Comma-separated metabolic substances to solve",
            "default": "Oxygen,Glucose,Lactate,H"
        },
        {
            "name": "watched_genes",
            "type": "STRING",
            "description": "Gene nodes whose flips change the metabolic reaction "
                           "laws and therefore trigger a re-solve (the genes "
                           "calculate_cell_metabolism gates on). Flips of any "
                           "other gene are ignored by design.",
            "default": "mitoATP,glycoATP"
        },
        {
            "name": "max_coupling_iterations",
            "type": "INT",
            "description": "Maximum Picard coupling iterations",
            "default": 10,
            "min_value": 1
        },
        {
            "name": "coupling_tolerance",
            "type": "FLOAT",
            "description": "Convergence tolerance for coupling (max change of the unrelaxed solution between consecutive solves; two consecutive passes below tolerance end the loop)",
            "default": 1e-4,
            "min_value": 0.0
        },
        {
            "name": "relaxation_factor",
            "type": "FLOAT",
            "description": "Under-relaxation factor (0 < α ≤ 1). Lower = more stable, slower",
            "default": 0.7,
            "min_value": 0.1,
            "max_value": 1.0
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
def run_diffusion_solver_metabolic_on_change(
    context: Dict[str, Any],
    substances: str = "Oxygen,Glucose,Lactate,H",
    watched_genes: str = "mitoATP,glycoATP",
    max_coupling_iterations: int = 10,
    coupling_tolerance: float = 1e-4,
    relaxation_factor: float = 0.7,
    oxygen_conversion_factor: float = 1.0,
    glucose_conversion_factor: float = 1.0,
    lactate_conversion_factor: float = 1.0,
    oxygen_consumption_multiplier: float = 1.0,
    verbose: Optional[bool] = None,
    **kwargs
) -> None:
    """Steady metabolic solve, skipped exactly while its fixed point is unchanged.

    See the module docstring for the trigger set and why skipping is exact.
    """
    simulator = context.get('simulator')
    population = context.get('population')

    if simulator is None:
        log_always("[run_diffusion_solver_metabolic_on_change] No simulator in context - cannot run.")
        return
    if population is None:
        log_always("[run_diffusion_solver_metabolic_on_change] No population - nothing consumes or produces; skipping.")
        return

    substance_filter = [s.strip() for s in substances.split(',') if s.strip()]
    if not substance_filter:
        log_always("[run_diffusion_solver_metabolic_on_change] Empty substance list - nothing to solve.")
        return
    watched = [g.strip() for g in watched_genes.split(',') if g.strip()]

    signature = collect_field_signature(
        population, watched,
        params=(tuple(substance_filter), tuple(watched),
                max_coupling_iterations, coupling_tolerance, relaxation_factor,
                oxygen_conversion_factor, glucose_conversion_factor,
                lactate_conversion_factor, oxygen_consumption_multiplier))

    store = context.setdefault('_steady_on_change', {})
    entry = store.get('metabolic')
    if entry is None:
        # R1.5: announce the effective law once per run.
        log_always("[STEADY-ON-CHANGE] metabolic: steady-state fields are "
                   "re-equilibrated only when the field-relevant discrete state "
                   f"changes (watched genes: {watched}; plus phenotype, cell "
                   "membership/positions, parameters); otherwise the previous "
                   "converged solution is exact and kept")

    reason = describe_change(entry['signature'] if entry else None, signature)
    if reason is None:
        entry['skips'] += 1
        log(context,
            f"metabolic fields kept — no field-relevant change "
            f"({entry['skips']} consecutive skip(s))",
            prefix="[STEADY-ON-CHANGE]", node_verbose=verbose)
        return

    skipped = entry['skips'] if entry else 0
    solves = (entry['solves'] if entry else 0) + 1
    after = f" (after {skipped} skipped step(s))" if skipped else ""
    log_always(f"[STEADY-ON-CHANGE] metabolic: re-solving — {reason}{after} "
               f"[solve #{solves}]")

    _run_coupled(
        context,
        max_coupling_iterations=max_coupling_iterations,
        coupling_tolerance=coupling_tolerance,
        relaxation_factor=relaxation_factor,
        oxygen_conversion_factor=oxygen_conversion_factor,
        glucose_conversion_factor=glucose_conversion_factor,
        lactate_conversion_factor=lactate_conversion_factor,
        oxygen_consumption_multiplier=oxygen_consumption_multiplier,
        include_growth_factors=False,
        substance_filter=substance_filter,
        verbose=verbose,
    )
    store['metabolic'] = {'signature': signature, 'skips': 0, 'solves': solves}
