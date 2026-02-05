"""
Propagate Gene Networks - Configurable gene network propagation.

This function propagates gene networks with configurable update algorithm.
Supports multiple update modes selectable from the GUI.

Gene networks are accessed from context['gene_networks'] (dict mapping cell_id → BooleanNetwork).
"""

from typing import Dict, Any, List, Optional
from src.workflow.decorators import register_function
from interfaces.base import IGeneNetwork, ICellPopulation


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
    inputs=["population", "gene_networks"],
    outputs=[],
    cloneable=False
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
        
        # Propagate using specified mode
        gene_states = cell_gn.step(propagation_steps, mode=update_mode)
        
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

