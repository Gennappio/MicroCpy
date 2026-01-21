#!/usr/bin/env python3
"""
Standalone 3D FiPy test that exactly matches OpenCellComms's 3D approach.
Uses same parameters, same cell distribution, same calculations as OpenCellComms 3D.
"""

import numpy as np
import matplotlib.pyplot as plt

# Import FiPy
try:
    from fipy import Grid3D, CellVariable, DiffusionTerm
    from fipy.solvers.scipy import LinearGMRESSolver as Solver
    print("✅ FiPy available")
except ImportError:
    print("❌ FiPy not available")
    exit(1)

def main():
    print("🧬 Standalone 3D FiPy Test - Exact OpenCellComms Match")
    print("=" * 50)
    
    # EXACT OpenCellComms 3D parameters from jayatilake_experiment_config.yaml
    domain_size = 500e-6  # 500 μm in meters
    grid_size = (25, 25, 25)   # 25×25×25 grid (3D)
    nx, ny, nz = grid_size
    
    # OpenCellComms lactate parameters
    diffusion_coeff = 1.8e-10  # m²/s (lactate diffusion coefficient from config)
    initial_value = 1.0        # mM (lactate initial value from config)
    boundary_value = 1.0       # mM (lactate boundary value from config)
    cell_height = 5e-6         # 5 μm (from config - biological cell height)
    
    # Cell placement parameters
    initial_cell_count = 1000  # From config
    
    print(f"📐 Domain: {domain_size*1e6:.0f} × {domain_size*1e6:.0f} × {domain_size*1e6:.0f} μm")
    print(f"📐 Grid: {nx} × {ny} × {nz}")
    print(f"📐 Cell height: {cell_height*1e6:.1f} μm")
    print(f"📐 Diffusion coeff: {diffusion_coeff:.2e} m²/s")
    print(f"📐 Initial lactate: {initial_value} mM")
    print(f"📐 Boundary lactate: {boundary_value} mM")
    print(f"📐 Initial cell count: {initial_cell_count}")
    
    # Calculate mesh spacing
    dx = domain_size / nx
    dy = domain_size / ny
    dz = domain_size / nz
    
    print(f"📐 Grid spacing: {dx*1e6:.1f} × {dy*1e6:.1f} × {dz*1e6:.1f} μm")
    
    # Create FiPy 3D mesh
    mesh = Grid3D(dx=dx, dy=dy, dz=dz, nx=nx, ny=ny, nz=nz)
    
    # Create lactate variable
    lactate = CellVariable(mesh=mesh, value=initial_value)
    
    # Apply boundary conditions (all boundaries = boundary_value)
    lactate.constrain(boundary_value, mesh.exteriorFaces)
    
    print(f"✅ Created 3D mesh with {mesh.numberOfCells} cells")
    print(f"✅ Applied boundary conditions: {boundary_value} mM on all faces")
    
    # Calculate biological cell grid (same logic as OpenCellComms)
    bio_nx = int(domain_size / cell_height)  # 500μm / 5μm = 100
    bio_ny = int(domain_size / cell_height)  # 500μm / 5μm = 100  
    bio_nz = int(domain_size / cell_height)  # 500μm / 5μm = 100
    
    print(f"📐 Biological cell grid: {bio_nx} × {bio_ny} × {bio_nz}")
    
    # Place cells using EXACT same logic as OpenCellComms
    center_x, center_y, center_z = bio_nx // 2, bio_ny // 2, bio_nz // 2
    print(f"📐 Biological center: ({center_x}, {center_y}, {center_z})")
    
    # Place cells in expanding spherical pattern (same as OpenCellComms)
    used_positions = set()
    cell_positions = []
    radius = 1
    cells_placed = 0
    max_radius = min(bio_nx, bio_ny, bio_nz) // 2
    
    print(f"🔍 Placing {initial_cell_count} cells in spherical pattern...")
    
    while cells_placed < initial_cell_count and radius < max_radius:
        # 3D spherical placement (exact OpenCellComms logic)
        for x in range(max(0, center_x - radius), min(bio_nx, center_x + radius + 1)):
            for y in range(max(0, center_y - radius), min(bio_ny, center_y + radius + 1)):
                for z in range(max(0, center_z - radius), min(bio_nz, center_z + radius + 1)):
                    if cells_placed >= initial_cell_count:
                        break
                    
                    # Check if position is within spherical distance
                    distance = ((x - center_x)**2 + (y - center_y)**2 + (z - center_z)**2)**0.5
                    if distance <= radius:
                        position = (x, y, z)
                        if position not in used_positions:
                            used_positions.add(position)
                            cell_positions.append(position)
                            cells_placed += 1
                if cells_placed >= initial_cell_count:
                    break
            if cells_placed >= initial_cell_count:
                break
        radius += 1
    
    print(f"✅ Placed {len(cell_positions)} cells in {radius-1} radius sphere")
    
    # Create source field with EXACT same reaction rate as OpenCellComms
    source_field = np.zeros(nx * ny * nz)
    
    # Calculate mesh cell volume (same as OpenCellComms)
    mesh_cell_volume = dx * dy * dz  # m³ (true 3D volume)
    
    print(f"📐 Mesh cell volume: {mesh_cell_volume:.2e} m³")
    
    # EXACT same lactate production rate as OpenCellComms custom functions
    standalone_rate_mol_per_s = +8.24e-20  # mol/s/cell (PRODUCTION - positive)
    
    print(f"🧪 Lactate production rate: {standalone_rate_mol_per_s:.2e} mol/s/cell")
    
    # Convert biological cell positions to FiPy mesh indices and add reactions
    cells_mapped = 0
    for bio_x, bio_y, bio_z in cell_positions:
        # Convert biological coordinates to physical coordinates (meters)
        x_meters = bio_x * cell_height
        y_meters = bio_y * cell_height  
        z_meters = bio_z * cell_height
        
        # Convert physical coordinates to FiPy grid indices
        x = int(x_meters / dx)
        y = int(y_meters / dy)
        z = int(z_meters / dz)
        
        # Check bounds
        if 0 <= x < nx and 0 <= y < ny and 0 <= z < nz:
            # Convert to FiPy index for 3D (column-major order)
            fipy_idx = x * ny * nz + y * nz + z
            
            # Add reaction rate (convert from mol/s/cell to mM/s)
            # mol/s/cell → mM/s: divide by mesh_volume and multiply by 1000
            rate_mM_per_s = standalone_rate_mol_per_s / mesh_cell_volume * 1000
            source_field[fipy_idx] += rate_mM_per_s
            cells_mapped += 1
    
    print(f"✅ Mapped {cells_mapped}/{len(cell_positions)} cells to FiPy mesh")
    
    # Check source field statistics
    non_zero_count = np.count_nonzero(source_field)
    if non_zero_count > 0:
        print(f"🔍 Source field: {non_zero_count} non-zero terms, range: {np.min(source_field):.2e} to {np.max(source_field):.2e} mM/s")
    else:
        print("⚠️  Source field: All zeros!")
        return
    
    # Create FiPy source variable
    source_var = CellVariable(mesh=mesh, value=source_field)
    
    # Create equation: DiffusionTerm(D) == -source_var (same as OpenCellComms)
    equation = DiffusionTerm(coeff=diffusion_coeff) == -source_var
    
    print("\n🚀 Solving steady-state diffusion equation...")
    
    # Solve using same solver as OpenCellComms
    solver = Solver(iterations=1000, tolerance=1e-6)
    
    try:
        res = equation.solve(var=lactate, solver=solver)
        if res is not None:
            print(f"✅ FiPy solver finished. Final residual: {res:.2e}")
        else:
            print(f"✅ FiPy solver finished.")
    except Exception as e:
        print(f"💥 Error during solve: {e}")
        return
    
    # Analyze results
    final_min = float(np.min(lactate.value))
    final_max = float(np.max(lactate.value))
    final_mean = float(np.mean(lactate.value))
    
    print(f"\n📊 RESULTS:")
    print(f"Final lactate - Min: {final_min:.6f}, Max: {final_max:.6f}, Mean: {final_mean:.6f} mM")
    
    # Check center vs edge concentrations
    center_fipy_x = nx // 2
    center_fipy_y = ny // 2
    center_fipy_z = nz // 2
    center_idx = center_fipy_x * ny * nz + center_fipy_y * nz + center_fipy_z
    edge_idx = 0  # Corner
    
    center_conc = float(lactate.value[center_idx])
    edge_conc = float(lactate.value[edge_idx])
    
    print(f"Center concentration: {center_conc:.6f} mM")
    print(f"Edge concentration: {edge_conc:.6f} mM")
    print(f"Gradient magnitude: {abs(center_conc - edge_conc):.6f} mM")
    
    # Save 2D slice for visualization (middle Z plane)
    middle_z = nz // 2
    slice_data = np.zeros((nx, ny))
    
    for x in range(nx):
        for y in range(ny):
            idx = x * ny * nz + y * nz + middle_z
            slice_data[x, y] = lactate.value[idx]
    
    # Plot middle slice
    plt.figure(figsize=(10, 8))
    plt.imshow(slice_data.T, origin='lower', cmap='viridis', aspect='equal')
    plt.colorbar(label='Lactate Concentration (mM)')
    plt.title(f'3D Standalone FiPy - Lactate (Z={middle_z} slice)\n'
              f'Domain: {domain_size*1e6:.0f}×{domain_size*1e6:.0f}×{domain_size*1e6:.0f} μm, '
              f'Grid: {nx}×{ny}×{nz}, Cells: {len(cell_positions)}')
    plt.xlabel('X Grid Index')
    plt.ylabel('Y Grid Index')
    
    # Mark cell positions on the slice
    cell_x_coords = []
    cell_y_coords = []
    for bio_x, bio_y, bio_z in cell_positions:
        # Convert to FiPy coordinates
        x_meters = bio_x * cell_height
        y_meters = bio_y * cell_height
        z_meters = bio_z * cell_height
        
        x = int(x_meters / dx)
        y = int(y_meters / dy)
        z = int(z_meters / dz)
        
        # Only show cells in the middle slice (±1 for visibility)
        if abs(z - middle_z) <= 1:
            cell_x_coords.append(x)
            cell_y_coords.append(y)
    
    if cell_x_coords:
        plt.scatter(cell_x_coords, cell_y_coords, c='red', s=10, alpha=0.7, label=f'Cells (Z≈{middle_z})')
        plt.legend()
    
    plt.tight_layout()
    plt.savefig('standalone_3D_lactate_slice.png', dpi=150, bbox_inches='tight')
    print(f"✅ Saved plot: standalone_3D_lactate_slice.png")
    
    print(f"\n🎯 3D Standalone FiPy test completed successfully!")
    return lactate, source_field, cell_positions

if __name__ == "__main__":
    main()
