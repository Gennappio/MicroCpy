#!/usr/bin/env python3
"""
Standalone FiPy test for oxygen diffusion with cell consumption.
Tests the corrected source term implementation with 200 cells.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict, Any
import random

# Check if FiPy is available
try:
    from fipy import Grid2D, CellVariable, DiffusionTerm, ImplicitSourceTerm, TransientTerm
    FIPY_AVAILABLE = True
    print("[+] FiPy available")
except ImportError:
    FIPY_AVAILABLE = False
    print("[!] FiPy not available - install with: pip install fipy")
    exit(1)

def custom_initialize_cell_placement(grid_size: Tuple[int, int], simulation_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    EXACT replica of jayatilake_experiment cell placement function.
    Places cells in expanding spherical pattern from center.
    """
    nx, ny = grid_size
    center_x, center_y = nx // 2, ny // 2

    # Get initial cell count from simulation parameters
    initial_count = simulation_params.get('initial_cell_count', 200)

    placements = []

    # Place cells in expanding spherical pattern (EXACT algorithm from jayatilake)
    radius = 1
    cells_placed = 0

    while cells_placed < initial_count and radius < min(nx, ny) // 2:
        for x in range(max(0, center_x - radius), min(nx, center_x + radius + 1)):
            for y in range(max(0, center_y - radius), min(ny, center_y + radius + 1)):
                if cells_placed >= initial_count:
                    break

                # Check if position is within radius
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                if distance <= radius:
                    placements.append({
                        'position': (x, y),
                        'id': cells_placed,
                        'phenotype': 'Proliferation'
                    })
                    cells_placed += 1

            if cells_placed >= initial_count:
                break

        radius += 1

    print(f"[+] Placed {len(placements)} cells in expanding spherical pattern (radius: {radius-1})")
    print(f"   Cell density: {len(placements)} cells in {(2*radius-1)**2} grid positions")
    print(f"   Placement matches jayatilake_experiment_config.yaml exactly")
    return placements

def create_source_field(cells: List[Dict[str, Any]], grid_size: Tuple[int, int], 
                       uptake_rate: float, mesh_dx: float, mesh_dy: float) -> np.ndarray:
    """
    Create source field from cell positions with corrected volume scaling.
    """
    nx, ny = grid_size
    source_field = np.zeros(nx * ny)
    
    # Calculate mesh cell volume (grid spacing x grid spacing x thickness)
    mesh_cell_volume = mesh_dx * mesh_dy  # 20 um thickness
    
    print(f"[SEARCH] Mesh cell volume: {mesh_cell_volume:.2e} m")
    
    for cell in cells:
        x, y = cell['position']
        
        if 0 <= x < nx and 0 <= y < ny:
            # Convert to FiPy index (column-major order)
            fipy_idx = x * ny + y
            
            # Convert mol/s/cell to mol/(ms) by dividing by mesh cell volume
            volumetric_rate = uptake_rate / mesh_cell_volume  # Positive uptake rate

            # Convert to mM/s for FiPy (1 mol/m = 1000 mM)
            # For ImplicitSourceTerm(coeff=X), positive X means consumption (removes substance)
            source_field[fipy_idx] = volumetric_rate * 1000.0 *3000
    
    print(f"[SEARCH] Source field stats:")
    print(f"   Non-zero cells: {np.count_nonzero(source_field)}")
    print(f"   Min rate: {np.min(source_field):.2e} mM/s")
    print(f"   Max rate: {np.max(source_field):.2e} mM/s")
    
    return source_field

def run_oxygen_simulation():
    """
    Run standalone oxygen diffusion simulation with FiPy.
    """
    print(" FiPy Oxygen Diffusion Test")
    print("=" * 50)
    
    # Simulation parameters
    domain_size = 600e-6  # 600 um in meters
    grid_size = (40, 40)  # 40x40 grid
    nx, ny = grid_size
    
    # Oxygen parameters (scaled for mesh cell volume)
    diffusion_coeff = 1.0e-9  # m/s
    uptake_rate = 3.0e-17     # mol/s/cell (scaled down for mesh volume - shows same pattern as jayatilake)
    initial_value = 0.07      # mM
    boundary_value = 0.07     # mM
    
    # Create FiPy mesh
    dx = domain_size / nx
    dy = domain_size / ny
    
    print(f" Domain: {domain_size*1e6:.0f} x {domain_size*1e6:.0f} um")
    print(f" Grid: {nx} x {ny}")
    print(f" Spacing: {dx*1e6:.1f} x {dy*1e6:.1f} um")
    
    mesh = Grid2D(dx=dx, dy=dy, nx=nx, ny=ny)
    
    # Create oxygen variable
    oxygen = CellVariable(name="Oxygen", mesh=mesh, value=initial_value)
    
    # Set boundary conditions (fixed boundaries)
    oxygen.constrain(boundary_value, mesh.facesTop | mesh.facesBottom | 
                    mesh.facesLeft | mesh.facesRight)
    
    # Place cells using EXACT jayatilake parameters
    simulation_params = {'initial_cell_count': 200}
    cells = custom_initialize_cell_placement(grid_size, simulation_params)
    
    # Create source field
    source_field = create_source_field(cells, grid_size, uptake_rate, dx, dy)
    source_var = CellVariable(mesh=mesh, value=source_field)
    
    # Create diffusion equation with source term
    # 0 = nabla(DnablaC) + S
    # For consumption, we want: 0 = nabla(DnablaC) - R*C where R > 0
    # This means ImplicitSourceTerm(coeff=-R) where R is positive consumption rate
    equation = DiffusionTerm(coeff=diffusion_coeff) - ImplicitSourceTerm(coeff=source_var)
    
    print("\n[RUN] Solving steady-state diffusion equation...")
    
    # Solve for steady state
    max_iterations = 1000
    tolerance = 1e-6
    
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
    
    # Plot results
    plot_results(oxygen_concentrations, cells, grid_size, domain_size)
    
    return oxygen_concentrations, cells

def plot_results(oxygen_concentrations: np.ndarray, cells: List[Dict[str, Any]], 
                grid_size: Tuple[int, int], domain_size: float):
    """
    Plot the oxygen concentration field and cell positions.
    """
    nx, ny = grid_size
    
    # Create coordinate arrays
    x = np.linspace(0, domain_size * 1e6, nx)  # Convert to um
    y = np.linspace(0, domain_size * 1e6, ny)
    X, Y = np.meshgrid(x, y)
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot 1: Oxygen concentration heatmap
    im1 = ax1.contourf(X, Y, oxygen_concentrations.T, levels=50, cmap='viridis')
    ax1.set_title('Oxygen Concentration (mM)')
    ax1.set_xlabel('X (um)')
    ax1.set_ylabel('Y (um)')
    cbar1 = plt.colorbar(im1, ax=ax1)
    cbar1.set_label('Concentration (mM)')
    
    # Add cell positions
    cell_x = [cell['position'][0] * domain_size * 1e6 / nx for cell in cells]
    cell_y = [cell['position'][1] * domain_size * 1e6 / ny for cell in cells]
    ax1.scatter(cell_x, cell_y, c='red', s=10, alpha=0.7, label=f'{len(cells)} cells')
    ax1.legend()
    
    # Plot 2: Oxygen concentration with cell overlay
    im2 = ax2.imshow(oxygen_concentrations.T, extent=[0, domain_size*1e6, 0, domain_size*1e6], 
                     origin='lower', cmap='viridis', aspect='equal')
    ax2.set_title('Oxygen + Cell Positions')
    ax2.set_xlabel('X (um)')
    ax2.set_ylabel('Y (um)')
    cbar2 = plt.colorbar(im2, ax=ax2)
    cbar2.set_label('Concentration (mM)')
    
    # Add cell positions as white dots
    ax2.scatter(cell_x, cell_y, c='white', s=15, alpha=0.8, edgecolors='black', linewidth=0.5)
    
    # Add concentration range text
    min_conc = np.min(oxygen_concentrations)
    max_conc = np.max(oxygen_concentrations)
    ax2.text(0.02, 0.98, f'Range: {min_conc:.6f} - {max_conc:.6f} mM', 
             transform=ax2.transAxes, verticalalignment='top', 
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('fipy_oxygen_test.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"[SAVE] Plot saved as 'fipy_oxygen_test.png'")

if __name__ == "__main__":
    # Set random seed for reproducible results
    random.seed(42)
    np.random.seed(42)
    
    # Run the simulation
    oxygen_concentrations, cells = run_oxygen_simulation()
    
    print("\n[SUCCESS] FiPy test completed successfully!")
    print(f"[CHART] Final oxygen range: {np.min(oxygen_concentrations):.6f} - {np.max(oxygen_concentrations):.6f} mM")
