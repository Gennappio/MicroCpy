"""
Setup cell population and gene network.

This function initializes the cell population and gene network infrastructure.
"""

from typing import Dict, Any


def setup_population(
    context: Dict[str, Any],
    enable_gene_network: bool = True,
    custom_functions_module: str = "src/config/custom_functions.py",
    **kwargs
) -> bool:
    """
    Setup cell population and gene network.
    
    Args:
        context: Workflow context (must contain config, mesh_manager, simulator)
        enable_gene_network: Whether to enable the gene network
        custom_functions_module: Path to custom functions module
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Setting up cell population and gene network")
    
    try:
        from src.gene_network.boolean_network import BooleanNetwork
        from src.cell.cell_population import CellPopulation
        
        config = context.get('config')
        mesh_manager = context.get('mesh_manager')
        
        if not config or not mesh_manager:
            print("[ERROR] Config and mesh_manager must be set up before population")
            return False
        
        # Create gene network
        if enable_gene_network:
            gene_network = BooleanNetwork(config=config)
            print(f"   [+] Created gene network")
        else:
            gene_network = None
            print(f"   [+] Gene network disabled")
        
        context['gene_network'] = gene_network
        
        # Create cell population
        population = CellPopulation(
            grid_size=(config.domain.nx, config.domain.ny),
            gene_network=gene_network,
            custom_functions_module=custom_functions_module,
            config=config
        )
        context['population'] = population
        
        print(f"   [+] Created cell population")
        print(f"   [+] Grid size: {config.domain.nx}x{config.domain.ny}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup population: {e}")
        import traceback
        traceback.print_exc()
        return False

