#!/usr/bin/env python3
"""
Calculate what the proper oxygen consumption should be in FiPy units
"""

def main():
    print(" CALCULATING PROPER OXYGEN CONSUMPTION")
    print("=" * 50)
    
    # Current hardcoded values
    hardcoded_oxygen = -5.9e-21  # mol/s/cell
    hardcoded_glucose = -7.2e-21  # mol/s/cell
    hardcoded_lactate = +8.24e-20  # mol/s/cell
    
    print(f"[CHART] CURRENT HARDCODED VALUES:")
    print(f"  Oxygen: {hardcoded_oxygen:.2e} mol/s/cell")
    print(f"  Glucose: {hardcoded_glucose:.2e} mol/s/cell") 
    print(f"  Lactate: {hardcoded_lactate:.2e} mol/s/cell")
    
    # Config parameters
    vmax_oxygen = 1.0e-16  # mol/cell/s
    km_oxygen = 0.005      # mM (the_optimal_oxygen)
    local_oxygen = 0.07    # mM
    
    print(f"\n[CHART] CONFIG PARAMETERS:")
    print(f"  vmax_oxygen: {vmax_oxygen:.2e} mol/cell/s")
    print(f"  km_oxygen: {km_oxygen:.3f} mM")
    print(f"  local_oxygen: {local_oxygen:.3f} mM")
    
    # Calculate Michaelis-Menten factor
    oxygen_mm_factor = local_oxygen / (km_oxygen + local_oxygen)
    calculated_oxygen = -vmax_oxygen * oxygen_mm_factor
    
    print(f"\n MICHAELIS-MENTEN CALCULATION:")
    print(f"  MM factor: {local_oxygen:.3f} / ({km_oxygen:.3f} + {local_oxygen:.3f}) = {oxygen_mm_factor:.3f}")
    print(f"  Calculated oxygen: -{vmax_oxygen:.2e} x {oxygen_mm_factor:.3f} = {calculated_oxygen:.2e} mol/s/cell")
    
    # Compare
    ratio = abs(calculated_oxygen / hardcoded_oxygen)
    print(f"\n[GRAPH] COMPARISON:")
    print(f"  Calculated: {calculated_oxygen:.2e} mol/s/cell")
    print(f"  Hardcoded:  {hardcoded_oxygen:.2e} mol/s/cell")
    print(f"  Ratio: {ratio:.0f}x larger")
    
    # Domain parameters for FiPy conversion
    domain_size = 500e-6  # 500 um in meters
    nx, ny = 25, 25
    cell_height = 5.0e-6  # 5 um in meters
    
    # Calculate mesh cell volume
    dx = domain_size / nx
    dy = domain_size / ny
    mesh_cell_volume = dx * dy * cell_height  # m
    
    print(f"\n DOMAIN PARAMETERS:")
    print(f"  Domain: {domain_size*1e6:.0f} um x {domain_size*1e6:.0f} um")
    print(f"  Grid: {nx} x {ny}")
    print(f"  Cell height: {cell_height*1e6:.1f} um")
    print(f"  Grid spacing: {dx*1e6:.1f} um x {dy*1e6:.1f} um")
    print(f"  Mesh cell volume: {mesh_cell_volume:.2e} m")
    
    # Convert to FiPy units
    twodimensional_adjustment_coefficient = 1.0  # From config
    
    # Hardcoded conversion
    volumetric_rate_hardcoded = hardcoded_oxygen / mesh_cell_volume * twodimensional_adjustment_coefficient
    fipy_rate_hardcoded = volumetric_rate_hardcoded * 1000.0  # mM/s
    
    # Calculated conversion
    volumetric_rate_calculated = calculated_oxygen / mesh_cell_volume * twodimensional_adjustment_coefficient
    fipy_rate_calculated = volumetric_rate_calculated * 1000.0  # mM/s
    
    print(f"\n[TOOL] FIPY CONVERSION:")
    print(f"  Hardcoded FiPy rate: {fipy_rate_hardcoded:.2e} mM/s")
    print(f"  Calculated FiPy rate: {fipy_rate_calculated:.2e} mM/s")
    print(f"  FiPy ratio: {abs(fipy_rate_calculated / fipy_rate_hardcoded):.0f}x larger")
    
    # Estimate depletion time
    initial_oxygen = 0.07  # mM
    depletion_time_hardcoded = initial_oxygen / abs(fipy_rate_hardcoded)
    depletion_time_calculated = initial_oxygen / abs(fipy_rate_calculated)
    
    print(f"\n  DEPLETION TIME ESTIMATES:")
    print(f"  With hardcoded rate: {depletion_time_hardcoded:.0f} seconds ({depletion_time_hardcoded/3600:.1f} hours)")
    print(f"  With calculated rate: {depletion_time_calculated:.0f} seconds ({depletion_time_calculated/60:.1f} minutes)")
    
    # Recommendations
    print(f"\n[IDEA] RECOMMENDATIONS:")
    print(f"  1. Remove hardcoded override on line 627")
    print(f"  2. Use calculated Michaelis-Menten kinetics")
    print(f"  3. Expected oxygen gradients with {ratio:.0f}x higher consumption")
    print(f"  4. Depletion time: {depletion_time_calculated/60:.1f} minutes (realistic)")

if __name__ == "__main__":
    main()
