"""
Mark cells as proliferating based on gene network Proliferation output.

This function checks each cell's gene network state and marks cells
as Proliferation if the Proliferation gene is ON.

Cells not in Proliferation, Apoptosis, Necrosis, or Growth_Arrest
default to Quiescence.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation


@register_function(
    display_name="Mark Proliferating Cells",
    description="Mark cells as proliferating based on gene network Proliferation output",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_proliferating_cells(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Mark cells as proliferating based on gene network Proliferation output.

    For each cell:
    1. Skip cells already in Necrosis, Apoptosis, or Growth_Arrest
    2. Check if Proliferation gene is ON in gene_states
    3. If yes, mark cell phenotype as 'Proliferation'
    4. If no, mark cell phenotype as 'Quiescence' (default)

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
        print("[mark_proliferating_cells] No population in context - skipping")
        return

    # =========================================================================
    # MARK PROLIFERATING CELLS
    # =========================================================================
    updated_cells = {}
    proliferating_count = 0
    quiescent_count = 0
    skipped_count = 0

    # Phenotypes that should not be changed by this function
    # Note: Apoptotic cells are removed, so we only skip Necrosis and Growth_Arrest
    inactive_phenotypes = {'Necrosis', 'Growth_Arrest'}

    for cell_id, cell in population.state.cells.items():
        # Skip cells in inactive states (Necrosis, Growth_Arrest)
        if cell.state.phenotype in inactive_phenotypes:
            skipped_count += 1
            updated_cells[cell_id] = cell
            continue

        # Check gene network state for Proliferation
        gene_states = cell.state.gene_states
        if gene_states.get('Proliferation', False):
            # Mark as proliferating
            if cell.state.phenotype != 'Proliferation':
                cell.state = cell.state.with_updates(phenotype='Proliferation')
            proliferating_count += 1
        else:
            # Default to quiescence
            if cell.state.phenotype != 'Quiescence':
                cell.state = cell.state.with_updates(phenotype='Quiescence')
            quiescent_count += 1

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log summary
    total = proliferating_count + quiescent_count
    if total > 0:
        print(f"[PROLIFERATION] Proliferating: {proliferating_count}, "
              f"Quiescent: {quiescent_count}, Skipped (inactive): {skipped_count}")

    # Log population count at end
    final_count = len(population.state.cells)
    print(f"[PROLIFERATING-END] Population count: {final_count} cells")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['proliferation'] = {
        'proliferating': proliferating_count,
        'quiescent': quiescent_count,
        'skipped_inactive': skipped_count
    }

