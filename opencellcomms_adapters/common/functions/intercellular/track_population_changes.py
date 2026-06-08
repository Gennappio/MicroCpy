"""
Track population changes across all intercellular functions.

This function logs the cell count before and after the intercellular stage
to detect any unexpected cell removals.
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    requires=['population'],
    display_name="Track Population Changes (Start)",
    description="Log cell count at start of intercellular stage",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def track_population_start(
    env: BiologicalContext,
    **kwargs
) -> None:
    """
    Track population count at the start of intercellular stage.

    Args:
        env: Typed biological context (population access).
    """
    if env.cells.raw is None:
        print("[TRACK] No population in context")
        return

    cell_count = len(env.cells)
    # Private cross-function handoff to track_population_end (not a biological
    # result), so it lives on the raw context rather than env.results.
    env.raw_context['_population_count_start'] = cell_count
    print(f"[TRACK-START] Population count: {cell_count} cells")


@register_function(
    requires=['population'],
    display_name="Track Population Changes (End)",
    description="Log cell count at end of intercellular stage and detect changes",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def track_population_end(
    env: BiologicalContext,
    **kwargs
) -> None:
    """
    Track population count at the end of intercellular stage.

    Args:
        env: Typed biological context (population access).
    """
    if env.cells.raw is None:
        print("[TRACK] No population in context")
        return

    cell_count = len(env.cells)
    start_count = env.raw_context.get('_population_count_start', cell_count)
    
    change = cell_count - start_count
    
    if change != 0:
        print(f"[TRACK-END] Population count: {cell_count} cells (change: {change:+d})")
        if change < 0:
            print(f"[TRACK-END] ⚠️  WARNING: {abs(change)} cells were REMOVED!")
        else:
            print(f"[TRACK-END] ✓ {change} cells were ADDED (division)")
    else:
        print(f"[TRACK-END] Population count: {cell_count} cells (no change)")

