"""
Setup cell population and gene network.

This function initializes the cell population and gene network infrastructure.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
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
            "name": "custom_functions_module",
            "type": "STRING",
            "description": "Path to custom functions module",
            "default": "src/config/custom_functions.py"
        }
    ],
    outputs=["population", "gene_network"],
    cloneable=False
)
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
        from src.biology.gene_network import BooleanNetwork
        from src.biology.population import CellPopulation
        
        config = context.get('config')
        mesh_manager = context.get('mesh_manager')
        
        if not config or not mesh_manager:
            print("[ERROR] Config and mesh_manager must be set up before population")
            return False

        # Store custom functions path in config and context
        # Resolve path relative to workflow file directory (if relative path given)
        from pathlib import Path
        custom_functions_path = Path(custom_functions_module)

        # If path is relative, try multiple resolution strategies
        if not custom_functions_path.is_absolute() and not custom_functions_path.exists():
            resolved = False
            # This file is at: src/workflow/functions/initialization/setup_population.py
            # So we need to go up 5 levels to get to microc-2.0 root
            microc_root = Path(__file__).parent.parent.parent.parent.parent

            # Strategy 1: Relative to workflow file directory
            workflow_file = context.get('workflow_file')
            if workflow_file:
                workflow_dir = Path(workflow_file).parent
                resolved_path = workflow_dir / custom_functions_module
                if resolved_path.exists():
                    custom_functions_path = resolved_path
                    resolved = True
                    print(f"   [+] Resolved custom functions path (workflow-relative): {custom_functions_path}")

            # Strategy 2: Relative to microc-2.0 root directory
            if not resolved:
                resolved_path = microc_root / custom_functions_module
                if resolved_path.exists():
                    custom_functions_path = resolved_path
                    resolved = True
                    print(f"   [+] Resolved custom functions path (microc-root-relative): {custom_functions_path}")

            # Strategy 3: Search in tests/ directory and subdirectories
            if not resolved:
                tests_dir = microc_root / "tests"
                if tests_dir.exists():
                    # Search for the file in tests/ and all subdirectories
                    for found_path in tests_dir.rglob(custom_functions_module):
                        if found_path.is_file():
                            custom_functions_path = found_path
                            resolved = True
                            print(f"   [+] Resolved custom functions path (found in tests/): {custom_functions_path}")
                            break

            if not resolved:
                print(f"   [!] WARNING: Custom functions file not found at any location")
                print(f"       Tried: workflow-relative, microc-root-relative, tests/**/{custom_functions_module}")

        # Verify the path exists
        if not custom_functions_path.exists():
            print(f"   [!] ERROR: Custom functions file does not exist: {custom_functions_path}")
        else:
            print(f"   [+] Custom functions file exists: {custom_functions_path}")

        config.custom_functions_path = str(custom_functions_path.absolute())
        context['custom_functions_path'] = str(custom_functions_path.absolute())

        # Create gene network
        if enable_gene_network:
            gene_network = BooleanNetwork(config=config)
            print(f"   [+] Created gene network")
        else:
            gene_network = None
            print(f"   [+] Gene network disabled")
        
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

        # Create cell population (use resolved path, not original parameter)
        population = CellPopulation(
            grid_size=grid_size,
            gene_network=gene_network,
            custom_functions_module=str(custom_functions_path.absolute()),
            config=config
        )
        context['population'] = population

        print(f"   [+] Created cell population")
        print(f"   [+] Biological grid size: {grid_size}")
        print(f"   [+] FiPy solver grid: ({config.domain.nx}, {config.domain.ny}" + (f", {config.domain.nz})" if config.domain.dimensions == 3 else ")"))
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup population: {e}")
        import traceback
        traceback.print_exc()
        return False

