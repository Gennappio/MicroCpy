#!/usr/bin/env python3
"""
Quick test to verify Jayatilake experiment produces lactate gradients.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_jayatilake_fix():
    """Test that Jayatilake experiment produces lactate gradients"""
    print(" Test Jayatilake Fix")
    print("=" * 30)
    
    # Import components
    from config.config import MicroCConfig
    from core.domain import MeshManager
    from simulation.multi_substance_simulator import MultiSubstanceSimulator
    from biology.population import CellPopulation
    from biology.gene_network import BooleanNetwork
    
    # Load config
    config = MicroCConfig.load_from_yaml(Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml"))
    
    # Create components
    mesh_manager = MeshManager(config.domain)
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    gene_network = BooleanNetwork(config=config)
    population = CellPopulation(
        grid_size=(config.domain.nx, config.domain.ny),
        gene_network=gene_network,
        custom_functions_module="tests/jayatilake_experiment/jayatilake_experiment_custom_functions.py",
        config=config
    )
    
    # Add a single cell
    center_x = config.domain.nx // 2
    center_y = config.domain.ny // 2
    population.add_cell((center_x, center_y), "Proliferation")
    
    print(f"[+] Added cell at ({center_x}, {center_y})")
    
    # Run a single diffusion step
    current_concentrations = simulator.get_substance_concentrations()
    substance_reactions = population.get_substance_reactions(current_concentrations)
    simulator.update(substance_reactions)
    
    # Check results
    lactate_state = simulator.state.substances['Lactate']
    lactate_concentrations = lactate_state.concentrations
    
    print(f"\n[CHART] Results:")
    print(f"   Lactate range: {np.min(lactate_concentrations):.6f} - {np.max(lactate_concentrations):.6f} mM")
    print(f"   Initial value: 1.0 mM")
    print(f"   Max increase: {np.max(lactate_concentrations) - 1.0:.6f} mM")
    
    # Check if we have gradients
    concentration_range = np.max(lactate_concentrations) - np.min(lactate_concentrations)
    if concentration_range < 1e-6:
        print("   [!] ESSENTIALLY UNIFORM - No significant gradients!")
    else:
        print("   [+] GRADIENTS DETECTED!")
        print(f"   Gradient magnitude: {concentration_range:.6f} mM")
    
    return concentration_range > 1e-6

if __name__ == "__main__":
    success = test_jayatilake_fix()
    if success:
        print("\n[SUCCESS] SUCCESS: Jayatilake experiment now produces lactate gradients!")
    else:
        print("\n[!] FAILURE: Still no gradients in Jayatilake experiment.") 