"""
Setup cell population and gene network.

This function initializes the cell population and gene network infrastructure.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always


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
    custom_functions_module: str = "src/config/custom_functions.py",
    verbose: Optional[bool] = None,
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
        from pathlib import Path

        # === CLEAN ARCHITECTURE: Use context['resolve_path'] if available ===
        if 'resolve_path' in context:
            resolve_path = context['resolve_path']
            custom_functions_path = resolve_path(custom_functions_module)
            if custom_functions_path.exists():
                print(f"   [+] Resolved custom functions path: {custom_functions_path}")
            else:
                print(f"   [!] WARNING: Custom functions file not found: {custom_functions_module}")
        else:
            # Fallback to local resolution for legacy contexts
            custom_functions_path = Path(custom_functions_module)

            # If path is relative, try multiple resolution strategies
            if not custom_functions_path.is_absolute() and not custom_functions_path.exists():
                resolved = False
                project_root = Path(__file__).parent.parent.parent.parent.parent

                # Strategy 1: Relative to workflow file directory
                workflow_file = context.get('workflow_file')
                if workflow_file:
                    workflow_dir = Path(workflow_file).parent
                    resolved_path = workflow_dir / custom_functions_module
                    if resolved_path.exists():
                        custom_functions_path = resolved_path
                        resolved = True
                        print(f"   [+] Resolved custom functions path (workflow-relative): {custom_functions_path}")

                # Strategy 2: Relative to project root directory
                if not resolved:
                    resolved_path = project_root / custom_functions_module
                    if resolved_path.exists():
                        custom_functions_path = resolved_path
                        resolved = True
                        print(f"   [+] Resolved custom functions path (project-root-relative): {custom_functions_path}")

                # Strategy 3: Search in tests/ directory and subdirectories
                if not resolved:
                    tests_dir = project_root / "tests"
                    if tests_dir.exists():
                        for found_path in tests_dir.rglob(custom_functions_module):
                            if found_path.is_file():
                                custom_functions_path = found_path
                                resolved = True
                                print(f"   [+] Resolved custom functions path (found in tests/): {custom_functions_path}")
                                break

                if not resolved:
                    print(f"   [!] WARNING: Custom functions file not found at any location")
                    print(f"       Tried: workflow-relative, project-root-relative, tests/**/{custom_functions_module}")

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
            print(f"   [+] Created gene network with {len(gene_network.nodes)} nodes")
            if 'glycoATP' in gene_network.nodes:
                print(f"   [+] glycoATP node: FOUND")
            else:
                print(f"   [!] glycoATP node: NOT FOUND!")
                print(f"       Available nodes: {list(gene_network.nodes.keys())[:15]}...")
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
        # Pass context so gene networks are stored in context['gene_networks']
        population = CellPopulation(
            grid_size=grid_size,
            gene_network=gene_network,
            custom_functions_module=str(custom_functions_path.absolute()),
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

