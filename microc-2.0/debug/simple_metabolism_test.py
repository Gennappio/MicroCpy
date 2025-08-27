#!/usr/bin/env python3
"""
Simple test using existing config to verify metabolism fix.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def simple_metabolism_test():
    """Simple test using existing config"""
    print(" Simple Metabolism Test")
    print("=" * 40)
    
    # Import MicroC components
    try:
        from config.config import MicroCConfig
        from core.domain import MeshManager
        from simulation.multi_substance_simulator import MultiSubstanceSimulator
        print("[+] MicroC components imported")
    except ImportError as e:
        print(f"[!] Failed to import MicroC components: {e}")
        return
    
    # Use existing config file
    config_path = Path("src/config/default_config.yaml")
    if not config_path.exists():
        print(f"[!] Config file not found: {config_path}")
        return
    
    try:
        config = MicroCConfig.load_from_yaml(config_path)
        print("[+] Loaded existing config")
    except Exception as e:
        print(f"[!] Failed to load config: {e}")
        return
    
    # Create mesh manager
    mesh_manager = MeshManager(config.domain)
    print(f"[+] Created mesh: {config.domain.nx}x{config.domain.ny}")
    
    # Create simulator
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    print(f"[+] Created simulator with {len(simulator.state.substances)} substances")
    
    # Test metabolism function directly
    print("\n Testing metabolism function...")
    
    from config.custom_functions import calculate_cell_metabolism
    
    # Test proliferation phenotype
    cell_state = {'phenotype': 'Proliferation'}
    local_environment = {}
    
    metabolism = calculate_cell_metabolism(local_environment, cell_state)
    lactate_rate = metabolism['lactate_production_rate']
    
    print(f"   Cell phenotype: Proliferation")
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
    
    # Test with a simple source field
    print("\n[RUN] Testing with simple source field...")
    
    # Create a simple source field with one cell at center
    nx, ny = config.domain.nx, config.domain.ny
    source_field = np.zeros(nx * ny)
    
    center_x = nx // 2
    center_y = ny // 2
    
    # Place the calculated rate at center
    fipy_idx = center_x * ny + center_y
    source_field[fipy_idx] = final_rate
    
    print(f"   Placed rate {final_rate:.2e} mM/s at center ({center_x}, {center_y})")
    
    # Apply negation (like MicroC does)
    source_field = -source_field
    
    print(f"   After negation: {source_field[fipy_idx]:.2e} mM/s")
    
    # Get current lactate state
    if 'lactate' in simulator.state.substances:
        lactate_state = simulator.state.substances['lactate']
        print(f"   Current lactate range: {np.min(lactate_state.concentrations):.6f} - {np.max(lactate_state.concentrations):.6f} mM")
        
        # Create a simple reaction dict for testing
        reactions = {(center_x, center_y): {'lactate': lactate_rate}}
        
        # Update simulator
        simulator.update(reactions)
        
        # Check results
        new_concentrations = lactate_state.concentrations
        print(f"   New lactate range: {np.min(new_concentrations):.6f} - {np.max(new_concentrations):.6f} mM")
        
        # Check if we have gradients
        concentration_range = np.max(new_concentrations) - np.min(new_concentrations)
        if concentration_range < 1e-6:
            print("   [!] ESSENTIALLY UNIFORM - No significant gradients!")
        else:
            print("   [+] GRADIENTS DETECTED!")
        
        # Create plot
        print("\n[CHART] Creating plot...")
        
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        
        # Plot lactate concentrations
        im = ax.imshow(new_concentrations, origin='lower', cmap='viridis',
                       extent=[0, config.domain.size_x.value, 0, config.domain.size_y.value])
        cbar = plt.colorbar(im, ax=ax, label='Lactate concentration (mM)')
        ax.set_title('Simple Metabolism Test')
        ax.set_xlabel('X position (um)')
        ax.set_ylabel('Y position (um)')
        
        # Mark cell position
        x_pos = (center_x + 0.5) * config.domain.size_x.value / config.domain.nx
        y_pos = (center_y + 0.5) * config.domain.size_y.value / config.domain.ny
        ax.plot(x_pos, y_pos, 'r.', markersize=10, alpha=0.8)
        
        # Add text with key info
        ax.text(0.02, 0.98, f'Rate: {final_rate:.2e} mM/s\nRange: {np.min(new_concentrations):.3f} - {np.max(new_concentrations):.3f} mM',
                 transform=ax.transAxes, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig('simple_metabolism_test.png', dpi=300, bbox_inches='tight')
        print(f"[SAVE] Saved plot: simple_metabolism_test.png")
        
        # Show the plot
        plt.show()
        print("[CHART] Plot displayed")
        
        return new_concentrations
    else:
        print("   [!] Lactate substance not found in simulator")
        return None

if __name__ == "__main__":
    print(" Simple Metabolism Test")
    print("=" * 40)
    print("This test uses existing config to verify the metabolism fix.")
    print()
    
    result = simple_metabolism_test()
    if result is not None:
        print("\n[+] Simple metabolism test completed successfully!")
        
        # Compare with expectations
        print("\n[CHART] Comparison:")
        print("   If gradients are detected, the fix worked!")
        print("   If still uniform, there may be other issues.")
        
    else:
        print("\n[!] Simple metabolism test failed!")
    
    print("\n[SUCCESS] Test completed!") 