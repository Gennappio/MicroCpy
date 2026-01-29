"""
Mark and remove apoptotic cells based on gene network Apoptosis output.

This function checks each cell's gene network state and removes cells
where the Apoptosis gene is ON.

Apoptotic cells are REMOVED from the population (programmed cell death
with clearance), unlike necrotic cells which remain as debris.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Mark and Remove Apoptotic Cells",
    description="Mark and remove cells with Apoptosis gene ON (programmed cell death)",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_apoptotic_cells(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Mark and remove apoptotic cells based on gene network Apoptosis output.

    For each cell:
    1. Check if Apoptosis gene is ON in gene_states
    2. If yes, REMOVE the cell from population
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
    population = context.get('population')

    # =========================================================================
    # VALIDATE REQUIRED CORE ITEMS
    # =========================================================================
    if population is None:
        print("[mark_apoptotic_cells] No population in context - skipping")
        return

    # =========================================================================
    # REMOVE APOPTOTIC CELLS
    # =========================================================================
    updated_cells = {}
    removed_count = 0

    for cell_id, cell in population.state.cells.items():
        # Check gene network state for Apoptosis
        gene_states = cell.state.gene_states
        if gene_states.get('Apoptosis', False):
            # Remove apoptotic cell (don't add to updated_cells)
            removed_count += 1
            continue

        # Keep non-apoptotic cells
        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log summary
    if removed_count > 0:
        remaining = len(updated_cells)
        print(f"[APOPTOSIS] Removed {removed_count} apoptotic cells "
              f"(Apoptosis gene ON). Remaining: {remaining}")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['apoptosis'] = {
        'removed': removed_count,
        'remaining': len(updated_cells)
    }

