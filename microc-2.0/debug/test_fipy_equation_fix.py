#!/usr/bin/env python3
"""
Test if the FiPy equation fix works with a simple example
"""

import numpy as np
from fipy import Grid3D, CellVariable, DiffusionTerm, ImplicitSourceTerm
from fipy.solvers import Solver

def main():
    print(" TESTING FIPY EQUATION FIX")
    print("=" * 40)
    
    # Create simple 3D mesh (same as MicroC)
    nx, ny, nz = 25, 25, 25
    dx = dy = dz = 20e-6  # 20 um spacing
    mesh = Grid3D(dx=dx, dy=dy, dz=dz, nx=nx, ny=ny, nz=nz)
    
    print(f" Mesh: {nx}x{ny}x{nz}")
    print(f" Spacing: {dx*1e6:.1f} um")
    print(f" Total cells: {mesh.numberOfCells}")
    
    # Create oxygen variable
    initial_value = 0.07  # mM
    boundary_value = 0.07  # mM
    diffusion_coeff = 2.1e-9  # m/s (oxygen)
    
    oxygen = CellVariable(name="Oxygen", mesh=mesh, value=initial_value)
    
    # Apply boundary conditions (same as MicroC)
    oxygen.constrain(boundary_value, mesh.facesTop | mesh.facesBottom | 
                    mesh.facesLeft | mesh.facesRight)
    
    print(f" Initial oxygen: {initial_value} mM")
    print(f" Boundary oxygen: {boundary_value} mM")
    print(f" Diffusion coeff: {diffusion_coeff:.2e} m/s")
    
    # Create source field with significant consumption at center
    source_field = np.zeros(mesh.numberOfCells)
    
    # Find center cells and apply strong consumption
    cell_centers = mesh.cellCenters
    center_x = (nx * dx) / 2
    center_y = (ny * dy) / 2
    center_z = (nz * dz) / 2
    
    # Apply consumption in a 5x5x5 region at center
    consumption_rate = -0.1  # mM/s (very strong consumption)
    
    for i in range(mesh.numberOfCells):
        x = cell_centers[0][i]
        y = cell_centers[1][i] 
        z = cell_centers[2][i]
        
        # Check if cell is in center region
        if (abs(x - center_x) < 2*dx and 
            abs(y - center_y) < 2*dy and 
            abs(z - center_z) < 2*dz):
            source_field[i] = consumption_rate
    
    consumption_cells = np.count_nonzero(source_field)
    total_consumption = np.sum(source_field)
    
    print(f"\n[HOT] SOURCE TERMS:")
    print(f"   Consumption cells: {consumption_cells}")
    print(f"   Consumption rate: {consumption_rate} mM/s per cell")
    print(f"   Total consumption: {total_consumption:.2e} mM/s")
    
    # Test both equation formulations
    print(f"\n TESTING EQUATION FORMULATIONS:")
    
    # Method 1: DiffusionTerm == -source_var (old MicroC)
    print(f"\n1  Testing: DiffusionTerm == -source_var")
    
    oxygen1 = oxygen.copy()
    source_var1 = CellVariable(mesh=mesh, value=source_field)
    equation1 = DiffusionTerm(coeff=diffusion_coeff) == -source_var1
    
    # Solve
    for i in range(100):
        old_values = oxygen1.value.copy()
        equation1.solve(var=oxygen1)
        
        residual = np.max(np.abs(oxygen1.value - old_values)) / (np.max(np.abs(oxygen1.value)) + 1e-12)
        if residual < 1e-6:
            print(f"   [+] Converged in {i+1} iterations")
            break
    
    min1 = float(np.min(oxygen1.value))
    max1 = float(np.max(oxygen1.value))
    std1 = float(np.std(oxygen1.value))
    
    print(f"   Results: min={min1:.6f}, max={max1:.6f}, std={std1:.6f} mM")
    if std1 < 1e-10:
        print(f"   [!] UNIFORM! No gradients")
    else:
        print(f"   [+] Gradients detected!")
    
    # Method 2: DiffusionTerm - ImplicitSourceTerm (new fix)
    print(f"\n2  Testing: DiffusionTerm - ImplicitSourceTerm")
    
    oxygen2 = oxygen.copy()
    source_var2 = CellVariable(mesh=mesh, value=source_field)
    equation2 = DiffusionTerm(coeff=diffusion_coeff) - ImplicitSourceTerm(coeff=source_var2)
    
    # Solve
    for i in range(100):
        old_values = oxygen2.value.copy()
        equation2.solve(var=oxygen2)
        
        residual = np.max(np.abs(oxygen2.value - old_values)) / (np.max(np.abs(oxygen2.value)) + 1e-12)
        if residual < 1e-6:
            print(f"   [+] Converged in {i+1} iterations")
            break
    
    min2 = float(np.min(oxygen2.value))
    max2 = float(np.max(oxygen2.value))
    std2 = float(np.std(oxygen2.value))
    
    print(f"   Results: min={min2:.6f}, max={max2:.6f}, std={std2:.6f} mM")
    if std2 < 1e-10:
        print(f"   [!] UNIFORM! No gradients")
    else:
        print(f"   [+] Gradients detected!")
    
    # Method 3: Test with much stronger consumption
    print(f"\n3  Testing with 1000x stronger consumption")
    
    strong_source_field = source_field * 1000  # -100 mM/s
    oxygen3 = oxygen.copy()
    source_var3 = CellVariable(mesh=mesh, value=strong_source_field)
    equation3 = DiffusionTerm(coeff=diffusion_coeff) - ImplicitSourceTerm(coeff=source_var3)
    
    # Solve
    for i in range(100):
        old_values = oxygen3.value.copy()
        equation3.solve(var=oxygen3)
        
        residual = np.max(np.abs(oxygen3.value - old_values)) / (np.max(np.abs(oxygen3.value)) + 1e-12)
        if residual < 1e-6:
            print(f"   [+] Converged in {i+1} iterations")
            break
    
    min3 = float(np.min(oxygen3.value))
    max3 = float(np.max(oxygen3.value))
    std3 = float(np.std(oxygen3.value))
    
    print(f"   Strong consumption: {np.min(strong_source_field):.1f} mM/s")
    print(f"   Results: min={min3:.6f}, max={max3:.6f}, std={std3:.6f} mM")
    if std3 < 1e-10:
        print(f"   [!] STILL UNIFORM! Problem is elsewhere")
    else:
        print(f"   [+] Gradients detected!")
    
    print(f"\n[CHART] SUMMARY:")
    print(f"   Method 1 (== -source): std={std1:.2e}")
    print(f"   Method 2 (- ImplicitSource): std={std2:.2e}")
    print(f"   Method 3 (1000x stronger): std={std3:.2e}")

if __name__ == "__main__":
    main()
