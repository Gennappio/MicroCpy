"""
Propagate Gene Networks - Configurable gene network propagation.

This function propagates gene networks with configurable update algorithm.
Supports multiple update modes selectable from the GUI.

Gene networks are accessed from context['gene_networks'] (dict mapping cell_id → BooleanNetwork).
"""

from typing import Dict, Any, List, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IGeneNetwork, ICellPopulation


@register_function(
    display_name="Propagate Gene Networks",
    description="Propagate gene networks with configurable update algorithm",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps", "default": 500},
        {
            "name": "update_mode",
            "type": "STRING",
            "description": "Update algorithm: 'netlogo' (random single gene), 'synchronous' (all genes), or 'asynchronous' (random order)",
            "default": "netlogo"
        },
        {"name": "cell_ids", "type": "LIST", "description": "Optional list of cell IDs to update (empty = all cells)", "default": []},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def propagate_gene_networks(
    context: Dict[str, Any],
    propagation_steps: int = 500,
    update_mode: str = "netlogo",
    cell_ids: Optional[List[str]] = None,
    **kwargs
) -> bool:
    """
    Propagate gene networks with configurable update algorithm.
    
    Gene networks are accessed from context['gene_networks'].
    
    This function provides full control over gene network propagation:
    - Number of propagation steps
    - Update algorithm (netlogo, synchronous, asynchronous)
    - Which cells to update (specific cells or all)
    
    Args:
        context: Workflow context containing gene_networks and population
        propagation_steps: Number of propagation steps per cell
        update_mode: Update algorithm
            - 'netlogo': Random single gene per step (NetLogo-style)
            - 'synchronous': All genes update together each step
            - 'asynchronous': All genes update in random order each step
        cell_ids: Optional list of cell IDs to update (None or empty = all cells)
        
    Returns:
        True if successful, False otherwise
    """
    print(f"[PROPAGATE] Propagating gene networks ({propagation_steps} steps, mode={update_mode})")
    
    # Get gene networks from context
    gene_networks = context.get('gene_networks', {})
    
    if not gene_networks:
        print("[ERROR] No gene networks in context - run 'Initialize Gene Networks' first")
        return False
    
    # Get population
    population: Optional[ICellPopulation] = context.get('population')
    if population is None:
        print("[ERROR] No population in context")
        return False
    
    cells = population.state.cells
    
    # Determine which cells to update
    if cell_ids:
        target_cell_ids = cell_ids
    else:
        target_cell_ids = list(cells.keys())
    
    # Propagate each cell's gene network
    updated_cells = {}
    cells_propagated = 0
    cells_skipped = 0
    
    for cell_id in target_cell_ids:
        cell = cells.get(cell_id)
        if cell is None:
            cells_skipped += 1
            continue
            
        cell_gn: Optional[IGeneNetwork] = gene_networks.get(cell_id)
        if cell_gn is None:
            cells_skipped += 1
            updated_cells[cell_id] = cell
            continue
        
        cells_propagated += 1

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

        # Cache and update cell state
        cell._cached_gene_states = gene_states
        cell.state = cell.state.with_updates(gene_states=gene_states)
        updated_cells[cell_id] = cell
    
    # Include cells that weren't targeted for update
    for cell_id, cell in cells.items():
        if cell_id not in updated_cells:
            updated_cells[cell_id] = cell
    
    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)
    
    print(f"   [+] Propagated {cells_propagated} cells (skipped {cells_skipped})")
    
    # Store changes in context
    context['changes'] = context.get('changes', {})
    context['changes']['propagate_gene_networks'] = {
        'cells_propagated': cells_propagated,
        'propagation_steps': propagation_steps,
        'update_mode': update_mode
    }
    
    return True

