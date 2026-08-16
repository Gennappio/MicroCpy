"""
Picard-coupled diffusion solve for the METABOLIC substances only.

One of the two halves of the split diffusion step (the other is
run_growth_factor_solver):

    metabolic node      Oxygen / Glucose / Lactate / H — nonlinear
                        Michaelis-Menten consumption/production, so the PDE
                        and the per-cell metabolism must be iterated to a
                        self-consistent fixed point (Picard loop with
                        under-relaxation). This node.

    growth-factor node  TGFA / FGF / HGF / GI — linear laws
                        (R = γ_C·C uptake, R = γ_P production), solved in a
                        single implicit pass by run_growth_factor_solver.

Within one scheduler step the two groups do not couple (growth-factor fields
never enter the metabolism; gene states are updated elsewhere by
gene_update), so splitting them loses nothing and stops the linear
growth-factor fields from being pointlessly re-solved on every Picard
iteration.

The coupling loop itself is identical to run_diffusion_solver_coupled —
shared via _run_coupled — restricted to the substances listed in the
``substances`` parameter. Growth-factor reaction terms are not collected
here at all.
"""

from typing import Dict, Any, Optional

from src.workflow.decorators import register_function
from src.workflow.logging import log_always
from src.workflow.functions.diffusion.run_diffusion_solver_coupled import _run_coupled


@register_function(
    requires=['population', 'simulator'],
    typed_env_exempt=True,
    display_name="Run Diffusion Solver (Metabolic)",
    description="Picard-coupled steady-state solve of the metabolic substances "
                "only (default Oxygen,Glucose,Lactate,H) with Michaelis-Menten "
                "cell metabolism. Growth factors are deliberately excluded — "
                "pair this node with Run Growth Factor Solver, which handles "
                "their linear kinetics in a single implicit solve.",
    category="DIFFUSION",
    parameters=[
        {
            "name": "substances",
            "type": "STRING",
            "description": "Comma-separated metabolic substances to solve",
            "default": "Oxygen,Glucose,Lactate,H"
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
def run_diffusion_solver_metabolic(
    context: Dict[str, Any],
    substances: str = "Oxygen,Glucose,Lactate,H",
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
    """Run the Picard-coupled diffusion solve restricted to the metabolic
    substances. See the module docstring for the metabolic/growth-factor split."""
    substance_filter = [s.strip() for s in substances.split(',') if s.strip()]
    if not substance_filter:
        log_always("[run_diffusion_solver_metabolic] Empty substance list - nothing to solve.")
        return

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
