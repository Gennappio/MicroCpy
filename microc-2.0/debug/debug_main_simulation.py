#!/usr/bin/env python3
"""
Debug script to test the main simulation and see if metabolism functions are working.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def debug_main_simulation():
    """Debug the main simulation to see if metabolism functions are working"""
    print("[SEARCH] Debug Main Simulation")
    print("=" * 40)
    
    # Import main simulation components
    from config.config import MicroCConfig
    from core.domain import MeshManager
    from simulation.multi_substance_simulator import MultiSubstanceSimulator
    from biology.population import CellPopulation
    from biology.gene_network import BooleanNetwork
    import importlib.util
    
    # Load Jayatilake config
    config_path = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    config = MicroCConfig.load_from_yaml(config_path)
    
    print(f"[+] Loaded config: {config_path}")
    
    # Load custom functions
    custom_functions_path = "tests/jayatilake_experiment/jayatilake_experiment_custom_functions.py"
    spec = importlib.util.spec_from_file_location("custom_functions", custom_functions_path)
    custom_functions = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(custom_functions)
    
    print(f"[+] Loaded custom functions: {custom_functions_path}")
    
    # Create components
    mesh_manager = MeshManager(config.domain)
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    gene_network = BooleanNetwork(config=config)
    population = CellPopulation(
        grid_size=(config.domain.nx, config.domain.ny),
        gene_network=gene_network,
        custom_functions_module=custom_functions_path,
        config=config
    )
    
    print(f"[+] Created simulation components")
    
    # Test metabolism function directly
    print(f"\n Testing metabolism function...")
    
    # Create test cell state
    cell_state = {
        'phenotype': 'Proliferation',
        'gene_states': {
            'glycoATP': True,
            'mitoATP': False,
            'Necrosis': False,
            'Apoptosis': False
        },
        'id': 'test_cell'
    }
    
    # Create test environment
    local_environment = {
        'oxygen': 0.07,
        'glucose': 5.0,
        'lactate': 1.0,
        'h': 4e-5,
        'tgfa': 0.0,
        'hgf': 2e-6,
        'fgf': 0.0e-6,
        'gi': 0.0,
        'egfrd': 0.0e-3,
        'fgfrd': 0.0e-3,
        'cmetd': 0.0e-3,
        'mct1d': 0.0e-6,
        'glut1d': 0.0e-6
    }
    
    # Test metabolism function
    metabolism = custom_functions.calculate_cell_metabolism(local_environment, cell_state, config)
    
    print(f"   Cell phenotype: {cell_state['phenotype']}")
    print(f"   Gene states: {cell_state['gene_states']}")
    print(f"   Lactate reaction: {metabolism.get('Lactate', 'NOT FOUND'):.2e} mol/s/cell")
    
    # Calculate expected mM/s rate
    dx = config.domain.size_x.meters / config.domain.nx
    dy = config.domain.size_y.meters / config.domain.ny
    cell_height = config.domain.cell_height.meters
    mesh_cell_volume = dx * dy * cell_height
    
    volumetric_rate = metabolism.get('Lactate', 0.0) / mesh_cell_volume
    final_rate = volumetric_rate * 1000.0
    
    print(f"   Expected mM/s rate: {final_rate:.2e} mM/s")
    print(f"   Standalone rate: -2.8e-2 mM/s")
    
    ratio = abs(final_rate / 2.8e-2) if final_rate != 0 else 0
    print(f"   Ratio: {ratio:.2f}")
    
    if 0.8 < ratio < 1.2:
        print("   [+] Rates match!")
    else:
        print("   [!] Rates don't match!")
    
    # Test population metabolism
    print(f"\n Testing population metabolism...")
    
    # Add a test cell
    center_x = config.domain.nx // 2
    center_y = config.domain.ny // 2
    success = population.add_cell((center_x, center_y), "Proliferation")
    
    if success:
        print(f"   [+] Added test cell at ({center_x}, {center_y})")
        
        # Get the cell and check its gene states
        cell = list(population.state.cells.values())[0]
        print(f"   Cell gene states: {cell.state.gene_states}")
        
        # Get current concentrations
        current_concentrations = simulator.get_substance_concentrations()
        
        # Get reactions from population
        substance_reactions = population.get_substance_reactions(current_concentrations)
        
        print(f"   Got reactions for {len(substance_reactions)} cell positions")
        
        # Check reactions
        for position, reactions in substance_reactions.items():
            print(f"   Position {position}: {reactions}")
            
            # Check if lactate is in the reactions
            if 'Lactate' in reactions:
                lactate_rate = reactions['Lactate']
                print(f"   [+] Lactate reaction found: {lactate_rate:.2e} mol/s/cell")
                
                # Calculate expected mM/s rate
                volumetric_rate = lactate_rate / mesh_cell_volume
                final_rate = volumetric_rate * 1000.0
                print(f"   Expected mM/s rate: {final_rate:.2e} mM/s")
            else:
                print(f"   [!] Lactate reaction NOT found!")
                print(f"   Available reactions: {list(reactions.keys())}")
    else:
        print(f"   [!] Failed to add test cell")

if __name__ == "__main__":
    debug_main_simulation() 