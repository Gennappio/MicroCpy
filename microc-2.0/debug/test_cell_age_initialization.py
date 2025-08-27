#!/usr/bin/env python3
"""
Test script to verify the new cell age initialization behavior.
Tests both successful initialization and graceful failure when parameters are missing.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from config.config import MicroCConfig
from biology.population import CellPopulation
from biology.gene_network import BooleanNetwork
import importlib.util

def load_custom_functions():
    """Load the jayatilake custom functions"""
    custom_functions_path = Path(__file__).parent / "tests/jayatilake_experiment/jayatilake_experiment_custom_functions.py"
    
    spec = importlib.util.spec_from_file_location("custom_functions", custom_functions_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None

def test_successful_initialization():
    """Test cell age initialization with proper config"""
    print(" TEST 1: Successful Cell Age Initialization")
    print("=" * 50)
    
    # Load config
    config_path = Path(__file__).parent / "tests/jayatilake_experiment/jayatilake_experiment_config.yaml"
    config = MicroCConfig.load_from_yaml(config_path)
    
    # Load custom functions
    custom_functions = load_custom_functions()
    
    # Create population
    population = CellPopulation(
        grid_size=(10, 10),
        gene_network=None,
        custom_functions_module=custom_functions,
        config=config
    )
    
    # Add a few test cells
    for i in range(5):
        population.add_cell((i, 0), "Proliferation")
    
    print(f"   Created {len(population.state.cells)} cells")

    # Debug config structure
    print(f"   Config type: {type(config)}")
    print(f"   Config attributes: {[attr for attr in dir(config) if not attr.startswith('_')]}")
    if hasattr(config, 'max_cell_age'):
        print(f"   config.max_cell_age: {config.max_cell_age}")
    if hasattr(config, 'cell_cycle_time'):
        print(f"   config.cell_cycle_time: {config.cell_cycle_time}")
    if hasattr(config, 'custom_parameters'):
        print(f"   config.custom_parameters: {config.custom_parameters}")

    # Check initial ages (should all be 0)
    initial_ages = [cell.state.age for cell in population.state.cells.values()]
    print(f"   Initial ages: {initial_ages}")

    # Initialize cell ages
    custom_functions.initialize_cell_ages(population, config)
    
    # Check final ages (should be random)
    final_ages = [cell.state.age for cell in population.state.cells.values()]
    print(f"   Final ages: {[f'{age:.1f}' for age in final_ages]}")
    
    # Verify ages are different and within expected range
    assert all(age >= 0 for age in final_ages), "All ages should be >= 0"
    assert all(age <= 500.0 for age in final_ages), "All ages should be <= max_cell_age"
    assert len(set(final_ages)) > 1, "Ages should be different (random)"
    
    print("   [+] Test passed!")
    return True

def test_missing_parameters():
    """Test graceful failure when parameters are missing"""
    print("\n TEST 2: Missing Parameters (Graceful Failure)")
    print("=" * 50)
    
    # Create a minimal config without required parameters
    class MockConfig:
        def __init__(self):
            self.domain = None
            # Intentionally missing max_cell_age and cell_cycle_time
    
    mock_config = MockConfig()
    
    # Load custom functions
    custom_functions = load_custom_functions()
    
    # Create population
    population = CellPopulation(
        grid_size=(5, 5),
        gene_network=None,
        custom_functions_module=custom_functions,
        config=mock_config
    )
    
    # Add test cells
    for i in range(3):
        population.add_cell((i, 0), "Proliferation")
    
    print(f"   Created {len(population.state.cells)} cells")
    
    # Check initial ages
    initial_ages = [cell.state.age for cell in population.state.cells.values()]
    print(f"   Initial ages: {initial_ages}")
    
    # Try to initialize cell ages (should fail gracefully)
    custom_functions.initialize_cell_ages(population, mock_config)
    
    # Check that ages remain unchanged
    final_ages = [cell.state.age for cell in population.state.cells.values()]
    print(f"   Final ages: {final_ages}")
    
    # Verify ages remained at 0 (initialization was skipped)
    assert all(age == 0.0 for age in final_ages), "Ages should remain 0 when initialization fails"
    
    print("   [+] Test passed!")
    return True

def main():
    """Run all tests"""
    print(" Cell Age Initialization Tests")
    print("=" * 60)
    
    try:
        test1_passed = test_successful_initialization()
        test2_passed = test_missing_parameters()
        
        if test1_passed and test2_passed:
            print("\n[SUCCESS] ALL TESTS PASSED!")
            print("   [+] Cell age initialization works correctly")
            print("   [+] Graceful failure when parameters are missing")
        else:
            print("\n[!] SOME TESTS FAILED!")
            return 1
            
    except Exception as e:
        print(f"\n[!] TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
