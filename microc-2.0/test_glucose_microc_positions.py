#!/usr/bin/env python3
"""
Test glucose diffusion using EXACTLY the same cell positions as MicroC
to isolate whether cell placement is causing the difference in results.
"""

import numpy as np
import matplotlib.pyplot as plt
from fipy import Grid2D, CellVariable, DiffusionTerm

def test_glucose_with_microc_positions():
    """Test glucose diffusion using MicroC's exact cell positions"""
    
    # Domain setup (EXACTLY match MicroC)
    domain_size = 2000e-6  # 2000 μm = 2e-3 m
    nx, ny = 200, 200
    dx = domain_size / nx  # 10 μm
    dy = domain_size / ny  # 10 μm
    
    # Create mesh
    mesh = Grid2D(nx=nx, ny=ny, dx=dx, dy=dy)
    print(f"🧪 Testing glucose diffusion with MicroC cell positions...")
    print(f"   Mesh: {nx}×{ny} cells, spacing: {dx*1e6:.1f}×{dy*1e6:.1f} μm")
    
    # Glucose variable
    glucose = CellVariable(name="Glucose", mesh=mesh, value=5.0)  # Initial: 5 mM
    
    # Boundary conditions: fixed at 5.0 mM on all boundaries
    glucose.constrain(5.0, mesh.facesTop)
    glucose.constrain(5.0, mesh.facesBottom) 
    glucose.constrain(5.0, mesh.facesLeft)
    glucose.constrain(5.0, mesh.facesRight)
    print(f"   Boundary conditions: 5.0 mM on all edges")
    
    # Diffusion coefficient: 1.0e-9 m²/s (from config)
    D = 1.0e-9
    print(f"   Diffusion coefficient: {D:.2e} m²/s")
    
    # CRITICAL: Use MicroC's exact cell positions
    # MicroC places cells in a circular pattern around center (100, 100) in biological coordinates
    # which maps to (100, 100) in FiPy coordinates for a 200x200 grid
    source_field = np.zeros(nx * ny)
    
    # MicroC's cell placement algorithm (from debug output analysis)
    center_x, center_y = 100, 100  # Center of 200x200 grid
    cell_count = 0
    target_cells = 2000
    consumption_mol_per_s_val = -1e-22  # mol/s/cell (MATCH MicroC exactly)
    
    # Place cells in circular pattern (MicroC style)
    # Based on MicroC debug output showing cells at positions like (98,100), (100,98), etc.
    placed_positions = []
    
    for radius in range(1, 50):  # Expand outward from center
        for angle_deg in range(0, 360, 5):  # Every 5 degrees
            if cell_count >= target_cells:
                break
                
            angle_rad = np.radians(angle_deg)
            x = int(center_x + radius * np.cos(angle_rad))
            y = int(center_y + radius * np.sin(angle_rad))
            
            # Check bounds
            if 0 <= x < nx and 0 <= y < ny:
                # Check if position already used (avoid collisions like MicroC)
                pos_key = (x, y)
                if pos_key not in placed_positions:
                    placed_positions.append(pos_key)
                    
                    idx = x * ny + y
                    
                    # Convert consumption rate (SAME AS MICROC)
                    cell_volume = 2e-15  # m³
                    consumption_mol_per_s = consumption_mol_per_s_val
                    consumption_mM_per_s = consumption_mol_per_s / cell_volume * 1e6
                    
                    source_field[idx] = consumption_mM_per_s
                    cell_count += 1
        
        if cell_count >= target_cells:
            break
    
    print(f"   Placed {cell_count} consuming cells")
    print(f"   Consumption rate per cell: {consumption_mol_per_s:.2e} mol/s")
    print(f"   Converted to source term: {consumption_mM_per_s:.2e} mM/s")
    
    # Create source variable
    source_var = CellVariable(name="Source", mesh=mesh, value=source_field)
    
    # Check source field
    nonzero_count = np.sum(source_field != 0)
    source_min = float(np.min(source_field))
    source_max = float(np.max(source_field))
    print(f"   Source field: {nonzero_count} non-zero terms")
    print(f"   Source range: [{source_min:.2e}, {source_max:.2e}] mM/s")
    
    # Diffusion equation: ∇·(D∇C) = -S (SAME AS MICROC)
    equation = DiffusionTerm(coeff=D) == -source_var
    
    # Solve (SAME SOLVER SETTINGS AS MICROC)
    print(f"   Solving diffusion equation...")
    residual = 1.0
    iteration = 0
    max_iterations = 1000
    tolerance = 1e-6
    
    while residual > tolerance and iteration < max_iterations:
        old_values = glucose.value.copy()
        equation.solve(var=glucose)
        
        # Calculate residual
        residual = np.max(np.abs(glucose.value - old_values)) / (np.max(np.abs(glucose.value)) + 1e-12)
        iteration += 1
    
    print(f"   Converged in {iteration} iterations (residual: {residual:.2e})")
    
    # Results
    final_min = float(np.min(glucose.value))
    final_max = float(np.max(glucose.value))
    final_mean = float(np.mean(glucose.value))
    final_range = final_max - final_min
    
    print(f"\n📊 RESULTS:")
    print(f"   Final concentrations: min={final_min:.6f}, max={final_max:.6f}, mean={final_mean:.6f} mM")
    print(f"   Concentration range: {final_range:.6f} mM ({final_range/final_mean*100:.4f}% variation)")
    
    # Check for negative values
    negative_count = np.sum(glucose.value < 0)
    if negative_count > 0:
        print(f"   ⚠️  {negative_count} cells with negative concentrations!")
        print(f"   Most negative: {np.min(glucose.value):.6f} mM")
    
    # Compare with MicroC and original standalone
    print(f"\n🔍 COMPARISON:")
    print(f"   MicroC result: 2.000-5.000 mM")
    print(f"   Original standalone: 1.895-5.000 mM") 
    print(f"   This test: {final_min:.3f}-{final_max:.3f} mM")
    
    if abs(final_min - 2.0) < 0.01:
        print(f"   ✅ MATCHES MicroC! Cell placement explains the difference.")
    elif abs(final_min - 1.895) < 0.01:
        print(f"   ✅ MATCHES original standalone! Cell placement is NOT the issue.")
    else:
        print(f"   ❓ Different from both - something else is causing the difference.")
    
    return {
        'min': final_min,
        'max': final_max,
        'mean': final_mean,
        'negative_count': negative_count,
        'cell_count': cell_count
    }

if __name__ == "__main__":
    results = test_glucose_with_microc_positions()
    
    print(f"\n🎯 SUMMARY:")
    print(f"   This test uses MicroC-style cell placement to isolate the cause")
    print(f"   of the difference between MicroC (2.0 mM min) and standalone (1.895 mM min)")
    print(f"   Result: {results['min']:.3f} to {results['max']:.3f} mM")
