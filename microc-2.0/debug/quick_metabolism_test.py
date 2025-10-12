#!/usr/bin/env python3
"""
Quick test to verify the updated metabolism rates.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def quick_test():
    """Quick test of updated metabolism rates"""
    print(" Quick Metabolism Test")
    print("=" * 30)
    
    # Import the custom functions
    try:
        from config.custom_functions import calculate_cell_metabolism
        print("[+] Custom functions imported")
    except ImportError as e:
        print(f"[!] Import failed: {e}")
        return
    
    # Test parameters
    domain_size = 1500e-6
    nx, ny = 75, 75
    cell_height = 20e-6
    
    dx = domain_size / nx
    dy = domain_size / ny
    mesh_cell_volume = dx * dy * cell_height
    
    print(f" Volume: {mesh_cell_volume:.2e} m")
    
    # Test proliferation phenotype
    cell_state = {'phenotype': 'Proliferation'}
    local_environment = {}
    
    metabolism = calculate_cell_metabolism(local_environment, cell_state)
    lactate_rate = metabolism['lactate_production_rate']
    
    print(f"[SEARCH] Proliferation lactate rate: {lactate_rate:.2e} mol/s/cell")
    
    # Convert to mM/s
    volumetric_rate = lactate_rate / mesh_cell_volume
    final_rate = volumetric_rate * 1000.0
    
    print(f"[CHART] Final rate: {final_rate:.2e} mM/s")
    print(f"[CHART] Standalone rate: -2.8e-2 mM/s")
    
    ratio = abs(final_rate / 2.8e-2)
    print(f"[CHART] Ratio: {ratio:.2f}")
    
    if 0.8 < ratio < 1.2:
        print("[+] Rates match!")
    else:
        print("[!] Rates don't match!")

if __name__ == "__main__":
    quick_test() 