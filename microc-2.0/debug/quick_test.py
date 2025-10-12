#!/usr/bin/env python3
"""
Quick test to compare MicroC vs standalone calculations
"""

import numpy as np

def compare_calculations():
    """Compare the key calculations between MicroC and standalone"""
    
    print(" Quick Comparison Test")
    print("=" * 40)
    
    # Parameters (same as both scripts)
    domain_size = 1500e-6  # 1500 um in meters
    nx, ny = 75, 75
    cell_height = 20e-6  # 20 um
    
    # Calculate mesh spacing
    dx = domain_size / nx
    dy = domain_size / ny
    
    print(f" Grid spacing: {dx*1e6:.1f} x {dy*1e6:.1f} um")
    print(f" Cell height: {cell_height*1e6:.1f} um")
    
    # Reaction rate from MicroC custom_functions.py
    reaction_rate_mol_per_cell = 0.8e-17  # mol/s/cell
    
    print(f"[SEARCH] Reaction rate: {reaction_rate_mol_per_cell:.2e} mol/s/cell")
    
    # Volume calculations
    volume_2d = dx * dy  # 2D area only
    volume_3d = dx * dy * cell_height  # 3D volume
    
    print(f" Volume calculations:")
    print(f"   2D area: {volume_2d:.2e} m")
    print(f"   3D volume: {volume_3d:.2e} m")
    print(f"   Ratio (3D/2D): {volume_3d/volume_2d:.1f}")
    
    # Source term calculations
    twodimensional_adjustment_coefficient = 1.0
    
    # 2D calculation (old MicroC)
    volumetric_rate_2d = reaction_rate_mol_per_cell / volume_2d * twodimensional_adjustment_coefficient
    final_rate_2d = volumetric_rate_2d * 1000.0  # Convert to mM/s
    
    # 3D calculation (corrected MicroC)
    volumetric_rate_3d = reaction_rate_mol_per_cell / volume_3d * twodimensional_adjustment_coefficient
    final_rate_3d = volumetric_rate_3d * 1000.0  # Convert to mM/s
    
    print(f" Source term calculations:")
    print(f"   2D approach (old MicroC): {final_rate_2d:.2e} mM/s")
    print(f"   3D approach (corrected): {final_rate_3d:.2e} mM/s")
    print(f"   Ratio (2D/3D): {final_rate_2d/final_rate_3d:.1f}")
    
    # Standalone approach (direct mM/s)
    standalone_rate = 2.8e-2  # mM/s (from standalone script)
    
    print(f"[CHART] Comparison:")
    print(f"   Standalone (direct): {standalone_rate:.2e} mM/s")
    print(f"   MicroC 2D (old): {final_rate_2d:.2e} mM/s")
    print(f"   MicroC 3D (fixed): {final_rate_3d:.2e} mM/s")
    
    print(f"\n[IDEA] Analysis:")
    if abs(final_rate_3d - standalone_rate) / standalone_rate < 0.1:
        print(f"   [+] 3D MicroC matches standalone (within 10%)")
    else:
        print(f"   [!] 3D MicroC differs from standalone")
    
    if final_rate_2d > final_rate_3d * 100:
        print(f"   [WARNING]  2D MicroC was {final_rate_2d/final_rate_3d:.0f}x too large!")
        print(f"    This explains why MicroC was producing tiny gradients!")

if __name__ == "__main__":
    compare_calculations() 