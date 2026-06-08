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

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    requires=['gene_networks', 'population'],
    display_name="Remove Apoptotic Cells",
    description="Remove cells marked with Apoptosis phenotype from population",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def remove_apoptotic_cells(
    env: BiologicalContext,
    **kwargs
) -> None:
    """
    Remove apoptotic cells from the population.

    For each cell:
    1. Check if phenotype is 'Apoptosis'
    2. If yes, remove the cell from population
    3. Apoptotic cells are cleared (unlike necrotic cells which remain)

    Args:
        env: Typed biological context (cells + gene networks + results).
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # Population object needed for the low-level state rebuild below.
    population = env.cells.raw
    if population is None:
        print("[remove_apoptotic_cells] No population in context - skipping")
        return

    # =========================================================================
    # REMOVE APOPTOTIC CELLS
    # =========================================================================
    initial_count = len(env.cells)
    updated_cells = {}
    removed_count = 0

    for cell in env.cells:
        # Check if cell is marked as apoptotic
        if cell.is_apoptotic:
            # Remove apoptotic cell (don't add to updated_cells) and clean up
            # its orphaned gene network.
            removed_count += 1
            env.remove_gene_network(cell.id)
            continue

        # Keep non-apoptotic cells
        updated_cells[cell.id] = cell.raw

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells, total_cells=len(updated_cells))

    final_count = len(updated_cells)
    if removed_count > 0:
        print(f"[REMOVE-APOPTOSIS] Removed {removed_count} cells. Population: {initial_count} -> {final_count}")

    # Record change for GUI display.
    env.results.record_change('remove_apoptosis', {
        'removed': removed_count,
        'remaining': final_count
    })
