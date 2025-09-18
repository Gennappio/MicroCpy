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
    initial_lactate = 1.0  # mM (converted from config: 1.0 mM)
    
    # Create lactate concentration variable
    lactate = CellVariable(name="Lactate", mesh=mesh, value=initial_lactate)
    
    # Create source term field (initialize to zero)
    source_field = CellVariable(mesh=mesh, value=0.0)
    
    # Add source terms from MicroC debug output
    # These are the actual values being passed to FiPy
    source_data = [
        # (x, y, rate_mM_per_s)
        (33, 34, 3.02e-03),  # From the debug output
        (34, 33, 3.97e-03),  # Example from previous runs
        (34, 34, 3.97e-03),
        (34, 35, 4.03e-03),
        (35, 34, 3.97e-03),
        # Add some consumption terms (negative values)
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
    
    # Diffusion equation: ∂C/∂t = D∇²C + S
    eq = TransientTerm() == DiffusionTerm(coeff=D_lactate) + source_field
    
    # Store results
    times = []
    min_vals = []
    max_vals = []
    mean_vals = []
    
    # Initial state
    times.append(0)
    min_vals.append(float(lactate.min()))
    max_vals.append(float(lactate.max()))
    mean_vals.append(float(lactate.mean()))
    
    print(f"\nTime evolution:")
    print(f"t=0.0s: min={lactate.min():.6f}, max={lactate.max():.6f}, mean={lactate.mean():.6f} mM")
    
    # Time stepping
    for step in range(steps):
        eq.solve(var=lactate, dt=dt)
        
        current_time = (step + 1) * dt
        times.append(current_time)
        min_vals.append(float(lactate.min()))
        max_vals.append(float(lactate.max()))
        mean_vals.append(float(lactate.mean()))
        
        # Print progress every few steps
        if (step + 1) % 10 == 0 or step < 5:
            print(f"t={current_time:.1f}s: min={lactate.min():.6f}, max={lactate.max():.6f}, mean={lactate.mean():.6f} mM")
    
    # Final analysis
    final_range = lactate.max() - lactate.min()
    print(f"\nFinal results:")
    print(f"  Concentration range: {final_range:.6f} mM")
    print(f"  Relative variation: {final_range/lactate.mean()*100:.4f}%")
    
    if final_range > 0.01:  # 0.01 mM threshold
        print("  ✅ Significant gradients developed")
    else:
        print("  ❌ No significant gradients (source terms too weak)")
    
    # Create plots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # Plot 1: Final concentration field
    X, Y = mesh.faceCenters
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
    
    final_range = test_lactate_diffusion()
    
    print("\n" + "=" * 50)
    if final_range > 0.01:
        print("✅ CONCLUSION: Source terms should create visible gradients")
        print("   The problem is likely in MicroC's diffusion solver implementation")
    else:
        print("❌ CONCLUSION: Source terms are too weak to create visible gradients")
        print("   Need to check if metabolism rates are realistic")
