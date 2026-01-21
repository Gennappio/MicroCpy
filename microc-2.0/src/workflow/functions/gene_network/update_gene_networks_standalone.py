"""
Update Gene Networks (Standalone) - Propagate gene networks for all cells.

This function propagates the Boolean network for N steps.
Input nodes stay FIXED during propagation (they are excluded from updates).
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Update Gene Networks (Standalone)",
    description="Propagate gene networks for all cells. Input nodes stay FIXED.",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps", "default": 500},
    ],
    inputs=["population"],  # Only needs population!
    outputs=[],
    cloneable=False
)
def update_gene_networks_standalone(
    population=None,
    context: Dict[str, Any] = None,
    propagation_steps: int = 500,
    **kwargs
) -> bool:
    """
    Propagate gene networks for all cells.

    Unlike the full update_gene_networks, this function:
    - Does NOT read from substance concentrations
    - Does NOT set input states from environment (they stay FIXED)
    - Only propagates the Boolean network for N steps

    This is for testing when input states are set manually.
    """
    # Get population from context if not passed directly
    if population is None and context:
        population = context.get('population')

    if population is None:
        print("[ERROR] No population found")
        return False

    cells = population.state.cells
    num_cells = len(cells)

    if num_cells == 0:
        print("[ERROR] No cells in population")
        return False

    print(f"[GENE_NETWORK] Propagating gene networks for {num_cells} cells ({propagation_steps} steps each)")

    updated_cells = {}

    for cell_id, cell in cells.items():
        cell_gn = cell.state.gene_network

        if cell_gn is None:
            continue

        # Propagate Boolean network (input nodes stay FIXED - they're excluded from updates)
        gene_states = cell_gn.step(propagation_steps)

        # Cache gene states
        cell._cached_gene_states = gene_states

        # Update cell's gene states
        cell.state = cell.state.with_updates(gene_states=gene_states)

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    print(f"   [+] Updated {len(updated_cells)} cells")

    return True

