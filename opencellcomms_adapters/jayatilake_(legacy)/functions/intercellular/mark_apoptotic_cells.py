"""
Mark apoptotic cells based on gene network Apoptosis output.

This function checks each cell's gene network state and marks cells
as 'Apoptosis' phenotype when the Apoptosis gene is ON.

Apoptotic cells are marked but NOT removed here. Use remove_apoptotic_cells
to actually remove marked cells from the population.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation


@register_function(
    display_name="Mark Apoptotic Cells",
    description="Mark cells with Apoptosis gene ON (sets phenotype to 'Apoptosis')",
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
    Mark apoptotic cells based on gene network Apoptosis output.

    This is the FIRST marking function in the cycle.  It resets ALL cell
    phenotypes to 'Quiescent' before applying marks, preventing stale
    phenotypes from previous iterations from carrying over.

    For each cell:
    0. Reset phenotype to 'Quiescent' (clear stale state)
    1. Check if Apoptosis gene is ON in gene_states
    2. If yes, set phenotype to 'Apoptosis'
    3. Cells remain in population until remove_apoptotic_cells is called

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
        print("[mark_apoptotic_cells] No population in context - skipping")
        return

    # =========================================================================
    # RESET ALL PHENOTYPES TO QUIESCENT
    # =========================================================================
    # This is the FIRST marking function in the cycle.  We reset every cell to
    # Quiescent so that stale phenotypes from the previous iteration do not
    # carry over.  Subsequent marking functions (Growth_Arrest, Proliferation)
    # will overwrite Quiescent when their respective gene is active.
    for cell in population.state.cells.values():
        if cell.state.phenotype != 'Quiescent':
            cell.state = cell.state.with_updates(phenotype='Quiescent')

    # =========================================================================
    # MARK APOPTOTIC CELLS
    # =========================================================================
    updated_cells = {}
    marked_count = 0
    marked_cell_ids = []

    for cell_id, cell in population.state.cells.items():
        # Check gene network state for Apoptosis
        gene_states = cell.state.gene_states
        if gene_states.get('Apoptosis', False):
            # Mark cell as apoptotic
            cell.state = cell.state.with_updates(phenotype='Apoptosis')
            marked_count += 1
            marked_cell_ids.append(cell_id[:8])

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    final_count = len(population.state.cells)

    if marked_count > 0:
        print(f"[APOPTOSIS] Marked {marked_count} cells as apoptotic")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['apoptosis'] = {
        'marked': marked_count,
        'total_cells': final_count
    }

