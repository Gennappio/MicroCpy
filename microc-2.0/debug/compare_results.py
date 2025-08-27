#!/usr/bin/env python3
"""
Compare jayatilake experiment results with standalone FiPy results
"""

import json
import numpy as np

def analyze_substance_data():
    """Analyze the substance data from jayatilake experiment"""
    try:
        with open('results/jayatilake_experiment/substance_data.json', 'r') as f:
            data = json.load(f)
        
        print("[CHART] JAYATILAKE EXPERIMENT SUBSTANCE ANALYSIS")
        print("=" * 50)
        
        for substance, values in data.items():
            if substance == 'Lactate':
                print(f"\n {substance}:")
                print(f"   Initial: {values['min'][0]} mM")
                print(f"   Final min: {values['min'][-1]:.6f} mM")
                print(f"   Final max: {values['max'][-1]:.6f} mM")
                print(f"   Final mean: {values['mean'][-1]:.6f} mM")
                
                # Calculate gradient
                gradient = values['max'][-1] - values['min'][-1]
                print(f"   Gradient range: {gradient:.6f} mM")
                
                if gradient > 0.001:
                    print(f"   [+] SIGNIFICANT GRADIENT DETECTED!")
                else:
                    print(f"   [!] No significant gradient")
        
        return data
        
    except Exception as e:
        print(f"[!] Error reading substance data: {e}")
        return None

def compare_with_standalone():
    """Compare with standalone FiPy results"""
    print("\n[CHART] COMPARISON WITH STANDALONE FIPY")
    print("=" * 50)
    
    print(" Standalone FiPy Results:")
    print("   Initial lactate: 1.0 mM")
    print("   Final range: -1.264101 to 0.999730 mM")
    print("   Gradient: ~2.26 mM")
    print("   [+] GRADIENTS DETECTED")
    
    print("\n Jayatilake Experiment Results:")
    data = analyze_substance_data()
    
    if data and 'Lactate' in data:
        jaya_gradient = data['Lactate']['max'][-1] - data['Lactate']['min'][-1]
        print(f"   Gradient: {jaya_gradient:.6f} mM")
        
        if jaya_gradient > 0.001:
            print("   [+] GRADIENTS DETECTED")
            print(f"   [TARGET] SUCCESS: Both simulations produce gradients!")
            print(f"   [GRAPH] Standalone gradient: ~2.26 mM")
            print(f"   [GRAPH] Jayatilake gradient: {jaya_gradient:.6f} mM")
        else:
            print("   [!] No significant gradients")

if __name__ == "__main__":
    compare_with_standalone() 