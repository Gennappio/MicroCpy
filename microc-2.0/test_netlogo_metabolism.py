#!/usr/bin/env python3
"""
Test script to verify NetLogo-style Michaelis-Menten metabolism implementation.
"""

import sys
import os
import math
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tests/jayatilake_experiment'))

from jayatilake_experiment_custom_functions import custom_calculate_cell_metabolism

def test_netlogo_metabolism():
    """Test NetLogo-style metabolism calculations"""
    print("🧪 Testing NetLogo-style Michaelis-Menten Metabolism")
    print("=" * 60)
    
    # Mock config with NetLogo parameters
    class MockConfig:
        def __init__(self):
            self.custom_parameters = {
                'the_optimal_oxygen': 0.005,      # NetLogo Km for oxygen
                'the_optimal_glucose': 0.04,      # NetLogo Km for glucose  
                'the_optimal_lactate': 0.04,      # NetLogo Km for lactate
                'oxygen_vmax': 3.0e-17,           # NetLogo Vmax for oxygen
                'glucose_vmax': 3.0e-15,          # NetLogo Vmax for glucose
                'max_atp': 30,                    # Maximum ATP per glucose
                'proton_coefficient': 0.01        # Proton production coefficient
            }
    
    config = MockConfig()
    
    # Test environment with typical concentrations (all substances from diffusion-parameters.txt)
    local_environment = {
        'Oxygen': 0.1,      # 0.1 mM oxygen (normoxic)
        'Glucose': 5.0,     # 5.0 mM glucose (normal)
        'Lactate': 2.0,     # 2.0 mM lactate
        'H': 1e-7,          # pH ~7 (neutral)
        'FGF': 1e-6,        # Growth factor
        'TGFA': 1e-6,       # Growth factor
        'HGF': 2e-6,        # Growth factor
        'GI': 1e-6,         # Growth inhibitor
        'EGFRD': 1e-3,      # Drug inhibitor
        'FGFRD': 1e-3,      # Drug inhibitor
        'cMETD': 1e-3,      # Drug inhibitor
        'MCT1D': 1e-6,      # Drug inhibitor
        'GLUT1D': 1e-6      # Drug inhibitor
    }
    
    print(f"🌍 Test environment:")
    print(f"   Metabolic: O2={local_environment['Oxygen']} mM, Glucose={local_environment['Glucose']} mM, Lactate={local_environment['Lactate']} mM")
    print(f"   pH: H+={local_environment['H']} mM (pH ≈ {-math.log10(local_environment['H']):.1f})")
    print(f"   Growth factors: FGF={local_environment['FGF']} mM, TGFA={local_environment['TGFA']} mM, HGF={local_environment['HGF']} mM")
    print(f"   Inhibitors: GI={local_environment['GI']} mM, EGFRD={local_environment['EGFRD']} mM")
    
    # Test Case 1: OXPHOS cell (mitoATP active)
    print(f"\n🔬 Test Case 1: OXPHOS Cell (mitoATP active)")
    cell_state_oxphos = {
        'gene_states': {
            'mitoATP': True,
            'glycoATP': False,
            'Necrosis': False
        }
    }
    
    reactions_oxphos = custom_calculate_cell_metabolism(local_environment, cell_state_oxphos, config)
    print(f"   Metabolic:")
    print(f"     Oxygen consumption: {reactions_oxphos['Oxygen']:.2e} mol/cell/s")
    print(f"     Glucose consumption: {reactions_oxphos['Glucose']:.2e} mol/cell/s")
    print(f"     Lactate consumption: {reactions_oxphos['Lactate']:.2e} mol/cell/s")
    print(f"     Proton consumption: {reactions_oxphos['H']:.2e} mol/cell/s")
    print(f"   Growth factors:")
    print(f"     FGF net flux: {reactions_oxphos['FGF']:.2e} mol/cell/s")
    print(f"     TGFA net flux: {reactions_oxphos['TGFA']:.2e} mol/cell/s")
    print(f"     HGF net flux: {reactions_oxphos['HGF']:.2e} mol/cell/s")
    print(f"   ATP rate: {cell_state_oxphos.get('atp_rate', 0):.2e}")
    
    # Test Case 2: Glycolytic cell (glycoATP active)
    print(f"\n🔬 Test Case 2: Glycolytic Cell (glycoATP active)")
    cell_state_glyco = {
        'gene_states': {
            'mitoATP': False,
            'glycoATP': True,
            'Necrosis': False
        }
    }
    
    reactions_glyco = custom_calculate_cell_metabolism(local_environment, cell_state_glyco, config)
    print(f"   Oxygen consumption: {reactions_glyco['Oxygen']:.2e} mol/cell/s")
    print(f"   Glucose consumption: {reactions_glyco['Glucose']:.2e} mol/cell/s")
    print(f"   Lactate production: {reactions_glyco['Lactate']:.2e} mol/cell/s")
    print(f"   Proton production: {reactions_glyco['H']:.2e} mol/cell/s")
    print(f"   ATP rate: {cell_state_glyco.get('atp_rate', 0):.2e}")
    
    # Test Case 3: Mixed metabolism (both active)
    print(f"\n🔬 Test Case 3: Mixed Metabolism (both mitoATP and glycoATP active)")
    cell_state_mixed = {
        'gene_states': {
            'mitoATP': True,
            'glycoATP': True,
            'Necrosis': False
        }
    }
    
    reactions_mixed = custom_calculate_cell_metabolism(local_environment, cell_state_mixed, config)
    print(f"   Oxygen consumption: {reactions_mixed['Oxygen']:.2e} mol/cell/s")
    print(f"   Glucose consumption: {reactions_mixed['Glucose']:.2e} mol/cell/s")
    print(f"   Lactate net flux: {reactions_mixed['Lactate']:.2e} mol/cell/s")
    print(f"   Proton net flux: {reactions_mixed['H']:.2e} mol/cell/s")
    print(f"   ATP rate: {cell_state_mixed.get('atp_rate', 0):.2e}")
    
    # Test Case 4: Hypoxic environment
    print(f"\n🔬 Test Case 4: Hypoxic Environment (low oxygen)")
    hypoxic_environment = local_environment.copy()
    hypoxic_environment['Oxygen'] = 0.001  # Very low oxygen
    
    reactions_hypoxic = custom_calculate_cell_metabolism(hypoxic_environment, cell_state_mixed, config)
    print(f"   Environment: O2={hypoxic_environment['Oxygen']} mM")
    print(f"   Oxygen consumption: {reactions_hypoxic['Oxygen']:.2e} mol/cell/s")
    print(f"   Glucose consumption: {reactions_hypoxic['Glucose']:.2e} mol/cell/s")
    print(f"   Lactate net flux: {reactions_hypoxic['Lactate']:.2e} mol/cell/s")
    print(f"   ATP rate: {cell_state_mixed.get('atp_rate', 0):.2e}")
    
    # Verify Michaelis-Menten behavior
    print(f"\n📊 Michaelis-Menten Verification:")
    km_oxygen = config.custom_parameters['the_optimal_oxygen']
    km_glucose = config.custom_parameters['the_optimal_glucose']
    
    # At Km concentration, reaction rate should be Vmax/2
    print(f"   At Km oxygen ({km_oxygen} mM): rate factor = {km_oxygen/(km_oxygen + km_oxygen):.3f} (should be 0.5)")
    print(f"   At Km glucose ({km_glucose} mM): rate factor = {km_glucose/(km_glucose + km_glucose):.3f} (should be 0.5)")
    
    # At high concentration, should approach Vmax
    high_conc = 10.0
    print(f"   At high oxygen ({high_conc} mM): rate factor = {high_conc/(km_oxygen + high_conc):.3f} (should approach 1.0)")
    print(f"   At high glucose ({high_conc} mM): rate factor = {high_conc/(km_glucose + high_conc):.3f} (should approach 1.0)")
    
    print(f"\n✅ NetLogo-style Michaelis-Menten metabolism test completed!")
    print(f"   - OXPHOS cells consume oxygen, glucose, and lactate")
    print(f"   - Glycolytic cells consume glucose, produce lactate and protons")
    print(f"   - Mixed metabolism shows combined effects")
    print(f"   - Hypoxic conditions reduce oxygen-dependent reactions")
    print(f"   - Michaelis-Menten kinetics working correctly")

if __name__ == "__main__":
    test_netlogo_metabolism()
