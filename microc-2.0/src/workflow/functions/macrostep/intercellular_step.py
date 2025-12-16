"""
Intercellular Step - Macrostep stage runner.

This function executes all functions in the intercellular stage.
Used in the macrostep canvas to control when and how many times
the intercellular stage runs.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Intercellular Step",
    description="Execute all intercellular stage functions (use step_count to control repetitions)",
    category="UTILITY",
    outputs=[],
    cloneable=False
)
def intercellular_step(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Execute the intercellular stage.
    
    This function runs all functions defined in the intercellular stage.
    In the macrostep canvas, set the step_count property to control how
    many times this executes per global timestep.
    
    Args:
        context: Workflow execution context
        **kwargs: Additional parameters (ignored)
    
    Example:
        In macrostep canvas, add this node with step_count=1 to run
        intercellular processes once per global timestep.
    """
    # Get the workflow executor from context
    executor = context.get('_executor')
    if not executor:
        print("[MACROSTEP] Warning: No executor in context, cannot run intercellular step")
        return
    
    # Execute the intercellular stage
    executor.execute_intercellular(context)

