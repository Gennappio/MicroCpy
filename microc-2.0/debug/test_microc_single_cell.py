#!/usr/bin/env python3
"""
Minimal MicroC test with single cell and hardcoded values.
Matches standalone_steadystate_fipy.py exactly for debugging.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import FiPy
try:
    from fipy import Grid2D, CellVariable, DiffusionTerm, ImplicitSourceTerm
    from fipy.solvers.scipy import LinearGMRESSolver as Solver
    print("[+] FiPy available")
except ImportError:
    print("[!] FiPy not available")
    exit(1)

def test_microc_single_cell():
    """Test MicroC diffusion with single cell and hardcoded values"""
    print(" MicroC Single Cell Test - Matching Standalone FiPy")
    print("=" * 60)
    
    # EXACT same parameters as standalone script
    domain_size = 1500e-6  # 1500 um in meters
    grid_size = (75, 75)   # 75x75 grid
    nx, ny = grid_size
    
    # MicroC lactate parameters (from config files)
    diffusion_coeff = 6.70e-11  # m/s (lactate diffusion coefficient from config)
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
    
    # STEP 1: Start with single cell in center
    print("\n Placing 1 cell in center...")
    
    cells = []
    center_x = nx // 2  # Center grid position
    center_y = ny // 2  # Center grid position
    
    # Single cell at center
    cells.append({
        'grid_x': center_x,
        'grid_y': center_y,
        'id': 0
    })
    
    print(f"[+] Placed {len(cells)} cell at center ({center_x}, {center_y})")
    
    # STEP 2: Use hardcoded reaction rate (mol/s/cell) from MicroC custom_functions.py
    print("\n Using hardcoded reaction rate from MicroC...")
    
    # From custom_functions.py: 'lactate_production_rate': 0.8e-17 (mol/s/cell)
    reaction_rate_mol_per_cell = 0.8e-17  # mol/s/cell (positive = production)
    
    print(f"[SEARCH] Reaction rate: {reaction_rate_mol_per_cell:.2e} mol/s/cell")
    
    # STEP 3: Apply MicroC's exact unit conversion logic
    print("\n[TOOL] Applying MicroC's unit conversion logic...")
    
    source_field = np.zeros(nx * ny)
    
    # MicroC volume calculation (from MultiSubstanceSimulator._create_source_field_from_reactions)
    mesh_cell_volume = dx * dy  # m (area only, as per actual MicroC code)
    twodimensional_adjustment_coefficient = 1.0  # From MicroC config
    
    print(f"[SEARCH] Volume calculation:")
    print(f"   dx: {dx:.2e} m")
    print(f"   dy: {dy:.2e} m")
    print(f"   cell_height: {cell_height:.2e} m (NOT USED in volume calculation)")
    print(f"   mesh_cell_volume: {mesh_cell_volume:.2e} m")
    print(f"   2D adjustment: {twodimensional_adjustment_coefficient}")
    
    for cell in cells:
        x = cell['grid_x']
        y = cell['grid_y']
        
        if 0 <= x < nx and 0 <= y < ny:
            # Convert to FiPy index (column-major order)
            fipy_idx = x * ny + y
            
            # EXACT MicroC calculation from _create_source_field_from_reactions
            # Convert mol/s/cell to mol/(ms) by dividing by mesh cell volume
            volumetric_rate = reaction_rate_mol_per_cell / mesh_cell_volume * twodimensional_adjustment_coefficient
            
            # Convert to mM/s for FiPy (1 mol/m = 1000 mM)
            final_rate = volumetric_rate * 1000.0
            
            source_field[fipy_idx] = final_rate
    
    print(f"[SEARCH] Source field stats:")
    print(f"   Non-zero cells: {np.count_nonzero(source_field)}")
    print(f"   Min rate: {np.min(source_field):.2e} mM/s")
    print(f"   Max rate: {np.max(source_field):.2e} mM/s")
    
    # STEP 4: Apply MicroC's negation logic
    print("\n Applying MicroC's source field negation...")
    
    # CRITICAL: MicroC negates the source field for FiPy
    # From MultiSubstanceSimulator.update(): source_field = -source_field
    source_field = -source_field
    
    print(f"[SEARCH] After negation:")
    print(f"   Min rate: {np.min(source_field):.2e} mM/s")
    print(f"   Max rate: {np.max(source_field):.2e} mM/s")
    
    # Create FiPy source variable
    source_var = CellVariable(mesh=mesh, value=source_field)
    
    # STEP 5: Use MicroC's exact equation formulation
    print("\n Using MicroC's equation formulation...")
    
    # From MultiSubstanceSimulator.update():
    # equation = (DiffusionTerm(coeff=config.diffusion_coeff) - ImplicitSourceTerm(coeff=source_var))
    equation = (DiffusionTerm(coeff=diffusion_coeff) - ImplicitSourceTerm(coeff=source_var))
    
    print("[RUN] Solving steady-state diffusion equation with MicroC's solver...")
    
    # Use MicroC's solver parameters
    solver = Solver(iterations=1000, tolerance=1e-6)
    
    # Solve using MicroC's approach
    try:
        res = equation.solve(var=lactate, solver=solver)
        
        # Check for divergence
        if np.any(np.isnan(lactate.value)) or np.any(np.isinf(lactate.value)):
            print(" Solver produced NaN or Inf values, indicating divergence.")
            return None, None
        
        if res is not None:
            print(f"[+] MicroC solver finished. Final residual: {res:.2e}")
        else:
            print(f"[+] MicroC solver finished.")
            
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
    
    # Create plots
    print("\n[CHART] Creating plots...")
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Lactate concentrations with cell positions
    im1 = ax1.imshow(lactate_concentrations.T, origin='lower', cmap='viridis',
                     extent=[0, domain_size*1e6, 0, domain_size*1e6])
    cbar1 = plt.colorbar(im1, ax=ax1, label='Lactate concentration (mM)')
    ax1.set_title('MicroC Single Cell - Lactate Concentration')
    ax1.set_xlabel('X position (um)')
    ax1.set_ylabel('Y position (um)')
    
    # Mark cell position
    for cell in cells:
        x_pos = (cell['grid_x'] + 0.5) * dx * 1e6
        y_pos = (cell['grid_y'] + 0.5) * dy * 1e6
        ax1.plot(x_pos, y_pos, 'r.', markersize=10, alpha=0.8)
    
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
    
    # Mark cell position on cross-section
    for cell in cells:
        if cell['grid_x'] == center_x:  # Cell on the center line
            y_pos = (cell['grid_y'] + 0.5) * dy * 1e6
            ax2.axvline(x=y_pos, color='red', alpha=0.8, linestyle=':', linewidth=2)
    
    plt.tight_layout()
    plt.savefig('microc_single_cell_lactate.png', dpi=300, bbox_inches='tight')
    print(f"[SAVE] Saved plot: microc_single_cell_lactate.png")
    
    # Show the plot
    plt.show()
    print("[CHART] Plot displayed")
    
    return lactate_concentrations, cells

def test_microc_200_cells():
    """Test MicroC diffusion with 200 cells (next step)"""
    print("\n" + "=" * 60)
    print(" MicroC 200 Cells Test")
    print("=" * 60)
    
    # EXACT same parameters as standalone script
    domain_size = 1500e-6  # 1500 um in meters
    grid_size = (75, 75)   # 75x75 grid
    nx, ny = grid_size
    
    # MicroC lactate parameters (from config files)
    diffusion_coeff = 6.70e-11  # m/s (lactate diffusion coefficient from config)
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
    
    # STEP 1: Place 200 cells in center using expanding circle pattern
    print("\n Placing 200 cells in center...")
    
    cells = []
    center_x = nx // 2  # Center grid position
    center_y = ny // 2  # Center grid position
    
    # Use expanding circle pattern like standalone script
    radius = 1
    cells_placed = 0
    max_cells = 200
    
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
    
    # STEP 2: Use hardcoded reaction rate (mol/s/cell) from MicroC custom_functions.py
    print("\n Using hardcoded reaction rate from MicroC...")
    
    # From custom_functions.py: 'lactate_production_rate': 0.8e-17 (mol/s/cell)
    reaction_rate_mol_per_cell = 0.8e-17  # mol/s/cell (positive = production)
    
    print(f"[SEARCH] Reaction rate: {reaction_rate_mol_per_cell:.2e} mol/s/cell")
    
    # STEP 3: Apply MicroC's exact unit conversion logic (FIXED VERSION)
    print("\n[TOOL] Applying MicroC's unit conversion logic (FIXED)...")
    
    source_field = np.zeros(nx * ny)
    
    # MicroC volume calculation (FIXED: include cell_height)
    mesh_cell_volume = dx * dy * cell_height  # m (area x height for 3D)
    twodimensional_adjustment_coefficient = 1.0  # From MicroC config
    
    print(f"[SEARCH] Volume calculation:")
    print(f"   dx: {dx:.2e} m")
    print(f"   dy: {dy:.2e} m")
    print(f"   cell_height: {cell_height:.2e} m")
    print(f"   mesh_cell_volume: {mesh_cell_volume:.2e} m")
    print(f"   2D adjustment: {twodimensional_adjustment_coefficient}")
    
    for cell in cells:
        x = cell['grid_x']
        y = cell['grid_y']
        
        if 0 <= x < nx and 0 <= y < ny:
            # Convert to FiPy index (column-major order)
            fipy_idx = x * ny + y
            
            # EXACT MicroC calculation from _create_source_field_from_reactions (FIXED)
            # Convert mol/s/cell to mol/(ms) by dividing by mesh cell volume
            volumetric_rate = reaction_rate_mol_per_cell / mesh_cell_volume * twodimensional_adjustment_coefficient
            
            # Convert to mM/s for FiPy (1 mol/m = 1000 mM)
            final_rate = volumetric_rate * 1000.0
            
            source_field[fipy_idx] = final_rate
    
    print(f"[SEARCH] Source field stats:")
    print(f"   Non-zero cells: {np.count_nonzero(source_field)}")
    print(f"   Min rate: {np.min(source_field):.2e} mM/s")
    print(f"   Max rate: {np.max(source_field):.2e} mM/s")
    
    # STEP 4: Apply MicroC's negation logic
    print("\n Applying MicroC's source field negation...")
    
    # CRITICAL: MicroC negates the source field for FiPy
    # From MultiSubstanceSimulator.update(): source_field = -source_field
    source_field = -source_field
    
    print(f"[SEARCH] After negation:")
    print(f"   Min rate: {np.min(source_field):.2e} mM/s")
    print(f"   Max rate: {np.max(source_field):.2e} mM/s")
    
    # Create FiPy source variable
    source_var = CellVariable(mesh=mesh, value=source_field)
    
    # STEP 5: Use MicroC's exact equation formulation
    print("\n Using MicroC's equation formulation...")
    
    # From MultiSubstanceSimulator.update():
    # equation = (DiffusionTerm(coeff=config.diffusion_coeff) - ImplicitSourceTerm(coeff=source_var))
    equation = (DiffusionTerm(coeff=diffusion_coeff) - ImplicitSourceTerm(coeff=source_var))
    
    print("[RUN] Solving steady-state diffusion equation with MicroC's solver...")
    
    # Use MicroC's solver parameters
    solver = Solver(iterations=1000, tolerance=1e-6)
    
    # Solve using MicroC's approach
    try:
        res = equation.solve(var=lactate, solver=solver)
        
        # Check for divergence
        if np.any(np.isnan(lactate.value)) or np.any(np.isinf(lactate.value)):
            print(" Solver produced NaN or Inf values, indicating divergence.")
            return None, None
        
        if res is not None:
            print(f"[+] MicroC solver finished. Final residual: {res:.2e}")
        else:
            print(f"[+] MicroC solver finished.")
            
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
    
    # Create plots
    print("\n[CHART] Creating plots...")
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Lactate concentrations with cell positions
    im1 = ax1.imshow(lactate_concentrations.T, origin='lower', cmap='viridis',
                     extent=[0, domain_size*1e6, 0, domain_size*1e6])
    cbar1 = plt.colorbar(im1, ax=ax1, label='Lactate concentration (mM)')
    ax1.set_title('MicroC 200 Cells - Lactate Concentration')
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
    plt.savefig('microc_200_cells_lactate.png', dpi=300, bbox_inches='tight')
    print(f"[SAVE] Saved plot: microc_200_cells_lactate.png")
    
    # Show the plot
    plt.show()
    print("[CHART] Plot displayed")
    
    return lactate_concentrations, cells

def test_microc_1000_cells():
    """Test MicroC diffusion with 1000 cells (next step)"""
    print("\n" + "=" * 60)
    print(" MicroC 1000 Cells Test")
    print("=" * 60)
    
    # TODO: Implement 1000 cells test
    print("[TOOL] TODO: Implement 1000 cells test")
    return None, None

if __name__ == "__main__":
    print(" MicroC Diffusion Debugging Test")
    print("=" * 60)
    print("This test matches standalone_steadystate_fipy.py exactly")
    print("to identify differences in the MicroC implementation.")
    print()
    
    # Test 1: Single cell
    print(" TEST 1: Single Cell")
    result1 = test_microc_single_cell()
    if result1 and result1[0] is not None:
        lactate_concentrations, cells = result1
        print("\n[+] Single cell test completed successfully!")
        
        # Compare with standalone results
        print("\n[CHART] Comparison with standalone script:")
        print("   If results match, MicroC implementation is correct.")
        print("   If results differ, we need to investigate further.")
        
        # TODO: Add actual comparison logic
    else:
        print("\n[!] Single cell test failed!")
    
    # Test 2: 200 cells
    print("\n TEST 2: 200 Cells")
    result2 = test_microc_200_cells()
    if result2 and result2[0] is not None:
        lactate_concentrations, cells = result2
        print("\n[+] 200 cells test completed successfully!")
        
        # Compare with standalone results
        print("\n[CHART] Comparison with standalone script:")
        print("   If results match, MicroC implementation is correct.")
        print("   If results differ, we need to investigate further.")
        
        # TODO: Add actual comparison logic
    else:
        print("\n[!] 200 cells test failed!")
    
    # TODO: Uncomment when ready to test more cells
    # test_microc_1000_cells()
    
    print("\n[SUCCESS] MicroC debugging test completed!") 