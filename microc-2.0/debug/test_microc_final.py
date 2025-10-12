#!/usr/bin/env python3
"""
Final test of MicroC simulation with fixed metabolism rates.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_microc_final():
    """Final test of MicroC with fixed metabolism"""
    print(" Final MicroC Test with Fixed Metabolism")
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
    
    # Create minimal config manually
    print("\n[TOOL] Creating minimal config...")
    
    # Import required classes
    from core.units import Length, Concentration
    from config.config import DomainConfig, TimeConfig, SubstanceConfig, DiffusionConfig
    
    domain_config = DomainConfig(
        size_x=Length(1500.0, "um"),
        size_y=Length(1500.0, "um"),
        nx=75,
        ny=75,
        dimensions=2,
        cell_height=Length(20.0, "um")
    )
    
    # Time config
    time_config = TimeConfig(
        dt=0.1,
        end_time=1.0,
        diffusion_step=1,
        intracellular_step=1,
        intercellular_step=10
    )
    
    # Substance config
    lactate_config = SubstanceConfig(
        name="Lactate",
        diffusion_coeff=6.70e-11,  # m/s
        production_rate=0.0,  # Will be set by metabolism function
        uptake_rate=0.0,
        initial_value=Concentration(1.0, "mM"),
        boundary_value=Concentration(1.0, "mM"),
        boundary_type="fixed"
    )
    
    # Diffusion config
    diffusion_config = DiffusionConfig(
        max_iterations=1000,
        tolerance=1e-6,
        solver_type="steady_state",
        twodimensional_adjustment_coefficient=1.0
    )
    
    # Create main config
    config = MicroCConfig(
        domain=domain_config,
        time=time_config,
        substances={"Lactate": lactate_config},
        diffusion=diffusion_config,
        associations={},
        thresholds={},
        output_dir=Path("test_output"),
        plots_dir=Path("test_output/plots")
    )
    
    print("[+] Created minimal config")
    
    # Create mesh manager
    mesh_manager = MeshManager(config.domain)
    print(f"[+] Created mesh: {config.domain.nx}x{config.domain.ny}")
    
    # Create simulator
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    print(f"[+] Created simulator with {len(simulator.state.substances)} substances")
    
    # Create gene network (minimal)
    gene_network = BooleanNetwork(config=config)
    print(f"[+] Created gene network")
    
    # Create cell population
    population = CellPopulation(
        grid_size=(config.domain.nx, config.domain.ny),
        gene_network=gene_network,
        custom_functions_module="src/config/custom_functions.py",  # Load custom functions
        config=config
    )
    
    # Add a single proliferative cell at center
    center_x = config.domain.nx // 2
    center_y = config.domain.ny // 2
    
    # Add cell using the correct method
    success = population.add_cell((center_x, center_y), "Proliferation")
    if success:
        print(f"[+] Added proliferative cell at center ({center_x}, {center_y})")
    else:
        print(f"[!] Failed to add cell at center ({center_x}, {center_y})")
        return None
    
    # Test metabolism function
    print("\n Testing metabolism function...")
    
    from config.custom_functions import calculate_cell_metabolism
    
    # Get the first cell from the population state
    cell = list(population.state.cells.values())[0] if population.state.cells else None
    if cell:
        local_environment = {}
        cell_state = {'phenotype': cell.state.phenotype}
        
        metabolism = calculate_cell_metabolism(local_environment, cell_state)
        lactate_rate = metabolism['lactate_production_rate']
        
        print(f"   Cell phenotype: {cell.state.phenotype}")
        print(f"   Lactate production rate: {lactate_rate:.2e} mol/s/cell")
        
        # Calculate expected mM/s rate
        dx = config.domain.size_x.meters / config.domain.nx
        dy = config.domain.size_y.meters / config.domain.ny
        cell_height = config.domain.cell_height.meters
        mesh_cell_volume = dx * dy * cell_height
        
        volumetric_rate = lactate_rate / mesh_cell_volume
        final_rate = volumetric_rate * 1000.0
        
        print(f"   Expected mM/s rate: {final_rate:.2e} mM/s")
        print(f"   Standalone rate: -2.8e-2 mM/s")
        
        ratio = abs(final_rate / 2.8e-2)
        print(f"   Ratio: {ratio:.2f}")
        
        if 0.8 < ratio < 1.2:
            print("   [+] Rates match!")
        else:
            print("   [!] Rates don't match!")
    else:
        print("   [!] No cells found in population")
        return None
    
    # Run a single diffusion step
    print("\n[RUN] Running single diffusion step...")
    
    # Get current concentrations
    current_concentrations = simulator.get_substance_concentrations()
    
    # Get reactions from population
    substance_reactions = population.get_substance_reactions(current_concentrations)
    
    print(f"   Got reactions for {len(substance_reactions)} cell positions")
    
    # Debug: Check what reactions were calculated
    for position, reactions in substance_reactions.items():
        print(f"   Position {position}: {reactions}")
    
    # FIX: Convert reactions to the format the simulator expects
    # The simulator expects: {position: {substance_name: rate}}
    # But we have: {position: {reaction_type: rate}}
    fixed_reactions = {}
    for position, reactions in substance_reactions.items():
        fixed_reactions[position] = {
            'Lactate': reactions.get('lactate_production_rate', 0.0)
        }
    
    print(f"   Fixed reactions: {fixed_reactions}")
    
    # Update diffusion with fixed reactions
    simulator.update(fixed_reactions)
    
    # Debug: Check what source terms were actually calculated
    print(f"\n[SEARCH] Debugging source terms...")
    
    # Check what substance names are available
    print(f"   Available substances: {list(simulator.state.substances.keys())}")
    print(f"   Looking for substance: 'Lactate'")
    
    # Check what's in the reactions
    for position, reactions in fixed_reactions.items():
        print(f"   Reactions at {position}: {list(reactions.keys())}")
    
    # Get the source field directly from the simulator
    source_field = simulator._create_source_field_from_reactions('Lactate', fixed_reactions)
    non_zero_indices = np.where(source_field != 0)[0]
    
    print(f"   Source field: {len(non_zero_indices)} non-zero terms")
    if len(non_zero_indices) > 0:
        print(f"   Range: {np.min(source_field):.2e} to {np.max(source_field):.2e} mM/s")
        for i, idx in enumerate(non_zero_indices[:3]):
            print(f"     idx {idx}: {source_field[idx]:.2e} mM/s")
    
    # Check after negation
    negated_source = -source_field
    print(f"   After negation: {np.min(negated_source):.2e} to {np.max(negated_source):.2e} mM/s")
    
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
    ax.set_title('MicroC Final Test - Single Cell')
    ax.set_xlabel('X position (um)')
    ax.set_ylabel('Y position (um)')
    
    # Mark cell position
    x_pos = (center_x + 0.5) * config.domain.size_x.value / config.domain.nx
    y_pos = (center_y + 0.5) * config.domain.size_y.value / config.domain.ny
    ax.plot(x_pos, y_pos, 'r.', markersize=10, alpha=0.8)
    
    # Add text with key info
    ax.text(0.02, 0.98, f'Cell: {cell.state.phenotype}\nRange: {np.min(lactate_concentrations):.3f} - {np.max(lactate_concentrations):.3f} mM',
             transform=ax.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('microc_final_single_cell.png', dpi=300, bbox_inches='tight')
    print(f"[SAVE] Saved plot: microc_final_single_cell.png")
    
    # Show the plot
    plt.show()
    print("[CHART] Plot displayed")
    
    return lactate_concentrations

def test_microc_200_cells():
    """Test MicroC with 200 cells"""
    print("\n" + "=" * 60)
    print(" MicroC Test with 200 Cells")
    print("=" * 60)
    
    # TODO: Implement 200 cells test
    print("[TOOL] TODO: Implement 200 cells test")
    return None

def test_microc_1000_cells():
    """Test MicroC with 1000 cells"""
    print("\n" + "=" * 60)
    print(" MicroC Test with 1000 Cells")
    print("=" * 60)
    
    # TODO: Implement 1000 cells test
    print("[TOOL] TODO: Implement 1000 cells test")
    return None

if __name__ == "__main__":
    print(" MicroC Final Test Suite")
    print("=" * 60)
    print("This test suite verifies that MicroC now produces gradients")
    print("with the fixed metabolism rates.")
    print()
    
    # Test 1: Single cell
    print(" TEST 1: Single Cell")
    result1 = test_microc_final()
    if result1 is not None:
        print("\n[+] Single cell test completed successfully!")
        
        # Check if gradients were detected
        concentration_range = np.max(result1) - np.min(result1)
        if concentration_range > 1e-6:
            print("[SUCCESS] SUCCESS: Gradients detected! The fix worked!")
        else:
            print("[!] FAILURE: Still no gradients detected.")
        
    else:
        print("\n[!] Single cell test failed!")
    
    # TODO: Uncomment when ready to test more cells
    # test_microc_200_cells()
    # test_microc_1000_cells()
    
    print("\n[SUCCESS] Final test suite completed!") 