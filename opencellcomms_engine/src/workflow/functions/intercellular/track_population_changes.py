"""
Track population changes across all intercellular functions.

This function logs the cell count before and after the intercellular stage
to detect any unexpected cell removals.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation


@register_function(
    display_name="Track Population Changes (Start)",
    description="Log cell count at start of intercellular stage",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def track_population_start(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Track population count at the start of intercellular stage.
    
    Args:
        context: Workflow execution context containing population
    """
    population: Optional[ICellPopulation] = context.get('population')

    if population is None:
        print("[TRACK] No population in context")
        return

    cell_count = len(population.state.cells)
    context['_population_count_start'] = cell_count
    print(f"[TRACK-START] Population count: {cell_count} cells")


@register_function(
    display_name="Track Population Changes (End)",
    description="Log cell count at end of intercellular stage and detect changes",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def track_population_end(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Track population count at the end of intercellular stage.
    
    Args:
        context: Workflow execution context containing population
    """
    population: Optional[ICellPopulation] = context.get('population')

    if population is None:
        print("[TRACK] No population in context")
        return

    cell_count = len(population.state.cells)
    start_count = context.get('_population_count_start', cell_count)
    
    change = cell_count - start_count
    
    if change != 0:
        print(f"[TRACK-END] Population count: {cell_count} cells (change: {change:+d})")
        if change < 0:
            print(f"[TRACK-END] ⚠️  WARNING: {abs(change)} cells were REMOVED!")
        else:
            print(f"[TRACK-END] ✓ {change} cells were ADDED (division)")
    else:
        print(f"[TRACK-END] Population count: {cell_count} cells (no change)")

