#!/usr/bin/env python3
"""
Test script to calculate exactly what values calculate_cell_metabolism produces
and how they get converted in MicroC.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_metabolism_values():
    """Test what values calculate_cell_metabolism produces"""
    print(" Testing Metabolism Values")
    print("=" * 50)
    
    # Import the custom functions
    try:
        from config.custom_functions import calculate_cell_metabolism
        print("[+] Custom functions imported successfully")
    except ImportError as e:
        print(f"[!] Failed to import custom functions: {e}")
        return
    
    # Test parameters (same as our simulations)
    domain_size = 1500e-6  # 1500 um in meters
    nx, ny = 75, 75
    cell_height = 20e-6  # 20 um
    
    # Calculate mesh spacing and volume
    dx = domain_size / nx
    dy = domain_size / ny
    mesh_cell_volume = dx * dy * cell_height  # m (FIXED: include cell_height)
    
    print(f" Grid spacing: {dx*1e6:.1f} x {dy*1e6:.1f} um")
    print(f" Cell height: {cell_height*1e6:.1f} um")
    print(f" Mesh cell volume: {mesh_cell_volume:.2e} m")
    
    # Test different phenotypes
    phenotypes = ["Proliferation", "Growth_Arrest", "Apoptosis", "Necrosis"]
    
    print(f"\n Testing metabolism for different phenotypes:")
    print("-" * 50)
    
    for phenotype in phenotypes:
        print(f"\n[CHART] Phenotype: {phenotype}")
        
        # Create mock cell state
        cell_state = {'phenotype': phenotype}
        local_environment = {}  # Empty for this test
        
        # Get metabolism rates
        metabolism = calculate_cell_metabolism(local_environment, cell_state)
        
        print(f"   Raw metabolism rates (mol/s/cell):")
        for substance, rate in metabolism.items():
            print(f"     {substance}: {rate:.2e}")
        
        # Test lactate specifically
        if 'lactate_production_rate' in metabolism:
            lactate_rate_mol_per_cell = metabolism['lactate_production_rate']
            
            print(f"   Lactate conversion:")
            print(f"     Input: {lactate_rate_mol_per_cell:.2e} mol/s/cell")
            
            # MicroC conversion steps
            volumetric_rate = lactate_rate_mol_per_cell / mesh_cell_volume  # mol/(ms)
            final_rate_mm_per_s = volumetric_rate * 1000.0  # mM/s
            
            print(f"     Volumetric rate: {volumetric_rate:.2e} mol/(ms)")
            print(f"     Final rate: {final_rate_mm_per_s:.2e} mM/s")
            
            # Compare with standalone
            standalone_rate = -2.8e-2  # mM/s
            ratio = abs(final_rate_mm_per_s / standalone_rate)
            
            print(f"     Standalone rate: {standalone_rate:.2e} mM/s")
            print(f"     Ratio (MicroC/Standalone): {ratio:.1f}")
            
            if ratio < 0.1:
                print(f"     [!] MicroC rate is {ratio:.1f}x smaller than standalone!")
            elif ratio > 10:
                print(f"     [!] MicroC rate is {ratio:.1f}x larger than standalone!")
            else:
                print(f"     [+] MicroC rate is reasonable compared to standalone")
    
    print(f"\n[IDEA] Analysis:")
    print(f"   The issue is that MicroC's metabolism function produces rates")
    print(f"   in mol/s/cell that are much smaller than the standalone's mM/s rates.")
    print(f"   This explains why MicroC shows uniform concentrations - the source")
    print(f"   terms are too small to create visible gradients.")

if __name__ == "__main__":
    test_metabolism_values() 