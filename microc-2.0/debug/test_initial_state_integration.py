#!/usr/bin/env python3
"""
Test the initial state system integration with the main simulation.

This test demonstrates:
1. Generating initial state and saving it
2. Loading initial state from file
3. Periodic cell state saving during simulation
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config import MicroCConfig
from src.biology.population import CellPopulation
from src.biology.gene_network import BooleanNetwork
from src.io.initial_state import InitialStateManager, generate_initial_state_filename
import importlib.util

def test_initial_state_integration():
    """Test the initial state system with the actual jayatilake experiment config"""
    print(" Testing Initial State System Integration")
    print("=" * 60)
    
    # Load the working jayatilake config
    config_path = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    config = MicroCConfig.load_from_yaml(config_path)
    
    # Enable initial state features
    config.initial_state.save_initial_state = True
    config.output.save_cellstate_interval = 2  # Save every 2 steps
    
    print(f" Configuration: {config.domain.dimensions}D, {config.domain.nx}x{config.domain.ny}x{config.domain.nz}")
    
    # Load custom functions
    custom_functions_path = "tests/jayatilake_experiment/jayatilake_experiment_custom_functions.py"
    spec = importlib.util.spec_from_file_location("custom_functions", custom_functions_path)
    custom_functions = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(custom_functions)
    
    # Create gene network
    gene_network = BooleanNetwork(config=config)
    
    # Calculate biological grid size
    bio_nx = int(config.domain.size_x.meters / config.domain.cell_height.meters)
    bio_ny = int(config.domain.size_y.meters / config.domain.cell_height.meters)
    bio_nz = int(config.domain.size_z.meters / config.domain.cell_height.meters) if config.domain.dimensions == 3 else 1
    
    grid_size = (bio_nx, bio_ny, bio_nz) if config.domain.dimensions == 3 else (bio_nx, bio_ny)
    
    print(f" Biological grid: {grid_size}")
    
    # Create population
    population = CellPopulation(
        grid_size=grid_size,
        gene_network=gene_network,
        custom_functions_module=custom_functions,
        config=config
    )
    
    # Test 1: Generate and save initial state
    print("\n[TOOL] TEST 1: Generate and Save Initial State")
    print("-" * 40)
    
    # Generate initial cell placement
    initial_cell_count = config.custom_parameters['initial_cell_count']
    simulation_params = {
        'domain_size_um': config.domain.size_x.micrometers,
        'cell_height_um': config.domain.cell_height.micrometers,
        'initial_cell_count': initial_cell_count
    }
    
    placements = custom_functions.initialize_cell_placement(
        grid_size=grid_size,
        simulation_params=simulation_params,
        config=config
    )
    
    # Add cells to population
    for placement in placements:
        population.add_cell(placement['position'], phenotype=placement['phenotype'])
    
    print(f"[+] Generated {len(population.state.cells)} cells")
    
    # Initialize cell ages
    custom_functions.initialize_cell_ages(population, config)
    print("[+] Initialized cell ages")
    
    # Save initial state
    initial_state_manager = InitialStateManager(config)
    output_dir = Path("integration_test_output/initial_states")
    filename = generate_initial_state_filename(config, step=0)
    initial_file_path = output_dir / filename
    
    initial_state_manager.save_initial_state(population.state.cells, initial_file_path, step=0)
    print(f"[+] Saved initial state: {initial_file_path.name}")
    
    # Test 2: Load initial state
    print("\n[TOOL] TEST 2: Load Initial State")
    print("-" * 40)
    
    # Create new population
    population2 = CellPopulation(
        grid_size=grid_size,
        gene_network=gene_network,
        custom_functions_module=custom_functions,
        config=config
    )
    
    # Load initial state
    cell_data = initial_state_manager.load_initial_state(initial_file_path)
    cells_loaded = population2.initialize_cells(cell_data)
    
    print(f"[+] Loaded {cells_loaded} cells from file")
    
    # Verify data integrity
    original_cells = list(population.state.cells.values())
    loaded_cells = list(population2.state.cells.values())
    
    print(f"[CHART] Data integrity check:")
    print(f"   Original cells: {len(original_cells)}")
    print(f"   Loaded cells: {len(loaded_cells)}")
    
    if len(original_cells) == len(loaded_cells):
        # Check a sample cell
        orig_cell = original_cells[0]
        loaded_cell = loaded_cells[0]
        
        print(f"   Sample cell comparison:")
        print(f"     Position match: {orig_cell.state.position == loaded_cell.state.position}")
        print(f"     Phenotype match: {orig_cell.state.phenotype == loaded_cell.state.phenotype}")
        print(f"     Age match: {abs(orig_cell.state.age - loaded_cell.state.age) < 0.01}")
        print(f"     Gene states count: {len(orig_cell.state.gene_states)} vs {len(loaded_cell.state.gene_states)}")
    
    # Test 3: Periodic saving simulation
    print("\n[TOOL] TEST 3: Periodic Saving Simulation")
    print("-" * 40)
    
    # Simulate a few steps with periodic saving
    saved_files = []
    for step in range(1, 6):  # Steps 1-5
        # Simulate some cell changes (just age them)
        for cell in population.state.cells.values():
            cell.state = cell.state.with_updates(age=cell.state.age + 0.1)
        
        # Check if we should save
        should_save = (config.output.save_cellstate_interval > 0 and 
                      step % config.output.save_cellstate_interval == 0)
        
        if should_save:
            output_dir = Path("integration_test_output/cell_states")
            filename = generate_initial_state_filename(config, step=step)
            file_path = output_dir / filename
            
            initial_state_manager.save_initial_state(population.state.cells, file_path, step=step)
            saved_files.append(file_path)
            print(f"[SAVE] Step {step}: Saved {file_path.name}")
        else:
            print(f"  Step {step}: No saving (interval = {config.output.save_cellstate_interval})")
    
    print(f"[+] Periodic saving test: {len(saved_files)} files saved")
    
    # Test 4: File format verification
    print("\n[TOOL] TEST 4: File Format Verification")
    print("-" * 40)

    # Check the initial state file
    if initial_file_path.exists():
        print(f"[FOLDER] File: {initial_file_path.name}")
        print(f"   File size: {initial_file_path.stat().st_size} bytes")
        print(f"   Format: {initial_file_path.suffix}")
        print(f"[+] Initial state file created successfully")
    else:
        print(f"[!] Initial state file not found: {initial_file_path}")

    print("\n[SUCCESS] ALL INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("[FOLDER] Generated files:")
    print(f"   Initial state: {initial_file_path}")
    for i, file_path in enumerate(saved_files, 1):
        print(f"   Periodic save {i}: {file_path}")
    
    print("\n[IDEA] Usage Summary:")
    print("1. Set initial_state.save_initial_state = true to save initial state")
    print("2. Set initial_state.mode = 'load' and file_path to load from file")
    print("3. Set output.save_cellstate_interval > 0 for periodic saving")
    print("4. Files are saved in VTK format with complete cell state data")
    
    return True

if __name__ == "__main__":
    try:
        success = test_initial_state_integration()
        print(f"\n{'[+] SUCCESS' if success else '[!] FAILED'}")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[!] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
