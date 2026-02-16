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
    1. Check if Proliferation gene is ON in gene_states
    2. If yes, mark cell phenotype as 'Proliferation' (overwrites previous phenotype)
    3. If no, leave phenotype unchanged (preserves Apoptosis/Growth_Arrest marks)
    
    Note: Proliferation phenotype overwrites Growth_Arrest and Apoptosis.
    This follows the principle that proliferating cells override other states.
    Cells without any marked phenotype default to 'Quiescence'.

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
    overwritten_count = 0
    unchanged_count = 0

    for cell_id, cell in population.state.cells.items():
        # Store old phenotype for logging
        old_phenotype = cell.state.phenotype

        # Check gene network state for Proliferation
        gene_states = cell.state.gene_states
        if gene_states.get('Proliferation', False):
            # Mark as proliferating (overwrites any previous phenotype)
            if cell.state.phenotype != 'Proliferation':
                cell.state = cell.state.with_updates(phenotype='Proliferation')
                if old_phenotype in {'Growth_Arrest', 'Apoptosis'}:
                    overwritten_count += 1
                    print(f"  [PROLIFERATION-OVERWRITE] Cell {cell_id[:8]}: {old_phenotype} -> Proliferation")
            proliferating_count += 1
        else:
            # If Proliferation gene is OFF, leave phenotype unchanged
            # This preserves Apoptosis/Growth_Arrest marks from previous functions
            unchanged_count += 1

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log summary
    print(f"[PROLIFERATION] Proliferating: {proliferating_count}, "
          f"Unchanged: {unchanged_count}, Overwritten: {overwritten_count}")

    # Log population count at end
    final_count = len(population.state.cells)
    print(f"[PROLIFERATING-END] Population count: {final_count} cells")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['proliferation'] = {
        'proliferating': proliferating_count,
        'unchanged': unchanged_count,
        'overwritten': overwritten_count
    }

