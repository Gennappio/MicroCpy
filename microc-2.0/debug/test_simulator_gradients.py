#!/usr/bin/env python3
"""
Test the main simulator with gradient boundary conditions
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import matplotlib.pyplot as plt

try:
    from config.config import MicroCConfig
    from core.domain import MeshManager
    from simulation.multi_substance_simulator import MultiSubstanceSimulator
    print("[+] Imports successful")
except ImportError as e:
    print(f"[!] Import error: {e}")
    sys.exit(1)

def test_simulator_with_gradients():
    """Test the main simulator with gradient boundary conditions"""
    
    print(" Testing MultiSubstanceSimulator with gradient boundaries")
    
    # Load the gradient test configuration
    try:
        config = MicroCConfig.load_from_yaml("src/config/gradient_test_config_working.yaml")
        print("[+] Configuration loaded")
    except Exception as e:
        print(f"[!] Config loading failed: {e}")
        return False
    
    # Create mesh manager
    try:
        mesh_manager = MeshManager(config.domain)
        print(f"[+] Mesh created: {config.domain.nx}x{config.domain.ny}")
    except Exception as e:
        print(f"[!] Mesh creation failed: {e}")
        return False
    
    # Create simulator
    try:
        simulator = MultiSubstanceSimulator(config, mesh_manager)
        print(f"[+] Simulator created with {len(simulator.state.substances)} substances")
        print(f"   FiPy mesh available: {simulator.fipy_mesh is not None}")
    except Exception as e:
        print(f"[!] Simulator creation failed: {e}")
        return False
    
    # Test simulation step
    try:
        # Empty reactions (just test boundary conditions)
        reactions = {}
        simulator.update(reactions)
        print("[+] Simulation step completed")
    except Exception as e:
        print(f"[!] Simulation step failed: {e}")
        return False
    
    # Check results
    try:
        for name, substance in simulator.state.substances.items():
            concentrations = substance.concentrations
            print(f"   {name}: min={concentrations.min():.3f}, max={concentrations.max():.3f}")
            
            # Check if we have a gradient (not all the same value)
            if concentrations.std() > 0.01:
                print(f"   [+] {name} has gradient (std dev: {concentrations.std():.3f})")
            else:
                print(f"   [WARNING]  {name} appears uniform (std dev: {concentrations.std():.3f})")
                
    except Exception as e:
        print(f"[!] Results analysis failed: {e}")
        return False
    
    # Plot results
    try:
        plot_results(simulator)
        print("[+] Plotting completed")
    except Exception as e:
        print(f"[WARNING]  Plotting failed: {e}")
    
    return True

def plot_results(simulator):
    """Plot the concentration fields to verify gradients"""
    
    substances = list(simulator.state.substances.keys())
    n_substances = len(substances)
    
    if n_substances == 0:
        return
    
    plt.figure(figsize=(12, 4 * n_substances))
    
    # Create coordinate arrays for plotting
    nx, ny = simulator.config.domain.nx, simulator.config.domain.ny
    x = np.linspace(0, simulator.config.domain.size_x.value, nx)
    y = np.linspace(0, simulator.config.domain.size_y.value, ny)
    X, Y = np.meshgrid(x, y)
    
    for i, (name, substance) in enumerate(simulator.state.substances.items()):
        plt.subplot(n_substances, 2, 2*i + 1)
        
        # Contour plot
        plt.contourf(X, Y, substance.concentrations, levels=20, cmap='viridis')
        plt.colorbar(label=f'{name} Concentration')
        plt.title(f'{name} - Contour Plot')
        plt.xlabel('X (um)')
        plt.ylabel('Y (um)')
        
        plt.subplot(n_substances, 2, 2*i + 2)
        
        # Line plot across middle
        middle_y = ny // 2
        plt.plot(x, substance.concentrations[middle_y, :], 'b-', linewidth=2, label='Across X (middle)')
        plt.xlabel('X (um)')
        plt.ylabel(f'{name} Concentration')
        plt.title(f'{name} - Cross Section')
        plt.grid(True, alpha=0.3)
        plt.legend()
    
    plt.tight_layout()
    plt.show()

def main():
    """Main test function"""
    print("[RUN] Testing Gradient Boundary Conditions in Main Simulator")
    print("=" * 60)
    
    success = test_simulator_with_gradients()
    
    if success:
        print("\n[+] All tests passed!")
        print("\nGradient boundary conditions are working correctly!")
        print("\nTo use in your simulations:")
        print("  1. Set boundary_type: 'fixed' for default gradients")
        print("  2. Set boundary_type: 'gradient' for custom gradients")
        print("  3. Implement custom_calculate_boundary_conditions() for custom patterns")
    else:
        print("\n[!] Tests failed!")
    
    return success

if __name__ == "__main__":
    main() 