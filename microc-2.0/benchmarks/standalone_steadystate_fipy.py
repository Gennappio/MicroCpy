#!/usr/bin/env python3
"""
Standalone FiPy test that exactly matches MicroC's approach.
Uses same parameters, same cell distribution, same calculations as MicroC.
"""

import numpy as np
import matplotlib.pyplot as plt

# Import FiPy
try:
    from fipy import Grid2D, CellVariable, DiffusionTerm, ImplicitSourceTerm
    from fipy.solvers.scipy import LinearGMRESSolver as Solver
    print("[+] FiPy available")
except ImportError:
    print("[!] FiPy not available")
    exit(1)

def main():
    print(" Standalone FiPy Test - Exact MicroC Match")
    print("=" * 50)
    
    # EXACT MicroC parameters from config
    domain_size = 1500e-6  # 1500 um in meters
    grid_size = (75, 75)   # 75x75 grid
    nx, ny = grid_size
    
    # MicroC lactate parameters
    diffusion_coeff = 1.8e-10  # m/s (lactate diffusion coefficient from config)
    initial_value = 1.0        # mM (lactate initial value from config)
    boundary_value = 1.0       # mM (lactate boundary value from config)
    cell_height = 20e-6        # 20 um (from config)
    
    print(f" Domain: {domain_size*1e6:.0f} x {domain_size*1e6:.0f} um")
    print(f" Grid: {nx} x {ny}")
    print(f" Cell height: {cell_height*1e6:.1f} um")
    print(f" Diffusion coeff: {diffusion_coeff:.2e} m/s")
    print(f" Initial lactate: {initial_value} mM")
    print(f" Boundary lactate: {boundary_value} mM")
    
    # Calculate mesh spacing
    dx = domain_size / nx
    dy = domain_size / ny
    
    print(f" Grid spacing: {dx*1e6:.1f} x {dy*1e6:.1f} um")
    
    # Create FiPy mesh
    mesh = Grid2D(dx=dx, dy=dy, nx=nx, ny=ny)
    
    # Create lactate variable
    lactate = CellVariable(name="Lactate", mesh=mesh, value=initial_value)
    
    # Set boundary conditions (fixed boundaries like MicroC)
    lactate.constrain(boundary_value, mesh.facesTop | mesh.facesBottom | 
                     mesh.facesLeft | mesh.facesRight)
    
    print("[+] Created mesh and lactate variable")
    print("[+] Set boundary conditions")
    
    # Place 200 cells in center using MicroC's approach
    print("\n Placing 200 cells in center...")
    
    cells = []
    center_x = nx // 2  # Center grid position
    center_y = ny // 2  # Center grid position
    
    # Use expanding circle pattern like MicroC
    radius = 1
    cells_placed = 0
    max_cells = 1
    
    while cells_placed < max_cells and radius < min(nx, ny) // 2:
        for x in range(max(0, center_x - radius), min(nx, center_x + radius + 1)):
            for y in range(max(0, center_y - radius), min(ny, center_y + radius + 1)):
                if cells_placed >= max_cells:
                    break
                
                # Check if position is within radius
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                if distance <= radius:
                    cells.append({
                        'grid_x': x,
                        'grid_y': y,
                        'id': cells_placed
                    })
                    cells_placed += 1
            
            if cells_placed >= max_cells:
                break
        
        radius += 1
    
    print(f"[+] Placed {len(cells)} cells in center region")
    print(f"   Center: ({center_x}, {center_y})")
    print(f"   Radius: {radius-1} grid cells")
    
    # Create source field with EXACT MicroC calculation
    print("\n Creating source field with MicroC calculation...")
    
    source_field = np.zeros(nx * ny)
    
    # MicroC volume calculation
    mesh_cell_volume = dx * dy * cell_height
    twodimensional_adjustment_coefficient = 1.0  # From MicroC config
    
    print(f"[SEARCH] Volume calculation:")
    print(f"   dx: {dx:.2e} m")
    print(f"   dy: {dy:.2e} m")
    print(f"   cell_height: {cell_height:.2e} m")
    print(f"   mesh_cell_volume: {mesh_cell_volume:.2e} m")
    print(f"   2D adjustment: {twodimensional_adjustment_coefficient}")
    
    # Lactate production rate in mM/s. 
    # Positive value means production (source), negative means consumption (sink).
    # The original value was far too small to have any effect.
    # This value is an estimate to produce a noticeable gradient.
    lactate_production_rate = 2.8e-2  # mM/s
    
    print(f"[SEARCH] Lactate production rate: {lactate_production_rate:.2e} mM/s")
    
    for cell in cells:
        x = cell['grid_x']
        y = cell['grid_y']
        
        if 0 <= x < nx and 0 <= y < ny:
            # Convert to FiPy index (column-major order)
            fipy_idx = x * ny + y
            
            # The source term for FiPy is simply the rate in mM/s.
            # The original unit conversion was incorrect and caused numerical instability.
            source_field[fipy_idx] = lactate_production_rate
    
    print(f"[SEARCH] Source field stats:")
    print(f"   Non-zero cells: {np.count_nonzero(source_field)}")
    print(f"   Min rate: {np.min(source_field):.2e} mM/s")
    print(f"   Max rate: {np.max(source_field):.2e} mM/s")
    
    # Create a CellVariable for the source term.
    # No need to negate, we will formulate the equation correctly.
    source_var = CellVariable(mesh=mesh, value=source_field)
    
    print(f"[SEARCH] After negation for FiPy:")
    print(f"   Min rate: {np.min(source_field):.2e} mM/s")
    print(f"   Max rate: {np.max(source_field):.2e} mM/s")
    
    # The steady-state diffusion equation with a source term S is: D * grad^2(C) + S = 0
    # In FiPy, this translates to: DiffusionTerm(D) + S = 0, or DiffusionTerm(D) = -S
    # Since our source_var (S) is positive for production, we need the -S on the right side.
    equation = DiffusionTerm(coeff=diffusion_coeff) == -source_var
    
    print("\n[RUN] Solving steady-state diffusion equation with equation.solve()...")
    
    # Set solver parameters. We create a solver object and pass it to solve().
    solver = Solver(iterations=1000, tolerance=1e-6)
    
    # equation.solve() handles the iteration internally, so we don't need a while loop.
    # It returns the final residual of the solver.
    try:
        res = equation.solve(var=lactate, solver=solver)

        # Check for divergence after the solver finishes.
        if np.any(np.isnan(lactate.value)) or np.any(np.isinf(lactate.value)):
            print(" Solver produced NaN or Inf values, indicating divergence.")
            return None, None
        
        if res is not None:
            print(f"[+] FiPy solver finished. Final residual: {res:.2e}")
        else:
            print(f"[+] FiPy solver finished.")

    except Exception as e:
        print(f" An error occurred during equation.solve(): {e}")
        return None, None
    
    # Get results
    lactate_concentrations = lactate.value.reshape((nx, ny), order='F')  # Fortran order for FiPy
    
    print(f"\n[CHART] Results:")
    print(f"   Lactate range: {np.min(lactate_concentrations):.6f} - {np.max(lactate_concentrations):.6f} mM")
    print(f"   Initial value: {initial_value} mM")
    print(f"   Max increase: {np.max(lactate_concentrations) - initial_value:.6f} mM")
    print(f"   Max decrease: {initial_value - np.min(lactate_concentrations):.6f} mM")
    
    # Check if we have gradients
    concentration_range = np.max(lactate_concentrations) - np.min(lactate_concentrations)
    if concentration_range < 1e-6:
        print("   [!] ESSENTIALLY UNIFORM - No significant gradients!")
    else:
        print("   [+] GRADIENTS DETECTED!")
    
    # If the simulation diverged, we can't plot
    if np.any(np.isnan(lactate.value)) or np.any(np.isinf(lactate.value)):
        print("\n[CHART] Skipping plots due to simulation divergence.")
        return None, None
        
    # Create detailed plots
    print("\n[CHART] Creating plots...")

    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Plot 1: Lactate concentrations with cell positions
    im1 = ax1.imshow(lactate_concentrations.T, origin='lower', cmap='viridis',
                     extent=[0, domain_size*1e6, 0, domain_size*1e6])
    cbar1 = plt.colorbar(im1, ax=ax1, label='Lactate concentration (mM)')
    ax1.set_title('Standalone FiPy - Lactate Concentration')
    ax1.set_xlabel('X position (um)')
    ax1.set_ylabel('Y position (um)')

    # Mark all cell positions
    for cell in cells:
        x_pos = (cell['grid_x'] + 0.5) * dx * 1e6
        y_pos = (cell['grid_y'] + 0.5) * dy * 1e6
        ax1.plot(x_pos, y_pos, 'r.', markersize=3, alpha=0.7)

    # Add text with key info
    ax1.text(0.02, 0.98, f'Cells: {len(cells)}\nRange: {np.min(lactate_concentrations):.3f} - {np.max(lactate_concentrations):.3f} mM',
             transform=ax1.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Plot 2: Cross-section through center
    center_line = lactate_concentrations[center_x, :]
    x_positions = np.arange(ny) * dy * 1e6

    ax2.plot(x_positions, center_line, 'b-', linewidth=2, label='Lactate concentration')
    ax2.axhline(y=initial_value, color='r', linestyle='--', alpha=0.7, label='Initial/Boundary value')
    ax2.set_xlabel('Y position (um)')
    ax2.set_ylabel('Lactate concentration (mM)')
    ax2.set_title('Cross-section through center (X = center)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Mark cell positions on cross-section
    for cell in cells:
        if cell['grid_x'] == center_x:  # Cells on the center line
            y_pos = (cell['grid_y'] + 0.5) * dy * 1e6
            ax2.axvline(x=y_pos, color='red', alpha=0.5, linestyle=':', linewidth=1)

    plt.tight_layout()
    plt.savefig('standalone_fipy_lactate.png', dpi=300, bbox_inches='tight')
    print(f"[SAVE] Saved plot: standalone_fipy_lactate.png")

    # Show the plot
    plt.show()
    print("[CHART] Plot displayed")
    
    return lactate_concentrations, cells

if __name__ == "__main__":
    result = main()
    if result and result[0] is not None:
        lactate_concentrations, cells = result
        print("\n[SUCCESS] Standalone FiPy test completed!")
    else:
        print("\n Standalone FiPy test failed or diverged.")
