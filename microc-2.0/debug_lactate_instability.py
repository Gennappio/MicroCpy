#!/usr/bin/env python3
"""
Debug script to investigate lactate production instability.

This script tests why changing lactate production coefficient from 2.8 to 2.9
causes simulation instability.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any

def simulate_lactate_dynamics(lactate_coeff: float, num_steps: int = 100, dt: float = 0.1,
                             include_diffusion: bool = False, cell_density: float = 1.0):
    """
    Simulate lactate production/consumption dynamics with different coefficients.

    Args:
        lactate_coeff: Coefficient for lactate production (2.8 vs 2.9)
        num_steps: Number of simulation steps
        dt: Time step size
        include_diffusion: Include diffusion effects
        cell_density: Number of cells per unit volume

    Returns:
        Dictionary with time series data
    """

    # Initial conditions (typical values from Jayatilake experiment)
    glucose = 5.0  # mM
    lactate = 1.0  # mM
    oxygen = 0.07  # mM
    
    # Kinetic parameters (from the custom functions)
    km_glucose = 0.04  # mM
    km_lactate = 0.04  # mM
    km_oxygen = 0.005  # mM
    vmax_glucose = 3.0e-15  # mol/cell/s
    vmax_oxygen = 3.0e-17  # mol/cell/s
    
    # Gene states (assume glycolytic cell)
    glyco_atp = 1.0
    mito_atp = 0.0
    
    # Storage for results
    time_points = []
    glucose_vals = []
    lactate_vals = []
    oxygen_vals = []
    glucose_consumption_vals = []
    lactate_production_vals = []
    
    print(f"🧪 Testing lactate coefficient: {lactate_coeff}")
    print(f"   Initial: Glucose={glucose:.3f}, Lactate={lactate:.3f}, Oxygen={oxygen:.3f}")
    
    for step in range(num_steps):
        time = step * dt
        
        # Calculate Michaelis-Menten factors
        glucose_mm_factor = glucose / (km_glucose + glucose) if (km_glucose + glucose) > 0 else 0
        oxygen_mm_factor = oxygen / (km_oxygen + oxygen) if (km_oxygen + oxygen) > 0 else 0
        
        # Glycolysis pathway (from the custom function)
        oxygen_factor_for_glycolysis = max(0.1, oxygen_mm_factor)
        glucose_consumption_glyco = (vmax_glucose * 1.0 / 6) * glucose_mm_factor * oxygen_factor_for_glycolysis
        
        # Lactate production with the test coefficient
        lactate_production = glucose_consumption_glyco * lactate_coeff * glyco_atp
        
        # Baseline lactate production if glucose is low
        if glucose < 0.1 and glyco_atp > 0:
            baseline_lactate = vmax_oxygen * 0.1 * glyco_atp
            lactate_production = max(lactate_production, baseline_lactate)
        
        # Small oxygen consumption from glycolysis
        oxygen_consumption = vmax_glucose * 0.5 * oxygen_factor_for_glycolysis
        
        # Update concentrations (simple Euler integration)
        # Scale by cell density to simulate multiple cells
        glucose -= glucose_consumption_glyco * dt * 1e15 * cell_density
        lactate += lactate_production * dt * 1e15 * cell_density
        oxygen -= oxygen_consumption * dt * 1e15 * cell_density

        # Include diffusion effects (simple decay towards boundary values)
        if include_diffusion:
            diffusion_rate = 0.1  # Simple diffusion coefficient
            glucose += (5.0 - glucose) * diffusion_rate * dt  # Boundary glucose = 5.0
            lactate += (0.0 - lactate) * diffusion_rate * dt  # Boundary lactate = 0.0
            oxygen += (0.07 - oxygen) * diffusion_rate * dt  # Boundary oxygen = 0.07
        
        # Prevent negative concentrations
        glucose = max(0, glucose)
        lactate = max(0, lactate)
        oxygen = max(0, oxygen)
        
        # Store results
        time_points.append(time)
        glucose_vals.append(glucose)
        lactate_vals.append(lactate)
        oxygen_vals.append(oxygen)
        glucose_consumption_vals.append(glucose_consumption_glyco)
        lactate_production_vals.append(lactate_production)
        
        # Check for instability
        if lactate > 1000 or np.isnan(lactate) or np.isinf(lactate):
            print(f"   ⚠️  INSTABILITY at step {step}: Lactate={lactate:.3f}")
            break
        
        # Print progress every 10 steps
        if step % 10 == 0:
            print(f"   Step {step:3d}: Glucose={glucose:.3f}, Lactate={lactate:.3f}, Production={lactate_production:.2e}")
    
    return {
        'time': time_points,
        'glucose': glucose_vals,
        'lactate': lactate_vals,
        'oxygen': oxygen_vals,
        'glucose_consumption': glucose_consumption_vals,
        'lactate_production': lactate_production_vals,
        'final_lactate': lactate_vals[-1] if lactate_vals else 0,
        'max_lactate': max(lactate_vals) if lactate_vals else 0,
        'stable': lactate < 100 and not np.isnan(lactate)
    }

def compare_coefficients():
    """Compare lactate dynamics with different coefficients"""

    coefficients = [2.7, 2.8, 2.85, 2.9, 2.95, 3.0]

    print("🔬 LACTATE COEFFICIENT STABILITY ANALYSIS")
    print("=" * 60)

    # Test different scenarios
    scenarios = [
        ("Single Cell", {"cell_density": 1.0, "include_diffusion": False}),
        ("High Density", {"cell_density": 10.0, "include_diffusion": False}),
        ("With Diffusion", {"cell_density": 1.0, "include_diffusion": True}),
        ("High Density + Diffusion", {"cell_density": 10.0, "include_diffusion": True}),
    ]

    all_results = {}

    for scenario_name, params in scenarios:
        print(f"\n🧪 SCENARIO: {scenario_name}")
        print("-" * 40)

        results = {}
        for coeff in coefficients:
            results[coeff] = simulate_lactate_dynamics(coeff, num_steps=50, **params)

        all_results[scenario_name] = results

        # Summary table for this scenario
        print(f"\n📊 {scenario_name} SUMMARY:")
        print("Coeff  | Final Lactate | Max Lactate | Stable")
        print("-------|---------------|-------------|-------")
        for coeff in coefficients:
            r = results[coeff]
            stable_str = "✅ YES" if r['stable'] else "❌ NO"
            print(f"{coeff:5.2f} | {r['final_lactate']:11.3f} | {r['max_lactate']:9.3f} | {stable_str}")

    return all_results

def plot_comparison(results: Dict[float, Dict]):
    """Plot comparison of different coefficients"""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    colors = ['blue', 'green', 'orange', 'red', 'purple', 'brown']
    
    for i, (coeff, data) in enumerate(results.items()):
        color = colors[i % len(colors)]
        label = f"Coeff = {coeff}"
        
        # Plot lactate concentration
        ax1.plot(data['time'], data['lactate'], color=color, label=label, linewidth=2)
        
        # Plot glucose concentration
        ax2.plot(data['time'], data['glucose'], color=color, label=label, linewidth=2)
        
        # Plot lactate production rate
        ax3.plot(data['time'], data['lactate_production'], color=color, label=label, linewidth=2)
        
        # Plot glucose consumption rate
        ax4.plot(data['time'], data['glucose_consumption'], color=color, label=label, linewidth=2)
    
    ax1.set_title('Lactate Concentration')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Lactate (mM)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')
    
    ax2.set_title('Glucose Concentration')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Glucose (mM)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    ax3.set_title('Lactate Production Rate')
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Production Rate (mol/cell/s)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_yscale('log')
    
    ax4.set_title('Glucose Consumption Rate')
    ax4.set_xlabel('Time')
    ax4.set_ylabel('Consumption Rate (mol/cell/s)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_yscale('log')
    
    plt.suptitle('Lactate Production Coefficient Stability Analysis', fontsize=16)
    plt.tight_layout()
    plt.savefig('lactate_stability_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    # Run the analysis
    all_results = compare_coefficients()

    # Create plots for the single cell scenario
    if "Single Cell" in all_results:
        plot_comparison(all_results["Single Cell"])

    print(f"\n💡 ANALYSIS COMPLETE")
    print(f"   Plot saved as: lactate_stability_analysis.png")
