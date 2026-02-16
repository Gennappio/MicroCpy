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

    This is the LAST marking function in the cycle and acts as the final arbiter.

    For each cell:
    1. Check if Proliferation gene is ON in gene_states
    2. If yes → phenotype = 'Proliferation' (overwrites any previous phenotype)
    3. If no  → check if an earlier marker (Apoptosis/Growth_Arrest) was set:
       - If yes → keep that phenotype (respect earlier marking functions)
       - If no  → reset to 'Quiescent' (no active fate this cycle → no action)

    The Quiescent reset is critical: without it, stale phenotypes from previous
    iterations would persist and cause cells to keep dividing/dying even when
    the gene network no longer supports that fate.

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
    quiescent_count = 0

    # Phenotypes that were set by earlier marking functions in THIS cycle
    # (mark_apoptotic_cells, mark_growth_arrest_cells).
    # These should NOT be overwritten to Quiescent.
    active_fate_phenotypes = {'Apoptosis', 'Growth_Arrest'}

    for cell_id, cell in population.state.cells.items():
        # Store old phenotype for logging
        old_phenotype = cell.state.phenotype

        # Check gene network state for Proliferation
        gene_states = cell.state.gene_states
        if gene_states.get('Proliferation', False):
            # Mark as proliferating (overwrites any previous phenotype)
            if cell.state.phenotype != 'Proliferation':
                cell.state = cell.state.with_updates(phenotype='Proliferation')
                if old_phenotype in active_fate_phenotypes:
                    overwritten_count += 1
                    print(f"  [PROLIFERATION-OVERWRITE] Cell {cell_id[:8]}: {old_phenotype} -> Proliferation")
            proliferating_count += 1
        else:
            # Proliferation gene is OFF.
            # If cell was already marked Apoptosis/Growth_Arrest by earlier
            # marking functions in this cycle, keep that phenotype.
            # Otherwise reset to Quiescent (no active fate → no action).
            if cell.state.phenotype not in active_fate_phenotypes:
                if cell.state.phenotype != 'Quiescent':
                    cell.state = cell.state.with_updates(phenotype='Quiescent')
                quiescent_count += 1
            else:
                unchanged_count += 1

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log summary
    print(f"[PROLIFERATION] Proliferating: {proliferating_count}, "
          f"Quiescent: {quiescent_count}, "
          f"Kept(Apoptosis/GA): {unchanged_count}, Overwritten: {overwritten_count}")

    # Log population count at end
    final_count = len(population.state.cells)
    print(f"[PROLIFERATING-END] Population count: {final_count} cells")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['proliferation'] = {
        'proliferating': proliferating_count,
        'quiescent': quiescent_count,
        'unchanged': unchanged_count,
        'overwritten': overwritten_count
    }

