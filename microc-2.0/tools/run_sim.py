#!/usr/bin/env python3
"""
MicroC 2.0 - Generic Simulation Runner

Usage:
    python run_sim.py config/my_simulation.yaml
    python run_sim.py config/complete_substances_config.yaml
    python run_sim.py my_custom_config.yaml

Features:
- Loads any YAML configuration file
- Automatically loads custom_functions.py specified in YAML
- Runs complete multi-substance simulation
- Saves results to specified output directory
- Configurable simulation parameters
"""

import sys
import argparse
from pathlib import Path
import time
import os
from datetime import datetime
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import MicroCConfig
from src.core.domain import MeshManager
from src.core.units import Length
from simulation.multi_substance_simulator import MultiSubstanceSimulator
from simulation.orchestrator import TimescaleOrchestrator
from biology.population import CellPopulation
from biology.gene_network import BooleanNetwork
from src.io.initial_state import InitialStateManager
import importlib.util

def load_custom_functions(custom_functions_path):
    """Load custom functions from file path"""
    if custom_functions_path is None:
        return None

    try:
        spec = importlib.util.spec_from_file_location("custom_functions", custom_functions_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    except Exception as e:
        print(f"Warning: Could not load custom functions: {e}")
        return None

# Try to import AutoPlotter, but make it optional to avoid scipy hanging issues
try:
    from visualization.auto_plotter import AutoPlotter
    AUTOPLOTTER_AVAILABLE = True
except ImportError as e:
    print(f"[!] AutoPlotter not available (plotting disabled): {e}")
    AUTOPLOTTER_AVAILABLE = False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="MicroC 2.0 - Generic Simulation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_sim.py config/complete_substances_config.yaml
  python run_sim.py my_custom_simulation.yaml
        """
    )
    
    parser.add_argument(
        'config_file',
        type=str,
        help='Path to YAML configuration file'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--save-data',
        action='store_true',
        help='Save simulation data to files'
    )

    parser.add_argument(
        '--no-plots',
        action='store_true',
        help='Disable automatic plot generation'
    )

    parser.add_argument(
        '--workflow',
        type=str,
        default=None,
        help='Path to workflow JSON file for custom simulation behavior'
    )

    return parser.parse_args()

def validate_configuration(config, config_path):
    """Comprehensive configuration validation"""
    print(f"[*] Validating configuration...")

    missing_params = []
    warnings = []

    # 1. Domain validation
    try:
        if not hasattr(config, 'domain'):
            missing_params.append("domain section")
        else:
            domain = config.domain
            if not hasattr(domain, 'size_x') or not hasattr(domain, 'size_y'):
                missing_params.append("domain.size_x and domain.size_y")
            if not hasattr(domain, 'nx') or not hasattr(domain, 'ny'):
                missing_params.append("domain.nx and domain.ny")
            if domain.nx <= 0 or domain.ny <= 0:
                missing_params.append("domain.nx and domain.ny must be positive integers")

            # Check grid spacing
            if hasattr(domain, 'size_x') and hasattr(domain, 'nx'):
                spacing = domain.size_x.micrometers / domain.nx
                if spacing < 1.0 or spacing > 50.0:
                    warnings.append(f"Grid spacing {spacing:.1f} um is outside recommended range (1-50 um)")
    except Exception as e:
        missing_params.append(f"domain configuration error: {e}")

    # 2. Time configuration validation
    try:
        if not hasattr(config, 'time'):
            missing_params.append("time section")
        else:
            time_cfg = config.time
            required_time_params = ['dt', 'end_time', 'diffusion_step', 'intracellular_step', 'intercellular_step']
            for param in required_time_params:
                if not hasattr(time_cfg, param):
                    missing_params.append(f"time.{param}")

            # Validate time values
            if hasattr(time_cfg, 'dt') and time_cfg.dt <= 0:
                missing_params.append("time.dt must be positive")
            if hasattr(time_cfg, 'end_time') and time_cfg.end_time <= 0:
                missing_params.append("time.end_time must be positive")
    except Exception as e:
        missing_params.append(f"time configuration error: {e}")

    # 3. Substances validation
    try:
        if not hasattr(config, 'substances') or not config.substances:
            missing_params.append("substances section (at least one substance required)")
        else:
            for substance_name, substance in config.substances.items():
                required_substance_params = ['diffusion_coeff', 'initial_value', 'boundary_value']
                for param in required_substance_params:
                    if not hasattr(substance, param):
                        missing_params.append(f"substances.{substance_name}.{param}")

                # Check for reasonable values
                if hasattr(substance, 'diffusion_coeff') and substance.diffusion_coeff < 0:
                    missing_params.append(f"substances.{substance_name}.diffusion_coeff must be non-negative")
    except Exception as e:
        missing_params.append(f"substances configuration error: {e}")

    # 4. Gene network validation
    try:
        if hasattr(config, 'gene_network') and config.gene_network:
            gene_net = config.gene_network
            if hasattr(gene_net, 'bnd_file') and gene_net.bnd_file:
                bnd_path = Path(gene_net.bnd_file)
                if not bnd_path.exists():
                    # Try relative to config file
                    bnd_path = config_path.parent / gene_net.bnd_file
                    if not bnd_path.exists():
                        missing_params.append(f"gene_network.bnd_file not found: {gene_net.bnd_file}")
        else:
            warnings.append("No gene network configuration found - cells will have minimal behavior")
    except Exception as e:
        missing_params.append(f"gene_network configuration error: {e}")

    # 5. Output configuration validation
    try:
        if not hasattr(config, 'output'):
            warnings.append("No output configuration found - using defaults")
        else:
            output = config.output
            if hasattr(output, 'save_data_interval') and output.save_data_interval <= 0:
                missing_params.append("output.save_data_interval must be positive")
    except Exception as e:
        missing_params.append(f"output configuration error: {e}")

    # 6. Custom functions validation
    try:
        if hasattr(config, 'custom_functions_path') and config.custom_functions_path:
            custom_path = Path(config.custom_functions_path)
            if not custom_path.exists():
                # Try relative to config file
                custom_path = config_path.parent / config.custom_functions_path
                if not custom_path.exists():
                    missing_params.append(f"custom_functions_path not found: {config.custom_functions_path}")
    except Exception as e:
        missing_params.append(f"custom_functions_path error: {e}")

    # Report results
    if missing_params:
        print(f"[!] Configuration validation failed!")
        print(f"   Missing or invalid parameters:")
        for param in missing_params:
            print(f"   * {param}")

        print(f"\n[HELP] Configuration Help:")
        print(f"   * Check example configurations in: tests/jayatilake_experiment/")
        print(f"   * See complete reference: src/config/complete_substances_config.yaml")
        print(f"   * Documentation: docs/running_simulations.md")
        print(f"   * Required sections: domain, time, substances")
        print(f"   * Optional sections: gene_network, associations, thresholds, output")
        return False

    if warnings:
        print(f"[!] Configuration warnings:")
        for warning in warnings:
            print(f"   * {warning}")

    print(f"[+] Configuration validation passed!")
    return True

def load_configuration(config_file):
    """Load and validate configuration strictly from file (no CLI overrides)."""
    config_path = Path(config_file)

    if not config_path.exists():
        print(f"[!] Configuration file not found: {config_path}")
        print(f"   Current directory: {Path.cwd()}")
        sys.exit(1)

    print(f"[FILE] Loading configuration: {config_path}")

    try:
        config = MicroCConfig.load_from_yaml(config_path)
        print(f"[+] Configuration loaded successfully!")
    except KeyError as e:
        print(f"[!] Failed to load configuration - Missing required parameter: {e}")
        print(f"   This parameter is required in your YAML configuration file.")
        print(f"\n[HELP] Configuration Help:")
        print(f"   * Check example configurations in: tests/jayatilake_experiment/")
        print(f"   * See complete reference: src/config/complete_substances_config.yaml")
        print(f"   * Required sections: domain, time, substances")
        print(f"   * Each section has required parameters - see documentation")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Failed to load configuration: {e}")
        print(f"   This usually indicates a YAML syntax error or missing required sections.")
        print(f"   Please check your configuration file format.")
        print(f"\n[HELP] Common issues:")
        print(f"   * YAML indentation must be consistent (use spaces, not tabs)")
        print(f"   * Missing required sections: domain, time, substances")
        print(f"   * Invalid YAML syntax (check colons, quotes, etc.)")
        sys.exit(1)

    # Validate configuration
    if not validate_configuration(config, config_path):
        sys.exit(1)

    # Load custom functions path from config only
    custom_functions_path = None
    if hasattr(config, 'custom_functions_path') and config.custom_functions_path:
        custom_functions_path = Path(config.custom_functions_path)
        if custom_functions_path.exists():
            print(f"[+] Custom functions found: {custom_functions_path}")
        else:
            print(f"[!] Custom functions file not found: {custom_functions_path}")

    return config, custom_functions_path

def setup_simulation(config, custom_functions_path=None):
    """Setup all simulation components (config-driven only)"""
    print(f"\n[SETUP] Setting up simulation components...")
    
    # Create mesh manager
    mesh_manager = MeshManager(config.domain)
    print(f"   [+] Mesh: {config.domain.nx}x{config.domain.ny} cells")
    print(f"   [+] Domain: {config.domain.size_x.value}x{config.domain.size_y.value} {config.domain.size_x.unit}")
    
    # Create multi-substance simulator
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    print(f"   [+] Substances: {len(simulator.state.substances)}")
    print(f"   [+] FiPy available: {simulator.fipy_mesh is not None}")
    
    # Create gene network
    gene_network = BooleanNetwork(config=config)
    print(f"   [+] Gene network: {len(gene_network.input_nodes)} inputs, {len(gene_network.output_nodes)} outputs")

    # Load custom functions first (from config only)
    custom_functions = load_custom_functions(custom_functions_path)

    # Initialize gene network with custom function if available
    if custom_functions and hasattr(custom_functions, 'initialize_gene_network'):
        custom_functions.initialize_gene_network(gene_network, config)

    # Create cell population with biological cell grid size (not FiPy grid size)
    # Calculate biological grid based on cell_height
    domain_size_um = config.domain.size_x.micrometers
    cell_height_um = config.domain.cell_height.micrometers
    biocell_nx = int(domain_size_um / cell_height_um)
    biocell_ny = int(domain_size_um / cell_height_um)

    if config.domain.dimensions == 3:
        biocell_nz = int(domain_size_um / cell_height_um)
        biocell_grid_size = (biocell_nx, biocell_ny, biocell_nz)
    else:
        biocell_grid_size = (biocell_nx, biocell_ny)

    print(f"   [*] Population biocell grid: {biocell_grid_size}")
    print(f"   [*] FiPy solver grid: {(config.domain.nx, config.domain.ny)}")

    population = CellPopulation(
        grid_size=biocell_grid_size,
        gene_network=gene_network,
        custom_functions_module=custom_functions,
        config=config
    )

    # Initialize cells based on configuration mode
    initial_state_manager = InitialStateManager(config)
    detected_cell_size_um = None

    print(f"[DEBUG] Initial state file_path: {config.initial_state.file_path}")
    print(f"[DEBUG] Domain dimensions: {config.domain.dimensions}")

    if config.initial_state.file_path:
        file_path = Path(config.initial_state.file_path)
        file_suffix = file_path.suffix.lower()

        try:
            if file_suffix == ".vtk":
                # Load initial state from VTK file
                print(f"[*] Loading initial state from VTK: {config.initial_state.file_path}")
                cell_data, detected_cell_size_um = initial_state_manager.load_initial_state_from_vtk(config.initial_state.file_path)
                print(f"[DEBUG] VTK loading successful, got {len(cell_data)} cells")
            elif file_suffix == ".csv":
                # Load initial state from CSV file
                print(f"[*] Loading initial state from CSV: {config.initial_state.file_path}")
                cell_data, detected_cell_size_um = initial_state_manager.load_initial_state_from_csv(config.initial_state.file_path)
                print(f"[DEBUG] CSV loading successful, got {len(cell_data)} cells")
            else:
                raise ValueError(f"Unsupported initial state file format: {file_suffix}. Supported formats: .vtk, .csv")

            if cell_data:
                first_cell = cell_data[0]
                print(f"[DEBUG] First cell: ID={first_cell.get('id', 'None')}, position={first_cell.get('position', 'None')}, phenotype={first_cell.get('phenotype', 'None')}")
                print(f"[DEBUG] First cell gene states: {len(first_cell.get('gene_states', {}))} genes")

            cells_loaded = population.initialize_cells(cell_data)
            print(f"   [+] Cells: {cells_loaded} (loaded from {file_suffix.upper()} file)")
            print(f"   [+] Detected cell size: {detected_cell_size_um:.2f} um")

            # Debug: Check first few cell positions
            if population.state.cells:
                print(f"   [DEBUG] First 3 cell positions:")
                for i, (_cell_id, cell) in enumerate(list(population.state.cells.items())[:3]):
                    pos = cell.state.position
                    print(f"     Cell {i}: {pos} (dimensions: {len(pos)})")

            # Update domain configuration with detected cell size
            print(f"[*] Updating domain cell_height from {config.domain.cell_height.micrometers:.2f} um to {detected_cell_size_um:.2f} um")
            config.domain.cell_height = Length(detected_cell_size_um, "um")
        except Exception as e:
            print(f"[!] Failed to load initial state: {e}")
            raise

            # Recalculate biological grid size based on detected cell size
            domain_size_um = config.domain.size_x.micrometers
            biocell_nx = int(domain_size_um / detected_cell_size_um)
            biocell_ny = int(domain_size_um / detected_cell_size_um)

            if config.domain.dimensions == 3:
                biocell_nz = int(domain_size_um / detected_cell_size_um)
                biocell_grid_size = (biocell_nx, biocell_ny, biocell_nz)
            else:
                biocell_grid_size = (biocell_nx, biocell_ny)

            print(f"[*] Updated biological cell grid size: {biocell_grid_size}")

            # Update population grid size
            population.grid_size = biocell_grid_size

        except Exception as e:
            print(f"[!] Failed to load VTK initial state: {e}")
            raise

    else:
        # No initial state file - cells will be initialized by workflow
        print(f"[*] No initial state file specified - cells will be initialized by workflow")
        print(f"   [+] Cells: 0 (will be created by workflow initialization stage)")

    return mesh_manager, simulator, gene_network, population, detected_cell_size_um

def print_concise_status(step, population):
    """Print concise one-line status with metabolic breakdown"""
    # Get metabolic state counts
    metabolic_counts = {
        'mitoATP': 0,
        'glycoATP': 0,
        'Both': 0,
        'None': 0
    }

    total_cells = 0
    for cell in population.state.cells.values():
        total_cells += 1
        if hasattr(cell.state, 'gene_states'):
            mito_atp = cell.state.gene_states.get('mitoATP', False)
            glyco_atp = cell.state.gene_states.get('glycoATP', False)

            if mito_atp and glyco_atp:
                metabolic_counts['Both'] += 1
            elif mito_atp:
                metabolic_counts['mitoATP'] += 1
            elif glyco_atp:
                metabolic_counts['glycoATP'] += 1
            else:
                metabolic_counts['None'] += 1
        else:
            metabolic_counts['None'] += 1

    # Print one-line status
    print(f"[STATS] Step {step}: mitoATP={metabolic_counts['mitoATP']}, glycoATP={metabolic_counts['glycoATP']}, Both={metabolic_counts['Both']}, None={metabolic_counts['None']} (Total: {total_cells})")

def print_detailed_status(step, num_steps, current_time, simulator, population, orchestrator, config, start_time, custom_functions=None):
    """Print detailed simulation status"""
    percentage = (step / num_steps) * 100

    # Get timing info and ETA
    timing_info = orchestrator.get_timing_summary()
    if step > 0:
        elapsed = time.time() - start_time
        avg_time_per_step = elapsed / step if step > 0 else 0
        remaining_steps = num_steps - step
        eta = avg_time_per_step * remaining_steps
        eta_str = f"{eta:.1f}s"
    else:
        eta_str = "calculating..."

    print(f"\n[STATS] STATUS UPDATE - Step {step+1}/{num_steps} ({percentage:.1f}%) - Time: {current_time:.3f} - ETA: {eta_str}")
    print("=" * 80)

    # Cell population analysis
    cell_data = population.get_cell_positions()
    total_cells = len(cell_data)

    # Count cells by phenotype/metabolic state
    phenotype_counts = {}
    metabolic_counts = {'OXPHOS': 0, 'Glyco': 0, 'Both': 0, 'Quiescent': 0, 'Other': 0}

    for pos, phenotype in cell_data:
        # Count by phenotype
        phenotype_counts[phenotype] = phenotype_counts[phenotype] + 1 if phenotype in phenotype_counts else 1

        # Get cell metabolic state using custom color function if available
        try:
            if custom_functions and hasattr(custom_functions, 'get_cell_color'):
                # Get the actual cell object
                cell = population.state.get_cell_at_position(pos)
                if cell:
                    color = custom_functions.get_cell_color(cell, cell.state.gene_states, config)
                    if 'blue' in color.lower() or 'oxphos' in color.lower():
                        metabolic_counts['OXPHOS'] += 1
                    elif 'red' in color.lower() or 'glyco' in color.lower():
                        metabolic_counts['Glycolytic'] += 1
                    elif 'gray' in color.lower() or 'quiescent' in color.lower():
                        metabolic_counts['Quiescent'] += 1
                    else:
                        metabolic_counts['Other'] += 1
                else:
                    metabolic_counts['Other'] += 1
            else:
                metabolic_counts['Other'] += 1
        except:
            metabolic_counts['Other'] += 1

    # Population statistics
    pop_stats = population.get_population_statistics()
    # Note: divisions and deaths are not tracked in get_population_statistics()
    # These would need to be tracked separately if needed
    divisions = pop_stats.get('divisions', 0)  # Default to 0 if not tracked
    deaths = pop_stats.get('deaths', 0)  # Default to 0 if not tracked

    # Count cells with proliferation gene active
    proliferation_active = 0
    for pos, phenotype in cell_data:
        try:
            cell = population.state.get_cell_at_position(pos)
            if cell and hasattr(cell.state, 'gene_states'):
                # Check if Proliferation gene is active
                if cell.state.gene_states['Proliferation']:
                    proliferation_active += 1
        except:
            pass

    print(f"[CELL] CELL POPULATION:")
    print(f"   Total cells: {total_cells}")
    print(f"   Divisions: {divisions}")
    print(f"   Deaths: {deaths}")
    print(f"   Proliferation active: {proliferation_active}")
    print(f"   Metabolic states:")
    for state, count in metabolic_counts.items():
        if count > 0:
            percentage_cells = (count / total_cells * 100) if total_cells > 0 else 0
            print(f"     * {state}: {count} ({percentage_cells:.1f}%)")

    # Substance concentrations
    stats = simulator.get_summary_statistics()
    print(f"\n[METAB] SUBSTANCE CONCENTRATIONS:")
    for substance, substance_stats in stats.items():
        min_val = substance_stats['min']
        max_val = substance_stats['max']
        mean_val = substance_stats['mean']
        print(f"   {substance:>8}: {min_val:.6f} - {max_val:.6f} (avg: {mean_val:.6f})")

    # Performance metrics
    if timing_info:
        print(f"\n[PERF] PERFORMANCE:")
        total_time = 0
        for process, process_stats in timing_info.items():
            avg_time = process_stats['average_time']
            total_time += avg_time
            print(f"   {process.capitalize():>12}: {avg_time:.3f}s")
        if total_time > 0:
            print(f"   {'Total':>12}: {total_time:.3f}s per step")

    print("=" * 80)

def run_simulation(config, simulator, gene_network, population, args, custom_functions_path=None, detected_cell_size_um=None):
    """Run the main simulation loop with multi-timescale orchestration"""

    # Debug: Check cell positions at start of simulation
    print(f"[DEBUG] Starting simulation with {population.state.total_cells} cells")
    if population.state.cells:
        first_cell = next(iter(population.state.cells.values()))
        pos = first_cell.state.position
        print(f"[DEBUG] First cell position: {pos} (dimensions: {len(pos)})")
        print(f"[DEBUG] Population grid size: {population.grid_size}")
        print(f"[DEBUG] Domain dimensions: {config.domain.dimensions}")

    # Determine simulation parameters strictly from config
    dt = config.time.dt
    total_time = config.time.end_time
    num_steps = int(total_time / dt)

    # Export initial state before simulation starts (for verification)
    print(f"\n[INIT] Exporting initial cell state for verification...")
    try:
        # Import export functionality
        import sys
        sys.path.append('tools')

        # Get cell size from detected value or config
        cell_size_um = detected_cell_size_um if detected_cell_size_um else config.output.cell_size_um

        # Export based on domain dimensions
        if config.domain.dimensions == 2:
            # 2D simulations use CSV export
            from csv_export import export_microc_csv_cell_state

            csv_output_dir = config.output_dir / "csv_cells"
            initial_csv_file = export_microc_csv_cell_state(
                population=population,
                output_dir=str(csv_output_dir),
                step=-1,  # Use -1 to indicate initial state
                cell_size_um=cell_size_um
            )

            if initial_csv_file:
                print(f"[+] Initial CSV state exported: {Path(initial_csv_file).name}")
                print(f"    Use this file to verify gene network loading before simulation")
            else:
                print(f"[!] Initial CSV export failed - no cell data")
        else:
            # 3D simulations use VTK export
            from vtk_export import export_microc_simulation_state

            vtk_output_dir = config.output_dir / "vtk_cells"
            initial_vtk_file = export_microc_simulation_state(
                population=population,
                output_dir=str(vtk_output_dir),
                step=-1,  # Use -1 to indicate initial state
                cell_size_um=cell_size_um
            )

            if initial_vtk_file:
                print(f"[+] Initial VTK state exported: {Path(initial_vtk_file).name}")
                print(f"    Use this file to verify gene network loading before simulation")
            else:
                print(f"[!] Initial VTK export failed - no cell data")

    except Exception as e:
        print(f"[!] Initial state export error: {e}")
        print("   Continuing with simulation...")

    print(f"\n[RUN] Running simulation with multi-timescale orchestration...")
    print(f"   * Time step: {dt}")
    print(f"   * Total steps: {num_steps}")
    print(f"   * Total time: {total_time}")
    print(f"   * Diffusion update interval: {config.time.diffusion_step}")
    print(f"   * Intracellular update interval: {config.time.intracellular_step}")
    print(f"   * Intercellular update interval: {config.time.intercellular_step}")
    print(f"   * Data saving interval: {config.output.save_data_interval}")
    print(f"   * Plot generation interval: {config.output.save_plots_interval}")
    print(f"   * Status print interval: {config.output.status_print_interval}")
    print(f"   * Output: {config.output_dir}")

    # Create output directory
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Load custom functions for orchestrator
    custom_functions = load_custom_functions(custom_functions_path)

    # Create multi-timescale orchestrator with custom functions
    orchestrator = TimescaleOrchestrator(config.time, custom_functions)

    # Generate TRUE initial state plots (before any simulation steps)
    if config.output.save_initial_plots:
        generate_initial_plots(config, simulator, population, args)

    # Storage for results
    results = {
        'time': [],
        'substance_stats': [],
        'cell_counts': [],
        'gene_network_states': []
    }

    start_time = time.time()
    
    for step in range(num_steps):
        current_time = step * dt
        step_start_time = time.time()

        # Log step start for detailed phenotype debugging
        population.phenotype_logger.log_step_start(step)

        # Determine which processes to update this step
        updates = orchestrator.step(step)

        # Get current cell positions and states
        cell_data = population.get_cell_positions()
        cell_positions = [pos for pos, phenotype in cell_data]
        cell_states = {pos: {'phenotype': phenotype} for pos, phenotype in cell_data}

        # Update intracellular processes (fast: aging, metabolism, gene networks)
        if updates['intracellular']:
            intracellular_start = time.time()

            # Update intracellular processes
            population.update_intracellular_processes(dt)

            orchestrator.record_process_timing('intracellular',
                                             time.time() - intracellular_start, step)

        # Update diffusion (medium speed: substance transport)
        if updates['diffusion']:
            diffusion_start = time.time()

            # Get current substance concentrations for metabolism calculation
            current_concentrations = simulator.get_substance_concentrations()

            # Get reactions from population (calls custom metabolism functions with current concentrations)
            substance_reactions = population.get_substance_reactions(current_concentrations)

            # Update substance diffusion with reactions (steady state - no dt needed)
            simulator.update(substance_reactions)

            orchestrator.record_process_timing('diffusion',
                                             time.time() - diffusion_start, step)

        # Update gene networks AFTER diffusion (respond to current environment)
        # Gene networks should update whenever diffusion updates OR intracellular updates
        if updates['diffusion'] or updates['intracellular']:
            # Update gene networks (respond quickly to environment changes)
            substance_concentrations = simulator.get_substance_concentrations()
            population.update_gene_networks(substance_concentrations)

            # Update phenotypes based on gene states
            population.update_phenotypes()

            # Remove dead cells
            population.remove_dead_cells()

        # Update intercellular processes (slow: migration, division, signaling)
        if updates['intercellular']:
            intercellular_start = time.time()

            # Update intercellular processes
            intercellular_stats = population.update_intercellular_processes()

            orchestrator.record_process_timing('intercellular',
                                             time.time() - intercellular_start, step)

        # Adaptive timing adjustment
        total_step_time = time.time() - step_start_time
        orchestrator.adapt_timing(total_step_time)

        # Collect data based on saving interval from config only
        if step % config.output.save_data_interval == 0:
            results['time'].append(current_time)
            results['substance_stats'].append(simulator.get_summary_statistics())
            results['cell_counts'].append(population.get_population_statistics())

            # Sample gene network state at center
            center_pos = (config.domain.nx // 2, config.domain.ny // 2)
            gene_inputs = simulator.get_gene_network_inputs_for_position(center_pos)
            gene_network.set_input_states(gene_inputs)
            gene_outputs = gene_network.step(1)
            results['gene_network_states'].append(gene_outputs)

        # Export cell states and substance fields (VTK for 3D, CSV for 2D)
        should_save_cellstate = (config.output.save_cellstate_interval > 0 and
                                step % config.output.save_cellstate_interval == 0)
        if should_save_cellstate:
            # Get cell size from detected value or config
            cell_size_um = detected_cell_size_um if detected_cell_size_um else config.output.cell_size_um

            # Import export functionality
            import sys
            sys.path.append('tools')

            # Determine export format based on domain dimensions
            if config.domain.dimensions == 2:
                print(f"\n[CSV] Exporting 2D simulation results at step {step}...")
                try:
                    from csv_export import export_microc_csv_cell_state, export_microc_csv_substance_fields

                    # Export CSV cell state
                    csv_output_dir = config.output_dir / "csv_cells"
                    csv_file = export_microc_csv_cell_state(
                        population=population,
                        output_dir=str(csv_output_dir),
                        step=step,
                        cell_size_um=cell_size_um
                    )

                    if csv_file:
                        print(f"[+] CSV cell state exported: {Path(csv_file).name}")
                    else:
                        print(f"[!] CSV cell export failed - no cell data")

                    # Export CSV substance concentration fields
                    substance_output_dir = config.output_dir / "csv_substances"
                    substance_files = export_microc_csv_substance_fields(
                        simulator=simulator,
                        output_dir=str(substance_output_dir),
                        step=step
                    )

                    if substance_files:
                        print(f"[+] CSV substance fields exported: {len(substance_files)} files")
                    else:
                        print(f"[!] CSV substance export failed - no substance data")

                except Exception as e:
                    print(f"[!] CSV export error: {e}")
                    print("   Continuing simulation...")

            else:
                # 3D simulations use VTK export
                print(f"\n[VTK] Exporting 3D simulation results at step {step}...")
                try:
                    from vtk_export import export_microc_simulation_state, export_microc_substance_fields

                    # Export VTK file
                    vtk_output_dir = config.output_dir / "vtk_cells"
                    vtk_file = export_microc_simulation_state(
                        population=population,
                        output_dir=str(vtk_output_dir),
                        step=step,
                        cell_size_um=cell_size_um
                    )

                    if vtk_file:
                        print(f"[+] VTK cell state exported: {Path(vtk_file).name}")
                    else:
                        print(f"[!] VTK export failed - no cell data")

                    # Export VTK substance concentration fields
                    substance_output_dir = config.output_dir / "vtk_substances"
                    substance_files = export_microc_substance_fields(
                        simulator=simulator,
                        output_dir=str(substance_output_dir),
                        step=step
                    )

                    if substance_files:
                        print(f"[+] VTK substance fields exported: {len(substance_files)} files")
                    else:
                        print(f"[!] VTK substance export failed - no substance data")

                except Exception as e:
                    print(f"[!] VTK export error: {e}")
                    print("   Continuing simulation...")

        # Generate intermediate plots based on plot interval
        should_generate_plots = (not args.no_plots and
                               AUTOPLOTTER_AVAILABLE and
                               step > 0 and
                               step % config.output.save_plots_interval == 0)
        if should_generate_plots:
            print(f"\n[STATS] Generating intermediate plots at step {step + 1}...")
            plotter = AutoPlotter(config, config.plots_dir)

            # Generate substance heatmaps for current state
            plot_count = 0
            for substance_name in config.substances.keys():
                if substance_name in simulator.state.substances:
                    concentrations = simulator.state.substances[substance_name].concentrations
                    cell_data = population.get_cell_positions()
                    cell_positions = [pos for pos, phenotype in cell_data]

                    plot_path = plotter.plot_substance_heatmap(
                        substance_name=substance_name,
                        concentrations=concentrations,
                        cell_positions=cell_positions,
                        time_point=current_time,
                        config_name=Path(args.config_file).stem,
                        population=population,
                        title_suffix=f"(t={current_time:.3f})",
                        quiet=True  # Reduce verbosity for intermediate plots
                    )
                    plot_count += 1
            print(f"   [+] Generated {plot_count} plots at t={current_time:.3f}")

        # Concise status printing based on status interval
        should_print_status = (step > 0 and
                              step % config.output.status_print_interval == 0 and
                              not args.verbose)  # Don't duplicate if already verbose
        if should_print_status:
            print_concise_status(step, population)

        # Detailed status printing for verbose mode
        should_print_detailed = (step > 0 and
                                step % config.output.status_print_interval == 0 and
                                args.verbose)
        if should_print_detailed:
            print_detailed_status(step, num_steps, current_time, simulator, population, orchestrator, config, start_time, custom_functions)
            # Print ATP statistics at status intervals
            population.print_atp_statistics()

        # Progress reporting
        if args.verbose or (step + 1) % max(1, num_steps // 10) == 0:
            progress = (step + 1) / num_steps * 100
            elapsed = time.time() - start_time
            eta = elapsed / (step + 1) * (num_steps - step - 1)

            # Show which processes were updated
            update_info = []
            if updates['intracellular']:
                update_info.append("I")
            if updates['diffusion']:
                update_info.append("D")
            if updates['intercellular']:
                update_info.append("C")
            update_str = "".join(update_info) if update_info else "-"

            print(f"   Step {step + 1:4d}/{num_steps} ({progress:5.1f}%) [{update_str}] - "
                  f"Time: {current_time:.3f} - ETA: {eta:.1f}s")

            if args.verbose:
                # Show substance concentrations (from config, not hardcoded)
                stats = simulator.get_summary_statistics()
                # Use substances from configuration instead of hardcoded list
                for substance_name in config.substances.keys():
                    if substance_name in stats:
                        s = stats[substance_name]
                        print(f"      {substance_name}: {s['min']:.6f} - {s['max']:.6f}")

                # Show cell counts
                cell_stats = population.get_population_statistics()
                print(f"      Cells: {cell_stats['total_cells']}")

                # Show timing information
                if step > 0:
                    timing_info = orchestrator.get_timing_summary()
                    print(f"      Timing: I={timing_info['intracellular']['average_time']:.3f}s "
                          f"D={timing_info['diffusion']['average_time']:.3f}s "
                          f"C={timing_info['intercellular']['average_time']:.3f}s")
    
    elapsed_time = time.time() - start_time
    print(f"[+] Simulation completed in {elapsed_time:.2f} seconds")
    
    return results

def save_results(results, config, args):
    """Save simulation results"""
    if not args.save_data:
        return
    
    print(f"\n[SAVE] Saving results to {config.output_dir}...")
    
    import json
    import numpy as np
    
    # Save configuration
    config_file = config.output_dir / "simulation_config.json"
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
            'num_steps': len(results['time']),
            'dt': results['time'][1] - results['time'][0] if len(results['time']) > 1 else 0
        }, f, indent=2)
    
    # Save time series data
    np.save(config.output_dir / "time.npy", results['time'])
    
    # Save substance statistics
    substance_data = {}
    for substance in config.substances.keys():
        substance_data[substance] = {
            'min': [stats[substance]['min'] for stats in results['substance_stats'] if substance in stats],
            'max': [stats[substance]['max'] for stats in results['substance_stats'] if substance in stats],
            'mean': [stats[substance]['mean'] for stats in results['substance_stats'] if substance in stats]
        }
    
    with open(config.output_dir / "substance_data.json", 'w') as f:
        json.dump(substance_data, f, indent=2)
    
    print(f"   [+] Configuration: simulation_config.json")
    print(f"   [+] Time series: time.npy")
    print(f"   [+] Substances: substance_data.json")

def generate_initial_plots(config, simulator, population, args):
    """Generate initial state plots"""
    if args.no_plots or not AUTOPLOTTER_AVAILABLE:
        if not AUTOPLOTTER_AVAILABLE:
            print(f"\n[STATS] Initial plots skipped (AutoPlotter not available)")
        return []

    print(f"\n[STATS] Generating initial state plots...")

    # Create plotter
    plotter = AutoPlotter(config, config.plots_dir)

    # Generate initial state summary
    try:
        initial_plot = plotter.plot_initial_state_summary(population, simulator)
        print(f"   [+] Initial state summary: {initial_plot.name}")
        return [initial_plot]
    except Exception as e:
        print(f"   [!] Could not generate initial plots: {e}")
        return []

def generate_plots(config, results, simulator, population, args):
    """Generate automatic plots"""
    if args.no_plots or not AUTOPLOTTER_AVAILABLE:
        if not AUTOPLOTTER_AVAILABLE:
            print(f"\n[STATS] Final plots skipped (AutoPlotter not available)")
        else:
            print(f"\n[STATS] Plot generation disabled (--no-plots)")
        return []

    print(f"\n[STATS] Generating final state plots...")

    # Create plotter
    plotter = AutoPlotter(config, config.plots_dir)

    # Generate all plots
    generated_plots = plotter.generate_all_plots(results, simulator, population)

    return generated_plots

def main():
    """Main simulation runner (CLI + setup + persistence/plots)."""
    print("MicroC 2.0 - Generic Simulation Runner")
    print("=" * 50)

    # Parse arguments
    args = parse_arguments()

    # Load configuration (no CLI overrides)
    config, custom_functions_path = load_configuration(args.config_file)

    # Create timestamped subfolder in results directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_output_dir = config.output_dir
    original_plots_dir = config.plots_dir

    # Create timestamped subfolder
    timestamped_dir = original_output_dir / timestamp
    config.output_dir = timestamped_dir
    config.plots_dir = timestamped_dir / "plots"

    # Create the timestamped directory
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.plots_dir.mkdir(parents=True, exist_ok=True)

    # Copy YAML configuration file to the timestamped folder
    config_file_path = Path(args.config_file)
    config_copy_path = config.output_dir / config_file_path.name
    shutil.copy2(config_file_path, config_copy_path)
    print(f"[+] Configuration copied to: {config_copy_path}")

    # Copy initial state file to the timestamped folder (if it exists)
    if hasattr(config, 'initial_state') and hasattr(config.initial_state, 'file_path') and config.initial_state.file_path:
        initial_state_path = Path(config.initial_state.file_path)
        if initial_state_path.exists():
            # Check if it's a VTK checkpoint folder or a single file
            if initial_state_path.is_dir():
                # It's a VTK checkpoint folder - copy the entire folder
                initial_state_copy_path = config.output_dir / initial_state_path.name
                shutil.copytree(initial_state_path, initial_state_copy_path, dirs_exist_ok=True)
                print(f"[+] Initial state folder copied to: {initial_state_copy_path}")
            else:
                # It's a single file (CSV or VTK) - copy the file
                initial_state_copy_path = config.output_dir / initial_state_path.name
                shutil.copy2(initial_state_path, initial_state_copy_path)
                print(f"[+] Initial state file copied to: {initial_state_copy_path}")

                # If it's a VTK file, also copy the logical file if it exists
                if initial_state_path.suffix == '.vtk':
                    logical_file = initial_state_path.parent / initial_state_path.name.replace('.vtk', '_logical.vtk')
                    if logical_file.exists():
                        logical_copy_path = config.output_dir / logical_file.name
                        shutil.copy2(logical_file, logical_copy_path)
                        print(f"[+] Logical VTK file copied to: {logical_copy_path}")
        else:
            print(f"[!] Initial state file not found: {initial_state_path}")

    print(f"[+] Results will be saved to: {config.output_dir}")

    # Load workflow if specified
    workflow = None
    if args.workflow:
        try:
            from src.workflow.loader import WorkflowLoader
            workflow_path = Path(args.workflow)
            workflow = WorkflowLoader.load(workflow_path)
            print(f"[+] Loaded workflow: {workflow.name}")
            print(f"    Description: {workflow.description}")

            # Copy workflow file to timestamped folder
            workflow_copy_path = config.output_dir / workflow_path.name
            shutil.copy2(workflow_path, workflow_copy_path)
            print(f"[+] Workflow copied to: {workflow_copy_path}")
        except Exception as e:
            print(f"[!] Failed to load workflow: {e}")
            print(f"    Continuing with default hardcoded behavior")
            workflow = None

    # Setup simulation
    mesh_manager, simulator, gene_network, population, detected_cell_size_um = setup_simulation(
        config, custom_functions_path
    )

    # Prefer the new SimulationEngine if available
    try:
        from src.simulation.engine import SimulationEngine
        custom_functions = load_custom_functions(custom_functions_path)

        # Determine steps and dt strictly from config
        dt = config.time.dt
        num_steps = int(config.time.end_time / dt)

        engine = SimulationEngine(
            config=config,
            simulator=simulator,
            population=population,
            gene_network=gene_network,
            custom_functions=custom_functions,
            workflow=workflow,
        )
        # Run via engine
        engine_results = engine.run(num_steps=num_steps, dt=dt, verbose=args.verbose)

        # Convert to legacy dict expected by save_results/generate_plots
        results = {
            'time': engine_results.time,
            'substance_stats': engine_results.substance_stats,
            'cell_counts': engine_results.cell_counts,
            'gene_network_states': engine_results.gene_network_states,
        }
    except Exception as _:
        # Fallback to legacy inline loop if engine import or execution fails
        results = run_simulation(
            config, simulator, gene_network, population, args, custom_functions_path, detected_cell_size_um
        )

    # Save results
    save_results(results, config, args)

    # Generate final plots
    if config.output.save_final_plots:
        generated_plots = generate_plots(config, results, simulator, population, args)
    else:
        generated_plots = []

    # Final report (custom)
    try:
        custom_functions = load_custom_functions(custom_functions_path)
        if custom_functions and hasattr(custom_functions, 'final_report'):
            final_local_environments = {}
            for cell in population.state.cells.values():
                grid_pos = cell.state.position
                local_env = simulator.state.get_local_environment(grid_pos)
                final_local_environments[cell.state.id] = {
                    'Oxygen': local_env['oxygen_concentration'],
                    'Glucose': local_env['glucose_concentration'],
                    'Lactate': local_env['lactate_concentration'],
                    'H': local_env['h_concentration'],
                    'FGF': local_env['fgf_concentration'],
                    'EGF': local_env['egf_concentration'],
                    'TGFA': local_env['tgfa_concentration'],
                    'HGF': local_env['hgf_concentration'],
                    'EGFRD': local_env['egfrd_concentration'],
                    'FGFRD': local_env['fgfrd_concentration'],
                    'GI': local_env['gi_concentration'],
                    'cMETD': local_env['cmetd_concentration'],
                    'pH': local_env['ph_concentration'],
                    'MCT1D': local_env['mct1d_concentration'],
                    'MCT4D': local_env['mct4d_concentration'],
                    'GLUT1D': local_env['glut1d_concentration'],
                }
            custom_functions.final_report(population, final_local_environments, config)
    except Exception as e:
        print(f"[!] Could not generate final report: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n" + "=" * 50)
    print("[+] SIMULATION COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print(f"[STATS] Results summary:")
    print(f"   * Substances simulated: {len(config.substances)}")
    print(f"   * Simulation steps: {len(results['time'])}")
    print(f"   * Output directory: {config.output_dir}")
    print(f"   * Plots directory: {config.plots_dir}")

    if args.save_data:
        print(f"   * Data saved for analysis")

    if generated_plots:
        print(f"   * Plots generated: {len(generated_plots)}")

    print(f"\n[RUN] To run again:")
    print(f"   python run_sim.py {args.config_file}")

if __name__ == "__main__":
    main()
