"""
Coupled diffusion solver with IMPLICIT growth-factor uptake.

WHY THIS NODE EXISTS (vs run_diffusion_solver_coupled)
    Both nodes run the same Picard coupling loop: recalculate the
    Michaelis-Menten cell metabolism, solve the steady-state
    diffusion-reaction PDE for every substance, repeat until the solution is
    self-consistent. They differ in ONE thing: how the first-order uptake of
    the signalling substances (TGFA/FGF/HGF/GI, per the reference model
    R_S = γ_S,C · C_S for consumption and R_S = γ_S,P for production) enters
    the PDE.

    run_diffusion_solver_coupled evaluates that uptake EXPLICITLY, at the
    previous iteration's concentrations, and moves it to the source side:

        ∇·(D∇C) = -(P(x) - γ_C·C_prev(x))

    For a substance with zero-flux (Neumann) boundaries and net production —
    TGFA, FGF, GI in MicroC — that steady-state system is SINGULAR and
    INCOMPATIBLE: nothing in the matrix anchors the concentration level, and
    no steady state exists for a net source with no outflow. In practice the
    iterative solver either leaves the field frozen (TGFA stuck at exactly 0)
    or dumps the imbalance into an arbitrary uniform constant — both wrong.

    This node instead keeps the SAME uptake law but puts it in the matrix,
    IMPLICITLY, where it belongs for a linear sink:

        ∇·(D∇C) - k(x)·C = -P(x),   k(x) = Σ_cells γ_S,C · fate_weight / V_mesh

    Algebraically this has the identical fixed point (R = γ_C·C at the
    solution), but the matrix is nonsingular whenever any cell takes the
    substance up, so the growth-factor fields get a real, bounded steady
    state: peaked around producing cells, decaying away by uptake — even with
    pure-Neumann boundaries. Solved by direct sparse LU.

    Oxygen/Glucose/Lactate/H are untouched: their nonlinear Michaelis-Menten
    metabolism stays explicit inside the Picard loop, exactly as in
    run_diffusion_solver_coupled.

PARAMETERS
    Deliberately fewer than the old node: max_iterations / tolerance /
    solver_type are not offered because the underlying simulator never reads
    them (a parameter that isn't wired is a lie).
"""

from typing import Dict, Any, Optional

from src.workflow.decorators import register_function
from src.workflow.functions.diffusion.run_diffusion_solver_coupled import _run_coupled


@register_function(
    requires=['population', 'simulator'],
    typed_env_exempt=True,
    display_name="Run Diffusion Solver (Coupled, Implicit Uptake)",
    description="Picard-coupled diffusion solve where growth-factor uptake "
                "(R = γ_C·C for TGFA/FGF/HGF/GI) is an implicit sink in the PDE "
                "matrix instead of an explicit source term. Gives the "
                "zero-flux-boundary growth factors a well-posed, bounded steady "
                "state; Michaelis-Menten metabolism is unchanged. See the node "
                "source for the equations.",
    category="DIFFUSION",
    parameters=[
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
def run_diffusion_solver_coupled_implicit(
    context: Dict[str, Any],
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
    """Run the Picard-coupled diffusion solve with implicit growth-factor uptake.

    Same coupling loop as run_diffusion_solver_coupled; the only difference is
    that the linear uptake of TGFA/FGF/HGF/GI enters the PDE matrix as an
    implicit sink -k(x)·C rather than being evaluated at the previous
    concentrations. See the module docstring for the equations and why the
    explicit form is ill-posed for zero-flux growth factors.
    """
    _run_coupled(
        context,
        max_coupling_iterations=max_coupling_iterations,
        coupling_tolerance=coupling_tolerance,
        relaxation_factor=relaxation_factor,
        oxygen_conversion_factor=oxygen_conversion_factor,
        glucose_conversion_factor=glucose_conversion_factor,
        lactate_conversion_factor=lactate_conversion_factor,
        oxygen_consumption_multiplier=oxygen_consumption_multiplier,
        implicit_growth_factor_uptake=True,
        verbose=verbose,
    )
