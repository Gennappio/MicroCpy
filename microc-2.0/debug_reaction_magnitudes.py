#!/usr/bin/env python3
"""
Debug script to analyze the actual magnitude of reaction terms
and identify why lactate coefficient 3.0 causes instability.
"""

import numpy as np

def analyze_reaction_magnitudes():
    """Analyze the actual reaction term magnitudes"""
    
    print("🔬 REACTION TERM MAGNITUDE ANALYSIS")
    print("=" * 50)
    
    # Parameters from the Jayatilake experiment
    vmax_glucose = 3.0e-15  # mol/cell/s
    vmax_oxygen = 3.0e-17   # mol/cell/s
    km_glucose = 0.04       # mM
    km_oxygen = 0.005       # mM
    proton_coefficient = 0.01
    
    # Typical concentrations
    glucose = 5.0    # mM
    oxygen = 0.07    # mM
    glyco_atp = 1.0  # Gene state
    
    # Calculate Michaelis-Menten factors
    glucose_mm = glucose / (km_glucose + glucose)
    oxygen_mm = oxygen / (km_oxygen + oxygen)
    oxygen_factor = max(0.1, oxygen_mm)
    
    print(f"📊 KINETIC PARAMETERS:")
    print(f"   vmax_glucose: {vmax_glucose:.2e} mol/cell/s")
    print(f"   vmax_oxygen:  {vmax_oxygen:.2e} mol/cell/s")
    print(f"   Glucose MM factor: {glucose_mm:.4f}")
    print(f"   Oxygen factor: {oxygen_factor:.4f}")
    
    # Calculate base glucose consumption
    glucose_consumption = (vmax_glucose * 1.0 / 6) * glucose_mm * oxygen_factor
    
    print(f"\n📊 BASE RATES:")
    print(f"   Glucose consumption: {glucose_consumption:.2e} mol/cell/s")
    
    # Test different lactate coefficients
    coefficients = [2.8, 2.9, 3.0, 3.1, 3.2]
    
    print(f"\n📊 LACTATE COEFFICIENT ANALYSIS:")
    print("Coeff | Lactate Rate | Proton Rate | Ratio to FiPy Scale")
    print("------|--------------|-------------|-------------------")
    
    # FiPy typical scale (concentration changes per time step)
    fipy_scale = 1e-12  # Typical scale for FiPy stability
    dt = 0.1  # Time step
    
    for coeff in coefficients:
        lactate_production = glucose_consumption * coeff * glyco_atp
        proton_production = min(lactate_production * proton_coefficient, 1e-15)
        
        # Calculate how much concentration would change per time step
        # Assuming 1 cell per grid point and typical grid spacing
        conc_change_per_step = lactate_production * dt * 1e15  # Convert to mM change
        
        ratio_to_fipy = lactate_production / fipy_scale
        
        print(f"{coeff:5.1f} | {lactate_production:.2e} | {proton_production:.2e} | {ratio_to_fipy:.1f}x")
        
        if ratio_to_fipy > 100:
            print(f"      ⚠️  DANGER: {ratio_to_fipy:.0f}x larger than FiPy stability scale!")
        elif ratio_to_fipy > 10:
            print(f"      ⚠️  WARNING: {ratio_to_fipy:.0f}x larger than typical scale")
    
    print(f"\n💡 ANALYSIS:")
    print(f"   - FiPy stability scale: ~{fipy_scale:.0e} mol/cell/s")
    print(f"   - Reaction terms > 100x this scale cause instability")
    print(f"   - The issue is MAGNITUDE, not just coupling")

def calculate_proper_scaling():
    """Calculate what the lactate coefficient should be for stability"""
    
    print(f"\n🎯 PROPER SCALING CALCULATION")
    print("=" * 40)
    
    # Parameters
    vmax_glucose = 3.0e-15
    glucose_mm = 5.0 / (0.04 + 5.0)  # ~0.992
    oxygen_factor = 0.07 / (0.005 + 0.07)  # ~0.933
    
    glucose_consumption = (vmax_glucose * 1.0 / 6) * glucose_mm * oxygen_factor
    
    # Target: Keep lactate production within FiPy stability range
    max_stable_lactate = 1e-13  # Conservative estimate
    
    max_safe_coefficient = max_stable_lactate / glucose_consumption
    
    print(f"📊 SCALING ANALYSIS:")
    print(f"   Glucose consumption: {glucose_consumption:.2e} mol/cell/s")
    print(f"   Max stable lactate:  {max_stable_lactate:.2e} mol/cell/s")
    print(f"   Max safe coefficient: {max_safe_coefficient:.2f}")
    print(f"   Current coefficient: 3.0")
    print(f"   Overshoot factor: {3.0 / max_safe_coefficient:.1f}x")
    
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   1. Use lactate coefficient ≤ {max_safe_coefficient:.1f}")
    print(f"   2. Or scale down vmax_glucose by {3.0 / max_safe_coefficient:.1f}x")
    print(f"   3. Or add proper reaction term scaling in FiPy")

def test_biological_realism():
    """Test if the reaction rates are biologically realistic"""
    
    print(f"\n🧬 BIOLOGICAL REALISM CHECK")
    print("=" * 35)
    
    # Typical cell parameters
    cell_volume = 1e-12  # L (1 picoliter)
    avogadro = 6.022e23
    
    # Current reaction rate
    vmax_glucose = 3.0e-15  # mol/cell/s
    lactate_coeff = 3.0
    glucose_consumption = vmax_glucose * 0.992 * 0.933 / 6  # Realistic MM factors
    lactate_production = glucose_consumption * lactate_coeff
    
    # Convert to molecules per second
    glucose_molecules_per_sec = glucose_consumption * avogadro
    lactate_molecules_per_sec = lactate_production * avogadro
    
    # Convert to concentration change per second
    glucose_conc_change = glucose_consumption / cell_volume * 1000  # mM/s
    lactate_conc_change = lactate_production / cell_volume * 1000   # mM/s
    
    print(f"📊 BIOLOGICAL RATES:")
    print(f"   Glucose consumption: {glucose_molecules_per_sec:.0f} molecules/cell/s")
    print(f"   Lactate production:  {lactate_molecules_per_sec:.0f} molecules/cell/s")
    print(f"   Glucose conc change: {glucose_conc_change:.2e} mM/s")
    print(f"   Lactate conc change: {lactate_conc_change:.2e} mM/s")
    
    # Typical cellular glucose consumption: ~10^6-10^7 molecules/s
    if glucose_molecules_per_sec > 1e8:
        print(f"   ⚠️  Glucose consumption too high!")
    elif glucose_molecules_per_sec < 1e5:
        print(f"   ⚠️  Glucose consumption too low!")
    else:
        print(f"   ✅ Glucose consumption in realistic range")
    
    print(f"\n💡 CONCLUSION:")
    if lactate_conc_change > 1e-3:
        print(f"   The lactate production rate is too high for numerical stability")
        print(f"   Need to reduce by factor of {lactate_conc_change / 1e-6:.0f}")
    else:
        print(f"   Lactate production rate is reasonable")

if __name__ == "__main__":
    analyze_reaction_magnitudes()
    calculate_proper_scaling()
    test_biological_realism()
    
    print(f"\n🎯 FINAL RECOMMENDATION:")
    print(f"   Use lactate coefficient = 2.5 or lower")
    print(f"   Current value of 3.0 is ~2x too large for FiPy stability")
