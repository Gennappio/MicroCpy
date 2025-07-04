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

# Set matplotlib backend early to avoid GUI issues in batch mode
import matplotlib
matplotlib.use('Agg')

import sys
import argparse
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "config"))
sys.path.insert(0, str(Path(__file__).parent))

from config.config import MicroCConfig
from core.domain import MeshManager
from simulation.multi_substance_simulator import MultiSubstanceSimulator
from simulation.orchestrator import TimescaleOrchestrator
from biology.population import CellPopulation
from biology.gene_network import BooleanNetwork
from interfaces.hooks import set_custom_functions_path, get_hook_manager

# Try to import AutoPlotter, but make it optional to avoid scipy hanging issues
try:
    from visualization.auto_plotter import AutoPlotter
    AUTOPLOTTER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  AutoPlotter not available (plotting disabled): {e}")
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
  python run_sim.py config/simple_oxygen_glucose.yaml --steps 100
  python run_sim.py config/drug_treatment.yaml --output results/drug_study
        """
    )
    
    parser.add_argument(
        'config_file',
        type=str,
        help='Path to YAML configuration file'
    )
    
    parser.add_argument(
        '--steps',
        type=int,
        default=None,
        help='Number of simulation steps (overrides config file)'
    )
    
    parser.add_argument(
        '--dt',
        type=float,
        default=None,
        help='Time step size (overrides config file)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory (overrides config file)'
    )
    
    parser.add_argument(
        '--custom-functions',
        type=str,
        default=None,
        help='Path to custom_functions.py file (overrides config file)'
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
    
    return parser.parse_args()

def load_configuration(config_file, args):
    """Load and validate configuration"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print(f"   Current directory: {Path.cwd()}")
        sys.exit(1)
    
    print(f"📁 Loading configuration: {config_path}")
    
    try:
        config = MicroCConfig.load_from_yaml(config_path)
        print(f"✅ Configuration loaded successfully!")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        sys.exit(1)
    
    # Apply command line overrides
    if args.output:
        config.output_dir = Path(args.output)
    
    # Load custom functions if specified
    custom_functions_path = None
    
    # Priority: command line > config file > auto-detection
    if args.custom_functions:
        custom_functions_path = Path(args.custom_functions)
    elif hasattr(config, 'custom_functions_path') and config.custom_functions_path:
        custom_functions_path = Path(config.custom_functions_path)
    
    if custom_functions_path:
        if custom_functions_path.exists():
            set_custom_functions_path(custom_functions_path)
            print(f"✅ Custom functions loaded: {custom_functions_path}")
        else:
            print(f"⚠️  Custom functions file not found: {custom_functions_path}")
    
    return config

def setup_simulation(config, args):
    """Setup all simulation components"""
    print(f"\n🔧 Setting up simulation components...")
    
    # Create mesh manager
    mesh_manager = MeshManager(config.domain)
    print(f"   ✅ Mesh: {config.domain.nx}×{config.domain.ny} cells")
    print(f"   ✅ Domain: {config.domain.size_x.value}×{config.domain.size_y.value} {config.domain.size_x.unit}")
    
    # Create multi-substance simulator
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    print(f"   ✅ Substances: {len(simulator.state.substances)}")
    print(f"   ✅ FiPy available: {simulator.fipy_mesh is not None}")
    
    # Create gene network
    gene_network = BooleanNetwork(config=config)
    print(f"   ✅ Gene network: {len(gene_network.input_nodes)} inputs, {len(gene_network.output_nodes)} outputs")
    
    # Create cell population with config for threshold-based gene inputs
    population = CellPopulation(
        grid_size=(config.domain.nx, config.domain.ny),
        gene_network=gene_network,
        config=config
    )
    
    # Initialize cells (can be customized via custom_functions.py)
    from interfaces.hooks import get_hook_manager
    hook_manager = get_hook_manager()
    
    try:
        # Try custom placement function with domain configuration
        # Get initial_cell_count from config custom_parameters if available, otherwise use default
        initial_cell_count = config.custom_parameters.get('initial_cell_count', 100)

        simulation_params = {
            'domain_size_um': config.domain.size_x.micrometers,  # Assume square domain
            'cell_height_um': config.domain.cell_height.micrometers,
            'initial_cell_count': initial_cell_count
        }

        placements = hook_manager.call_hook(
            'custom_initialize_cell_placement',
            grid_size=(config.domain.nx, config.domain.ny),
            simulation_params=simulation_params
        )
        for placement in placements:
            population.add_cell(placement['position'], phenotype=placement['phenotype'])
        print(f"   ✅ Cells: {len(placements)} (custom placement)")
    except NotImplementedError:
        # Default placement - center cluster
        center_x, center_y = config.domain.nx // 2, config.domain.ny // 2
        default_positions = [
            (center_x, center_y),
            (center_x-1, center_y), (center_x+1, center_y),
            (center_x, center_y-1), (center_x, center_y+1)
        ]
        for pos in default_positions:
            population.add_cell(pos, phenotype="Proliferation") #TODO check proliferation
        print(f"   ✅ Cells: {len(default_positions)} (default center placement)")
    
    return mesh_manager, simulator, gene_network, population

def print_detailed_status(step, num_steps, current_time, simulator, population, orchestrator, config, start_time):
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

    print(f"\n📊 STATUS UPDATE - Step {step+1}/{num_steps} ({percentage:.1f}%) - Time: {current_time:.3f} - ETA: {eta_str}")
    print("=" * 80)

    # Cell population analysis
    cell_data = population.get_cell_positions()
    total_cells = len(cell_data)

    # Count cells by phenotype/metabolic state
    phenotype_counts = {}
    metabolic_counts = {'OXPHOS': 0, 'Glycolytic': 0, 'Quiescent': 0, 'Other': 0}

    for pos, phenotype in cell_data:
        # Count by phenotype
        phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1

        # Get cell metabolic state using custom color function if available
        try:
            hook_manager = get_hook_manager()
            custom_color_func = hook_manager.loader.get_function('custom_get_cell_color')
            if custom_color_func:
                # Get the actual cell object
                cell = population.state.get_cell_at_position(pos)
                if cell:
                    color = custom_color_func(cell, cell.state.gene_states, config)
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
    divisions = pop_stats.get('divisions', 0)
    deaths = pop_stats.get('deaths', 0)

    # Count cells with proliferation gene active
    proliferation_active = 0
    for pos, phenotype in cell_data:
        try:
            cell = population.state.get_cell_at_position(pos)
            if cell and hasattr(cell.state, 'gene_states'):
                # Check if Proliferation gene is active
                if cell.state.gene_states.get('Proliferation', False):
                    proliferation_active += 1
        except:
            pass

    print(f"🧬 CELL POPULATION:")
    print(f"   Total cells: {total_cells}")
    print(f"   Divisions: {divisions}")
    print(f"   Deaths: {deaths}")
    print(f"   Proliferation active: {proliferation_active}")
    print(f"   Metabolic states:")
    for state, count in metabolic_counts.items():
        if count > 0:
            percentage_cells = (count / total_cells * 100) if total_cells > 0 else 0
            print(f"     • {state}: {count} ({percentage_cells:.1f}%)")

    # Substance concentrations
    stats = simulator.get_summary_statistics()
    print(f"\n🧪 SUBSTANCE CONCENTRATIONS:")
    for substance, substance_stats in stats.items():
        min_val = substance_stats['min']
        max_val = substance_stats['max']
        mean_val = substance_stats['mean']
        print(f"   {substance:>8}: {min_val:.6f} - {max_val:.6f} (avg: {mean_val:.6f})")

    # Performance metrics
    if timing_info:
        print(f"\n⚡ PERFORMANCE:")
        total_time = 0
        for process, process_stats in timing_info.items():
            avg_time = process_stats['average_time']
            total_time += avg_time
            print(f"   {process.capitalize():>12}: {avg_time:.3f}s")
        if total_time > 0:
            print(f"   {'Total':>12}: {total_time:.3f}s per step")

    print("=" * 80)

def run_simulation(config, simulator, gene_network, population, args):
    """Run the main simulation loop with multi-timescale orchestration"""

    # Determine simulation parameters
    dt = args.dt if args.dt else config.time.dt
    total_time = config.time.end_time

    if args.steps:
        num_steps = args.steps
        total_time = num_steps * dt
    else:
        num_steps = int(total_time / dt)

    print(f"\n🚀 Running simulation with multi-timescale orchestration...")
    print(f"   • Time step: {dt}")
    print(f"   • Total steps: {num_steps}")
    print(f"   • Total time: {total_time}")
    print(f"   • Diffusion update interval: {config.time.diffusion_step}")
    print(f"   • Intracellular update interval: {config.time.intracellular_step}")
    print(f"   • Intercellular update interval: {config.time.intercellular_step}")
    print(f"   • Data saving interval: {config.output.save_data_interval}")
    print(f"   • Plot generation interval: {config.output.save_plots_interval}")
    print(f"   • Status print interval: {config.output.status_print_interval}")
    print(f"   • Output: {config.output_dir}")

    # Create output directory
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Create multi-timescale orchestrator
    orchestrator = TimescaleOrchestrator(config.time)

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

        # Collect data based on saving interval
        should_save_data = (args.save_data and (step % config.output.save_data_interval == 0)) or args.verbose
        if should_save_data:
            results['time'].append(current_time)
            results['substance_stats'].append(simulator.get_summary_statistics())
            results['cell_counts'].append(population.get_population_statistics())

            # Sample gene network state at center
            center_pos = (config.domain.nx // 2, config.domain.ny // 2)
            gene_inputs = simulator.get_gene_network_inputs_for_position(center_pos)
            gene_network.set_input_states(gene_inputs)
            gene_outputs = gene_network.step(1)
            results['gene_network_states'].append(gene_outputs)

        # Generate intermediate plots based on plot interval
        should_generate_plots = (not args.no_plots and
                               AUTOPLOTTER_AVAILABLE and
                               step > 0 and
                               step % config.output.save_plots_interval == 0)
        if should_generate_plots:
            print(f"\n📊 Generating intermediate plots at step {step + 1}...")
            plotter = AutoPlotter(config, config.plots_dir)

            # Generate substance heatmaps for current state
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
                        title_suffix=f"(t={current_time:.3f})"
                    )
                    print(f"   ✅ {substance_name} heatmap: {plot_path.name}")

        # Detailed status printing based on status interval
        should_print_status = (step > 0 and
                              step % config.output.status_print_interval == 0 and
                              not args.verbose)  # Don't duplicate if already verbose
        if should_print_status:
            print_detailed_status(step, num_steps, current_time, simulator, population, orchestrator, config, start_time)
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
    print(f"✅ Simulation completed in {elapsed_time:.2f} seconds")
    
    return results

def save_results(results, config, args):
    """Save simulation results"""
    if not args.save_data:
        return
    
    print(f"\n💾 Saving results to {config.output_dir}...")
    
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
    
    print(f"   ✅ Configuration: simulation_config.json")
    print(f"   ✅ Time series: time.npy")
    print(f"   ✅ Substances: substance_data.json")

def generate_initial_plots(config, simulator, population, args):
    """Generate initial state plots"""
    if args.no_plots or not AUTOPLOTTER_AVAILABLE:
        if not AUTOPLOTTER_AVAILABLE:
            print(f"\n📊 Initial plots skipped (AutoPlotter not available)")
        return []

    print(f"\n📊 Generating initial state plots...")

    # Create plotter
    plotter = AutoPlotter(config, config.plots_dir)

    # Generate initial state summary
    try:
        initial_plot = plotter.plot_initial_state_summary(population, simulator)
        print(f"   ✅ Initial state summary: {initial_plot.name}")
        return [initial_plot]
    except Exception as e:
        print(f"   ⚠️  Could not generate initial plots: {e}")
        return []

def generate_plots(config, results, simulator, population, args):
    """Generate automatic plots"""
    if args.no_plots or not AUTOPLOTTER_AVAILABLE:
        if not AUTOPLOTTER_AVAILABLE:
            print(f"\n📊 Final plots skipped (AutoPlotter not available)")
        else:
            print(f"\n📊 Plot generation disabled (--no-plots)")
        return []

    print(f"\n📊 Generating final state plots...")

    # Create plotter
    plotter = AutoPlotter(config, config.plots_dir)

    # Generate all plots
    generated_plots = plotter.generate_all_plots(results, simulator, population)

    return generated_plots

def main():
    """Main simulation runner"""
    print("🧬 MicroC 2.0 - Generic Simulation Runner")
    print("=" * 50)
    
    # Parse arguments
    args = parse_arguments()
    
    # Load configuration
    config = load_configuration(args.config_file, args)
    
    # Setup simulation
    mesh_manager, simulator, gene_network, population = setup_simulation(config, args)

    # Run simulation (initial plots generated inside before first step)
    results = run_simulation(config, simulator, gene_network, population, args)
    
    # Save results
    save_results(results, config, args)

    # Generate final plots
    if config.output.save_final_plots:
        generated_plots = generate_plots(config, results, simulator, population, args)
    else:
        generated_plots = []

    # Generate final cell metabolic report if custom function is available
    try:
        hook_manager = get_hook_manager()
        custom_final_report_func = hook_manager.loader.get_function('custom_final_report')
        if custom_final_report_func:
            # Get final local environments for each cell using the state method
            final_local_environments = {}
            for cell in population.cells:
                # Convert cell position to grid coordinates
                grid_pos = (int(cell.x), int(cell.y))
                # Get local environment using the state method
                local_env = simulator.state.get_local_environment(grid_pos)
                # Convert to the format expected by the custom function
                final_local_environments[cell.cell_id] = {
                    'Oxygen': local_env.get('oxygen_concentration', 0.0),
                    'Glucose': local_env.get('glucose_concentration', 0.0),
                    'Lactate': local_env.get('lactate_concentration', 0.0),
                    'H': local_env.get('h_concentration', 0.0),
                    'FGF': local_env.get('fgf_concentration', 0.0),
                    'EGF': local_env.get('egf_concentration', 0.0),
                    'TGFA': local_env.get('tgfa_concentration', 0.0),
                    'HGF': local_env.get('hgf_concentration', 0.0),
                    'EGFRD': local_env.get('egfrd_concentration', 0.0),
                    'FGFRD': local_env.get('fgfrd_concentration', 0.0),
                    'GI': local_env.get('gi_concentration', 0.0),
                    'cMETD': local_env.get('cmetd_concentration', 0.0),
                    'pH': local_env.get('ph_concentration', 0.0),
                    'MCT1D': local_env.get('mct1d_concentration', 0.0),
                    'MCT4D': local_env.get('mct4d_concentration', 0.0),
                    'GLUT1D': local_env.get('glut1d_concentration', 0.0)
                }
            custom_final_report_func(population, final_local_environments, config)
    except Exception as e:
        print(f"⚠️  Could not generate final report: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n" + "=" * 50)
    print("✅ SIMULATION COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print(f"📊 Results summary:")
    print(f"   • Substances simulated: {len(config.substances)}")
    print(f"   • Simulation steps: {len(results['time'])}")
    print(f"   • Output directory: {config.output_dir}")
    print(f"   • Plots directory: {config.plots_dir}")

    if args.save_data:
        
        print(f"   • Data saved for analysis")

    if generated_plots:
        print(f"   • Plots generated: {len(generated_plots)}")

    print(f"\n🚀 To run again:")
    print(f"   python run_sim.py {args.config_file}")

if __name__ == "__main__":
    main()
