#!/usr/bin/env python3
"""
Debug script to investigate FiPy reaction term instability.

This script tests the actual reaction terms being passed to FiPy
and checks for numerical instability.
"""

import sys
import os
sys.path.append('src')

import numpy as np
from typing import Dict, Any, List
import importlib.util

def load_custom_functions():
    """Load the Jayatilake custom functions"""
    spec = importlib.util.spec_from_file_location(
        "jayatilake_custom_functions", 
        "tests/jayatilake_experiment/jayatilake_experiment_custom_functions.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_reaction_terms(lactate_coeff: float = 2.9):
    """Test reaction terms with different lactate coefficients"""
    
    print(f"🧪 Testing reaction terms with lactate coefficient: {lactate_coeff}")
    
    # Load custom functions
    custom_funcs = load_custom_functions()
    
    # Create a mock cell state
    cell_state = {
        'atp_rate': 0.0,
        'metabolic_state': {}
    }
    
    # Create a mock cell object
    class MockCell:
        def __init__(self):
            self.state = type('obj', (object,), {
                'gene_states': {
                    'glycoATP': 1.0,
                    'mitoATP': 0.0,
                    'Apoptosis': False,
                    'Necrosis': False
                },
                'metabolic_state': {}
            })()
    
    cell = MockCell()
    
    # Test different environmental conditions
    test_conditions = [
        {
            'name': 'Normal',
            'environment': {
                'Oxygen': 0.07, 'Glucose': 5.0, 'Lactate': 1.0, 'H': 1e-7,
                'TGFA': 4e-5, 'HGF': 0.0, 'FGF': 0.0, 'GI': 0.0,
                'EGFRD': 0.0, 'FGFRD': 0.0, 'cMETD': 0.0, 'MCT1D': 0.0, 'GLUT1D': 0.0
            }
        },
        {
            'name': 'High Lactate',
            'environment': {
                'Oxygen': 0.07, 'Glucose': 5.0, 'Lactate': 10.0, 'H': 1e-7,
                'TGFA': 4e-5, 'HGF': 0.0, 'FGF': 0.0, 'GI': 0.0,
                'EGFRD': 0.0, 'FGFRD': 0.0, 'cMETD': 0.0, 'MCT1D': 0.0, 'GLUT1D': 0.0
            }
        },
        {
            'name': 'Low Oxygen',
            'environment': {
                'Oxygen': 0.01, 'Glucose': 5.0, 'Lactate': 1.0, 'H': 1e-7,
                'TGFA': 4e-5, 'HGF': 0.0, 'FGF': 0.0, 'GI': 0.0,
                'EGFRD': 0.0, 'FGFRD': 0.0, 'cMETD': 0.0, 'MCT1D': 0.0, 'GLUT1D': 0.0
            }
        },
        {
            'name': 'Low Glucose',
            'environment': {
                'Oxygen': 0.07, 'Glucose': 0.1, 'Lactate': 1.0, 'H': 1e-7,
                'TGFA': 4e-5, 'HGF': 0.0, 'FGF': 0.0, 'GI': 0.0,
                'EGFRD': 0.0, 'FGFRD': 0.0, 'cMETD': 0.0, 'MCT1D': 0.0, 'GLUT1D': 0.0
            }
        }
    ]
    
    print("\n📊 REACTION TERM ANALYSIS:")
    print("Condition    | Glucose | Lactate | Oxygen  | H       | ATP Rate")
    print("-------------|---------|---------|---------|---------|----------")
    
    for condition in test_conditions:
        env = condition['environment']
        name = condition['name']
        
        # Temporarily modify the lactate coefficient in the custom function
        # We'll do this by monkey-patching the function
        original_func = custom_funcs.calculate_metabolism
        
        def modified_metabolism(cell_state, local_environment, gene_states, config=None):
            # Call original function but modify lactate production
            reactions = original_func(cell_state, local_environment, gene_states, config)
            
            # Check if we need to modify lactate production
            if 'Lactate' in reactions:
                # Get the original lactate production
                original_lactate = reactions['Lactate']
                
                # Recalculate with new coefficient
                # This is a simplified version - in reality we'd need to extract the exact calculation
                if original_lactate > 0:  # Only modify production, not consumption
                    # Scale by the ratio of new to old coefficient
                    scale_factor = lactate_coeff / 2.8  # Assuming 2.8 was the original
                    reactions['Lactate'] = original_lactate * scale_factor
            
            return reactions
        
        # Apply the modified function
        custom_funcs.calculate_metabolism = modified_metabolism
        
        try:
            # Calculate reactions
            reactions = custom_funcs.calculate_metabolism(
                cell_state, env, cell.state.gene_states, None
            )
            
            # Extract key reaction terms
            glucose_rate = reactions.get('Glucose', 0.0)
            lactate_rate = reactions.get('Lactate', 0.0)
            oxygen_rate = reactions.get('Oxygen', 0.0)
            h_rate = reactions.get('H', 0.0)
            atp_rate = cell_state.get('atp_rate', 0.0)
            
            print(f"{name:12} | {glucose_rate:7.2e} | {lactate_rate:7.2e} | {oxygen_rate:7.2e} | {h_rate:7.2e} | {atp_rate:8.2e}")
            
            # Check for problematic values
            if abs(lactate_rate) > 1e-12:
                print(f"   ⚠️  Large lactate rate: {lactate_rate:.2e}")
            if any(np.isnan([glucose_rate, lactate_rate, oxygen_rate, h_rate])):
                print(f"   ❌ NaN detected in reactions!")
            if any(np.isinf([glucose_rate, lactate_rate, oxygen_rate, h_rate])):
                print(f"   ❌ Inf detected in reactions!")
                
        except Exception as e:
            print(f"{name:12} | ERROR: {e}")
        
        finally:
            # Restore original function
            custom_funcs.calculate_metabolism = original_func
    
    print("\n💡 ANALYSIS:")
    print("   - Check for reaction terms > 1e-12 (may cause FiPy instability)")
    print("   - Look for NaN or Inf values")
    print("   - Compare lactate production rates between coefficients")

def compare_lactate_coefficients():
    """Compare reaction terms for different lactate coefficients"""
    
    coefficients = [2.8, 2.85, 2.9, 2.95, 3.0]
    
    print(f"\n🔬 LACTATE COEFFICIENT COMPARISON")
    print("=" * 60)
    
    # Standard environment
    environment = {
        'Oxygen': 0.07, 'Glucose': 5.0, 'Lactate': 1.0, 'H': 1e-7,
        'TGFA': 4e-5, 'HGF': 0.0, 'FGF': 0.0, 'GI': 0.0,
        'EGFRD': 0.0, 'FGFRD': 0.0, 'cMETD': 0.0, 'MCT1D': 0.0, 'GLUT1D': 0.0
    }
    
    print("Coeff | Lactate Rate | Glucose Rate | H Rate     | Ratio to 2.8")
    print("------|--------------|--------------|------------|-------------")
    
    baseline_lactate = None
    
    for coeff in coefficients:
        test_reaction_terms(coeff)
        
        # For now, just show the coefficient
        # In a full implementation, we'd extract the actual reaction terms
        print(f"{coeff:5.2f} | {'TBD':>12} | {'TBD':>12} | {'TBD':>10} | {'TBD':>11}")

if __name__ == "__main__":
    print("🔬 FIPY REACTION TERM ANALYSIS")
    print("=" * 50)
    
    # Test with problematic coefficient
    test_reaction_terms(2.9)
    
    # Compare different coefficients
    compare_lactate_coefficients()
    
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   1. Check FiPy solver tolerance settings")
    print(f"   2. Consider scaling reaction terms")
    print(f"   3. Add reaction term bounds checking")
    print(f"   4. Investigate coupling with other substances")
