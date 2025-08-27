#!/usr/bin/env python3
"""
Debug script to compare MicroC vs Standalone FiPy results.
Tests the exact same parameters to identify the source of differences.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict, Any

# Check if FiPy is available
try:
    from fipy import Grid2D, CellVariable, DiffusionTerm, ImplicitSourceTerm
    FIPY_AVAILABLE = True
    print("[+] FiPy available")
except ImportError:
    FIPY_AVAILABLE = False
    print("[!] FiPy not available")
    exit(1)

def run_microc_matched_test():
    """
    Run standalone FiPy test with EXACT MicroC parameters.
    """
    print(" MicroC-Matched FiPy Test")
    print("=" * 50)
    
    # EXACT MicroC parameters
    domain_size = 1500e-6  # 1500 um in meters (MicroC domain)
    grid_size = (75, 75)   # 75x75 grid (MicroC grid)
    nx, ny = grid_size
    
    # MicroC oxygen parameters
    diffusion_coeff = 2.2e-10  # m/s (from MicroC config)
    uptake_rate = 1.0e-16      # mol/s/cell (MicroC oxygen_vmax)
    initial_value = 0.07       # mM (MicroC initial)
    boundary_value = 0.07      # mM (MicroC boundary)
    cell_height = 20e-6        # 20 um (MicroC cell_height)
    
    # Create FiPy mesh
    dx = domain_size / nx
    dy = domain_size / ny
    
    print(f" Domain: {domain_size*1e6:.0f} x {domain_size*1e6:.0f} um")
    print(f" Grid: {nx} x {ny}")
    print(f" Spacing: {dx*1e6:.1f} x {dy*1e6:.1f} um")
    print(f" Cell height: {cell_height*1e6:.1f} um")
    
    mesh = Grid2D(dx=dx, dy=dy, nx=nx, ny=ny)
    
    # Create oxygen variable
    oxygen = CellVariable(name="Oxygen", mesh=mesh, value=initial_value)
    
    # Set boundary conditions (fixed boundaries)
    oxygen.constrain(boundary_value, mesh.facesTop | mesh.facesBottom | 
                    mesh.facesLeft | mesh.facesRight)
    
    # Place 2000 cells using EXACT MicroC placement algorithm
    cells = []
    center_x, center_y = nx // 2, ny // 2

    # Use expanding spherical pattern (EXACT MicroC algorithm)
    radius = 1
    cells_placed = 0

    while cells_placed < 2000 and radius < min(nx, ny) // 2:
        for x in range(max(0, center_x - radius), min(nx, center_x + radius + 1)):
            for y in range(max(0, center_y - radius), min(ny, center_y + radius + 1)):
                if cells_placed >= 2000:
                    break

                # Check if position is within radius
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                if distance <= radius:
                    cells.append({'position': (x, y), 'id': cells_placed})
                    cells_placed += 1

            if cells_placed >= 2000:
                break

        radius += 1
    
    print(f"[+] Placed {len(cells)} cells in center region")
    
    # Create source field with EXACT MicroC calculation
    source_field = np.zeros(nx * ny)
    
    # MicroC volume calculation: dx * dy * cell_height
    mesh_cell_volume = dx * dy * cell_height
    twodimensional_adjustment_coefficient = 1.0  # MicroC value
    
    print(f"[SEARCH] MicroC Volume Calculation:")
    print(f"   dx: {dx:.2e} m")
    print(f"   dy: {dy:.2e} m") 
    print(f"   cell_height: {cell_height:.2e} m")
    print(f"   mesh_cell_volume: {mesh_cell_volume:.2e} m")
    print(f"   2D adjustment: {twodimensional_adjustment_coefficient}")
    
    for cell in cells:
        x, y = cell['position']
        
        if 0 <= x < nx and 0 <= y < ny:
            # Convert to FiPy index (column-major order)
            fipy_idx = x * ny + y
            
            # EXACT MicroC calculation
            reaction_rate = uptake_rate  # mol/s/cell (negative for consumption)
            volumetric_rate = reaction_rate / mesh_cell_volume * twodimensional_adjustment_coefficient
            final_rate = volumetric_rate * 1000.0  # Convert to mM/s
            
            source_field[fipy_idx] = final_rate
    
    print(f"[SEARCH] Source field stats:")
    print(f"   Non-zero cells: {np.count_nonzero(source_field)}")
    print(f"   Min rate: {np.min(source_field):.2e} mM/s")
    print(f"   Max rate: {np.max(source_field):.2e} mM/s")
    
    # Negate source field for FiPy (MicroC does this)
    source_field = -source_field
    source_var = CellVariable(mesh=mesh, value=source_field)
    
    # Create diffusion equation (EXACT MicroC equation)
    equation = (DiffusionTerm(coeff=diffusion_coeff) - 
               ImplicitSourceTerm(coeff=source_var))
    
    print("\n[RUN] Solving steady-state diffusion equation...")
    
    # Solve for steady state (MicroC parameters)
    max_iterations = 100
    tolerance = 1e-4
    
    residual = 1.0
    iteration = 0
    
    while residual > tolerance and iteration < max_iterations:
        old_values = oxygen.value.copy()
        equation.solve(var=oxygen)
        
        # Calculate residual (relative change)
        residual = np.max(np.abs(oxygen.value - old_values)) / (np.max(np.abs(oxygen.value)) + 1e-12)
        iteration += 1
    
    if iteration >= max_iterations:
        print(f"[WARNING]  Did not converge after {max_iterations} iterations (residual: {residual:.2e})")
    else:
        print(f"[+] Converged in {iteration} iterations (residual: {residual:.2e})")
    
    # Get results
    oxygen_concentrations = oxygen.value.reshape((nx, ny), order='F')  # Fortran order for FiPy
    
    print(f"\n[CHART] Results:")
    print(f"   Oxygen range: {np.min(oxygen_concentrations):.6f} - {np.max(oxygen_concentrations):.6f} mM")
    print(f"   Depletion: {initial_value - np.min(oxygen_concentrations):.6f} mM")
    print(f"   Relative depletion: {(initial_value - np.min(oxygen_concentrations))/initial_value*100:.2f}%")
    
    return oxygen_concentrations, cells

def compare_with_original_standalone():
    """
    Compare with the original standalone test parameters.
    """
    print("\n" + "="*50)
    print("[SEARCH] COMPARISON WITH ORIGINAL STANDALONE")
    print("="*50)
    
    # Original standalone parameters
    print("Original Standalone:")
    print(f"   Domain: 600x600 um")
    print(f"   Grid: 40x40")
    print(f"   Cells: 200")
    print(f"   Uptake rate: 3.0e-17 mol/s/cell * 3000 = 9.0e-15 mol/s/cell")
    print(f"   Volume: dx*dy only (no height)")
    print(f"   Result: 0.016656 - 0.069969 mM (significant depletion)")
    
    print("\nMicroC-Matched:")
    print(f"   Domain: 1500x1500 um")
    print(f"   Grid: 75x75") 
    print(f"   Cells: 2000")
    print(f"   Uptake rate: 1.0e-16 mol/s/cell")
    print(f"   Volume: dx*dy*height (includes 20 um height)")
    
    # Calculate the effective rate difference
    original_rate = 3.0e-17 * 3000  # 9.0e-15 mol/s/cell
    microc_rate = 1.0e-16           # 1.0e-16 mol/s/cell
    
    # Volume difference
    original_volume = (600e-6/40) * (600e-6/40)  # dx*dy only
    microc_volume = (1500e-6/75) * (1500e-6/75) * 20e-6  # dx*dy*height
    
    print(f"\n[SEARCH] Rate Analysis:")
    print(f"   Original effective rate: {original_rate:.2e} mol/s/cell")
    print(f"   MicroC rate: {microc_rate:.2e} mol/s/cell")
    print(f"   Rate ratio: {original_rate/microc_rate:.1f}x higher in original")
    
    print(f"\n[SEARCH] Volume Analysis:")
    print(f"   Original volume: {original_volume:.2e} m")
    print(f"   MicroC volume: {microc_volume:.2e} m")
    print(f"   Volume ratio: {microc_volume/original_volume:.1f}x larger in MicroC")
    
    # Combined effect
    original_volumetric = original_rate / original_volume
    microc_volumetric = microc_rate / microc_volume
    
    print(f"\n[SEARCH] Volumetric Rate Analysis:")
    print(f"   Original volumetric: {original_volumetric:.2e} mol/(ms)")
    print(f"   MicroC volumetric: {microc_volumetric:.2e} mol/(ms)")
    print(f"   Volumetric ratio: {original_volumetric/microc_volumetric:.1f}x higher in original")

if __name__ == "__main__":
    # Run the MicroC-matched test
    oxygen_concentrations, cells = run_microc_matched_test()
    
    # Compare with original
    compare_with_original_standalone()
    
    print("\n[SUCCESS] Analysis completed!")
