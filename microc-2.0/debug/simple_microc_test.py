#!/usr/bin/env python3
"""
Simple test with exact MicroC parameters
"""

import numpy as np

# Check if FiPy is available
try:
    from fipy import Grid2D, CellVariable, DiffusionTerm, ImplicitSourceTerm
    print("[+] FiPy available")
except ImportError:
    print("[!] FiPy not available")
    exit(1)

def main():
    print(" Simple MicroC Parameter Test")
    print("=" * 40)
    
    # EXACT MicroC parameters
    domain_size = 1500e-6  # 1500 um
    nx, ny = 75, 75        # 75x75 grid
    
    # MicroC parameters
    diffusion_coeff = 2.2e-10  # m/s
    uptake_rate = 1.0e-16      # mol/s/cell
    initial_value = 0.07       # mM
    boundary_value = 0.07      # mM
    cell_height = 20e-6        # 20 um
    
    # Calculate mesh
    dx = domain_size / nx
    dy = domain_size / ny
    
    print(f" Domain: {domain_size*1e6:.0f} um")
    print(f" Grid: {nx}x{ny}")
    print(f" Spacing: {dx*1e6:.1f} um")
    print(f" Cell height: {cell_height*1e6:.1f} um")
    
    # Create mesh and variable
    mesh = Grid2D(dx=dx, dy=dy, nx=nx, ny=ny)
    oxygen = CellVariable(name="Oxygen", mesh=mesh, value=initial_value)
    
    # Boundary conditions
    oxygen.constrain(boundary_value, mesh.facesTop | mesh.facesBottom | 
                    mesh.facesLeft | mesh.facesRight)
    
    # Place 100 cells in center (simplified test)
    source_field = np.zeros(nx * ny)
    center_x, center_y = nx // 2, ny // 2
    
    # Place cells in 10x10 center region
    cell_count = 0
    for x in range(center_x-5, center_x+5):
        for y in range(center_y-5, center_y+5):
            if 0 <= x < nx and 0 <= y < ny and cell_count < 100:
                fipy_idx = x * ny + y
                
                # MicroC calculation
                mesh_cell_volume = dx * dy * cell_height
                volumetric_rate = uptake_rate / mesh_cell_volume * 1.0  # 2D adjustment = 1.0
                final_rate = volumetric_rate * 1000.0  # Convert to mM/s
                
                source_field[fipy_idx] = final_rate
                cell_count += 1
    
    print(f"[+] Placed {cell_count} cells")
    print(f"[SEARCH] Mesh volume: {mesh_cell_volume:.2e} m")
    print(f"[SEARCH] Source rate: {final_rate:.2e} mM/s")
    
    # Negate for FiPy (consumption)
    source_field = -source_field
    source_var = CellVariable(mesh=mesh, value=source_field)
    
    # Solve
    equation = (DiffusionTerm(coeff=diffusion_coeff) - 
               ImplicitSourceTerm(coeff=source_var))
    
    print("\n[RUN] Solving...")
    
    # Simple solve
    for i in range(100):
        old_values = oxygen.value.copy()
        equation.solve(var=oxygen)
        
        residual = np.max(np.abs(oxygen.value - old_values)) / (np.max(np.abs(oxygen.value)) + 1e-12)
        if residual < 1e-4:
            print(f"[+] Converged in {i+1} iterations")
            break
    
    # Results
    oxygen_array = oxygen.value.reshape((nx, ny), order='F')
    min_val = np.min(oxygen_array)
    max_val = np.max(oxygen_array)
    
    print(f"\n[CHART] Results:")
    print(f"   Range: {min_val:.8f} - {max_val:.8f} mM")
    print(f"   Depletion: {initial_value - min_val:.8f} mM")
    print(f"   Relative depletion: {(initial_value - min_val)/initial_value*100:.6f}%")
    
    if (initial_value - min_val) < 1e-6:
        print("   [WARNING]  ESSENTIALLY UNIFORM - No significant depletion!")
    else:
        print("   [+] Visible depletion detected")

if __name__ == "__main__":
    main()
