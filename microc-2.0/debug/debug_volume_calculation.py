#!/usr/bin/env python3
"""
Debug script to check volume calculation.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def debug_volume_calculation():
    """Debug the volume calculation"""
    print("[SEARCH] Debug Volume Calculation")
    print("=" * 40)
    
    # Test parameters (same as test)
    domain_size = 1500e-6  # 1500 um in meters
    nx, ny = 75, 75
    cell_height = 20e-6  # 20 um
    
    # Calculate mesh spacing and volume
    dx = domain_size / nx
    dy = domain_size / ny
    mesh_cell_volume = dx * dy * cell_height
    
    print(f" Domain size: {domain_size*1e6:.0f} um")
    print(f" Grid: {nx} x {ny}")
    print(f" Cell height: {cell_height*1e6:.1f} um")
    print(f" dx: {dx:.2e} m")
    print(f" dy: {dy:.2e} m")
    print(f" mesh_cell_volume: {mesh_cell_volume:.2e} m")
    
    # Test metabolism rate
    from config.custom_functions import calculate_cell_metabolism
    
    cell_state = {'phenotype': 'Proliferation'}
    local_environment = {}
    
    metabolism = calculate_cell_metabolism(local_environment, cell_state)
    lactate_rate = metabolism['lactate_production_rate']
    
    print(f"\n Metabolism test:")
    print(f"   Input rate: {lactate_rate:.2e} mol/s/cell")
    
    # Calculate volumetric rate
    volumetric_rate = lactate_rate / mesh_cell_volume
    print(f"   Volumetric rate: {volumetric_rate:.2e} mol/(ms)")
    
    # Convert to mM/s
    final_rate = volumetric_rate * 1000.0
    print(f"   Final rate: {final_rate:.2e} mM/s")
    
    # Expected rate
    expected_rate = 2.8e-2  # mM/s
    print(f"   Expected rate: {expected_rate:.2e} mM/s")
    
    ratio = abs(final_rate / expected_rate)
    print(f"   Ratio: {ratio:.2f}")
    
    # Check if the issue is in the volume calculation
    print(f"\n[SEARCH] Volume analysis:")
    print(f"   dx x dy: {dx * dy:.2e} m")
    print(f"   dx x dy x cell_height: {dx * dy * cell_height:.2e} m")
    
    # Check if we're missing a factor
    expected_volume = lactate_rate / (expected_rate / 1000.0)
    print(f"   Expected volume for correct rate: {expected_volume:.2e} m")
    
    volume_ratio = mesh_cell_volume / expected_volume
    print(f"   Volume ratio: {volume_ratio:.2f}")
    
    if abs(volume_ratio - 1.0) < 0.1:
        print("   [+] Volume calculation is correct")
    else:
        print(f"   [!] Volume calculation is off by factor of {volume_ratio:.2f}")

if __name__ == "__main__":
    debug_volume_calculation() 