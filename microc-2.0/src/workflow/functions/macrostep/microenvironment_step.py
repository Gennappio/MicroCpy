"""
Microenvironment Step - Macrostep stage runner.

This function executes all functions in the microenvironment (diffusion) stage.
Used in the macrostep canvas to control when and how many times
the microenvironment stage runs.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Microenvironment Step",
    description="Execute all microenvironment/diffusion stage functions (use step_count to control repetitions)",
    category="UTILITY",
    outputs=[],
    cloneable=False
)
def microenvironment_step(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Execute the microenvironment (diffusion) stage.
    
    This function runs all functions defined in the microenvironment stage.
    In the macrostep canvas, set the step_count property to control how
    many times this executes per global timestep.
    
    Args:
        context: Workflow execution context
        **kwargs: Additional parameters (ignored)
    
    Example:
        In macrostep canvas, add this node with step_count=5 to run
        diffusion solver 5 times per global timestep.
    """
    # Get the workflow executor from context
    executor = context.get('_executor')
    if not executor:
        print("[MACROSTEP] Warning: No executor in context, cannot run microenvironment step")
        return
    
    # Execute the microenvironment stage
    executor.execute_microenvironment(context)

