"""Save checkpoint file with cell positions and gene states.

This function saves cell data to a VTK checkpoint file that can be loaded later.
VTK format supports both 2D and 3D simulations with gene networks.
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Save Checkpoint (VTK)",
    description="Save cell positions and gene states to a VTK checkpoint file",
    category="FINALIZATION",
    parameters=[
        {
            "name": "file_path",
            "type": "STRING",
            "description": "Path to save checkpoint VTK file (relative to output_dir or absolute)",
            "default": "checkpoint.vtk",
            "required": True
        },
        {
            "name": "include_gene_states",
            "type": "BOOL",
            "description": "Include gene network states in checkpoint",
            "default": True
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def save_checkpoint_vtk(
    context: Dict[str, Any],
    file_path: str = "checkpoint.vtk",
    include_gene_states: bool = True,
    **kwargs
) -> bool:
    """
    Save cell positions and gene states to a VTK checkpoint file.

    This function saves current population state to a VTK file that can be
    loaded later with read_checkpoint. VTK format supports 2D and 3D simulations
    with gene networks, phenotypes, ages, and generations.

    Args:
        context: Workflow context containing population, config, gene_networks, etc.
        file_path: Path to save checkpoint VTK file (relative to output_dir or absolute)
        include_gene_states: Whether to include gene network states
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    population = context.get('population')
    config = context.get('config')
    gene_networks = context.get('gene_networks', {})
    
    if population is None:
        raise RuntimeError("No population in context")
    if config is None:
        raise RuntimeError("No config in context")

    # Determine output directory
    if 'output_dir' in context:
        output_dir = Path(context['output_dir'])
    else:
        output_dir = Path(config.output_dir) if hasattr(config, 'output_dir') else Path('results')
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Resolve checkpoint path
    checkpoint_path = Path(file_path)
    if not checkpoint_path.is_absolute():
        checkpoint_path = output_dir / file_path
    
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[WORKFLOW] Saving checkpoint to: {checkpoint_path}")

    from src.io.vtk_domain_loader import VTKDomainLoader

    # CellPopulation owns cells through its immutable population state.
    cells = list(population.state.cells.values())
    if not cells:
        print("[WARNING] No cells to save")
        return True
        
    positions = []
    phenotypes = []
    ages = []
    generations = []
    gene_states_list = []
    metabolism_list = []
        
    # Extract all gene node names from first cell's gene network (if available)
    gene_nodes = []
    if include_gene_states and gene_networks:
        first_cell_id = cells[0].state.id
        if first_cell_id in gene_networks:
            gene_network = gene_networks[first_cell_id]
            if hasattr(gene_network, 'nodes'):
                gene_nodes = list(gene_network.nodes.keys())
        
    # Collect data from all cells
    for cell in cells:
        state = cell.state
        positions.append(tuple(state.position))
        phenotypes.append(state.phenotype)
        ages.append(state.age)
        generations.append(state.division_count)
            
        # Gene states
        if include_gene_states and state.id in gene_networks:
            gene_network = gene_networks[state.id]
            gene_states_list.append({
                gene_name: bool(gene_network.nodes[gene_name].current_state)
                if hasattr(gene_network, 'nodes') and gene_name in gene_network.nodes
                else False
                for gene_name in gene_nodes
            })
        else:
            gene_states_list.append({})
        metabolism_list.append(state.metabolic_state.get('value', 0))
        
    # Prepare metadata
    cell_size_um = getattr(config.domain, 'cell_height', 20.0)
    if hasattr(cell_size_um, 'micrometers'):
        cell_size_um = cell_size_um.micrometers
        
    metadata = {
        'biocell_grid_size_um': float(cell_size_um),
        'dimensions': config.domain.dimensions,
        'ages': ages,
        'generations': generations,
    }
        
    # Save as VTK domain file
    loader = VTKDomainLoader()
    loader.save_complete_domain(
        file_path=str(checkpoint_path),
        positions=positions,
        gene_states=gene_states_list,
        phenotypes=phenotypes,
        metabolism=metabolism_list,
        gene_nodes=gene_nodes,
        metadata=metadata,
    )
        
    print(f"[WORKFLOW] Successfully saved {len(cells)} cells to checkpoint")
    print(f"   [+] File: {checkpoint_path}")
    print(f"   [+] Gene networks: {'Yes' if gene_nodes else 'No'}")
    print(f"   [+] Gene nodes: {len(gene_nodes)}")
    return True
