#!/usr/bin/env python3
"""
Simple test script for the chessboard experiment
"""

from config.config import MicroCConfig
from simulation.multi_substance_simulator import MultiSubstanceSimulator
from core.domain import MeshManager
from biology.population import CellPopulation
from biology.gene_network import BooleanNetwork
from interfaces.hooks import get_hook_manager
from visualization.auto_plotter import AutoPlotter
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

def create_combination_plot(simulator, population, config):
    """Create a comprehensive plot showing all 16 combinations."""

    # Create figure with subplots for each substance + cell phenotypes
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Systematic Combination Experiment: All 2^4 = 16 Combinations', fontsize=16, fontweight='bold')

    # Key substances for systematic combinations
    key_substances = ['Oxygen', 'Lactate', 'Glucose', 'TGFA']

    # Plot each key substance concentration
    for idx, substance_name in enumerate(key_substances):
        row = idx // 2
        col = idx % 2
        ax = axes[row, col]

        concentrations = simulator.state.substances[substance_name].concentrations

        # Create heatmap
        im = ax.imshow(concentrations, cmap='viridis', aspect='equal')
        ax.set_title(f'{substance_name} Concentrations', fontweight='bold')
        ax.set_xlabel('X Position')
        ax.set_ylabel('Y Position')

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(f'{substance_name} (mM)', rotation=270, labelpad=15)

        # Add text annotations for each cell
        for i in range(4):
            for j in range(4):
                combination_id = i * 4 + j
                value = concentrations[i, j]

                # Determine if high or low
                params = config.custom_parameters
                if substance_name == 'Oxygen':
                    is_high = value > params.get('oxygen_low', 0.01)
                elif substance_name == 'Lactate':
                    is_high = value > params.get('lactate_low', 0.5)
                elif substance_name == 'Glucose':
                    is_high = value > params.get('glucose_low', 2.0)
                elif substance_name == 'TGFA':
                    is_high = value > params.get('tgfa_low', 5.0e-7)

                state_text = "HIGH" if is_high else "LOW"
                ax.text(j, i, f'#{combination_id}\n{state_text}\n{value:.2e}',
                       ha='center', va='center', fontsize=8, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # Plot cell phenotypes
    ax_cells = axes[1, 2]

    # Create a grid to show cell phenotypes
    phenotype_grid = np.zeros((4, 4))
    phenotype_names = []

    for cell in population.state.cells.values():
        x, y = cell.state.position
        phenotype = cell.state.phenotype

        # Map phenotype to number for coloring
        if phenotype not in phenotype_names:
            phenotype_names.append(phenotype)
        phenotype_id = phenotype_names.index(phenotype)
        phenotype_grid[y, x] = phenotype_id

    # Plot phenotypes
    im_cells = ax_cells.imshow(phenotype_grid, cmap='tab10', aspect='equal')
    ax_cells.set_title('Cell Phenotypes', fontweight='bold')
    ax_cells.set_xlabel('X Position')
    ax_cells.set_ylabel('Y Position')

    # Add text annotations for phenotypes
    for i in range(4):
        for j in range(4):
            combination_id = i * 4 + j
            phenotype_id = int(phenotype_grid[i, j])
            phenotype_name = phenotype_names[phenotype_id] if phenotype_id < len(phenotype_names) else "Unknown"

            ax_cells.text(j, i, f'#{combination_id}\n{phenotype_name}',
                         ha='center', va='center', fontsize=8, fontweight='bold',
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # Add combination table as text
    ax_table = axes[0, 2]
    ax_table.axis('off')
    ax_table.set_title('Combination Table', fontweight='bold')

    # Create table text
    table_text = "ID  Oxygen  Lactate Glucose TGFA\n"
    table_text += "" * 35 + "\n"

    for i in range(4):
        for j in range(4):
            combination_id = i * 4 + j
            oxygen_state = "HIGH" if (combination_id >> 0) & 1 else "LOW "
            lactate_state = "HIGH" if (combination_id >> 1) & 1 else "LOW "
            glucose_state = "HIGH" if (combination_id >> 2) & 1 else "LOW "
            tgfa_state = "HIGH" if (combination_id >> 3) & 1 else "LOW "

            table_text += f"{combination_id:2d}  {oxygen_state}   {lactate_state}   {glucose_state}   {tgfa_state}\n"

    ax_table.text(0.05, 0.95, table_text, transform=ax_table.transAxes,
                  fontfamily='monospace', fontsize=10, verticalalignment='top')

    plt.tight_layout()

    # Save the plot
    plots_dir = Path(config.plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    filepath = plots_dir / "systematic_combinations_plot.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"   [SAVE] Saved: {filepath}")

    plt.show()

def test_chessboard():
    """Test the chessboard experiment setup."""
    
    print("[TARGET] Testing Chessboard Experiment")
    print("=" * 40)
    
    # Load configuration
    config_file = "tests/chessboard_experiment/chessboard_config.yaml"
    print(f"[FOLDER] Loading: {config_file}")
    config = MicroCConfig.load_from_yaml(Path(config_file))
    print("[+] Config loaded")
    
    # Load custom functions
    from interfaces.hooks import set_custom_functions_path
    if config.custom_functions_path:
        set_custom_functions_path(Path(config.custom_functions_path))
        print("[+] Custom functions loaded")

    hook_manager = get_hook_manager()
    
    # Create components
    mesh_manager = MeshManager(config.domain)
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    print(f"[+] Simulator created with {len(simulator.state.substances)} substances")
    
    # Create population FIRST
    gene_network = BooleanNetwork(config=config)
    population = CellPopulation(
        grid_size=(config.domain.nx, config.domain.ny),
        gene_network=gene_network,
        config=config
    )

    # Place cells
    initial_cell_count = config.custom_parameters.get('initial_cell_count', 64)
    simulation_params = {
        'domain_size_um': config.domain.size_x.micrometers,
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

    print(f"[+] Placed {len(placements)} cells")

    # Apply chessboard patterns AFTER cells are placed
    print(" Applying chessboard patterns...")
    from tests.chessboard_experiment.chessboard_custom_functions import custom_setup_chessboard_concentrations
    custom_setup_chessboard_concentrations(simulator, config)

    # Generate initial plots with chessboard patterns
    print("[CHART] Generating initial plots with chessboard patterns...")
    plotter = AutoPlotter(config, config.plots_dir)

    # Create individual heatmaps for key substances
    key_substances = ['Oxygen', 'Lactate', 'Glucose', 'TGFA']
    cell_positions = [(cell.state.position[0], cell.state.position[1]) for cell in population.state.cells.values()]

    for substance_name in key_substances:
        if substance_name in simulator.state.substances:
            concentrations = simulator.state.substances[substance_name].concentrations
            plotter.plot_substance_heatmap(
                substance_name, concentrations, cell_positions, 0.0, "chessboard_initial", population
            )
            print(f"   [+] {substance_name} heatmap with chessboard pattern")

    print("[+] Initial plots with chessboard patterns generated")
    
    # Run a few steps
    print("[RUN] Running 3 simulation steps...")
    for step in range(3):
        # Extract substance concentrations for gene network update
        substance_concentrations = {}
        for substance_name, substance in simulator.state.substances.items():
            substance_concentrations[substance_name] = {}
            for i in range(4):
                for j in range(4):
                    substance_concentrations[substance_name][(j, i)] = substance.concentrations[i, j]

        population.update_gene_networks(substance_concentrations)
        population.update_phenotypes()
        print(f"   Step {step+1}/3 completed")

    # Create final heatmaps showing cell responses
    print("[CHART] Creating final plots showing cell responses...")

    # Generate heatmaps for key substances with final cell states
    cell_positions = [(cell.state.position[0], cell.state.position[1]) for cell in population.state.cells.values()]

    for substance_name in key_substances:
        if substance_name in simulator.state.substances:
            concentrations = simulator.state.substances[substance_name].concentrations
            plotter.plot_substance_heatmap(
                substance_name, concentrations, cell_positions, 3.0, "chessboard_final", population
            )
            print(f"   [+] {substance_name} final heatmap with cell responses")

    # Create a comprehensive combination plot
    print("[CHART] Creating systematic combination plot...")
    create_combination_plot(simulator, population, config)
    print("[+] Combination plot generated")

    # Print final cell states for easy analysis
    print("\n FINAL CELL STATES:")
    print(f"   {'ID':<3} {'Pos':<7} {'Phenotype':<15} {'O2':<8} {'Lac':<8} {'Gluc':<8} {'TGFA':<8}")
    print(f"   {'-'*3} {'-'*7} {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

    for i in range(4):
        for j in range(4):
            combination_id = i * 4 + j

            # Find cell at this position
            cell_phenotype = "No Cell"
            for cell in population.state.cells.values():
                if cell.state.position == (j, i):
                    cell_phenotype = cell.state.phenotype
                    break

            # Get concentrations at this position
            oxygen_conc = simulator.state.substances['Oxygen'].concentrations[i, j]
            lactate_conc = simulator.state.substances['Lactate'].concentrations[i, j]
            glucose_conc = simulator.state.substances['Glucose'].concentrations[i, j]
            tgfa_conc = simulator.state.substances['TGFA'].concentrations[i, j]

            # Determine high/low states
            oxygen_state = "HIGH" if oxygen_conc > 0.03 else "LOW"
            lactate_state = "HIGH" if lactate_conc > 2.0 else "LOW"
            glucose_state = "HIGH" if glucose_conc > 4.0 else "LOW"
            tgfa_state = "HIGH" if tgfa_conc > 1.0e-6 else "LOW"

            print(f"   {combination_id:<3} ({j},{i})<3 {cell_phenotype:<15} {oxygen_state:<8} {lactate_state:<8} {glucose_state:<8} {tgfa_state:<8}")

    print("[+] Final analysis complete")
    
    print(f"\n[SUCCESS] Test completed successfully!")
    print(f"   Grid: {config.domain.nx}x{config.domain.ny}")
    print(f"   Cells: {len(population.state.cells)}")
    print(f"   Plots: {config.plots_dir}")

if __name__ == "__main__":
    test_chessboard()
