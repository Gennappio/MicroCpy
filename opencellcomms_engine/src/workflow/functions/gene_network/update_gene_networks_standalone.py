"""
Update Gene Networks (Standalone) - Propagate gene networks for all cells.

This function propagates the Boolean network for N steps.
Input nodes stay FIXED during propagation (they are excluded from updates).

Gene networks are accessed from context['gene_networks'] (dict mapping cell_id → BooleanNetwork).
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IGeneNetwork


@register_function(
    display_name="Update Gene Networks (Standalone)",
    description="Propagate gene networks for all cells. Input nodes stay FIXED.",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps", "default": 500},
        {"name": "update_mode", "type": "STRING", "description": "Update mode: 'netlogo' or 'synchronous'", "default": "netlogo"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def update_gene_networks_standalone(
    context: Dict[str, Any] = None,
    propagation_steps: int = 500,
    update_mode: str = "netlogo",
    **kwargs
) -> bool:
    """
    Propagate gene networks for all cells.

    Gene networks are accessed from context['gene_networks'].

    Unlike the full update_gene_networks, this function:
    - Does NOT read from substance concentrations
    - Does NOT set input states from environment (they stay FIXED)
    - Only propagates the Boolean network for N steps

    This is for testing when input states are set manually.

    Args:
        context: Workflow context containing population and gene_networks
        propagation_steps: Number of propagation steps
        update_mode: 'netlogo' (random single gene) or 'synchronous' (all genes)
    """
    # =========================================================================
    # VALIDATE CONTEXT
    # =========================================================================
    if not context:
        print("[ERROR] [update_gene_networks_standalone] No context provided")
        return False

    # =========================================================================
    # GET REQUIRED ITEMS FROM CONTEXT
    # =========================================================================
    population = context.get('population')
    if population is None:
        print("[ERROR] [update_gene_networks_standalone] No population in context")
        return False

    gene_networks = context.get('gene_networks', {})

    if not gene_networks:
        print("[ERROR] No gene networks in context - run 'Initialize Gene Networks' first")
        return False

    cells = population.state.cells
    num_cells = len(cells)

    if num_cells == 0:
        print("[ERROR] No cells in population")
        return False

    print(f"[GENE_NETWORK] Propagating gene networks for {num_cells} cells ({propagation_steps} steps each, mode={update_mode})")

    updated_cells = {}
    cells_with_gn = 0

    for cell_id, cell in cells.items():
        # Get gene network from context (NOT from cell.state)
        cell_gn: Optional[IGeneNetwork] = gene_networks.get(cell_id)

        if cell_gn is None:
            updated_cells[cell_id] = cell
            continue

        cells_with_gn += 1

        # Propagate Boolean network (input nodes stay FIXED - they're excluded from updates)
        gene_states = cell_gn.step(propagation_steps, mode=update_mode)

        # Cache gene states
        cell._cached_gene_states = gene_states

        # Update cell's gene states
        cell.state = cell.state.with_updates(gene_states=gene_states)

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    print(f"   [+] Updated {cells_with_gn} cells with gene networks")

    return True

