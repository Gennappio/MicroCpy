"""
Intracellular Step - Macrostep stage runner.

This function executes all functions in the intracellular stage.
Used in the macrostep canvas to control when and how many times
the intracellular stage runs.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Intracellular Step",
    description="Execute all intracellular stage functions (use step_count to control repetitions)",
    category="UTILITY",
    outputs=[],
    cloneable=False
)
def intracellular_step(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Execute the intracellular stage.
    
    This function runs all functions defined in the intracellular stage.
    In the macrostep canvas, set the step_count property to control how
    many times this executes per global timestep.
    
    Args:
        context: Workflow execution context
        **kwargs: Additional parameters (ignored)
    
    Example:
        In macrostep canvas, add this node with step_count=3 to run
        intracellular processes 3 times per global timestep.
    """
    # Get the workflow executor from context
    executor = context.get('_executor')
    if not executor:
        print("[MACROSTEP] Warning: No executor in context, cannot run intracellular step")
        return
    
    # Execute the intracellular stage
    executor.execute_intracellular(context)

