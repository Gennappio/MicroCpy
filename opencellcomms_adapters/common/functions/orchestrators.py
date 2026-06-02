"""Legacy high-level workflow orchestrators, lifted out of the engine's
``standard_functions.py``.

These build populations / gene networks or drive the legacy ``helpers``-based
intracellular loop, so they are biology and live in the ``common`` adapter.
They are referenced only by legacy workflows; the active ABM models do not use
them.
"""
from typing import Dict, Any
from pathlib import Path

from src.workflow.decorators import register_function


@register_function(
    display_name="Load Config File",
    description="Load YAML configuration file and setup simulation infrastructure",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "config_file",
            "type": "STRING",
            "description": "Path to YAML configuration file",
            "default": "config/default_config.yaml",
            "required": True
        }
    ],
    outputs=["config", "simulator", "population", "gene_network"],
    cloneable=False
)
def load_config_file(
    context: Dict[str, Any],
    config_file: str,
    **kwargs
) -> bool:
    """
    Load configuration file in initialization stage.

    This function loads a YAML configuration file and sets up the simulation
    infrastructure (config, simulator, population, etc.).

    Args:
        context: Workflow context (will be populated with config, simulator, etc.)
        config_file: Path to YAML configuration file (relative to project root or absolute)
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    print(f"[WORKFLOW] Loading configuration file: {config_file}")

    try:
        import sys
        from datetime import datetime
        import shutil

        # Add the engine's tools/ directory to path to import load_configuration.
        # This file lives at opencellcomms_adapters/common/functions/orchestrators.py,
        # so parents[3] is the repo root and the engine is a sibling package.
        engine_root = Path(__file__).resolve().parents[3] / "opencellcomms_engine"
        tools_dir = engine_root / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))

        from run_sim import load_configuration, setup_simulation

        # Resolve config file path relative to the engine root if not absolute
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = engine_root / config_path

        # Load configuration (suppress output)
        config, custom_functions_path = load_configuration(str(config_path), verbose=False)

        # Mark as workflow mode to skip automatic VTK loading
        config._workflow_mode = True

        print(f"[WORKFLOW] Configuration loaded successfully")

        # Create timestamped subfolder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_output_dir = config.output_dir
        timestamped_dir = original_output_dir / timestamp
        config.output_dir = timestamped_dir
        config.plots_dir = timestamped_dir / "plots"
        config.output_dir.mkdir(parents=True, exist_ok=True)
        config.plots_dir.mkdir(parents=True, exist_ok=True)

        # Copy config file to output directory (use resolved path)
        config_copy_path = config.output_dir / config_path.name
        shutil.copy2(config_path, config_copy_path)
        print(f"[WORKFLOW] Configuration copied to: {config_copy_path}")

        # Setup simulation infrastructure (suppress output in workflow mode)
        mesh_manager, simulator, gene_network, population, detected_cell_size_um = setup_simulation(
            config, custom_functions_path, verbose=False
        )

        # Populate context
        context['config'] = config
        context['simulator'] = simulator
        context['gene_network'] = gene_network
        context['population'] = population
        context['mesh_manager'] = mesh_manager
        context['custom_functions_path'] = custom_functions_path
        context['results'] = {
            'time': [],
            'cell_count': [],
            'substance_stats': {}
        }

        print(f"[WORKFLOW] Simulation infrastructure initialized")
        print(f"   [+] Output directory: {config.output_dir}")

        return True

    except Exception as e:
        print(f"[WORKFLOW] Error loading config file: {e}")
        import traceback
        traceback.print_exc()
        return False


def initialize_simulation_infrastructure(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Initialize simulation infrastructure (substances, mesh, gene network).

    This function initializes all the infrastructure components that are
    normally initialized automatically in non-workflow mode:
    - Substance simulator with initial concentrations
    - Mesh and domain setup
    - Gene network initialization

    This should be called in the initialization stage before any other functions.

    Args:
        context: Workflow context containing config, simulator, etc.
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    print("[WORKFLOW] Initializing simulation infrastructure...")

    try:
        simulator = context.get('simulator')
        config = context.get('config')

        if not simulator or not config:
            print("[WORKFLOW] Error: simulator or config not found in context")
            return False

        # Infrastructure is already initialized by setup_simulation()
        # This function just prints a summary
        print(f"   [+] Substances: {len(config.substances)}")
        print(f"   [+] Domain: {config.domain.size_x.micrometers}x{config.domain.size_y.micrometers} um")
        print(f"   [+] Mesh: {config.domain.nx}x{config.domain.ny} cells")

        return True

    except Exception as e:
        print(f"[WORKFLOW] Error initializing infrastructure: {e}")
        import traceback
        traceback.print_exc()
        return False


@register_function(
    display_name="Standard Intracellular Update",
    description="Standard intracellular update (metabolism, gene networks, phenotypes, death)",
    category="INTRACELLULAR",
    outputs=[],
    cloneable=False
)
def standard_intracellular_update(
    population,
    simulator,
    gene_network,
    config,
    dt: float,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Standard intracellular update workflow function.

    This is the default behavior when no custom workflow is specified.
    Calls all the standard intracellular operations in order:
    1. Update intracellular processes (metabolism, gene networks)
    2. Update gene networks based on environment
    3. Update phenotypes based on gene states
    4. Remove dead cells

    Args:
        population: Population object
        simulator: Diffusion simulator
        gene_network: Gene network object
        config: Configuration object
        dt: Time step
        helpers: Dictionary of helper functions
    """
    # Run intracellular processes (calls custom metabolism functions)
    helpers['update_intracellular']()

    # Update gene networks based on current environment
    helpers['update_gene_networks']()


@register_function(
    display_name="Standard Intercellular Update",
    description="Standard intercellular update (cell division, migration)",
    category="INTERCELLULAR",
    outputs=[],
    cloneable=False
)
def standard_intercellular_update(
    population,
    simulator,
    gene_network,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Standard intercellular update workflow function.

    This is the default behavior when no custom workflow is specified.
    Handles cell division, migration, and other intercellular processes.

    Args:
        population: Population object
        simulator: Diffusion simulator
        gene_network: Gene network object
        config: Configuration object
        helpers: Dictionary of helper functions
    """
    # Run intercellular processes (calls custom division/migration functions)
    helpers['update_intercellular']()


def custom_intracellular_with_logging(
    population,
    simulator,
    gene_network,
    config,
    dt: float,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Example custom intracellular function with logging.

    Shows how to add custom behavior around standard operations.
    """
    print(f"[CUSTOM] Starting intracellular update at step {step}")

    # Get cell count before
    cell_count_before = len(population.cells)

    # Run standard intracellular update
    helpers['update_intracellular']()
    helpers['update_gene_networks']()

    # NOTE: Phenotype marking now handled by separate functions in intercellular stage
    # Cells are no longer removed - they remain in population but become inactive

    # Get cell count after
    cell_count_after = len(population.cells)

    if cell_count_after < cell_count_before:
        print(f"[CUSTOM] {cell_count_before - cell_count_after} cells changed state")


@register_function(
    display_name="Minimal Intracellular",
    description="Minimal intracellular update (metabolism only, no phenotype changes)",
    category="INTRACELLULAR",
    outputs=[],
    cloneable=False
)
def minimal_intracellular(
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Minimal intracellular update - only metabolism, no phenotype changes.

    Example of a custom workflow that skips certain operations.
    """
    # Only run metabolism, skip phenotype updates
    helpers['update_intracellular']()
    helpers['update_gene_networks']()


@register_function(
    display_name="No Death Intracellular",
    description="Intracellular update without cell death",
    category="INTRACELLULAR",
    outputs=[],
    cloneable=False
)
def no_death_intracellular(
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Intracellular update without cell death.

    Example of a custom workflow that prevents cell death.
    """
    helpers['update_intracellular']()
    helpers['update_gene_networks']()


def intracellular_with_analysis(
    population,
    simulator,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Intracellular update with real-time analysis.

    Example showing how to add custom analysis during simulation.
    """
    # Run standard updates
    helpers['update_intracellular']()
    helpers['update_gene_networks']()
    # NOTE: Phenotype marking now handled by separate functions in intercellular stage

    # Custom analysis
    if step % 10 == 0:  # Every 10 steps
        phenotype_counts = {}
        for cell in population.cells.values():
            phenotype = cell.phenotype
            phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1

        print(f"[ANALYSIS] Step {step} phenotype distribution: {phenotype_counts}")

