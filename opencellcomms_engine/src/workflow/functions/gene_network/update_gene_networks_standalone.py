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

        # === INLINE step() logic ===
        import random

        if update_mode == "synchronous":
            # === INLINE _synchronous_step() (line 435) ===
            # Cache the list of updatable genes (only computed once)
            if not hasattr(cell_gn, '_cached_updatable_genes'):
                cell_gn._cached_updatable_genes = [
                    name for name, gene_node in cell_gn.nodes.items()
                    if not gene_node.is_input and gene_node.update_function
                ]

            if cell_gn._cached_updatable_genes:
                for step in range(propagation_steps):
                    # Get ALL current states BEFORE any updates (synchronous semantics)
                    current_states = {name: node.current_state for name, node in cell_gn.nodes.items()}

                    # Evaluate ALL genes based on previous state, then update
                    new_states = {}
                    for gene_name in cell_gn._cached_updatable_genes:
                        gene_node = cell_gn.nodes[gene_name]
                        if gene_node.update_function:
                            new_states[gene_name] = gene_node.update_function(current_states)

                    # Apply all updates simultaneously
                    for gene_name, new_state in new_states.items():
                        cell_gn.nodes[gene_name].current_state = new_state

            # Get all states
            gene_states = {name: node.current_state for name, node in cell_gn.nodes.items()}
            # === END INLINE _synchronous_step() ===
        else:
            # === INLINE _default_step() (NetLogo mode) (line 467) ===
            for step in range(propagation_steps):
                # === INLINE _netlogo_single_gene_update() (line 476) ===
                # Cache the list of updatable genes (only computed once)
                if not hasattr(cell_gn, '_cached_updatable_genes'):
                    cell_gn._cached_updatable_genes = [
                        name for name, gene_node in cell_gn.nodes.items()
                        if not gene_node.is_input and gene_node.update_function
                    ]

                if cell_gn._cached_updatable_genes:
                    # Randomly select ONE gene (NetLogo style)
                    selected_gene = random.choice(cell_gn._cached_updatable_genes)
                    gene_node = cell_gn.nodes[selected_gene]

                    # Cache and reuse the current states dictionary
                    if not hasattr(cell_gn, '_state_cache'):
                        cell_gn._state_cache = {}

                    # Update the cached states with current values
                    for name, node in cell_gn.nodes.items():
                        cell_gn._state_cache[name] = node.current_state

                    # Evaluate the gene's rule and update ONLY this gene
                    new_state = gene_node.update_function(cell_gn._state_cache)
                    gene_node.current_state = new_state
                # === END INLINE _netlogo_single_gene_update() ===

            # Get all states
            gene_states = {name: node.current_state for name, node in cell_gn.nodes.items()}
            # === END INLINE _default_step() ===
        # === END INLINE step() ===

        # Cache gene states
        cell._cached_gene_states = gene_states

        # Update cell's gene states
        cell.state = cell.state.with_updates(gene_states=gene_states)

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    print(f"   [+] Updated {cells_with_gn} cells with gene networks")

    return True

