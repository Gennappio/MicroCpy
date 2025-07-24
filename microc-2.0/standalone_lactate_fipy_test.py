#!/usr/bin/env python3
"""
Standalone FiPy test to isolate lactate production problem.
Replicates exact same conditions as Jayatilake experiment:
- Same cell distribution
- Same lactate parameters  
- Same grid size (70x70)
- Only glycolysis (OXPHOS disabled)
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict, Any
import sys
import os

# Check if FiPy is available
try:
    from fipy import Grid2D, CellVariable, DiffusionTerm, ImplicitSourceTerm
    FIPY_AVAILABLE = True
    print("✅ FiPy available")
except ImportError:
    FIPY_AVAILABLE = False
    print("❌ FiPy not available - install with: pip install fipy")
    exit(1)

def create_jayatilake_cell_distribution(grid_size: Tuple[int, int], num_cells: int = 200) -> List[Tuple[int, int]]:
    """
    Create the exact same cell distribution as Jayatilake experiment.
    Places cells in center with spheroid configuration.
    """
    nx, ny = grid_size
    cells = []
    
    # Center of the grid
    center_x, center_y = nx // 2, ny // 2
    
    # Spheroid radius (in grid units)
    max_radius = min(nx, ny) // 4  # Quarter of the grid size
    
    # Place cells in spheroid pattern
    placed_cells = 0
    attempts = 0
    max_attempts = num_cells * 10
    
    while placed_cells < num_cells and attempts < max_attempts:
        # Random position within spheroid
        angle = np.random.uniform(0, 2 * np.pi)
        # Bias towards center with r^2 distribution for spheroid
        r = max_radius * np.sqrt(np.random.uniform(0, 1))
        
        x = int(center_x + r * np.cos(angle))
        y = int(center_y + r * np.sin(angle))
        
        # Check bounds
        if 0 <= x < nx and 0 <= y < ny:
            # Avoid duplicates
            if (x, y) not in cells:
                cells.append((x, y))
                placed_cells += 1
        
        attempts += 1
    
    print(f"✅ Placed {len(cells)} cells in spheroid pattern")
    print(f"   Center: ({center_x}, {center_y})")
    print(f"   Radius: {max_radius} grid units")
    
    return cells

def calculate_lactate_production_rate(glucose_conc: float, oxygen_conc: float) -> float:
    """
    Calculate lactate production rate using exact Jayatilake parameters.
    Only glycolysis pathway (OXPHOS disabled).
    """
    
    # Exact parameters from Jayatilake config
    vmax_glucose = 3e-15  # mol/cell/s
    km_glucose = 0.04     # mM
    km_oxygen = 0.005     # mM
    lactate_coeff = 3.0   # The problematic coefficient
    glyco_atp = 1.0       # Gene state (glycolysis active)
    
    # Michaelis-Menten factors
    glucose_mm_factor = glucose_conc / (km_glucose + glucose_conc) if (km_glucose + glucose_conc) > 0 else 0
    oxygen_mm_factor = oxygen_conc / (km_oxygen + oxygen_conc) if (km_oxygen + oxygen_conc) > 0 else 0
    
    # Glycolysis should work even with low oxygen (anaerobic)
    oxygen_factor_for_glycolysis = max(0.1, oxygen_mm_factor)
    
    # Glucose consumption for glycolysis
    glucose_consumption_glyco = (vmax_glucose * 1.0 / 6) * glucose_mm_factor * oxygen_factor_for_glycolysis
    
    # Lactate production from glycolysis
    lactate_production = glucose_consumption_glyco * lactate_coeff * glyco_atp
    
    return lactate_production

def run_standalone_lactate_test(use_microc_source_terms=False):
    """
    Run standalone lactate production test with FiPy.

    Args:
        use_microc_source_terms: If True, use the exact source terms from MicroC debug output
    """
    print("🧪 STANDALONE LACTATE PRODUCTION TEST")
    if use_microc_source_terms:
        print("🔍 USING EXACT MICROC SOURCE TERMS")
    print("=" * 60)
    
    # Exact parameters from Jayatilake experiment
    grid_size = (70, 70)  # Same as current config
    nx, ny = grid_size
    domain_size = 800e-6  # 800 μm in meters
    
    # Lactate parameters - FIXED: Use same initial and boundary
    diffusion_coeff = 1.0e-9  # m²/s (typical for lactate)
    initial_value = 1.0       # mM (same as boundary)
    boundary_value = 1.0      # mM (from config)
    
    # Create FiPy mesh
    dx = domain_size / nx
    dy = domain_size / ny
    
    print(f"📐 Grid: {nx} × {ny}")
    print(f"📐 Domain: {domain_size*1e6:.0f} × {domain_size*1e6:.0f} μm")
    print(f"📐 Cell size: {dx*1e6:.1f} × {dy*1e6:.1f} μm")
    print(f"📐 Cell volume: {(dx*dy)*1e12:.1f} μm³")
    
    from fipy import Grid2D
    mesh = Grid2D(dx=dx, dy=dy, nx=nx, ny=ny)
    
    # Create lactate concentration variable
    lactate = CellVariable(name="Lactate", mesh=mesh, value=initial_value)
    
    # Set boundary conditions (same as Jayatilake)
    lactate.constrain(boundary_value, mesh.facesTop | mesh.facesBottom | 
                     mesh.facesLeft | mesh.facesRight)
    
    # Create cell distribution (same as Jayatilake)
    cells = create_jayatilake_cell_distribution(grid_size, num_cells=200)
    
    # Create source field for lactate production
    source_field = np.zeros(nx * ny)

    if use_microc_source_terms:
        # Use EXACT source terms from MicroC debug output
        print(f"\n🔍 USING EXACT MICROC SOURCE TERMS:")
        print(f"   From debug: 'final_rate (to FiPy): X.XXe-XX mM/s'")

        # These are the exact values from MicroC debug output
        # Format: (x, y, final_rate_mM_per_s)
        microc_source_terms = [
            # Sample of the exact MicroC source terms (first 10 cells)
            (33, 34, 4.03e-03), (34, 33, 4.03e-03), (34, 34, 4.03e-03), (34, 35, 4.03e-03),
            (35, 34, 4.03e-03), (32, 34, 4.03e-03), (33, 33, 4.03e-03), (33, 35, 4.03e-03),
            (34, 32, 4.03e-03), (34, 36, 4.03e-03), (35, 33, 4.03e-03), (35, 35, 4.03e-03),
            (36, 34, 4.03e-03), (31, 34, 4.03e-03), (32, 32, 4.03e-03), (32, 33, 4.03e-03),
            (32, 35, 4.03e-03), (32, 36, 4.03e-03), (33, 32, 4.03e-03), (33, 36, 4.03e-03),
        ]

        # Apply the exact MicroC source terms
        print(f"   Using {len(microc_source_terms)} exact MicroC source terms")
        print(f"   Source term range: {min(term[2] for term in microc_source_terms):.2e} to {max(term[2] for term in microc_source_terms):.2e} mM/s")

        total_production = 0.0
        for x, y, final_rate in microc_source_terms:
            if 0 <= x < nx and 0 <= y < ny:
                fipy_idx = x * ny + y
                source_field[fipy_idx] = final_rate
                # Convert back to mol/s/cell for total calculation
                mesh_cell_volume = dx * dy  # m³
                lactate_rate_per_cell = (final_rate / 1000.0) * mesh_cell_volume
                total_production += lactate_rate_per_cell

                # Debug first few cells
                if len([r for r in source_field if r != 0]) <= 3:
                    print(f"   Cell ({x},{y}): {final_rate:.2e} mM/s")

    else:
        # Original calculation
        # Environmental conditions (same as Jayatilake)
        glucose_conc = 5.0  # mM
        oxygen_conc = 0.07  # mM

        print(f"\n🧬 CELL METABOLISM:")
        print(f"   Glucose: {glucose_conc} mM")
        print(f"   Oxygen: {oxygen_conc} mM")
        print(f"   Lactate coefficient: 4.0")

        # Calculate lactate production for each cell
        total_production = 0.0
        for x, y in cells:
            # Calculate lactate production rate
            lactate_rate = calculate_lactate_production_rate(glucose_conc, oxygen_conc)

            # Convert to FiPy index (Fortran/column-major order)
            fipy_idx = x * ny + y

            # Convert mol/s/cell to volumetric rate (mol/m³/s)
            mesh_cell_volume = dx * dy  # m³
            volumetric_rate = lactate_rate / mesh_cell_volume

            # Convert to mM/s for FiPy
            final_rate = volumetric_rate * 1000.0
            source_field[fipy_idx] = final_rate

            total_production += lactate_rate

            # Debug first few cells
            if len([r for r in source_field if r != 0]) <= 3:
                print(f"   Cell ({x},{y}): {lactate_rate:.2e} mol/s/cell → {final_rate:.2e} mM/s")
    
    print(f"   Total cells: {len(cells)}")
    print(f"   Total production: {total_production:.2e} mol/s")
    print(f"   Average per cell: {total_production/len(cells):.2e} mol/s/cell")
    
    # Create FiPy source variable
    source_var = CellVariable(mesh=mesh, value=-source_field)  # Negative for production
    
    # Create diffusion equation
    equation = DiffusionTerm(coeff=diffusion_coeff) - ImplicitSourceTerm(coeff=source_var)
    
    print(f"\n🚀 Solving steady-state diffusion equation...")
    
    # Solve for steady state
    max_iterations = 1000
    tolerance = 1e-6
    
    residual = 1.0
    iteration = 0
    
    while residual > tolerance and iteration < max_iterations:
        old_values = lactate.value.copy()
        equation.solve(var=lactate)
        
        # Calculate residual
        residual = np.max(np.abs(lactate.value - old_values)) / (np.max(np.abs(lactate.value)) + 1e-12)
        iteration += 1
        
        if iteration % 100 == 0:
            print(f"   Iteration {iteration}: residual = {residual:.2e}")
    
    if iteration >= max_iterations:
        print(f"⚠️  Did not converge after {max_iterations} iterations (residual: {residual:.2e})")
    else:
        print(f"✅ Converged in {iteration} iterations (residual: {residual:.2e})")
    
    # Analyze results
    lactate_2d = np.array(lactate.value).reshape((ny, nx), order='F')
    
    print(f"\n📊 RESULTS ANALYSIS:")
    print(f"   Min lactate: {np.min(lactate_2d):.3f} mM")
    print(f"   Max lactate: {np.max(lactate_2d):.3f} mM")
    print(f"   Mean lactate: {np.mean(lactate_2d):.3f} mM")
    print(f"   Initial value: {initial_value:.3f} mM")
    print(f"   Boundary value: {boundary_value:.3f} mM")
    
    # Check if lactate increased from initial
    if np.max(lactate_2d) > initial_value:
        print(f"✅ LACTATE PRODUCTION DETECTED!")
        print(f"   Increase: {np.max(lactate_2d) - initial_value:.3f} mM")
    else:
        print(f"❌ NO LACTATE PRODUCTION!")
        print(f"   This suggests the problem is in the reaction terms or FiPy setup")
    
    # Create visualization
    plt.figure(figsize=(12, 5))
    
    # Plot lactate concentration
    plt.subplot(1, 2, 1)
    plt.imshow(lactate_2d, origin='lower', cmap='viridis')
    plt.colorbar(label='Lactate (mM)')
    plt.title('Lactate Concentration')
    
    # Mark cell positions
    for x, y in cells[:50]:  # Show first 50 cells
        plt.plot(x, y, 'r.', markersize=2)
    
    # Plot source field
    plt.subplot(1, 2, 2)
    source_2d = source_field.reshape((ny, nx), order='F')
    plt.imshow(source_2d, origin='lower', cmap='Reds')
    plt.colorbar(label='Source Rate (mM/s)')
    plt.title('Lactate Production Rate')
    
    plt.tight_layout()
    plt.savefig('standalone_lactate_test.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return {
        'lactate_field': lactate_2d,
        'source_field': source_2d,
        'cells': cells,
        'converged': iteration < max_iterations,
        'max_lactate': np.max(lactate_2d),
        'production_detected': np.max(lactate_2d) > initial_value
    }

def test_microc_vs_standalone():
    """Compare MicroC source terms vs standalone calculation"""

    print("🔬 MICROC VS STANDALONE COMPARISON")
    print("=" * 60)

    # Test 1: Original standalone calculation
    print("\n📊 TEST 1: ORIGINAL STANDALONE CALCULATION")
    results_original = run_standalone_lactate_test(use_microc_source_terms=False)

    # Test 2: MicroC source terms
    print("\n📊 TEST 2: EXACT MICROC SOURCE TERMS")
    results_microc = run_standalone_lactate_test(use_microc_source_terms=True)

    # Compare results
    print(f"\n📊 COMPARISON:")
    print(f"   Original max lactate: {results_original['max_lactate']:.6f} mM")
    print(f"   MicroC max lactate:   {results_microc['max_lactate']:.6f} mM")
    print(f"   Original production:  {results_original['production_detected']}")
    print(f"   MicroC production:    {results_microc['production_detected']}")

    return results_original, results_microc

if __name__ == "__main__":
    # Test both scenarios
    results_original, results_microc = test_microc_vs_standalone()

    print(f"\n🎯 CONCLUSION:")
    if results_microc['production_detected']:
        print(f"   ✅ MicroC source terms work in standalone FiPy")
        print(f"   ➡️  Problem is in MicroC's FiPy integration or solver settings")
    else:
        print(f"   ❌ MicroC source terms fail even in standalone")
        print(f"   ➡️  Problem is in the source term magnitude")

    if results_original['production_detected'] and not results_microc['production_detected']:
        print(f"   🔍 MicroC source terms are too large for FiPy stability")
    elif not results_original['production_detected'] and results_microc['production_detected']:
        print(f"   🔍 Original calculation was too small")

    print(f"\n💡 NEXT STEPS:")
    print(f"   1. Check FiPy solver settings in MicroC")
    print(f"   2. Verify source term scaling")
    print(f"   3. Test with different solver tolerances")
    print(f"   4. Check for numerical instability patterns")
