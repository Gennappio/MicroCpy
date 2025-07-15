#!/usr/bin/env python3
"""
Improved multi-test runner with better resource management.
"""

# Set matplotlib to non-interactive backend to avoid GUI issues
import matplotlib
matplotlib.use('Agg')

import subprocess
import sys
import time
import os
import gc
from pathlib import Path

def run_all_simulations_improved():
    """Run all 16 combination simulations with better resource management."""
    print("🎯 Improved Multi-Test Runner")
    print("=" * 50)
    print("🧪 Running all 16 single-cell combination simulations")
    print("⚡ With improved resource management")
    print()
    
    results = []
    total_start_time = time.time()
    
    # Run all combinations
    for i in range(16):
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
            
            # Run with consistent short duration for comparison
            result = subprocess.run([
                sys.executable, "run_sim.py", config_file,
                "--steps", "5"  # Short duration for consistent comparison
            ], capture_output=True, text=True, timeout=300, env=env,
            encoding='utf-8', errors='replace')
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                print(f"✅ Completed in {duration:.1f} seconds")
                results.append({"id": i, "success": True, "duration": duration})
            else:
                print(f"❌ Failed after {duration:.1f} seconds")
                print(f"Error: {result.stderr}")
                results.append({"id": i, "success": False, "duration": duration})
                
        except subprocess.TimeoutExpired:
            print("❌ Timed out after 5 minutes")
            results.append({"id": i, "success": False, "duration": 300})
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({"id": i, "success": False, "duration": 0})
        
        # Force garbage collection after each simulation
        gc.collect()
        
        # Add a small delay to let system recover
        time.sleep(1)
        
        # Print memory status every 5 simulations
        if (i + 1) % 5 == 0:
            print(f"🔄 Completed {i+1}/16 simulations, continuing...")
    
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
    
    if failed > 0:
        failed_ids = [r["id"] for r in results if not r["success"]]
        print(f"\n⚠️  Failed combinations: {failed_ids}")
        print(f"   You can retry individual failures with:")
        for fid in failed_ids:
            filename_desc = get_combination_filename(fid)
            print(f"   python run_sim.py tests/multitest/config_{filename_desc}.yaml")
    
    # Return True if all attempted simulations succeeded
    return successful == 16

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
    print("Starting improved multi-test simulation runner...")
    success = run_all_simulations_improved()
    
    if success:
        print("\n🎉 All simulations completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Some simulations failed. Check the results above.")
        sys.exit(1)
