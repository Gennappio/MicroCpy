"""
Mark and track cells in Growth_Arrest state.

This function tracks how long cells have been in Growth_Arrest state using
a counter stored in the mutable context. Cells in Growth_Arrest are like
necrotic cells - they do nothing (no metabolism, no gene network updates).

When the growth arrest time expires, cells can transition to another state.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Mark Growth Arrest Cells",
    description="Track and manage cells in Growth_Arrest state with time limit",
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "max_growth_arrest_steps",
            "type": "INT",
            "description": "Maximum number of steps a cell can remain in Growth_Arrest",
            "default": 100
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_growth_arrest_cells(
    context: Dict[str, Any],
    max_growth_arrest_steps: int = 100,
    **kwargs
) -> None:
    """
    Track and manage cells in Growth_Arrest state.

    For each cell:
    1. If phenotype is Growth_Arrest, increment counter
    2. If counter exceeds max_growth_arrest_steps, cell stays arrested (permanent)
    3. If phenotype changes from Growth_Arrest, reset counter

    Counters are stored in context['growth_arrest_counters'] dict.

    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
        max_growth_arrest_steps: Maximum steps in Growth_Arrest before permanent arrest
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place, updates context counters)
    """
    # =========================================================================
    # EXTRACT CORE CONTEXT ITEMS
    # =========================================================================
    population = context.get('population')

    # =========================================================================
    # VALIDATE REQUIRED CORE ITEMS
    # =========================================================================
    if population is None:
        print("[mark_growth_arrest_cells] No population in context - skipping")
        return

    # =========================================================================
    # INITIALIZE OR GET GROWTH ARREST COUNTERS FROM CONTEXT
    # =========================================================================
    if 'growth_arrest_counters' not in context:
        context['growth_arrest_counters'] = {}

    counters = context['growth_arrest_counters']

    # =========================================================================
    # UPDATE GROWTH ARREST COUNTERS
    # =========================================================================
    updated_cells = {}
    cells_in_arrest = 0
    cells_expired = 0
    cells_exited = 0

    for cell_id, cell in population.state.cells.items():
        phenotype = cell.state.phenotype

        if phenotype == 'Growth_Arrest':
            # Cell is in Growth_Arrest - increment counter
            if cell_id not in counters:
                counters[cell_id] = 0
            counters[cell_id] += 1
            cells_in_arrest += 1

            # Check if time has expired
            if counters[cell_id] >= max_growth_arrest_steps:
                cells_expired += 1
                # Cell remains in Growth_Arrest (permanent arrest)
                # Could transition to Necrosis or Quiescence here if desired

        else:
            # Cell is not in Growth_Arrest
            if cell_id in counters:
                # Cell exited Growth_Arrest - reset counter
                del counters[cell_id]
                cells_exited += 1

        updated_cells[cell_id] = cell

    # Update population state (no changes to cells, just tracking)
    population.state = population.state.with_updates(cells=updated_cells)

    # Log summary
    if cells_in_arrest > 0 or cells_exited > 0:
        print(f"[GROWTH_ARREST] In arrest: {cells_in_arrest}, "
              f"Expired (>={max_growth_arrest_steps} steps): {cells_expired}, "
              f"Exited: {cells_exited}")

    # Log population count at end
    final_count = len(population.state.cells)
    print(f"[GROWTH-ARREST-END] Population count: {final_count} cells")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['growth_arrest'] = {
        'cells_in_arrest': cells_in_arrest,
        'cells_expired': cells_expired,
        'cells_exited': cells_exited,
        'max_steps': max_growth_arrest_steps,
        'total_tracked': len(counters)
    }

