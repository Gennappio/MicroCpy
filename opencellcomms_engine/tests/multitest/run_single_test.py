#!/usr/bin/env python3
"""
Run a single combination test using the existing run_sim.py infrastructure.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_single_combination(combination_id):
    """Run a single combination test."""
    config_file = f"tests/multitest/config_{combination_id:02d}.yaml"
    
    if not Path(config_file).exists():
        print(f"[!] Config file not found: {config_file}")
        return False
    
    print(f"[TARGET] Running Combination {combination_id:02d}")
    print(f"========================================")
    print(f"[FOLDER] Config: {config_file}")
    
    # Read the config to show substance concentrations
    try:
        import yaml
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        oxygen_conc = config_data['substances']['Oxygen']['initial_value']
        lactate_conc = config_data['substances']['Lactate']['initial_value']
        glucose_conc = config_data['substances']['Glucose']['initial_value']
        tgfa_conc = config_data['substances']['TGFA']['initial_value']
        
        print(f" Substance concentrations:")
        print(f"   Oxygen: {oxygen_conc:.3f} mM ({'HIGH' if oxygen_conc > 0.03 else 'LOW'})")
        print(f"   Lactate: {lactate_conc:.1f} mM ({'HIGH' if lactate_conc > 2.0 else 'LOW'})")
        print(f"   Glucose: {glucose_conc:.1f} mM ({'HIGH' if glucose_conc > 4.0 else 'LOW'})")
        print(f"   TGFA: {tgfa_conc:.1e} mM ({'HIGH' if tgfa_conc > 1.0e-6 else 'LOW'})")
        
    except Exception as e:
        print(f"[WARNING]  Could not read config details: {e}")
    
    # Run the simulation using run_sim.py
    print("[RUN] Running simulation...")
    start_time = time.time()
    
    try:
        # Run the simulation
        result = subprocess.run([
            sys.executable, "run_sim.py", config_file
        ], capture_output=True, text=True, timeout=120)
        
        end_time = time.time()
        
        if result.returncode == 0:
            print(f"[+] Simulation completed successfully in {end_time - start_time:.1f} seconds")
            
            # Try to extract final phenotype from output
            final_phenotype = "Unknown"
            if "Final phenotype" in result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "Final phenotype" in line:
                        final_phenotype = line.split(':')[-1].strip()
                        break
            
            print(f"[CHART] Final phenotype: {final_phenotype}")
            
            # Show where plots were saved
            plots_dir = f"plots/multitest/combination_{combination_id:02d}"
            if Path(plots_dir).exists():
                print(f"[FOLDER] Plots saved to: {plots_dir}")
            
            return True
            
        else:
            print(f"[!] Simulation failed with return code {result.returncode}")
            print(f"Error output: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("[!] Simulation timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"[!] Error running simulation: {e}")
        return False

def main():
    """Main function to run a single test or all tests."""
    if len(sys.argv) != 2:
        print("Usage: python run_single_test.py <combination_id>")
        print("   combination_id: 0-15 for individual test, 'all' for all tests")
        return
    
    arg = sys.argv[1]
    
    if arg.lower() == 'all':
        # Run all 16 tests
        print("[TARGET] Multi-Test Runner")
        print("========================================")
        print(" Running all 16 single-cell combination tests")
        
        results = []
        start_time = time.time()
        
        for i in range(16):
            success = run_single_combination(i)
            results.append(success)
            print()  # Add spacing between tests
        
        end_time = time.time()
        
        # Print summary
        print(f"[SUCCESS] ALL TESTS COMPLETED!")
        print(f"========================================")
        print(f"  Total time: {end_time - start_time:.1f} seconds")
        print(f"[+] Successful tests: {sum(results)}")
        print(f"[!] Failed tests: {16 - sum(results)}")
        
        # List failed tests
        failed_tests = [i for i, success in enumerate(results) if not success]
        if failed_tests:
            print(f"[!] Failed test IDs: {failed_tests}")
        
        print(f"\n[FOLDER] Individual results saved in: plots/multitest/combination_XX/")
        
    else:
        # Run single test
        try:
            combination_id = int(arg)
            if 0 <= combination_id <= 15:
                run_single_combination(combination_id)
            else:
                print("[!] Combination ID must be between 0 and 15")
        except ValueError:
            print("[!] Invalid combination ID. Must be a number between 0-15 or 'all'")

if __name__ == "__main__":
    main()
