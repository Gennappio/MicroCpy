"""
Remove cells that have entered Apoptosis (programmed cell death).

This function checks each cell's phenotype and removes cells that have
entered the Apoptosis state from the population.

Apoptosis is programmed cell death - a controlled process where the cell
actively participates in its own death in response to specific signals.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Remove Apoptotic Cells",
    description="Remove cells with Apoptosis phenotype (programmed cell death)",
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
    Remove cells that have entered Apoptosis (programmed cell death).

    Iterates through all cells and removes those with phenotype 'Apoptosis'.

    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
            - config: Configuration object
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # =========================================================================
    # EXTRACT CORE CONTEXT ITEMS
    # =========================================================================
    population = context.get('population')
    config = context.get('config')

    # =========================================================================
    # VALIDATE REQUIRED CORE ITEMS
    # =========================================================================
    if population is None:
        print("[remove_apoptotic_cells] No population in context - skipping")
        return

    # Filter out apoptotic cells
    living_cells = {}
    apoptotic_count = 0

    for cell_id, cell in population.state.cells.items():
        phenotype = cell.state.phenotype

        # Check if cell is in apoptosis
        if phenotype == 'Apoptosis':
            apoptotic_count += 1
            # Cell is dying via apoptosis - don't add to living_cells
            continue

        # Cell is not apoptotic - keep it
        living_cells[cell_id] = cell

    # Update population with only non-apoptotic cells
    if apoptotic_count > 0:
        population.state = population.state.with_updates(cells=living_cells)

        # Log removal
        print(f"[APOPTOSIS] Removed {apoptotic_count} apoptotic cells. "
              f"Remaining: {len(living_cells)} cells")

