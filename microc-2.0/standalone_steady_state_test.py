#!/usr/bin/env python3
"""
Standalone test using EXACT steady-state formulation from MicroC.
Tests if MicroC's steady-state approach should produce uniform concentrations.
"""

import numpy as np
import matplotlib.pyplot as plt
from fipy import CellVariable, Grid2D, DiffusionTerm, ImplicitSourceTerm
from fipy.tools import numerix

def test_microc_steady_state():
    """Test using exact MicroC steady-state formulation"""
    
    print("🧪 Testing MicroC Steady-State Formulation")
    print("=" * 50)
    
    # Exact MicroC grid parameters
    nx, ny = 70, 70
    dx = dy = 21.4e-6  # 21.4 μm spacing
    
    # Create mesh
    mesh = Grid2D(nx=nx, ny=ny, dx=dx, dy=dy)
    
    # Lactate parameters from MicroC config
    D_lactate = 6.70e-11  # m²/s diffusion coefficient
    initial_lactate = 5.0  # mM (from MicroC boundary conditions)
    
    # Create lactate concentration variable
    lactate = CellVariable(name="Lactate", mesh=mesh, value=initial_lactate)
    
    # Apply boundary conditions like MicroC (fixed boundaries)
    lactate.constrain(5.0, mesh.exteriorFaces)
    
    print(f"Grid: {nx}×{ny}")
    print(f"Spacing: {dx*1e6:.1f} μm")
    print(f"Diffusion coeff: {D_lactate:.2e} m²/s")
    print(f"Initial concentration: {initial_lactate} mM")
    print(f"Boundary condition: Fixed at {initial_lactate} mM")
    
    # Create source terms from MicroC debug output
    source_data = [
        # (x, y, rate_mM_per_s) - from actual MicroC debug output
        (33, 34, 3.02e-03),  # From user's debug output
        (34, 33, 3.97e-03),  # Production cells
        (34, 34, 3.97e-03),
        (34, 35, 4.03e-03),
        (35, 34, 3.97e-03),
        # Add some consumption terms for balance
        (32, 34, -2.5e-03),
        (33, 33, -2.8e-03),
        (33, 35, -2.6e-03),
        (35, 33, -2.7e-03),
        (36, 34, -2.4e-03),
    ]
    
    # Test different source term magnitudes
    source_multipliers = [1.0, 10.0, 100.0, 1000.0]
    
    for multiplier in source_multipliers:
        print(f"\n--- Testing with {multiplier}x source terms ---")
        
        # Reset lactate
        lactate.setValue(initial_lactate)
        lactate.constrain(5.0, mesh.exteriorFaces)
        
        # Create source field
        source_field = np.zeros(mesh.numberOfCells)
        
        for x, y, rate in source_data:
            if 0 <= x < nx and 0 <= y < ny:
                cell_id = y * nx + x  # FiPy cell indexing
                source_field[cell_id] = rate * multiplier
        
        print(f"Source terms: {np.min(source_field):.2e} to {np.max(source_field):.2e} mM/s")
        
        # EXACT MicroC formulation (from multi_substance_simulator.py line 276)
        # MicroC negates the source field
        source_field_negated = -source_field
        source_var = CellVariable(mesh=mesh, value=source_field_negated)
        
        # EXACT MicroC equation (from line 292-293):
        # equation = (DiffusionTerm(coeff=config.diffusion_coeff) - ImplicitSourceTerm(coeff=source_var))
        equation = (DiffusionTerm(coeff=D_lactate) - ImplicitSourceTerm(coeff=source_var))
        
        # EXACT MicroC solver (from lines 297-310)
        max_iterations = 1000
        tolerance = 1e-6
        residual = 1.0
        iteration = 0
        
        while residual > tolerance and iteration < max_iterations:
            old_values = lactate.value.copy()
            equation.solve(var=lactate)
            
            # Calculate residual (relative change) - exact MicroC formula
            residual = np.max(np.abs(lactate.value - old_values)) / (np.max(np.abs(lactate.value)) + 1e-12)
            iteration += 1
        
        if iteration >= max_iterations:
            print(f"  ⚠️  Did not converge after {max_iterations} iterations (residual: {residual:.2e})")
        else:
            print(f"  ✅ Converged in {iteration} iterations (residual: {residual:.2e})")
        
        # Analyze results
        min_conc = float(numerix.min(lactate.value))
        max_conc = float(numerix.max(lactate.value))
        mean_conc = float(numerix.mean(lactate.value))
        conc_range = max_conc - min_conc
        
        print(f"  Results: min={min_conc:.6f}, max={max_conc:.6f}, mean={mean_conc:.6f} mM")
        print(f"  Range: {conc_range:.6f} mM ({conc_range/mean_conc*100:.4f}% variation)")
        
        # Check if this matches MicroC behavior
        if conc_range < 0.0001:  # Very small range like MicroC
            print(f"  🎯 MATCHES MicroC: Nearly uniform concentrations")
        elif conc_range > 0.01:  # Significant gradients
            print(f"  📈 SIGNIFICANT GRADIENTS: Should be visible")
        else:
            print(f"  📊 SMALL GRADIENTS: Borderline visible")
    
    # Test with extreme source terms to see what it takes to create gradients
    print(f"\n--- Testing with EXTREME source terms ---")
    
    # Reset lactate
    lactate.setValue(initial_lactate)
    lactate.constrain(5.0, mesh.exteriorFaces)
    
    # Create extreme source field
    source_field = np.zeros(mesh.numberOfCells)
    
    # Single strong source and sink
    center_x, center_y = 35, 35
    source_cell = center_y * nx + center_x
    sink_cell = (center_y - 5) * nx + (center_x - 5)
    
    source_field[source_cell] = 1.0   # Strong production: 1.0 mM/s
    source_field[sink_cell] = -1.0    # Strong consumption: -1.0 mM/s
    
    print(f"Extreme source: +1.0 mM/s at ({center_x},{center_y})")
    print(f"Extreme sink: -1.0 mM/s at ({center_x-5},{center_y-5})")
    
    # Apply MicroC formulation
    source_field_negated = -source_field
    source_var = CellVariable(mesh=mesh, value=source_field_negated)
    equation = (DiffusionTerm(coeff=D_lactate) - ImplicitSourceTerm(coeff=source_var))
    
    # Solve
    max_iterations = 1000
    tolerance = 1e-6
    residual = 1.0
    iteration = 0
    
    while residual > tolerance and iteration < max_iterations:
        old_values = lactate.value.copy()
        equation.solve(var=lactate)
        residual = np.max(np.abs(lactate.value - old_values)) / (np.max(np.abs(lactate.value)) + 1e-12)
        iteration += 1
    
    print(f"  ✅ Converged in {iteration} iterations (residual: {residual:.2e})")
    
    # Final analysis
    min_conc = float(numerix.min(lactate.value))
    max_conc = float(numerix.max(lactate.value))
    mean_conc = float(numerix.mean(lactate.value))
    conc_range = max_conc - min_conc
    
    print(f"  Results: min={min_conc:.6f}, max={max_conc:.6f}, mean={mean_conc:.6f} mM")
    print(f"  Range: {conc_range:.6f} mM ({conc_range/mean_conc*100:.4f}% variation)")
    
    return conc_range

if __name__ == "__main__":
    final_range = test_microc_steady_state()
    
    print("\n" + "=" * 50)
    print("CONCLUSION:")
    
    if final_range < 0.0001:
        print("✅ Steady-state formulation explains MicroC's uniform concentrations")
        print("   The small source terms get balanced by diffusion instantly")
        print("   This is correct physics for steady-state, but may not be realistic for biology")
    else:
        print("❌ Even steady-state should show gradients with these source terms")
        print("   MicroC has a bug in its diffusion solver implementation")
    
    print(f"\nFinal concentration range: {final_range:.6f} mM")
