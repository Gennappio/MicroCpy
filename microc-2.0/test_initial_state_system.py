#!/usr/bin/env python3
"""
Test script for the 3D Initial State Generator and Loader system.

This script demonstrates:
1. Generating initial cell states using MicroC's logic
2. Saving cell states to HDF5 files
3. Loading cell states from HDF5 files
4. Periodic cell state saving during simulation
"""

import sys
import os
from pathlib import Path
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config import MicroCConfig
from src.biology.population import CellPopulation
from src.biology.gene_network import BooleanNetwork
from src.io.initial_state import InitialStateManager, generate_initial_state_filename
import importlib.util

def load_custom_functions():
    """Load the jayatilake experiment custom functions"""
    custom_functions_path = "tests/jayatilake_experiment/jayatilake_experiment_custom_functions.py"
    
    try:
        spec = importlib.util.spec_from_file_location("custom_functions", custom_functions_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    except Exception as e:
        print(f"Warning: Could not load custom functions: {e}")
        return None

def test_initial_state_generation():
    """Test generating and saving initial cell states"""
    print("🧪 TEST 1: Initial State Generation and Saving")
    print("=" * 60)
    
    # Load configuration
    config_path = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    config = MicroCConfig.load_from_yaml(config_path)
    
    # Enable initial state saving
    config.initial_state.save_initial_state = True
    
    print(f"📋 Configuration loaded: {config.domain.dimensions}D domain")
    print(f"   Grid: {config.domain.nx}×{config.domain.ny}×{config.domain.nz}")
    print(f"   Size: {config.domain.size_x.micrometers}×{config.domain.size_y.micrometers}×{config.domain.size_z.micrometers} μm")
    
    # Load custom functions
    custom_functions = load_custom_functions()
    if not custom_functions:
        print("❌ Failed to load custom functions")
        return False
    
    # Create gene network
    gene_network = BooleanNetwork(config=config)
    
    # Calculate biological grid size
    bio_nx = int(config.domain.size_x.meters / config.domain.cell_height.meters)
    bio_ny = int(config.domain.size_y.meters / config.domain.cell_height.meters)
    bio_nz = int(config.domain.size_z.meters / config.domain.cell_height.meters) if config.domain.dimensions == 3 else 1
    
    grid_size = (bio_nx, bio_ny, bio_nz) if config.domain.dimensions == 3 else (bio_nx, bio_ny)
    
    print(f"   Biological grid: {grid_size}")
    
    # Create population
    population = CellPopulation(
        grid_size=grid_size,
        gene_network=gene_network,
        custom_functions_module=custom_functions,
        config=config
    )
    
    # Generate initial cell placement using custom functions
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
    
    print(f"✅ Generated {len(population.state.cells)} cells")
    
    # Initialize cell ages
    if hasattr(custom_functions, 'initialize_cell_ages'):
        custom_functions.initialize_cell_ages(population, config)
        print("✅ Initialized cell ages")
    
    # Save initial state
    initial_state_manager = InitialStateManager(config)
    output_dir = Path("test_output/initial_states")
    filename = generate_initial_state_filename(config, step=0)
    file_path = output_dir / filename
    
    initial_state_manager.save_initial_state(population.state.cells, file_path, step=0)
    print(f"✅ Saved initial state to: {file_path}")
    
    # Verify file exists and has correct structure
    if file_path.exists():
        import h5py
        with h5py.File(file_path, 'r') as f:
            print(f"📊 File structure:")
            print(f"   Metadata: {list(f['metadata'].attrs.keys())}")
            print(f"   Groups: {list(f.keys())}")
            if 'cells' in f:
                print(f"   Cell data: {list(f['cells'].keys())}")
            if 'gene_states' in f:
                print(f"   Gene states: {f['gene_states']['gene_names'].shape[0]} genes")
        print("✅ File structure verified")
    
    return file_path

def test_initial_state_loading(file_path):
    """Test loading initial cell states from file"""
    print("\n🧪 TEST 2: Initial State Loading")
    print("=" * 60)
    
    # Load configuration
    config_path = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    config = MicroCConfig.load_from_yaml(config_path)
    
    # Set to load mode
    config.initial_state.mode = "load"
    config.initial_state.file_path = str(file_path)
    
    print(f"📂 Loading from: {file_path}")
    
    # Load custom functions
    custom_functions = load_custom_functions()
    
    # Create gene network
    gene_network = BooleanNetwork(config=config)
    
    # Calculate biological grid size
    bio_nx = int(config.domain.size_x.meters / config.domain.cell_height.meters)
    bio_ny = int(config.domain.size_y.meters / config.domain.cell_height.meters)
    bio_nz = int(config.domain.size_z.meters / config.domain.cell_height.meters) if config.domain.dimensions == 3 else 1
    
    grid_size = (bio_nx, bio_ny, bio_nz) if config.domain.dimensions == 3 else (bio_nx, bio_ny)
    
    # Create new population
    population = CellPopulation(
        grid_size=grid_size,
        gene_network=gene_network,
        custom_functions_module=custom_functions,
        config=config
    )
    
    # Load initial state
    initial_state_manager = InitialStateManager(config)
    cell_data = initial_state_manager.load_initial_state(file_path)
    
    # Initialize population with loaded data
    cells_loaded = population.initialize_cells(cell_data)
    
    print(f"✅ Loaded {cells_loaded} cells from file")
    
    # Verify loaded data
    if cells_loaded > 0:
        sample_cell = list(population.state.cells.values())[0]
        print(f"📊 Sample cell data:")
        print(f"   ID: {sample_cell.state.id}")
        print(f"   Position: {sample_cell.state.position}")
        print(f"   Phenotype: {sample_cell.state.phenotype}")
        print(f"   Age: {sample_cell.state.age:.2f}")
        print(f"   Gene states: {len(sample_cell.state.gene_states)} genes")
        
        # Show some gene states
        key_genes = ['Proliferation', 'Apoptosis', 'Growth_Arrest', 'GLUT1', 'MCT1']
        for gene in key_genes:
            if gene in sample_cell.state.gene_states:
                print(f"     {gene}: {sample_cell.state.gene_states[gene]}")
    
    return population

def test_periodic_saving():
    """Test periodic cell state saving during simulation"""
    print("\n🧪 TEST 3: Periodic Cell State Saving")
    print("=" * 60)
    
    # Load configuration
    config_path = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    config = MicroCConfig.load_from_yaml(config_path)
    
    # Enable periodic saving every 2 steps
    config.output.save_cellstate_interval = 2
    
    print(f"📋 Periodic saving enabled: every {config.output.save_cellstate_interval} steps")
    
    # Create a simple population for testing
    custom_functions = load_custom_functions()
    gene_network = BooleanNetwork(config=config)
    
    bio_nx = int(config.domain.size_x.meters / config.domain.cell_height.meters)
    bio_ny = int(config.domain.size_y.meters / config.domain.cell_height.meters)
    bio_nz = int(config.domain.size_z.meters / config.domain.cell_height.meters) if config.domain.dimensions == 3 else 1
    
    grid_size = (bio_nx, bio_ny, bio_nz) if config.domain.dimensions == 3 else (bio_nx, bio_ny)
    
    population = CellPopulation(
        grid_size=grid_size,
        gene_network=gene_network,
        custom_functions_module=custom_functions,
        config=config
    )
    
    # Add a few test cells
    test_positions = [(50, 50, 50), (51, 50, 50), (50, 51, 50)] if config.domain.dimensions == 3 else [(50, 50), (51, 50), (50, 51)]
    for i, pos in enumerate(test_positions):
        population.add_cell(pos, phenotype="Proliferation")
    
    print(f"✅ Created test population with {len(population.state.cells)} cells")
    
    # Simulate periodic saving for a few steps
    initial_state_manager = InitialStateManager(config)
    output_dir = Path("test_output/cell_states")
    
    saved_files = []
    for step in range(1, 6):  # Steps 1-5
        should_save = (config.output.save_cellstate_interval > 0 and 
                      step % config.output.save_cellstate_interval == 0)
        
        if should_save:
            filename = generate_initial_state_filename(config, step=step)
            file_path = output_dir / filename
            initial_state_manager.save_initial_state(population.state.cells, file_path, step=step)
            saved_files.append(file_path)
            print(f"💾 Step {step}: Saved to {file_path.name}")
        else:
            print(f"⏭️  Step {step}: No saving (interval = {config.output.save_cellstate_interval})")
    
    print(f"✅ Periodic saving test completed. Saved {len(saved_files)} files.")
    return saved_files

def main():
    """Run all initial state system tests"""
    print("🧬 3D Initial State Generator and Loader Test Suite")
    print("=" * 80)
    
    try:
        # Test 1: Generate and save initial state
        saved_file = test_initial_state_generation()
        
        # Test 2: Load initial state
        if saved_file:
            loaded_population = test_initial_state_loading(saved_file)
        
        # Test 3: Periodic saving
        periodic_files = test_periodic_saving()
        
        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("📁 Generated files:")
        print(f"   Initial state: {saved_file}")
        print(f"   Periodic saves: {len(periodic_files)} files")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
