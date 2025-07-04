#!/usr/bin/env python3
"""
Run all 16 single-cell combination tests.
Each test runs a separate simulation with different substance concentrations.
"""

import os
import sys
import time
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent.parent.parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from config.config import MicroCConfig
from simulation.simulator import MicroCSimulator
from biology.population import CellPopulation
from biology.gene_network import BooleanNetwork
from visualization.auto_plotter import AutoPlotter
from utils.hook_manager import HookManager

def run_single_test(config_file, combination_id):
    """Run a single test with the given config file."""
    print(f"\n🎯 Running Test {combination_id:02d}")
    print(f"========================================")
    print(f"📁 Config: {config_file}")
    
    try:
        # Load configuration
        config = MicroCConfig.load_from_yaml(Path(config_file))
        print("✅ Config loaded")
        
        # Create hook manager and load custom functions
        hook_manager = HookManager()
        if hasattr(config, 'custom_functions_path') and config.custom_functions_path:
            hook_manager.load_custom_functions(config.custom_functions_path)
            print("✅ Custom functions loaded")
        
        # Create simulator
        simulator = MicroCSimulator(config)
        print(f"✅ Simulator created with {len(simulator.state.substances)} substances")
        
        # Create gene network and population
        gene_network = BooleanNetwork(config=config)
        population = CellPopulation(
            grid_size=(config.domain.nx, config.domain.ny),
            gene_network=gene_network,
            config=config
        )
        print("✅ Gene network and population created")
        
        # Place single cell at center
        center_pos = (0, 0)  # 1x1 grid, so center is (0,0)
        population.add_cell(center_pos, phenotype="Proliferation")
        print(f"✅ Placed 1 cell at {center_pos}")
        
        # Get substance concentrations for this combination
        oxygen_conc = config.substances.Oxygen.initial_value.value if hasattr(config.substances.Oxygen.initial_value, 'value') else config.substances.Oxygen.initial_value
        lactate_conc = config.substances.Lactate.initial_value.value if hasattr(config.substances.Lactate.initial_value, 'value') else config.substances.Lactate.initial_value
        glucose_conc = config.substances.Glucose.initial_value.value if hasattr(config.substances.Glucose.initial_value, 'value') else config.substances.Glucose.initial_value
        tgfa_conc = config.substances.TGFA.initial_value.value if hasattr(config.substances.TGFA.initial_value, 'value') else config.substances.TGFA.initial_value
        
        print(f"🧬 Substance concentrations:")
        print(f"   Oxygen: {oxygen_conc:.3f} mM ({'HIGH' if oxygen_conc > 0.03 else 'LOW'})")
        print(f"   Lactate: {lactate_conc:.1f} mM ({'HIGH' if lactate_conc > 2.0 else 'LOW'})")
        print(f"   Glucose: {glucose_conc:.1f} mM ({'HIGH' if glucose_conc > 4.0 else 'LOW'})")
        print(f"   TGFA: {tgfa_conc:.1e} mM ({'HIGH' if tgfa_conc > 1.0e-6 else 'LOW'})")
        
        # Generate initial plots
        plotter = AutoPlotter(config, config.plots_dir)
        plotter.plot_initial_state_summary(population, simulator)
        print("✅ Initial plots generated")
        
        # Run simulation for a few steps
        print("🚀 Running simulation...")
        initial_phenotype = None
        final_phenotype = None
        
        # Get initial phenotype
        if population.state.cells:
            cell = list(population.state.cells.values())[0]
            initial_phenotype = cell.state.phenotype
            print(f"   Initial phenotype: {initial_phenotype}")
        
        # Run simulation steps
        num_steps = 10
        for step in range(num_steps):
            # Get substance concentrations at cell position
            substance_concentrations = {}
            for substance_name, substance in simulator.state.substances.items():
                substance_concentrations[substance_name] = substance.concentrations[0, 0]  # Single cell at (0,0)
            
            # Update gene networks
            population.update_gene_networks(substance_concentrations)
            
            # Update cell behaviors
            population.update_cell_behaviors(simulator.state.current_time)
            
            # Advance time
            simulator.state.current_time += config.time.dt.value if hasattr(config.time.dt, 'value') else config.time.dt
            
            # Check for phenotype changes
            if population.state.cells:
                cell = list(population.state.cells.values())[0]
                current_phenotype = cell.state.phenotype
                if current_phenotype != initial_phenotype:
                    print(f"   Step {step+1}: Phenotype changed from {initial_phenotype} to {current_phenotype}")
                    initial_phenotype = current_phenotype
        
        # Get final phenotype
        if population.state.cells:
            cell = list(population.state.cells.values())[0]
            final_phenotype = cell.state.phenotype
        
        # Generate final plots
        plotter.plot_final_state_summary(population, simulator)
        print("✅ Final plots generated")
        
        # Print results
        print(f"📊 RESULTS:")
        print(f"   Final phenotype: {final_phenotype}")
        print(f"   Plots saved to: {config.plots_dir}")
        
        return {
            'combination_id': combination_id,
            'oxygen': oxygen_conc,
            'lactate': lactate_conc,
            'glucose': glucose_conc,
            'tgfa': tgfa_conc,
            'final_phenotype': final_phenotype,
            'success': True
        }
        
    except Exception as e:
        print(f"❌ Error in test {combination_id:02d}: {str(e)}")
        return {
            'combination_id': combination_id,
            'final_phenotype': 'ERROR',
            'success': False,
            'error': str(e)
        }

def main():
    """Run all 16 combination tests."""
    print("🎯 Multi-Test Runner")
    print("========================================")
    print("🧪 Running 16 single-cell combination tests")
    print("📁 Each test has different substance concentrations")
    
    # Find all config files
    config_dir = Path("tests/multitest")
    config_files = sorted(config_dir.glob("config_*.yaml"))
    
    if len(config_files) != 16:
        print(f"❌ Expected 16 config files, found {len(config_files)}")
        print("   Run generate_configs.py first!")
        return
    
    print(f"✅ Found {len(config_files)} config files")
    
    # Run all tests
    results = []
    start_time = time.time()
    
    for i, config_file in enumerate(config_files):
        combination_id = int(config_file.stem.split('_')[1])
        result = run_single_test(config_file, combination_id)
        results.append(result)
    
    end_time = time.time()
    
    # Print summary
    print(f"\n🎉 ALL TESTS COMPLETED!")
    print(f"========================================")
    print(f"⏱️  Total time: {end_time - start_time:.1f} seconds")
    print(f"✅ Successful tests: {sum(1 for r in results if r['success'])}")
    print(f"❌ Failed tests: {sum(1 for r in results if not r['success'])}")
    
    # Print results table
    print(f"\n📋 RESULTS SUMMARY:")
    print(f"{'ID':<3} {'O2':<8} {'Lac':<8} {'Gluc':<8} {'TGFA':<10} {'Final Phenotype':<15}")
    print(f"{'-'*3} {'-'*8} {'-'*8} {'-'*8} {'-'*10} {'-'*15}")
    
    for result in sorted(results, key=lambda x: x['combination_id']):
        if result['success']:
            oxygen_state = "HIGH" if result['oxygen'] > 0.03 else "LOW"
            lactate_state = "HIGH" if result['lactate'] > 2.0 else "LOW"
            glucose_state = "HIGH" if result['glucose'] > 4.0 else "LOW"
            tgfa_state = "HIGH" if result['tgfa'] > 1.0e-6 else "LOW"
            
            print(f"{result['combination_id']:<3} {oxygen_state:<8} {lactate_state:<8} {glucose_state:<8} {tgfa_state:<10} {result['final_phenotype']:<15}")
        else:
            print(f"{result['combination_id']:<3} {'ERROR':<8} {'ERROR':<8} {'ERROR':<8} {'ERROR':<10} {'ERROR':<15}")
    
    print(f"\n📁 Individual results saved in: plots/multitest/combination_XX/")

if __name__ == "__main__":
    main()
