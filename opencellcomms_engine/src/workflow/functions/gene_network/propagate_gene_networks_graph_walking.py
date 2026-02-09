"""
Propagate Gene Networks with Graph Walking Update Mechanism.

This function implements NetLogo-style graph walking propagation that follows
network topology instead of randomly selecting genes:

1. Start from last_node (initially a random input)
2. Pick ONE random outgoing link (node that depends on current node)
3. Update that target node's state based on its boolean logic
4. If fate node fires → reset to OFF (transient trigger), return to random input
5. Otherwise → continue walking from the updated node

Key differences from random NetLogo propagation:
- Follows signal propagation chains through network topology
- Fate nodes are transient triggers (reset after firing)
- Updates are spatially correlated (follow dependency chains)

This matches the behavior of gene_network_graph_walking.py benchmark script.
"""

from typing import Dict, Any, Optional, Set
from collections import Counter
import random
from src.workflow.decorators import register_function


@register_function(
    display_name="Propagate Gene Networks (Graph Walking)",
    description="Graph walking propagation - follows network topology and signal chains",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps", "default": 500},
        {"name": "verbose", "type": "BOOL", "description": "Enable detailed logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def propagate_gene_networks_graph_walking(
    context: Dict[str, Any] = None,
    propagation_steps: int = 500,
    verbose: bool = False,
    **kwargs
) -> bool:
    """
    Propagate gene networks using graph walking update mechanism.
    
    Follows network topology: from current node, pick one random outgoing link,
    update target node. If fate node fires, reset it and return to input.
    
    This implements the algorithm from gene_network_graph_walking.py.
    """
    print(f"[GENE_NETWORK] Graph walking propagation for all cells ({propagation_steps} steps each)")
    
    # =========================================================================
    # GET REQUIRED ITEMS FROM CONTEXT
    # =========================================================================
    if not context:
        print("[ERROR] No context provided")
        return False
    
    population = context.get('population')
    if not population:
        print("[ERROR] No population in context")
        return False
    
    gene_networks = context.get('gene_networks', {})
    if not gene_networks:
        print("[ERROR] No gene networks in context - run 'Initialize Gene Networks' first")
        return False
    
    cells = population.state.cells
    num_cells = len(cells)
    
    # Check if hierarchical (has fate_hierarchy attribute)
    sample_gn = next(iter(gene_networks.values()))
    is_hierarchical = hasattr(sample_gn, 'fate_hierarchy')
    
    # =========================================================================
    # BUILD GRAPH CONNECTIVITY FOR ALL CELLS
    # =========================================================================
    # Build output links (which nodes depend on each node)
    for cell_id, cell_gn in gene_networks.items():
        if not hasattr(cell_gn, '_output_links_built'):
            _build_output_links(cell_gn)
            cell_gn._output_links_built = True
    
    # =========================================================================
    # PROPAGATE EACH CELL'S GENE NETWORK
    # =========================================================================
    cells_with_gn = 0
    cells_without_gn = 0
    phenotype_updates = 0
    
    for cell_id, cell in cells.items():
        cell_gn = gene_networks.get(cell_id)
        
        if cell_gn is None:
            cells_without_gn += 1
            continue
        
        cells_with_gn += 1
        
        # === GRAPH WALKING PROPAGATION ===
        # Initialize last_node to random input (or any node with outputs)
        if not hasattr(cell_gn, '_last_node'):
            cell_gn._last_node = _get_random_start_node(cell_gn)
        
        # Track fate firings for hierarchical networks
        if is_hierarchical:
            fate_fire_counts = {fate: 0 for fate in cell_gn.fate_hierarchy}
        
        # Propagate for N steps
        for _ in range(propagation_steps):
            updated_node, fate_fired = _graph_walking_update(cell_gn)
            
            # Track fate firings for hierarchical logic
            if is_hierarchical and fate_fired and updated_node:
                if updated_node in fate_fire_counts:
                    fate_fire_counts[updated_node] += 1
        
        # Get final states
        gene_states = {name: node.current_state for name, node in cell_gn.nodes.items()}
        
        # Update cell state
        updates = {'gene_states': gene_states}
        
        # Apply hierarchical fate logic if applicable
        if is_hierarchical:
            # Determine effective fate (last one that fired wins)
            effective_fate = "Quiescent"
            for fate in cell_gn.fate_hierarchy:
                if fate_fire_counts[fate] > 0:
                    effective_fate = fate
            
            cell_gn.effective_fate = effective_fate
            updates['phenotype'] = effective_fate
            phenotype_updates += 1
        
        cell.state = cell.state.with_updates(**updates)
    
    # =========================================================================
    # LOG SUMMARY
    # =========================================================================
    if verbose:
        print(f"   [+] Updated {cells_with_gn}/{num_cells} cells")
        if cells_without_gn > 0:
            print(f"   [!] Skipped {cells_without_gn} cells without gene network")
        if phenotype_updates > 0:
            print(f"   [+] Updated phenotype for {phenotype_updates} cells (hierarchical fate logic)")
            
            # Show phenotype distribution (for comparison)
            phenotype_counts = Counter()
            for cell_id, cell in cells.items():
                phenotype = cell.state.phenotype if hasattr(cell.state, 'phenotype') else None
                if phenotype:
                    phenotype_counts[phenotype] += 1
            
            if phenotype_counts:
                pheno_str = ", ".join([f"'{k}': {v}" for k, v in sorted(phenotype_counts.items(), key=lambda x: -x[1])])
                print(f"   [+] Phenotype distribution: {{{pheno_str}}}")
        else:
            print(f"   [+] No phenotype updates (using BooleanNetwork without fate logic)")
    
    return True


def _build_output_links(gene_network):
    """
    Build output links (which nodes depend on each node).
    
    For each node, find all nodes whose inputs list mentions it.
    This creates the dependency graph needed for graph walking.
    """
    # Initialize output sets for all nodes
    for node in gene_network.nodes.values():
        if not hasattr(node, 'outputs'):
            node.outputs = set()
    
    # Build output links by examining input dependencies
    for node_name, node in gene_network.nodes.items():
        if node.is_input or not node.update_function:
            continue
        
        # Use the inputs list (already extracted from logic)
        if hasattr(node, 'inputs') and node.inputs:
            dependencies = node.inputs if isinstance(node.inputs, set) else set(node.inputs)
            
            # Add this node as an output for each dependency
            for dep_name in dependencies:
                if dep_name in gene_network.nodes:
                    gene_network.nodes[dep_name].outputs.add(node_name)


def _get_random_start_node(gene_network):
    """Get a random input node (or any node with outputs) to start graph walking."""
    # Try to find input nodes
    input_nodes = [name for name, node in gene_network.nodes.items() if node.is_input]
    if input_nodes:
        return random.choice(input_nodes)
    
    # Fallback: any node with outputs
    nodes_with_outputs = [name for name, node in gene_network.nodes.items() 
                         if hasattr(node, 'outputs') and node.outputs]
    if nodes_with_outputs:
        return random.choice(nodes_with_outputs)
    
    # Last resort: any node
    return random.choice(list(gene_network.nodes.keys()))


def _graph_walking_update(gene_network):
    """
    Perform one graph walking update step.
    
    1. Start from last_node
    2. Pick ONE random outgoing link
    3. Update target node
    4. If fate node fires → reset to OFF, return to input
    5. Otherwise → continue from target
    
    Returns:
        Tuple of (updated_node_name, fate_fired)
    """
    # Get current node
    current_node = gene_network.nodes.get(gene_network._last_node)
    if not current_node:
        gene_network._last_node = _get_random_start_node(gene_network)
        current_node = gene_network.nodes[gene_network._last_node]
    
    # Check if node has outputs
    if not hasattr(current_node, 'outputs') or not current_node.outputs:
        # No outgoing links: reset to random input
        gene_network._last_node = _get_random_start_node(gene_network)
        return None, False
    
    # Pick ONE random outgoing link (graph walking)
    target_name = random.choice(list(current_node.outputs))
    target_node = gene_network.nodes[target_name]
    
    # Evaluate target node's logic rule
    if target_node.update_function:
        current_states = {name: node.current_state for name, node in gene_network.nodes.items()}
        new_state = target_node.update_function(current_states)
        
        # Update target node
        old_state = target_node.current_state
        target_node.current_state = new_state
        
        # Check if this is a fate node that fired
        fate_nodes = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}
        fate_fired = False
        
        if target_name in fate_nodes and new_state:
            # Fate node fired!
            fate_fired = True
            
            # Reset fate node to OFF (transient trigger behavior)
            target_node.current_state = False
            
            # Return to random input node
            gene_network._last_node = _get_random_start_node(gene_network)
            
            return target_name, fate_fired
        else:
            # Regular node: continue walking from this node
            gene_network._last_node = target_name
            return target_name, False
    else:
        # No update function
        gene_network._last_node = target_name
        return None, False
