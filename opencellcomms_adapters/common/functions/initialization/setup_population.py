"""
Setup cell population and gene network.

This function initializes the cell population and gene network infrastructure.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig, IMeshManager
from src.workflow.logging import log, log_always


@register_function(
    typed_env_exempt=True,
    requires=['gene_networks', 'mesh_manager'],
    display_name="Setup Cell Population",
    description="Initialize cell population and gene network",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "enable_gene_network",
            "type": "BOOL",
            "description": "Whether to enable the gene network",
            "default": True
        },
        {
            "name": "verbose",
            "type": "BOOL",
            "description": "Enable detailed logging",
            "default": None
        }
    ],
    inputs=["context"],
    outputs=["population", "gene_network"],
    cloneable=False
)
def setup_population(
    context: Dict[str, Any],
    enable_gene_network: bool = True,
    verbose: Optional[bool] = None,
    **kwargs
) -> bool:
    """
    Setup cell population and gene network.

    Model-specific behavior belongs in registered plugin functions, not here:
    the legacy `custom_functions_module` hook file was removed. A stray
    `custom_functions_module` value from an archived workflow is absorbed by
    **kwargs and ignored.

    Args:
        context: Workflow context (must contain config, mesh_manager, simulator)
        enable_gene_network: Whether to enable the gene network
        **kwargs: Additional parameters

    Returns:
        True if successful
    """
    # print(f"[WORKFLOW] Setting up cell population and gene network")
    
    try:
        from src.biology.gene_network import BooleanNetwork
        from src.biology.population import CellPopulation
        
        config: Optional[IConfig] = context.get('config')
        mesh_manager: Optional[IMeshManager] = context.get('mesh_manager')
        
        if not config or not mesh_manager:
            print("[ERROR] Config and mesh_manager must be set up before population")
            return False

        # Create gene network
        if enable_gene_network:
            gene_network = BooleanNetwork(config=config)
        else:
            gene_network = None
        
        context['gene_network'] = gene_network

        # Calculate biological grid size based on domain dimensions
        # For biological cells, we use a grid based on cell_height
        domain_size_um = config.domain.size_x.micrometers
        cell_height_um = config.domain.cell_height.micrometers
        biocell_nx = int(domain_size_um / cell_height_um)
        biocell_ny = int(domain_size_um / cell_height_um)

        if config.domain.dimensions == 3:
            biocell_nz = int(domain_size_um / cell_height_um)
            grid_size = (biocell_nx, biocell_ny, biocell_nz)
        else:
            grid_size = (biocell_nx, biocell_ny)

        # Create cell population
        # Pass context so gene networks are stored in context['gene_networks']
        population = CellPopulation(
            grid_size=grid_size,
            gene_network=gene_network,
            config=config,
            context=context  # Pass context for gene network storage
        )
        context['population'] = population

        log(context, f"Created cell population", prefix="[+]", node_verbose=verbose)
        log(context, f"Biological grid size: {grid_size}", prefix="[+]", node_verbose=verbose)
        log(context, f"FiPy solver grid: ({config.domain.nx}, {config.domain.ny}" + (f", {config.domain.nz})" if config.domain.dimensions == 3 else ")"), prefix="[+]", node_verbose=verbose)

        return True

    except Exception as e:
        log_always(f"[ERROR] Failed to setup population: {e}")
        import traceback
        traceback.print_exc()
        return False

