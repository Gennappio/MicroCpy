#!/usr/bin/env python3
"""
Standalone test to verify lactate diffusion with MicroC parameters.
Tests if the source terms from MicroC should create visible concentration gradients.
"""

import numpy as np
import matplotlib.pyplot as plt
from fipy import CellVariable, Grid2D, TransientTerm, DiffusionTerm, Viewer
from fipy.tools import numerix

def test_lactate_diffusion():
    """Test lactate diffusion with MicroC parameters"""
    
    # MicroC grid parameters
    nx, ny = 70, 70
    dx = dy = 21.4e-6  # 21.4 μm spacing
    
    # Create mesh
    mesh = Grid2D(nx=nx, ny=ny, dx=dx, dy=dy)
    
    # Lactate parameters from MicroC config
    D_lactate = 6.70e-11  # m²/s diffusion coefficient
    initial_lactate = 5.0  # mM (from MicroC: boundary_value: 5.0, but simulation shows 1.0)
    
    # Create lactate concentration variable
    lactate = CellVariable(name="Lactate", mesh=mesh, value=initial_lactate)
    
    # Create source term field (initialize to zero)
    source_field = CellVariable(mesh=mesh, value=0.0)
    
    # Add source terms from MicroC debug output
    # These are the actual values being passed to FiPy
    source_data = [
        # (x, y, rate_mM_per_s) - from actual MicroC debug output
        (33, 34, 3.02e-03),  # From the user's debug output
        (34, 33, 3.97e-03),  # Example from previous runs
        (34, 34, 3.97e-03),
        (34, 35, 4.03e-03),
        (35, 34, 3.97e-03),
        # Add some consumption terms (negative values) for realistic gradients
        (32, 34, -2.5e-03),
        (33, 33, -2.8e-03),
        (33, 35, -2.6e-03),
        (35, 33, -2.7e-03),
        (36, 34, -2.4e-03),
    ]
    
    # Apply source terms to the mesh
    for x, y, rate in source_data:
        if 0 <= x < nx and 0 <= y < ny:
            cell_id = y * nx + x  # FiPy cell indexing
            source_field[cell_id] = rate
            print(f"Applied source term: ({x},{y}) -> cell {cell_id} = {rate:.3e} mM/s")
    
    # Time stepping parameters
    dt = 0.2  # seconds (MicroC uses dt=0.1 with diffusion every 2 steps)
    total_time = 10.0  # seconds
    steps = int(total_time / dt)
    
    print(f"\nSimulation parameters:")
    print(f"  Grid: {nx}×{ny}")
    print(f"  Spacing: {dx*1e6:.1f} μm")
    print(f"  Diffusion coeff: {D_lactate:.2e} m²/s")
    print(f"  Time step: {dt} s")
    print(f"  Total time: {total_time} s")
    print(f"  Steps: {steps}")
    
    # Check stability criterion
    stability_limit = (dx**2) / (2 * D_lactate)
    print(f"  Stability limit: {stability_limit:.2f} s (dt = {dt} s)")
    if dt > stability_limit:
        print("  ⚠️  WARNING: Time step may be too large for stability!")
    else:
        print("  ✅ Time step is stable")
    
    # Test both transient and steady-state
    print(f"\n=== TRANSIENT SOLVER (like standalone) ===")

    # Diffusion equation: ∂C/∂t = D∇²C + S
    eq_transient = TransientTerm() == DiffusionTerm(coeff=D_lactate) + source_field
    
    # Store results
    times = []
    min_vals = []
    max_vals = []
    mean_vals = []
    
    # Initial state
    times.append(0)
    min_vals.append(float(numerix.min(lactate.value)))
    max_vals.append(float(numerix.max(lactate.value)))
    mean_vals.append(float(numerix.mean(lactate.value)))

    print(f"\nTime evolution:")
    print(f"t=0.0s: min={numerix.min(lactate.value):.6f}, max={numerix.max(lactate.value):.6f}, mean={numerix.mean(lactate.value):.6f} mM")
    
    # Time stepping
    for step in range(steps):
        eq_transient.solve(var=lactate, dt=dt)
        
        current_time = (step + 1) * dt
        times.append(current_time)
        min_vals.append(float(numerix.min(lactate.value)))
        max_vals.append(float(numerix.max(lactate.value)))
        mean_vals.append(float(numerix.mean(lactate.value)))

        # Print progress every few steps
        if (step + 1) % 10 == 0 or step < 5:
            print(f"t={current_time:.1f}s: min={numerix.min(lactate.value):.6f}, max={numerix.max(lactate.value):.6f}, mean={numerix.mean(lactate.value):.6f} mM")
    
    # Final analysis for transient
    final_range_transient = numerix.max(lactate.value) - numerix.min(lactate.value)
    print(f"\nTransient results:")
    print(f"  Concentration range: {final_range_transient:.6f} mM")
    print(f"  Relative variation: {final_range_transient/numerix.mean(lactate.value)*100:.4f}%")

    if final_range_transient > 0.01:  # 0.01 mM threshold
        print("  ✅ Significant gradients developed")
    else:
        print("  ❌ No significant gradients (source terms too weak)")

    # Now test STEADY-STATE like MicroC
    print(f"\n=== STEADY-STATE SOLVER (like MicroC) ===")

    # Reset lactate to initial conditions
    lactate_steady = CellVariable(name="Lactate", mesh=mesh, value=initial_lactate)

    # Negate source field like MicroC does (line 276 in multi_substance_simulator.py)
    source_field_negated = -source_field
    source_var = CellVariable(mesh=mesh, value=source_field_negated.value)

    # Steady-state equation like MicroC: 0 = ∇·(D∇C) - R*C
    from fipy import ImplicitSourceTerm
    eq_steady = (DiffusionTerm(coeff=D_lactate) - ImplicitSourceTerm(coeff=source_var))

    # Solve steady-state (like MicroC does)
    max_iterations = 1000
    tolerance = 1e-6
    residual = 1.0
    iteration = 0

    print(f"Solving steady-state with negated source terms...")
    while residual > tolerance and iteration < max_iterations:
        old_values = lactate_steady.value.copy()
        eq_steady.solve(var=lactate_steady)

        # Calculate residual (relative change)
        residual = numerix.max(numerix.abs(lactate_steady.value - old_values)) / (numerix.max(numerix.abs(lactate_steady.value)) + 1e-12)
        iteration += 1

        if iteration % 100 == 0:
            print(f"  Iteration {iteration}: residual = {residual:.2e}")

    print(f"Converged in {iteration} iterations (residual: {residual:.2e})")

    # Final analysis for steady-state
    final_range_steady = numerix.max(lactate_steady.value) - numerix.min(lactate_steady.value)
    print(f"\nSteady-state results:")
    print(f"  Concentration range: {final_range_steady:.6f} mM")
    print(f"  Relative variation: {final_range_steady/numerix.mean(lactate_steady.value)*100:.4f}%")

    if final_range_steady > 0.01:
        print("  ✅ Significant gradients developed")
    else:
        print("  ❌ No significant gradients (source terms too weak)")

    final_range = final_range_steady  # Return steady-state result for comparison
    
    # Create plots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # Plot 1: Final concentration field
    X, Y = mesh.cellCenters
    X = X.reshape((ny, nx)) * 1e6  # Convert to μm
    Y = Y.reshape((ny, nx)) * 1e6
    C = lactate.value.reshape((ny, nx))
    
    im1 = ax1.contourf(X, Y, C, levels=50, cmap='viridis')
    ax1.set_title('Final Lactate Concentration')
    ax1.set_xlabel('X (μm)')
    ax1.set_ylabel('Y (μm)')
    plt.colorbar(im1, ax=ax1, label='Lactate (mM)')
    
    # Mark source locations
    for x, y, rate in source_data:
        color = 'red' if rate > 0 else 'blue'
        ax1.plot(x * dx * 1e6, y * dy * 1e6, 'o', color=color, markersize=4)
    
    # Plot 2: Source field
    S = source_field.value.reshape((ny, nx))
    im2 = ax2.contourf(X, Y, S, levels=50, cmap='RdBu_r')
    ax2.set_title('Source Terms')
    ax2.set_xlabel('X (μm)')
    ax2.set_ylabel('Y (μm)')
    plt.colorbar(im2, ax=ax2, label='Source (mM/s)')
    
    # Plot 3: Time evolution
    ax3.plot(times, min_vals, 'b-', label='Min')
    ax3.plot(times, max_vals, 'r-', label='Max')
    ax3.plot(times, mean_vals, 'g-', label='Mean')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Lactate (mM)')
    ax3.set_title('Concentration Evolution')
    ax3.legend()
    ax3.grid(True)
    
    # Plot 4: Concentration range over time
    ranges = np.array(max_vals) - np.array(min_vals)
    ax4.plot(times, ranges, 'k-', linewidth=2)
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Concentration Range (mM)')
    ax4.set_title('Gradient Development')
    ax4.grid(True)
    
    plt.tight_layout()
    plt.savefig('lactate_diffusion_test.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return final_range

if __name__ == "__main__":
    print("🧪 Standalone Lactate Diffusion Test")
    print("=" * 50)
    
    final_range_transient, final_range_steady = test_lactate_diffusion()

    print("\n" + "=" * 50)

    if final_range_steady > 0.01:
        print("✅ CONCLUSION: Even steady-state should create visible gradients")
        print("   MicroC has a bug in diffusion solver or source term application")
    else:
        print("❌ CONCLUSION: Steady-state explains the small gradients")
        print("   MicroC behavior is correct for steady-state physics")
