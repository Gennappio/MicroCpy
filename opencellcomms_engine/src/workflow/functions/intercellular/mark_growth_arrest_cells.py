"""
Mark cells in Growth_Arrest state based on gene network output.

This function marks cells as 'Growth_Arrest' phenotype when the Growth_Arrest
gene is ON. It also tracks how long cells have been in Growth_Arrest state
using a counter stored in the mutable context.

Cells in Growth_Arrest are like necrotic cells - they do nothing (no metabolism,
no gene network updates). When the growth arrest time expires, cells remain
arrested (permanent arrest).

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation


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
    Mark and track cells in Growth_Arrest state.

    For each cell:
    1. Check if Growth_Arrest gene is ON in gene_states
    2. If yes, set phenotype to 'Growth_Arrest' and increment counter
    3. If counter exceeds max_growth_arrest_steps, cell stays arrested (permanent)
    4. If phenotype changes from Growth_Arrest, reset counter

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
    population: Optional[ICellPopulation] = context.get('population')

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
    # MARK AND UPDATE GROWTH ARREST CELLS
    # =========================================================================
    updated_cells = {}
    cells_in_arrest = 0
    cells_expired = 0
    cells_exited = 0
    cells_newly_marked = 0

    for cell_id, cell in population.state.cells.items():
        # Check gene network state for Growth_Arrest
        gene_states = cell.state.gene_states
        old_phenotype = cell.state.phenotype

        if gene_states.get('Growth_Arrest', False):
            # Mark as Growth_Arrest if not already
            if old_phenotype != 'Growth_Arrest':
                cell.state = cell.state.with_updates(phenotype='Growth_Arrest')
                cells_newly_marked += 1
            
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
            # Cell is not in Growth_Arrest gene state
            if cell_id in counters:
                # Cell exited Growth_Arrest - reset counter
                del counters[cell_id]
                cells_exited += 1

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log only when something actually changed
    if cells_newly_marked > 0 or cells_exited > 0:
        print(f"[GROWTH_ARREST] Newly marked: {cells_newly_marked}, "
              f"Exited: {cells_exited}, In arrest: {cells_in_arrest}")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['growth_arrest'] = {
        'cells_in_arrest': cells_in_arrest,
        'newly_marked': cells_newly_marked,
        'cells_expired': cells_expired,
        'cells_exited': cells_exited,
        'max_steps': max_growth_arrest_steps,
        'total_tracked': len(counters)
    }

