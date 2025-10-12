#!/usr/bin/env python3
"""
Debug script to test lactate consumption vs production
"""

import json
import numpy as np

def test_lactate_values():
    """Test what lactate values we're actually getting"""
    
    print("[SEARCH] LACTATE DEBUG ANALYSIS")
    print("=" * 50)
    
    # Check substance data
    try:
        with open('results/jayatilake_experiment/substance_data.json', 'r') as f:
            data = json.load(f)
        
        print("[CHART] Substance Data Analysis:")
        for substance, values in data.items():
            if substance in ['Lactate', 'Glucose']:
                print(f"\n {substance}:")
                print(f"   Initial: {values['min'][0]} mM")
                print(f"   Final min: {values['min'][-1]:.6f} mM")
                print(f"   Final max: {values['max'][-1]:.6f} mM")
                print(f"   Final mean: {values['mean'][-1]:.6f} mM")
                
                # Calculate gradient
                gradient = values['max'][-1] - values['min'][-1]
                print(f"   Gradient range: {gradient:.6f} mM")
                
                # Check if this matches expected behavior
                if substance == 'Lactate':
                    expected_initial = 1.0
                    if abs(values['min'][0] - expected_initial) < 0.1:
                        print(f"   [+] Initial value correct ({expected_initial} mM)")
                    else:
                        print(f"   [!] Initial value wrong: expected {expected_initial}, got {values['min'][0]}")
                        
                    # Check if we see consumption (decreasing from center)
                    if values['min'][-1] < values['max'][-1]:
                        print(f"   [DECLINE] Pattern suggests consumption (min < max)")
                    else:
                        print(f"   [GRAPH] Pattern suggests production (min > max)")
                        
    except Exception as e:
        print(f"[!] Error reading substance data: {e}")
    
    print("\n[TARGET] EXPECTED BEHAVIOR:")
    print("   Standalone FiPy shows lactate CONSUMPTION:")
    print("   - Initial: 1.0 mM")
    print("   - Final range: -1.26 to 0.999 mM")
    print("   - Pattern: Cells consume lactate (negative values)")
    print("   - Gradient: High at edges, low in cell region")

if __name__ == "__main__":
    test_lactate_values() 