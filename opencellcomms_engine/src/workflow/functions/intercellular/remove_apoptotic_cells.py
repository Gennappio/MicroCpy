"""
Remove apoptotic cells from the population.

This function removes cells that have been marked with 'Apoptosis' phenotype.
Should be called after mark_apoptotic_cells and after update_cell_division
to handle programmed cell death.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation


@register_function(
    display_name="Remove Apoptotic Cells",
    description="Remove cells marked with Apoptosis phenotype from population",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def remove_apoptotic_cells(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Remove apoptotic cells from the population.

    For each cell:
    1. Check if phenotype is 'Apoptosis'
    2. If yes, remove the cell from population
    3. Apoptotic cells are cleared (unlike necrotic cells which remain)

    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # =========================================================================
    # EXTRACT CORE CONTEXT ITEMS
    # =========================================================================
    population: Optional[ICellPopulation] = context.get('population')

    # =========================================================================
    # VALIDATE REQUIRED CORE ITEMS
    # =========================================================================
    if population is None:
        print("[remove_apoptotic_cells] No population in context - skipping")
        return

    # =========================================================================
    # REMOVE APOPTOTIC CELLS
    # =========================================================================
    initial_count = len(population.state.cells)
    updated_cells = {}
    removed_count = 0
    removed_cell_ids = []

    # Get gene networks dict to clean up orphaned networks
    gene_networks = context.get('gene_networks', {})

    for cell_id, cell in population.state.cells.items():
        # Check if cell is marked as apoptotic
        if cell.state.phenotype == 'Apoptosis':
            # Remove apoptotic cell (don't add to updated_cells)
            removed_count += 1
            removed_cell_ids.append(cell_id[:8])  # Store short ID for logging
            # Also remove the gene network for this cell
            if cell_id in gene_networks:
                del gene_networks[cell_id]
            continue

        # Keep non-apoptotic cells
        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log summary
    final_count = len(updated_cells)
    print(f"[REMOVE-APOPTOSIS] Cell count: {initial_count} -> {final_count} (removed {removed_count})")
    if removed_count > 0:
        print(f"[REMOVE-APOPTOSIS] Removed cells: {', '.join(removed_cell_ids)}")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['remove_apoptosis'] = {
        'removed': removed_count,
        'remaining': final_count
    }
