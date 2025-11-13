"""
Standard workflow functions for MicroC.

These are high-level orchestrator functions that can be used in workflows.
They receive the full simulation context and can call helper functions.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from src.io.initial_state import InitialStateManager


# ============================================================================
# INITIALIZATION FUNCTIONS
# ============================================================================

def load_cells_from_vtk(
    context: Dict[str, Any],
    file_path: str,
    **kwargs
) -> bool:
    """
    Load cells from a VTK file during workflow initialization.

    This function loads cell data from a VTK file and initializes the population.
    It should be used in the initialization stage of a workflow.

    Args:
        context: Workflow context containing population, config, etc.
        file_path: Path to VTK file (relative to microc-2.0 root or absolute)
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    population = context['population']
    config = context['config']

    print(f"[WORKFLOW] Loading cells from VTK: {file_path}")

    # Resolve file path
    vtk_path = Path(file_path)
    if not vtk_path.is_absolute():
        # Try relative to microc-2.0 root
        microc_root = Path(__file__).parent.parent.parent
        vtk_path = microc_root / file_path

    if not vtk_path.exists():
        print(f"[ERROR] VTK file not found: {vtk_path}")
        return False

    try:
        # Create initial state manager
        initial_state_manager = InitialStateManager(config)

        # Load cell data from VTK
        cell_data, detected_cell_size_um = initial_state_manager.load_initial_state_from_vtk(str(vtk_path))

        print(f"[WORKFLOW] Loaded {len(cell_data)} cells from VTK")
        print(f"[WORKFLOW] Detected cell size: {detected_cell_size_um:.2f} um")

        # Initialize cells in population
        cells_loaded = population.initialize_cells(cell_data)

        print(f"[WORKFLOW] Successfully initialized {cells_loaded} cells")

        # Update config with detected cell size if needed
        if detected_cell_size_um:
            try:
                from src.config.config import Length
                config.domain.cell_height = Length(detected_cell_size_um, "um")
                print(f"[WORKFLOW] Updated cell_height to {detected_cell_size_um:.2f} um")
            except ImportError:
                # If Length import fails, just skip updating cell_height
                print(f"[WORKFLOW] Note: Detected cell size {detected_cell_size_um:.2f} um (config not updated)")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to load VTK file: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_cells_from_csv(
    context: Dict[str, Any],
    file_path: str,
    **kwargs
) -> bool:
    """
    Load cells from a CSV file during workflow initialization.

    This function loads cell data from a CSV file and initializes the population.
    It should be used in the initialization stage of a workflow.

    Args:
        context: Workflow context containing population, config, etc.
        file_path: Path to CSV file (relative to microc-2.0 root or absolute)
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    population = context['population']
    config = context['config']

    print(f"[WORKFLOW] Loading cells from CSV: {file_path}")

    # Resolve file path
    csv_path = Path(file_path)
    if not csv_path.is_absolute():
        # Try relative to microc-2.0 root
        microc_root = Path(__file__).parent.parent.parent
        csv_path = microc_root / file_path

    if not csv_path.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        return False

    try:
        # Create initial state manager
        initial_state_manager = InitialStateManager(config)

        # Load cell data from CSV
        cell_data, detected_cell_size_um = initial_state_manager.load_initial_state_from_csv(str(csv_path))

        print(f"[WORKFLOW] Loaded {len(cell_data)} cells from CSV")
        if detected_cell_size_um:
            print(f"[WORKFLOW] Detected cell size: {detected_cell_size_um:.2f} um")

        # Initialize cells in population
        cells_loaded = population.initialize_cells(cell_data)

        print(f"[WORKFLOW] Successfully initialized {cells_loaded} cells")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to load CSV file: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# INTRACELLULAR FUNCTIONS
# ============================================================================

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
    
    # Update phenotypes based on gene states
    helpers['update_phenotypes']()
    
    # Remove dead cells
    helpers['remove_dead_cells']()


def standard_diffusion_update(
    population,
    simulator,
    gene_network,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Standard diffusion update workflow function.
    
    This is the default behavior when no custom workflow is specified.
    Runs the diffusion solver with substance reactions from cells.
    
    Args:
        population: Population object
        simulator: Diffusion simulator
        gene_network: Gene network object
        config: Configuration object
        helpers: Dictionary of helper functions
    """
    # Run diffusion solver
    helpers['run_diffusion']()


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
    helpers['update_phenotypes']()
    helpers['remove_dead_cells']()
    
    # Get cell count after
    cell_count_after = len(population.cells)
    
    if cell_count_after < cell_count_before:
        print(f"[CUSTOM] {cell_count_before - cell_count_after} cells died")


def custom_diffusion_with_validation(
    population,
    simulator,
    gene_network,
    config,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Example custom diffusion function with validation.
    
    Shows how to add validation around diffusion.
    """
    # Get concentrations before
    conc_before = simulator.get_substance_concentrations()
    
    # Run diffusion
    helpers['run_diffusion']()
    
    # Get concentrations after
    conc_after = simulator.get_substance_concentrations()
    
    # Validate (example: check for negative concentrations)
    for substance_name, conc_field in conc_after.items():
        min_conc = conc_field.min()
        if min_conc < 0:
            print(f"[WARNING] Negative concentration detected for {substance_name}: {min_conc}")


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
    # Deliberately skip: helpers['update_phenotypes']()
    helpers['remove_dead_cells']()


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
    helpers['update_phenotypes']()
    # Deliberately skip: helpers['remove_dead_cells']()


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
    helpers['update_phenotypes']()
    helpers['remove_dead_cells']()
    
    # Custom analysis
    if step % 10 == 0:  # Every 10 steps
        phenotype_counts = {}
        for cell in population.cells.values():
            phenotype = cell.phenotype
            phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1
        
        print(f"[ANALYSIS] Step {step} phenotype distribution: {phenotype_counts}")


def diffusion_with_boundary_check(
    simulator,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Diffusion update with boundary condition checking.

    Example showing how to monitor boundary conditions.
    """
    # Run diffusion
    helpers['run_diffusion']()

    # Check boundary conditions
    if step % 50 == 0:  # Every 50 steps
        conc = simulator.get_substance_concentrations()
        for substance_name, conc_field in conc.items():
            mean_conc = conc_field.mean()
            print(f"[BOUNDARY] Step {step} - {substance_name} mean: {mean_conc:.6f}")


# ============================================================================
# FINALIZATION FUNCTIONS
# ============================================================================

def standard_data_collection(
    population,
    simulator,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Standard data collection for finalization stage.

    Collects final statistics about the simulation:
    - Cell population statistics
    - Substance concentration statistics
    - Final state summary

    This should be called in the finalization stage of the workflow.
    """
    print("[STATS] Collecting final simulation data...")

    # Get final population statistics
    pop_stats = population.get_population_statistics()
    print(f"[STATS] Final cell count: {pop_stats.get('total_cells', 0)}")

    # Get final substance statistics
    substance_stats = simulator.get_summary_statistics()
    print(f"[STATS] Final substance statistics:")
    for substance_name, stats in substance_stats.items():
        print(f"  {substance_name}: mean={stats['mean']:.6f}, min={stats['min']:.6f}, max={stats['max']:.6f}")

    # Phenotype distribution
    if hasattr(population, 'cells'):
        phenotype_counts = {}
        for cell in population.cells.values():
            phenotype = cell.phenotype if hasattr(cell, 'phenotype') else 'unknown'
            phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1

        print(f"[STATS] Final phenotype distribution:")
        for phenotype, count in sorted(phenotype_counts.items()):
            print(f"  {phenotype}: {count} cells")


def export_final_state(
    population,
    simulator,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Export final simulation state.

    This can be used in the finalization stage to export the final state
    of the simulation for analysis or visualization.
    """
    print("[EXPORT] Exporting final simulation state...")

    # This would call the appropriate export functions
    # For now, just a placeholder showing the pattern
    # In the future, this could call helpers['export_final_state']()
    pass


def generate_summary_plots(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Generate summary plots in finalization stage.

    This function generates all automatic plots (substance heatmaps, etc.)
    that would normally be generated automatically in non-workflow mode.

    Args:
        context: Workflow context containing population, simulator, config, etc.
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    print("[WORKFLOW] Generating summary plots...")

    try:
        # Import AutoPlotter
        from src.plotting.autoplotter import AutoPlotter

        population = context['population']
        simulator = context['simulator']
        config = context['config']
        results = context.get('results', {})

        # Create plotter
        plotter = AutoPlotter(config, config.plots_dir)

        # Generate all plots
        generated_plots = plotter.generate_all_plots(results, simulator, population)

        print(f"[WORKFLOW] Generated {len(generated_plots)} plots")
        return True

    except ImportError:
        print("[WORKFLOW] AutoPlotter not available, skipping plots")
        return False
    except Exception as e:
        print(f"[WORKFLOW] Error generating plots: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_simulation_data(
    context: Dict[str, Any],
    save_config: bool = True,
    save_timeseries: bool = True,
    save_substances: bool = True,
    **kwargs
) -> bool:
    """
    Save simulation data to files in finalization stage.

    This function saves simulation results (time series, substance data, config)
    that would normally be saved automatically in non-workflow mode.

    Args:
        context: Workflow context containing results, config, etc.
        save_config: Whether to save simulation configuration
        save_timeseries: Whether to save time series data
        save_substances: Whether to save substance statistics
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    print("[WORKFLOW] Saving simulation data...")

    try:
        import json
        import numpy as np

        config = context['config']
        results = context.get('results', {})

        output_dir = config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save configuration
        if save_config:
            config_file = output_dir / "simulation_config.json"
            with open(config_file, 'w') as f:
                json.dump({
                    'domain': {
                        'nx': config.domain.nx,
                        'ny': config.domain.ny,
                        'size_x': config.domain.size_x.value,
                        'size_y': config.domain.size_y.value
                    },
                    'substances': list(config.substances.keys()),
                    'associations': config.associations,
                    'num_steps': len(results.get('time', [])),
                    'dt': results['time'][1] - results['time'][0] if len(results.get('time', [])) > 1 else 0
                }, f, indent=2)
            print(f"   [OK] Saved config to {config_file}")

        # Save time series data
        if save_timeseries and 'time' in results:
            np.save(output_dir / "time.npy", results['time'])
            print(f"   [OK] Saved time series data")

        # Save substance statistics
        if save_substances and 'substance_stats' in results:
            substance_data = {}
            for substance_name, stats in results['substance_stats'].items():
                substance_data[substance_name] = {
                    'mean': stats['mean'],
                    'min': stats['min'],
                    'max': stats['max']
                }

            with open(output_dir / "substance_stats.json", 'w') as f:
                json.dump(substance_data, f, indent=2)
            print(f"   [OK] Saved substance statistics")

        print(f"[WORKFLOW] Data saved to {output_dir}")
        return True

    except Exception as e:
        print(f"[WORKFLOW] Error saving data: {e}")
        import traceback
        traceback.print_exc()
        return False

