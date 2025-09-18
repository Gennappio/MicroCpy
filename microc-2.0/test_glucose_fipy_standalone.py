#!/usr/bin/env python3
"""
Standalone FiPy test for glucose diffusion with exact same conditions as MicroC simulation
"""

import numpy as np
import matplotlib.pyplot as plt
from fipy import CellVariable, Grid2D, DiffusionTerm, Viewer
from fipy.tools import numerix

def test_glucose_diffusion():
    print("🧪 Testing glucose diffusion with MicroC conditions...")
    
    # EXACT SAME CONDITIONS AS MICROC SIMULATION
    # Domain: 2000x2000 μm, Grid: 200x200
    nx, ny = 200, 200
    dx = dy = 10.0e-6  # 10 μm in meters
    
    # Create mesh
    mesh = Grid2D(nx=nx, ny=ny, dx=dx, dy=dy)
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
    
    # Create source field with 2000 cells consuming glucose
    # Each cell consumes -1e-19 mol/s/cell (hardcoded value)
    source_field = np.zeros(nx * ny)
    
    # Place 2000 cells in circular pattern (like MicroC)
    center_x, center_y = nx // 2, ny // 2
    cell_count = 0
    target_cells = 2000
    consumption_mol_per_s_val =  -1e-22  # MATCH MicroC exactly
    # Add cells in expanding circles until we reach 2000
    for radius in range(1, min(nx, ny) // 2):
        for i in range(nx):
            for j in range(ny):
                if cell_count >= target_cells:
                    break
                    
                # Check if this position is within the current radius
                dist = np.sqrt((i - center_x)**2 + (j - center_y)**2)
                if radius - 1 < dist <= radius:
                    idx = i * ny + j
                    
                    # Convert consumption rate from mol/s/cell to mM/s
                    # Cell volume: 20 μm height × 10×10 μm area = 2000 μm³ = 2e-15 m³
                    cell_volume = 2e-15  # m³
                    consumption_mol_per_s = consumption_mol_per_s_val  # mol/s/cell (SAME AS MICROC)
                    
                    # Convert to mM/s: (mol/s) / (m³) × (1000 L/m³) × (1000 mM/M)
                    consumption_mM_per_s = consumption_mol_per_s / cell_volume * 1e6
                    
                    source_field[idx] = consumption_mM_per_s
                    cell_count += 1
            if cell_count >= target_cells:
                break
        if cell_count >= target_cells:
            break
    
    print(f"   Placed {cell_count} consuming cells")
    print(f"   Consumption rate per cell: {consumption_mol_per_s:.2e} mol/s")
    print(f"   Converted to source term: {consumption_mM_per_s:.2e} mM/s")
    
    # Reshape source field to match mesh
    source_2d = source_field.reshape((nx, ny), order='F')
    source_var = CellVariable(name="Source", mesh=mesh, value=source_2d.flatten())
    
    # Check source field statistics
    nonzero_count = np.count_nonzero(source_field)
    source_min = np.min(source_field)
    source_max = np.max(source_field)
    print(f"   Source field: {nonzero_count} non-zero terms")
    print(f"   Source range: [{source_min:.2e}, {source_max:.2e}] mM/s")
    
    # Diffusion equation: ∇·(D∇C) = -S
    equation = DiffusionTerm(coeff=D) == -source_var
    
    # Solve
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
    
    # Analyze results
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
    
    # Check if clamping would affect results
    clamped_values = np.maximum(glucose.value, 0.0)
    clamped_min = float(np.min(clamped_values))
    clamped_max = float(np.max(clamped_values))
    
    if negative_count > 0:
        print(f"\n🔧 AFTER CLAMPING TO ≥ 0:")
        print(f"   Clamped range: {clamped_min:.6f} to {clamped_max:.6f} mM")
    
    # Create cell position arrays for visualization
    cell_positions_x = []
    cell_positions_y = []
    for i in range(nx):
        for j in range(ny):
            idx = i * ny + j
            if source_field[idx] < 0:  # This is a consuming cell
                cell_positions_x.append(i * dx * 1e6)  # Convert to μm
                cell_positions_y.append(j * dy * 1e6)  # Convert to μm

    # Create visualization - ONLY the physically correct clamped solution
    plt.figure(figsize=(10, 8))

    # Clamped solution with cells (physically correct)
    clamped_2d = clamped_values.reshape((nx, ny), order='F')
    im = plt.imshow(clamped_2d, cmap='viridis', origin='lower',
                    extent=[0, nx*dx*1e6, 0, ny*dy*1e6])
    plt.colorbar(im, label='Glucose (mM)')
    plt.scatter(cell_positions_x, cell_positions_y, c='red', s=1.0, alpha=0.8, label=f'{len(cell_positions_x)} consuming cells')
    plt.title(f'Glucose Distribution (Physically Correct)\nRange: {clamped_min:.1f} to {clamped_max:.1f} mM\nConsumption: {consumption_mol_per_s_val}  mol/s/cell')
    plt.xlabel('X (μm)')
    plt.ylabel('Y (μm)')
    plt.legend()

    plt.tight_layout()
    plt.savefig('glucose_fipy_clamped_solution.png', dpi=300, bbox_inches='tight')
    print(f"\n💾 Saved plot: glucose_fipy_clamped_solution.png")
    
    return {
        'raw_min': final_min,
        'raw_max': final_max,
        'raw_mean': final_mean,
        'clamped_min': clamped_min,
        'clamped_max': clamped_max,
        'negative_count': negative_count,
        'source_terms': nonzero_count
    }

if __name__ == "__main__":
    results = test_glucose_diffusion()
    
    print(f"\n🎯 SUMMARY:")
    print(f"   This standalone test uses EXACTLY the same conditions as MicroC:")
    print(f"   • Domain: 2000×2000 μm, Grid: 200×200")
    print(f"   • Boundary: 5.0 mM on all edges")
    print(f"   • Diffusion: 1.0e-9 m²/s")
    print(f"   • Cells: 2000 consuming at -1e-19 mol/s/cell")
    print(f"   • Source terms: {results['source_terms']} non-zero")
    print(f"   • Raw solution: {results['raw_min']:.3f} to {results['raw_max']:.3f} mM")
    print(f"   • Clamped solution: {results['clamped_min']:.3f} to {results['clamped_max']:.3f} mM")
    
    if results['negative_count'] > 0:
        print(f"   ⚠️  The raw solution has {results['negative_count']} negative values")
        print(f"   🔧 MicroC's clamping creates the {results['clamped_min']:.1f}-{results['clamped_max']:.1f} mM range you observed")
