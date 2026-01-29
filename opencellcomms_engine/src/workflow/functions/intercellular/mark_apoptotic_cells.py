"""
Mark cells as apoptotic based on gene network Apoptosis output.

This function checks each cell's gene network state and marks cells
as Apoptotic if the Apoptosis gene is ON.

Apoptotic cells remain in the population but do nothing (no metabolism,
no gene network updates, no phenotype changes).

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Mark Apoptotic Cells",
    description="Mark cells as apoptotic based on gene network Apoptosis output",
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
    Mark cells as apoptotic based on gene network Apoptosis output.

    For each cell:
    1. Check if Apoptosis gene is ON in gene_states
    2. If yes, mark cell phenotype as 'Apoptosis'
    3. Apoptotic cells stay in population but are inactive

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
    # MARK APOPTOTIC CELLS
    # =========================================================================
    updated_cells = {}
    newly_apoptotic = 0
    already_apoptotic = 0

    for cell_id, cell in population.state.cells.items():
        # Skip cells already marked as Apoptosis or Necrosis
        if cell.state.phenotype in ('Apoptosis', 'Necrosis'):
            if cell.state.phenotype == 'Apoptosis':
                already_apoptotic += 1
            updated_cells[cell_id] = cell
            continue

        # Check gene network state for Apoptosis
        gene_states = cell.state.gene_states
        if gene_states.get('Apoptosis', False):
            # Mark as apoptotic
            cell.state = cell.state.with_updates(phenotype='Apoptosis')
            newly_apoptotic += 1

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log summary
    if newly_apoptotic > 0:
        print(f"[APOPTOSIS] Marked {newly_apoptotic} cells as apoptotic "
              f"(Apoptosis gene ON). Already apoptotic: {already_apoptotic}")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['apoptosis'] = {
        'newly_marked': newly_apoptotic,
        'already_apoptotic': already_apoptotic
    }

