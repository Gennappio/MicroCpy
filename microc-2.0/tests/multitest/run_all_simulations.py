#!/usr/bin/env python3
"""
Run all 16 combination simulations sequentially.
"""

# Set matplotlib to non-interactive backend to avoid GUI issues
import matplotlib
matplotlib.use('Agg')

import subprocess
import sys
import time
import os
from pathlib import Path

def run_all_simulations():
    """Run all 16 combination simulations."""
    print("🎯 Multi-Test Runner")
    print("=" * 50)
    print("🧪 Running all 16 single-cell combination simulations")
    print("⏱️  This may take 10-30 minutes depending on your system")
    print()
    
    # Validate configs first
    print("📋 Validating all configurations...")
    try:
        result = subprocess.run([
            sys.executable, "tests/multitest/test_combination.py", "all"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print("❌ Configuration validation failed!")
            print(result.stderr)
            return False
        else:
            print("✅ All configurations validated successfully")
    except Exception as e:
        print(f"❌ Error validating configurations: {e}")
        return False
    
    print()
    print("🚀 Starting simulations...")
    print("=" * 50)
    
    results = []
    total_start_time = time.time()
    
    # Allow testing just a subset for debugging
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_range = range(3)  # Test only first 3 combinations
        print("🧪 TEST MODE: Running only first 3 combinations\n")
    else:
        test_range = range(16)  # Run all combinations

    # Run all combinations (or subset in test mode)
    for i in test_range:
        # Generate descriptive config filename
        filename_desc = get_combination_filename(i)
        config_file = f"tests/multitest/config_{filename_desc}.yaml"
        
        print(f"\n📊 Running Combination {i:02d}/15 ({i+1}/16)")
        print(f"📁 Config: {config_file}")
        
        # Show what this combination represents
        combination_desc = get_combination_description(i)
        print(f"🧬 Conditions: {combination_desc}")
        
        start_time = time.time()
        
        try:
            # Set environment to handle Unicode properly
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            # Run the simulation
            result = subprocess.run([
                sys.executable, "run_sim.py", config_file
            ], capture_output=True, text=True, timeout=300, env=env,
            encoding='utf-8', errors='replace')  # 5 minute timeout per simulation
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                print(f"✅ Completed in {duration:.1f} seconds")
                results.append({"id": i, "success": True, "duration": duration})
            else:
                print(f"❌ Failed after {duration:.1f} seconds")
                print(f"Error: {result.stderr}")  # Show full error
                if result.stdout:
                    print(f"Output: {result.stdout}")  # Show stdout too
                results.append({"id": i, "success": False, "duration": duration})
                
        except subprocess.TimeoutExpired:
            print("❌ Timed out after 5 minutes")
            results.append({"id": i, "success": False, "duration": 300})
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({"id": i, "success": False, "duration": 0})
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Print summary
    print("\n" + "=" * 50)
    print("🎉 ALL SIMULATIONS COMPLETED!")
    print("=" * 50)
    
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    
    print(f"⏱️  Total time: {total_duration/60:.1f} minutes")
    print(f"✅ Successful: {successful}/16")
    print(f"❌ Failed: {failed}/16")
    
    if successful > 0:
        avg_time = sum(r["duration"] for r in results if r["success"]) / successful
        print(f"📊 Average time per simulation: {avg_time:.1f} seconds")
    
    # Show results table
    print(f"\n📋 DETAILED RESULTS:")
    print(f"{'ID':<3} {'Status':<8} {'Time':<8} {'Description':<30}")
    print("-" * 55)
    
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        duration = f"{result['duration']:.1f}s"
        desc = get_combination_description(result["id"])
        print(f"{result['id']:02d}  {status:<8} {duration:<8} {desc:<30}")
    
    # Show where results are saved
    print(f"\n📁 Results saved in:")
    print(f"   plots/multitest/O2{{level}}_Lac{{level}}_Gluc{{level}}_TGFA{{level}}/")
    print(f"   results/multitest/O2{{level}}_Lac{{level}}_Gluc{{level}}_TGFA{{level}}/")
    print(f"   data/multitest/O2{{level}}_Lac{{level}}_Gluc{{level}}_TGFA{{level}}/")
    
    if failed > 0:
        failed_ids = [r["id"] for r in results if not r["success"]]
        print(f"\n⚠️  Failed combinations: {failed_ids}")
        print(f"   You can retry individual failures with:")
        for fid in failed_ids:
            print(f"   python run_sim.py tests/multitest/config_{fid:02d}.yaml")
    
    # Return True if all attempted simulations succeeded
    total_attempted = len(results)
    return successful == total_attempted

def get_combination_filename(combination_id):
    """Get the filename format for this combination."""
    oxygen_high = bool((combination_id >> 0) & 1)
    lactate_high = bool((combination_id >> 1) & 1)
    glucose_high = bool((combination_id >> 2) & 1)
    tgfa_high = bool((combination_id >> 3) & 1)

    oxygen_state = "high" if oxygen_high else "low"
    lactate_state = "high" if lactate_high else "low"
    glucose_state = "high" if glucose_high else "low"
    tgfa_state = "high" if tgfa_high else "low"

    return f"O2{oxygen_state}_Lac{lactate_state}_Gluc{glucose_state}_TGFA{tgfa_state}"

def get_combination_description(combination_id):
    """Get a description of what this combination represents."""
    oxygen_high = bool((combination_id >> 0) & 1)
    lactate_high = bool((combination_id >> 1) & 1)
    glucose_high = bool((combination_id >> 2) & 1)
    tgfa_high = bool((combination_id >> 3) & 1)

    oxygen_state = "HIGH" if oxygen_high else "LOW"
    lactate_state = "HIGH" if lactate_high else "LOW"
    glucose_state = "HIGH" if glucose_high else "LOW"
    tgfa_state = "HIGH" if tgfa_high else "LOW"

    return f"O2={oxygen_state}, Lac={lactate_state}, Gluc={glucose_state}, TGFA={tgfa_state}"

if __name__ == "__main__":
    # Show usage if help requested
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        print("🧬 MicroC 2.0 - Multi-Test Runner")
        print("=" * 50)
        print("Usage:")
        print("  python run_all_simulations.py        # Run all 16 combinations")
        print("  python run_all_simulations.py test   # Run only first 3 combinations (for testing)")
        print("  python run_all_simulations.py help   # Show this help message")
        print()
        print("This script runs all 16 combinations of oxygen/glucose/lactate/TGFA conditions")
        print("to test the complete parameter space of the MicroC simulation.")
        sys.exit(0)

    print("Starting multi-test simulation runner...")
    success = run_all_simulations()
    
    if success:
        print("\n🎉 All simulations completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Some simulations failed. Check the results above.")
        sys.exit(1)
