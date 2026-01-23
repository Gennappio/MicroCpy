"""
Remove cells that have entered Necrosis (uncontrolled cell death).

This function checks each cell's phenotype and removes cells that have
entered the Necrosis state from the population.

Necrosis is uncontrolled cell death - typically caused by external factors
like lack of oxygen (hypoxia), lack of nutrients, or physical damage.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Remove Necrotic Cells",
    description="Remove cells with Necrosis phenotype (uncontrolled cell death)",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def remove_necrotic_cells(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Remove cells that have entered Necrosis (uncontrolled cell death).

    Iterates through all cells and removes those with phenotype 'Necrosis'.

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
        print("[remove_necrotic_cells] No population in context - skipping")
        return

    # Filter out necrotic cells
    living_cells = {}
    necrotic_count = 0

    for cell_id, cell in population.state.cells.items():
        phenotype = cell.state.phenotype

        # Check if cell is in necrosis
        if phenotype == 'Necrosis':
            necrotic_count += 1
            # Cell is dying via necrosis - don't add to living_cells
            continue

        # Cell is not necrotic - keep it
        living_cells[cell_id] = cell

    # Update population with only non-necrotic cells
    if necrotic_count > 0:
        population.state = population.state.with_updates(cells=living_cells)

        # Log removal
        print(f"[NECROSIS] Removed {necrotic_count} necrotic cells. "
              f"Remaining: {len(living_cells)} cells")

