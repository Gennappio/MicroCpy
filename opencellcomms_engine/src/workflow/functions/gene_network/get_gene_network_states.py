"""
Get Gene Network States - Retrieve current gene states from context.

This function retrieves the current gene network states for specified cells
from context['gene_networks'].

Gene networks are accessed from context['gene_networks'] (dict mapping cell_id → BooleanNetwork).
"""

from typing import Dict, Any, List, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IGeneNetwork


@register_function(
    display_name="Get Gene Network States",
    description="Retrieve current gene network states for specified cells",
    category="INTRACELLULAR",
    parameters=[
        {"name": "cell_ids", "type": "LIST", "description": "Optional list of cell IDs (empty = all cells)", "default": []},
        {"name": "output_nodes_only", "type": "BOOL", "description": "Return only output/fate nodes", "default": False},
    ],
    inputs=["context"],
    outputs=["gene_states_by_cell"],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def get_gene_network_states(
    context: Dict[str, Any],
    cell_ids: Optional[List[str]] = None,
    output_nodes_only: bool = False,
    **kwargs
) -> Dict[str, Dict[str, bool]]:
    """
    Retrieve current gene network states for specified cells.
    
    Gene networks are accessed from context['gene_networks'].
    
    Args:
        context: Workflow context containing gene_networks
        cell_ids: Optional list of cell IDs (None or empty = all cells)
        output_nodes_only: If True, return only output/fate nodes (Proliferation, Apoptosis, etc.)
        
    Returns:
        Dict mapping cell_id → gene_states dict
    """
    # Get gene networks from context
    gene_networks = context.get('gene_networks', {})
    
    if not gene_networks:
        print("[GET_STATES] No gene networks in context")
        return {}
    
    # Determine which cells to query
    if cell_ids:
        target_cell_ids = cell_ids
    else:
        target_cell_ids = list(gene_networks.keys())
    
    # Collect states
    gene_states_by_cell = {}
    
    for cell_id in target_cell_ids:
        cell_gn: Optional[IGeneNetwork] = gene_networks.get(cell_id)
        if cell_gn is None:
            continue

        if output_nodes_only:
            # === INLINE get_output_states() (from BooleanNetwork.get_output_states() line 521) ===
            # Get current output node states
            gene_states_by_cell[cell_id] = {
                name: cell_gn.nodes[name].current_state
                for name in cell_gn.output_nodes
                if name in cell_gn.nodes
            }
            # === END INLINE get_output_states() ===
        else:
            # === INLINE get_all_states() (from BooleanNetwork.get_all_states() line 529) ===
            # Get all node states
            gene_states_by_cell[cell_id] = {
                name: node.current_state for name, node in cell_gn.nodes.items()
            }
            # === END INLINE get_all_states() ===
    
    print(f"[GET_STATES] Retrieved gene states for {len(gene_states_by_cell)} cells")
    
    # Store in context for downstream use
    context['gene_states_by_cell'] = gene_states_by_cell
    
    return gene_states_by_cell


def get_gene_network(context: Dict[str, Any], cell_id: str) -> Optional[IGeneNetwork]:
    """
    Helper function to safely get a single cell's gene network from context.

    Args:
        context: Workflow context containing gene_networks dict
        cell_id: The cell's unique identifier

    Returns:
        IGeneNetwork instance or None if not found
    """
    gene_networks = context.get('gene_networks', {})
    return gene_networks.get(cell_id)


def set_gene_network(context: Dict[str, Any], cell_id: str, gene_network: IGeneNetwork) -> None:
    """
    Helper function to set a cell's gene network in context.

    Args:
        context: Workflow context containing gene_networks dict
        cell_id: The cell's unique identifier
        gene_network: IGeneNetwork instance to store
    """
    if 'gene_networks' not in context:
        context['gene_networks'] = {}
    context['gene_networks'][cell_id] = gene_network


def remove_gene_network(context: Dict[str, Any], cell_id: str) -> None:
    """
    Helper function to remove a cell's gene network from context.
    
    Useful when cells die or are removed from the simulation.
    
    Args:
        context: Workflow context containing gene_networks dict
        cell_id: The cell's unique identifier
    """
    gene_networks = context.get('gene_networks', {})
    if cell_id in gene_networks:
        del gene_networks[cell_id]

