#!/usr/bin/env python3
"""
Debug script to find the exact difference between MicroC and standalone test
that causes convergence failure in MicroC but success in standalone.
"""

import numpy as np
from fipy import CellVariable, Grid2D, DiffusionTerm, ImplicitSourceTerm
from fipy.tools import numerix

def test_microc_exact_setup():
    """Test using EXACT MicroC setup step by step"""
    
    print("🔍 DEBUGGING: MicroC vs Standalone Differences")
    print("=" * 60)
    
    # EXACT MicroC parameters
    nx, ny = 70, 70
    dx = dy = 21.4e-6  # 21.4 μm spacing
    D_lactate = 6.70e-11  # m²/s diffusion coefficient
    initial_lactate = 1.0  # mM (MicroC config)
    boundary_lactate = 1.0  # mM (MicroC config)
    
    # Create mesh
    mesh = Grid2D(nx=nx, ny=ny, dx=dx, dy=dy)
    
    print(f"Grid: {nx}×{ny}")
    print(f"Diffusion coeff: {D_lactate:.2e} m²/s")
    print(f"Initial/boundary: {initial_lactate} mM")
    
    # Test 1: Standalone method (known to work)
    print(f"\n--- TEST 1: Standalone Method (Working) ---")
    
    lactate1 = CellVariable(name="Lactate", mesh=mesh, value=initial_lactate)
    lactate1.constrain(boundary_lactate, mesh.exteriorFaces)
    
    # Simple source terms
    source_field1 = np.zeros(mesh.numberOfCells)
    source_field1[2344] = 3.02e-03  # Single source term
    source_field1 = -source_field1  # Negate like MicroC
    source_var1 = CellVariable(mesh=mesh, value=source_field1)
    
    equation1 = (DiffusionTerm(coeff=D_lactate) - ImplicitSourceTerm(coeff=source_var1))
    
    # Solve
    max_iterations = 1000
    tolerance = 1e-6
    residual = 1.0
    iteration = 0
    
    while residual > tolerance and iteration < max_iterations:
        old_values = lactate1.value.copy()
        equation1.solve(var=lactate1)
        residual = np.max(np.abs(lactate1.value - old_values)) / (np.max(np.abs(lactate1.value)) + 1e-12)
        iteration += 1
    
    print(f"  Converged: {iteration < max_iterations} in {iteration} iterations (residual: {residual:.2e})")
    print(f"  Range: {numerix.max(lactate1.value) - numerix.min(lactate1.value):.6f} mM")
    
    # Test 2: MicroC method (boundary condition setup)
    print(f"\n--- TEST 2: MicroC Boundary Method ---")
    
    lactate2 = CellVariable(name="Lactate", mesh=mesh, value=initial_lactate)
    # Use MicroC's boundary condition setup
    lactate2.constrain(boundary_lactate, mesh.facesTop | mesh.facesBottom | mesh.facesLeft | mesh.facesRight)
    
    # Same source terms
    source_field2 = np.zeros(mesh.numberOfCells)
    source_field2[2344] = 3.02e-03
    source_field2 = -source_field2
    source_var2 = CellVariable(mesh=mesh, value=source_field2)
    
    equation2 = (DiffusionTerm(coeff=D_lactate) - ImplicitSourceTerm(coeff=source_var2))
    
    # Solve
    residual = 1.0
    iteration = 0
    
    while residual > tolerance and iteration < max_iterations:
        old_values = lactate2.value.copy()
        equation2.solve(var=lactate2)
        residual = np.max(np.abs(lactate2.value - old_values)) / (np.max(np.abs(lactate2.value)) + 1e-12)
        iteration += 1
    
    print(f"  Converged: {iteration < max_iterations} in {iteration} iterations (residual: {residual:.2e})")
    print(f"  Range: {numerix.max(lactate2.value) - numerix.min(lactate2.value):.6f} mM")
    
    # Test 3: Check if multiple source terms cause issues
    print(f"\n--- TEST 3: Multiple Source Terms (Like MicroC) ---")
    
    lactate3 = CellVariable(name="Lactate", mesh=mesh, value=initial_lactate)
    lactate3.constrain(boundary_lactate, mesh.exteriorFaces)
    
    # Multiple source terms like MicroC debug output
    source_field3 = np.zeros(mesh.numberOfCells)
    source_indices = [1854, 1920, 1921, 1922, 1923, 2344, 2413, 2414]
    for idx in source_indices:
        source_field3[idx] = 3.02e-03
    
    source_field3 = -source_field3
    source_var3 = CellVariable(mesh=mesh, value=source_field3)
    
    equation3 = (DiffusionTerm(coeff=D_lactate) - ImplicitSourceTerm(coeff=source_var3))
    
    # Solve
    residual = 1.0
    iteration = 0
    
    while residual > tolerance and iteration < max_iterations:
        old_values = lactate3.value.copy()
        equation3.solve(var=lactate3)
        residual = np.max(np.abs(lactate3.value - old_values)) / (np.max(np.abs(lactate3.value)) + 1e-12)
        iteration += 1
    
    print(f"  Converged: {iteration < max_iterations} in {iteration} iterations (residual: {residual:.2e})")
    print(f"  Range: {numerix.max(lactate3.value) - numerix.min(lactate3.value):.6f} mM")
    
    # Test 4: Check if source term magnitude is the issue
    print(f"\n--- TEST 4: Larger Source Terms ---")
    
    lactate4 = CellVariable(name="Lactate", mesh=mesh, value=initial_lactate)
    lactate4.constrain(boundary_lactate, mesh.exteriorFaces)
    
    # Larger source terms (10x)
    source_field4 = np.zeros(mesh.numberOfCells)
    for idx in source_indices:
        source_field4[idx] = 3.02e-02  # 10x larger
    
    source_field4 = -source_field4
    source_var4 = CellVariable(mesh=mesh, value=source_field4)
    
    equation4 = (DiffusionTerm(coeff=D_lactate) - ImplicitSourceTerm(coeff=source_var4))
    
    # Solve
    residual = 1.0
    iteration = 0
    
    while residual > tolerance and iteration < max_iterations:
        old_values = lactate4.value.copy()
        equation4.solve(var=lactate4)
        residual = np.max(np.abs(lactate4.value - old_values)) / (np.max(np.abs(lactate4.value)) + 1e-12)
        iteration += 1
        
        # Check for instability
        if np.any(np.isnan(lactate4.value)) or np.any(np.isinf(lactate4.value)) or np.max(lactate4.value) > 1e10:
            print(f"  ⚠️  INSTABILITY detected at iteration {iteration}")
            break
    
    print(f"  Converged: {iteration < max_iterations} in {iteration} iterations (residual: {residual:.2e})")
    if iteration < max_iterations:
        print(f"  Range: {numerix.max(lactate4.value) - numerix.min(lactate4.value):.6f} mM")
    else:
        print(f"  Max value: {numerix.max(lactate4.value):.2e} mM (UNSTABLE)")
    
    # Test 5: Check if it's a mesh/indexing issue
    print(f"\n--- TEST 5: Check Mesh Indexing ---")
    
    print(f"  Mesh cells: {mesh.numberOfCells}")
    print(f"  Expected cells: {nx * ny} = {nx * ny}")
    print(f"  Source indices: {source_indices}")
    print(f"  Max valid index: {mesh.numberOfCells - 1}")
    
    # Check if any source indices are out of bounds
    invalid_indices = [idx for idx in source_indices if idx >= mesh.numberOfCells]
    if invalid_indices:
        print(f"  ⚠️  INVALID INDICES: {invalid_indices}")
    else:
        print(f"  ✅ All indices valid")
    
    print(f"\n" + "=" * 60)
    print("SUMMARY:")
    print("  Test 1 (Standalone): Should work")
    print("  Test 2 (MicroC boundaries): Check if boundary setup causes issues")
    print("  Test 3 (Multiple sources): Check if multiple source terms cause issues")
    print("  Test 4 (Large sources): Check instability threshold")
    print("  Test 5 (Indexing): Check for mesh/indexing bugs")

if __name__ == "__main__":
    test_microc_exact_setup()
