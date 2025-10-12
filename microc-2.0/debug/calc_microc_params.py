#!/usr/bin/env python3
"""
Calculate MicroC parameters without FiPy
"""

import numpy as np

def calculate_microc_parameters():
    print(" MicroC Parameter Calculation")
    print("=" * 40)
    
    # MicroC parameters
    domain_size = 1500e-6  # m
    nx, ny = 75, 75
    cell_height = 20e-6    # m
    uptake_rate = 1.0e-16  # mol/s/cell
    diffusion_coeff = 2.2e-10  # m/s
    
    # Calculate mesh
    dx = domain_size / nx
    dy = domain_size / ny
    mesh_volume = dx * dy * cell_height
    
    print(f" Domain: {domain_size*1e6:.0f} um")
    print(f" Grid: {nx}x{ny}")
    print(f" Spacing: {dx*1e6:.1f} um")
    print(f" Cell height: {cell_height*1e6:.1f} um")
    print(f" Mesh volume: {mesh_volume:.2e} m")
    
    # Source term calculation
    volumetric_rate = uptake_rate / mesh_volume * 1.0  # 2D adjustment = 1.0
    final_rate_mM_per_s = volumetric_rate * 1000.0
    
    print(f"\n[SEARCH] Source Term Calculation:")
    print(f"   Uptake rate: {uptake_rate:.2e} mol/s/cell")
    print(f"   Mesh volume: {mesh_volume:.2e} m")
    print(f"   Volumetric rate: {volumetric_rate:.2e} mol/(ms)")
    print(f"   Final rate: {final_rate_mM_per_s:.2e} mM/s")
    
    # Compare with original standalone
    original_domain = 600e-6  # m
    original_nx = 40
    original_dx = original_domain / original_nx
    original_volume = original_dx * original_dx  # No height
    original_uptake = 3.0e-17 * 3000  # mol/s/cell
    original_volumetric = original_uptake / original_volume
    original_final = original_volumetric * 1000.0
    
    print(f"\n[SEARCH] Comparison with Original Standalone:")
    print(f"   Original final rate: {original_final:.2e} mM/s")
    print(f"   MicroC final rate: {final_rate_mM_per_s:.2e} mM/s")
    print(f"   Ratio: {original_final/final_rate_mM_per_s:.1f}x higher in original")
    
    # Estimate diffusion length scale
    # For steady state: DnablaC = R
    # Characteristic length: L ~ sqrt(D/R) where R is volumetric consumption
    char_length = np.sqrt(diffusion_coeff / volumetric_rate)
    char_length_grid = char_length / dx
    
    print(f"\n[SEARCH] Diffusion Analysis:")
    print(f"   Diffusion coeff: {diffusion_coeff:.2e} m/s")
    print(f"   Characteristic length: {char_length:.2e} m = {char_length*1e6:.1f} um")
    print(f"   Characteristic length (grid units): {char_length_grid:.1f}")
    
    if char_length_grid > 10:
        print("   [+] Diffusion length >> grid spacing - should see gradients")
    elif char_length_grid > 3:
        print("   [WARNING]  Diffusion length ~ few grid spacings - weak gradients")
    else:
        print("   [!] Diffusion length < grid spacing - essentially uniform")
    
    # Estimate concentration drop
    # For a point source: DeltaC ~ R*L/D where L is distance from source
    # For 100 cells in 10x10 region, estimate total consumption
    total_cells = 100
    source_region_size = 10 * dx  # 10 grid cells
    total_consumption = total_cells * uptake_rate / (source_region_size**2 * cell_height)
    
    # Estimate concentration drop over characteristic length
    delta_c_estimate = total_consumption * char_length**2 / diffusion_coeff / 1000.0  # Convert to mM
    
    print(f"\n[SEARCH] Concentration Drop Estimate:")
    print(f"   Total cells: {total_cells}")
    print(f"   Source region: {source_region_size*1e6:.0f} um")
    print(f"   Total consumption: {total_consumption:.2e} mol/(ms)")
    print(f"   Estimated DeltaC: {delta_c_estimate:.6f} mM")
    
    if delta_c_estimate < 1e-6:
        print("   [!] Negligible depletion expected")
    elif delta_c_estimate < 1e-3:
        print("   [WARNING]  Very small depletion expected")
    else:
        print("   [+] Measurable depletion expected")

if __name__ == "__main__":
    calculate_microc_parameters()
