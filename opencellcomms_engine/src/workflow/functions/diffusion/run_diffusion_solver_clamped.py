"""
Run the diffusion solver with concentration clamping.

This solver is identical to run_diffusion_solver but adds a post-processing step
to clamp all concentrations to non-negative values. This prevents physically
impossible negative concentrations that can occur when consumption rates are
too high relative to diffusion supply.

The clamping is a numerical safeguard, not a physics fix. For a more physically
correct approach, use run_diffusion_solver_coupled which uses iterative coupling.
"""

from typing import Dict, Any
import numpy as np
from src.workflow.decorators import register_function


@register_function(
    display_name="Run Diffusion Solver (Clamped)",
    description="Solve diffusion PDE with concentration clamping to prevent negative values",
    category="DIFFUSION",
    parameters=[
        {
            "name": "max_iterations",
            "type": "INT",
            "description": "Maximum solver iterations",
            "default": 1000,
            "min_value": 1
        },
        {
            "name": "tolerance",
            "type": "FLOAT",
            "description": "Convergence tolerance",
            "default": 1e-6,
            "min_value": 0.0
        },
        {
            "name": "solver_type",
            "type": "STRING",
            "description": "Solver type",
            "default": "steady_state",
            "options": ["steady_state", "transient"]
        },
        {
            "name": "min_concentration",
            "type": "FLOAT",
            "description": "Minimum allowed concentration (clamp floor)",
            "default": 0.0,
            "min_value": 0.0
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def run_diffusion_solver_clamped(
    context: Dict[str, Any],
    max_iterations: int = 1000,
    tolerance: float = 1e-6,
    solver_type: str = "steady_state",
    min_concentration: float = 0.0,
    **kwargs
) -> None:
    """
    Run the diffusion solver with post-solve concentration clamping.

    This function:
    1. Runs the standard diffusion solver
    2. Clamps all concentrations to be >= min_concentration
    3. Updates the simulator state with clamped values

    Args:
        context: Workflow execution context
        max_iterations: Maximum iterations for solver
        tolerance: Convergence tolerance for solver
        solver_type: Type of solver - "steady_state" or "transient"
        min_concentration: Minimum allowed concentration (default 0.0)
        **kwargs: Additional parameters

    Returns:
        None (modifies simulator state in-place)
    """
    # Import the base solver function
    from src.workflow.functions.diffusion.run_diffusion_solver import (
        run_diffusion_solver,
        _collect_substance_definitions,
        _configure_substances,
        _collect_cell_reactions
    )

    simulator = context.get('simulator')
    if simulator is None:
        print("[run_diffusion_solver_clamped] No simulator in context - cannot run diffusion.")
        return

    # Run the standard diffusion solver
    run_diffusion_solver(
        context,
        max_iterations=max_iterations,
        tolerance=tolerance,
        solver_type=solver_type,
        **kwargs
    )

    # Now clamp all concentrations to non-negative values
    clamped_count = 0
    total_clamped_amount = 0.0

    for name, substance_state in simulator.state.substances.items():
        concentrations = substance_state.concentrations
        
        # Find negative values
        negative_mask = concentrations < min_concentration
        num_negative = np.sum(negative_mask)
        
        if num_negative > 0:
            # Calculate how much we're clamping
            negative_values = concentrations[negative_mask]
            total_clamped_amount += np.sum(min_concentration - negative_values)
            clamped_count += num_negative
            
            # Clamp to minimum
            substance_state.concentrations = np.maximum(concentrations, min_concentration)
            
            print(f"[CLAMPED] {name}: clamped {num_negative} cells "
                  f"(min was {np.min(negative_values):.4e}, now {min_concentration})")
            
            # Update FiPy variable if it exists
            if hasattr(simulator, 'fipy_variables') and name in simulator.fipy_variables:
                simulator.fipy_variables[name].setValue(
                    substance_state.concentrations.flatten(order='F')
                )

    if clamped_count > 0:
        print(f"[CLAMPED] Total: {clamped_count} values clamped, "
              f"total mass correction: {total_clamped_amount:.4e} mM")
    else:
        print("[CLAMPED] No negative concentrations found - no clamping needed")

