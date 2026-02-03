"""
Initialize gene states for all cells.

This function randomizes gene states for all cells after population setup.
This ensures cells start with random metabolic states (mitoATP, glycoATP, etc.)
rather than all being False/inactive.
"""

from typing import Dict, Any
import random
from src.workflow.decorators import register_function


@register_function(
    display_name="Initialize Gene States",
    description="Randomize gene states for all cells after population setup. Ensures cells start with active metabolism.",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "random_seed",
            "type": "INT",
            "description": "Random seed for reproducibility (0 = use system time)",
            "default": 0
        },
        {
            "name": "fate_nodes_false",
            "type": "BOOL",
            "description": "Keep fate nodes (Apoptosis, Proliferation, etc.) as False",
            "default": True
        }
    ],
    inputs=["context"],
    outputs=["initialized_gene_states"],
    cloneable=False
)
def initialize_gene_states(
    context: Dict[str, Any],
    random_seed: int = 0,
    fate_nodes_false: bool = True,
    **kwargs
) -> bool:
    """
    Initialize gene states for all cells with random values.
    
    This function should be called after setup_population and setup_gene_network
    to ensure all cells start with properly initialized gene states rather than
    empty dictionaries or all False values.
    
    Args:
        context: Workflow context containing population and gene_network
        random_seed: Random seed for reproducibility (0 = use system time)
        fate_nodes_false: If True, keep fate nodes (Apoptosis, Proliferation, etc.) as False
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    population = context.get('population')
    gene_network = context.get('gene_network')
    
    if not population:
        print("[ERROR] Population must be set up before initializing gene states")
        return False
    
    if not gene_network:
        print("[WARNING] No gene network found - skipping gene state initialization")
        return True
    
    # Set random seed if specified
    if random_seed > 0:
        random.seed(random_seed)
        print(f"[WORKFLOW] Initializing gene states with random seed: {random_seed}")
    else:
        print(f"[WORKFLOW] Initializing gene states with random values")
    
    # Get all gene node names from the gene network template
    gene_node_names = list(gene_network.nodes.keys())
    
    # Define fate nodes that should stay False
    fate_nodes = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}
    
    # Track statistics
    total_cells = len(population.state.cells)
    cells_updated = 0
    gene_stats = {gene: 0 for gene in gene_node_names}
    
    # Update each cell's gene states
    updated_cells = {}
    
    for cell_id, cell in population.state.cells.items():
        # Create random gene states for this cell
        new_gene_states = {}
        
        for gene_name in gene_node_names:
            # Check if this is a fate node
            if fate_nodes_false and gene_name in fate_nodes:
                # Fate nodes start as False
                new_gene_states[gene_name] = False
            else:
                # All other nodes get random True/False
                new_gene_states[gene_name] = random.choice([True, False])
                if new_gene_states[gene_name]:
                    gene_stats[gene_name] += 1
        
        # Update cell state with new gene states
        cell.state = cell.state.with_updates(gene_states=new_gene_states)
        updated_cells[cell_id] = cell
        cells_updated += 1
    
    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)
    
    # Print summary
    print(f"[WORKFLOW] Initialized gene states for {cells_updated}/{total_cells} cells")
    print(f"[WORKFLOW] Gene activation statistics:")
    
    # Show key metabolic genes
    key_genes = ['mitoATP', 'glycoATP', 'GLUT1', 'MCT1', 'MCT4']
    for gene in key_genes:
        if gene in gene_stats:
            count = gene_stats[gene]
            percentage = (count / total_cells * 100) if total_cells > 0 else 0
            print(f"   {gene}: {count}/{total_cells} active ({percentage:.1f}%)")
    
    # Show fate nodes (should all be 0 if fate_nodes_false=True)
    if fate_nodes_false:
        fate_active = sum(gene_stats.get(fn, 0) for fn in fate_nodes)
        print(f"   Fate nodes (Apoptosis, Proliferation, etc.): {fate_active} active (should be 0)")
    
    return True

