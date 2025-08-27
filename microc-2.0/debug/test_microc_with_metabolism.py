#!/usr/bin/env python3
"""
Test MicroC simulation with updated metabolism function.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_microc_with_metabolism():
    """Test MicroC simulation with updated metabolism"""
    print(" MicroC Test with Updated Metabolism")
    print("=" * 50)
    
    # Import MicroC components
    try:
        from config.config import MicroCConfig
        from core.domain import MeshManager
        from simulation.multi_substance_simulator import MultiSubstanceSimulator
        from biology.population import CellPopulation
        from biology.gene_network import BooleanNetwork
        print("[+] MicroC components imported")
    except ImportError as e:
        print(f"[!] Failed to import MicroC components: {e}")
        return
    
    # Create a minimal config for testing
    config_data = {
        'domain': {
            'size_x': 1500.0,
            'size_x_unit': 'um',
            'size_y': 1500.0,
            'size_y_unit': 'um',
            'nx': 75,
            'ny': 75,
            'dimensions': 2,
            'cell_height': 20.0,
            'cell_height_unit': 'um'
        },
        'time': {
            'dt': 0.1,
            'end_time': 1.0,
            'diffusion_step': 1,
            'intracellular_step': 1,
            'intercellular_step': 10
        },
        'substances': {
            'Lactate': {
                'diffusion_coeff': 6.70e-11,
                'diffusion_coeff_unit': 'm2/s',
                'initial_value': 1.0,
                'initial_value_unit': 'mM',
                'boundary_value': 1.0,
                'boundary_value_unit': 'mM',
                'boundary_type': 'fixed'
            }
        },
        'diffusion': {
            'twodimensional_adjustment_coefficient': 1.0
        },
        'associations': {},
        'thresholds': {},
        'output': {
            'save_data_interval': 1,
            'save_plots_interval': 1,
            'status_print_interval': 1,
            'save_initial_plots': True,
            'save_final_plots': True
        }
    }
    
    # Create config object
    config = MicroCConfig.from_dict(config_data)
    config.output_dir = Path("test_output")
    config.plots_dir = Path("test_output/plots")
    
    print("[+] Created test configuration")
    
    # Create mesh manager
    mesh_manager = MeshManager(config.domain)
    print(f"[+] Created mesh: {config.domain.nx}x{config.domain.ny}")
    
    # Create simulator
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    print(f"[+] Created simulator with {len(simulator.state.substances)} substances")
    
    # Create gene network (minimal)
    gene_network = BooleanNetwork(config=config)
    print(f"[+] Created gene network")
    
    # Create cell population with single proliferative cell
    population = CellPopulation(
        grid_size=(config.domain.nx, config.domain.ny),
        gene_network=gene_network,
        custom_functions_module=None,
        config=config
    )
    
    # Add a single proliferative cell at center
    center_x = config.domain.nx // 2
    center_y = config.domain.ny // 2
    
    # Create cell data
    cell_data = [{
        'position': (center_x, center_y),
        'phenotype': 'Proliferation'
    }]
    
    # Initialize population with our cell
    population.initialize_cells(cell_data)
    print(f"[+] Added {len(cell_data)} proliferative cell at center")
    
    # Test metabolism function
    print("\n Testing metabolism function...")
    cell = population.cells[0] if population.cells else None
    if cell:
        local_environment = {}
        cell_state = {'phenotype': cell.phenotype}
        
        # Import and test metabolism
        from config.custom_functions import calculate_cell_metabolism
        metabolism = calculate_cell_metabolism(local_environment, cell_state)
        
        print(f"   Cell phenotype: {cell.phenotype}")
        print(f"   Lactate production rate: {metabolism['lactate_production_rate']:.2e} mol/s/cell")
        
        # Calculate expected mM/s rate
        dx = config.domain.size_x.meters / config.domain.nx
        dy = config.domain.size_y.meters / config.domain.ny
        cell_height = config.domain.cell_height.meters
        mesh_cell_volume = dx * dy * cell_height
        
        volumetric_rate = metabolism['lactate_production_rate'] / mesh_cell_volume
        final_rate = volumetric_rate * 1000.0
        
        print(f"   Expected mM/s rate: {final_rate:.2e} mM/s")
        print(f"   Standalone rate: -2.8e-2 mM/s")
        
        ratio = abs(final_rate / 2.8e-2)
        print(f"   Ratio: {ratio:.2f}")
        
        if 0.8 < ratio < 1.2:
            print("   [+] Rates match!")
        else:
            print("   [!] Rates don't match!")
    
    # Run a single diffusion step
    print("\n[RUN] Running single diffusion step...")
    
    # Get current concentrations
    current_concentrations = simulator.get_substance_concentrations()
    
    # Get reactions from population
    substance_reactions = population.get_substance_reactions(current_concentrations)
    
    print(f"   Got reactions for {len(substance_reactions)} cell positions")
    
    # Update diffusion
    simulator.update(substance_reactions)
    
    # Get results
    lactate_state = simulator.state.substances['Lactate']
    lactate_concentrations = lactate_state.concentrations
    
    print(f"\n[CHART] Results:")
    print(f"   Lactate range: {np.min(lactate_concentrations):.6f} - {np.max(lactate_concentrations):.6f} mM")
    print(f"   Initial value: 1.0 mM")
    print(f"   Max increase: {np.max(lactate_concentrations) - 1.0:.6f} mM")
    print(f"   Max decrease: {1.0 - np.min(lactate_concentrations):.6f} mM")
    
    # Check if we have gradients
    concentration_range = np.max(lactate_concentrations) - np.min(lactate_concentrations)
    if concentration_range < 1e-6:
        print("   [!] ESSENTIALLY UNIFORM - No significant gradients!")
    else:
        print("   [+] GRADIENTS DETECTED!")
    
    # Create plot
    print("\n[CHART] Creating plot...")
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    
    # Plot lactate concentrations
    im = ax.imshow(lactate_concentrations, origin='lower', cmap='viridis',
                   extent=[0, config.domain.size_x.value, 0, config.domain.size_y.value])
    cbar = plt.colorbar(im, ax=ax, label='Lactate concentration (mM)')
    ax.set_title('MicroC Test with Updated Metabolism')
    ax.set_xlabel('X position (um)')
    ax.set_ylabel('Y position (um)')
    
    # Mark cell position
    x_pos = (center_x + 0.5) * config.domain.size_x.value / config.domain.nx
    y_pos = (center_y + 0.5) * config.domain.size_y.value / config.domain.ny
    ax.plot(x_pos, y_pos, 'r.', markersize=10, alpha=0.8)
    
    # Add text with key info
    ax.text(0.02, 0.98, f'Cell: {cell.phenotype}\nRange: {np.min(lactate_concentrations):.3f} - {np.max(lactate_concentrations):.3f} mM',
             transform=ax.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('microc_metabolism_test.png', dpi=300, bbox_inches='tight')
    print(f"[SAVE] Saved plot: microc_metabolism_test.png")
    
    # Show the plot
    plt.show()
    print("[CHART] Plot displayed")
    
    return lactate_concentrations

if __name__ == "__main__":
    print(" MicroC Metabolism Test")
    print("=" * 50)
    print("This test runs MicroC with the updated metabolism function")
    print("to see if it now produces gradients.")
    print()
    
    result = test_microc_with_metabolism()
    if result is not None:
        print("\n[+] MicroC metabolism test completed successfully!")
        
        # Compare with expectations
        print("\n[CHART] Comparison:")
        print("   If gradients are detected, the fix worked!")
        print("   If still uniform, there may be other issues.")
        
    else:
        print("\n[!] MicroC metabolism test failed!")
    
    print("\n[SUCCESS] Test completed!") 