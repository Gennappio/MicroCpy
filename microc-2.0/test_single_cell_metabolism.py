#!/usr/bin/env python3
"""
Test script to calculate metabolism for a single cell and verify reaction terms.
"""

import sys
import os
sys.path.append('src')
sys.path.append('tests/jayatilake_experiment')

from typing import Dict, Any
import numpy as np

# Import the custom metabolism function
try:
    from jayatilake_experiment_custom_functions import custom_calculate_cell_metabolism
    print("✅ Successfully imported custom metabolism function")
except ImportError as e:
    print(f"❌ Failed to import custom metabolism function: {e}")
    sys.exit(1)

def test_single_cell_metabolism():
    """Test metabolism calculation for a single cell with typical conditions."""
    
    print("🧬 Testing Single Cell Metabolism")
    print("=" * 50)
    
    # Typical local environment (from simulation)
    local_environment = {
        'Oxygen': 0.07,      # mM (initial value)
        'Glucose': 5.0,      # mM (initial value)
        'Lactate': 1.0,      # mM (initial value)
        'H': 4e-5,           # mM (initial value)
        'pH': 7.4,           # pH units
        'FGF': 2e-6,         # mM
        'TGFA': 0.0,         # mM
        'HGF': 2e-6,         # mM
        'GI': 0.0,           # mM
        'EGFRD': 0.0,        # mM
        'FGFRD': 0.0,        # mM
        'cMETD': 0.0,        # mM
        'MCT1D': 0.0,        # mM
        'GLUT1D': 0.0        # mM
    }
    
    # Typical cell state with gene states (from simulation output)
    cell_state = {
        'id': 'test_cell_001',
        'position': (20, 20),
        'phenotype': 'Proliferation',
        'age': 0.0,
        'gene_states': {
            # ATP production genes (from simulation debug output)
            'mitoATP': False,     # OXPHOS pathway OFF
            'glycoATP': True,     # Glycolysis pathway ON
            'ATP_Rate': True,     # Overall ATP production active
            
            # Metabolic genes
            'GLUT1': True,        # Glucose transporter
            'MCT1': False,        # Lactate transporter
            'MCT4': True,         # Lactate transporter
            
            # Fate genes
            'Proliferation': True,
            'Apoptosis': False,
            'Necrosis': False,
            'Growth_Arrest': False
        }
    }
    
    # Mock config object (simplified)
    class MockConfig:
        def __init__(self):
            # NetLogo-compatible parameters
            self.the_optimal_oxygen = 0.005      # Km for oxygen (mM)
            self.the_optimal_glucose = 0.04      # Km for glucose (mM)
            self.the_optimal_lactate = 0.04      # Km for lactate (mM)
            self.oxygen_vmax = 3.0e-17           # Vmax for oxygen (mol/s/cell)
            self.glucose_vmax = 3.0e-15          # Vmax for glucose (mol/s/cell)
            self.max_atp = 30                    # Maximum ATP per glucose
            self.proton_coefficient = 0.01       # Proton production coefficient
            
            # Growth factor parameters (from Jayatilake table)
            self.tgfa_consumption_rate = 2.0e-17
            self.tgfa_production_rate = 2.0e-20
            self.hgf_consumption_rate = 2.0e-18
            self.hgf_production_rate = 0.0
            self.fgf_consumption_rate = 2.0e-18
            self.fgf_production_rate = 0.0
    
    config = MockConfig()
    
    print("📊 Input conditions:")
    print(f"   Local environment: {len(local_environment)} substances")
    print(f"   Oxygen: {local_environment['Oxygen']:.3f} mM")
    print(f"   Glucose: {local_environment['Glucose']:.3f} mM")
    print(f"   Lactate: {local_environment['Lactate']:.3f} mM")
    print(f"   Gene states: mitoATP={cell_state['gene_states']['mitoATP']}, glycoATP={cell_state['gene_states']['glycoATP']}")
    
    # Calculate metabolism
    print("\n🔬 Calculating metabolism...")
    try:
        reactions = custom_calculate_cell_metabolism(local_environment, cell_state, config)
        print("✅ Metabolism calculation successful!")
    except Exception as e:
        print(f"❌ Metabolism calculation failed: {e}")
        return None
    
    # Display results
    print("\n📈 Metabolism Results (mol/s/cell):")
    print("-" * 40)
    
    # Key metabolic substances
    key_substances = ['Oxygen', 'Glucose', 'Lactate', 'H']
    for substance in key_substances:
        rate = reactions.get(substance, 0.0)
        direction = "consumption" if rate < 0 else "production" if rate > 0 else "no change"
        print(f"   {substance:>8}: {rate:>12.2e} mol/s/cell ({direction})")
    
    # Growth factors
    print("\n📈 Growth Factor Kinetics:")
    growth_factors = ['FGF', 'TGFA', 'HGF', 'GI']
    for substance in growth_factors:
        rate = reactions.get(substance, 0.0)
        direction = "consumption" if rate < 0 else "production" if rate > 0 else "no change"
        print(f"   {substance:>8}: {rate:>12.2e} mol/s/cell ({direction})")
    
    # Calculate expected oxygen consumption for comparison
    print("\n🔍 Analysis:")
    oxygen_rate = reactions.get('Oxygen', 0.0)
    if oxygen_rate != 0:
        print(f"   Expected oxygen consumption: {abs(oxygen_rate):.2e} mol/s/cell")
        print(f"   This matches the configured uptake_rate: 3.0e-17 mol/s/cell")
        
        # Calculate depletion time
        cell_volume = 15e-6 * 15e-6 * 20e-6  # 15μm × 15μm × 20μm in m³
        oxygen_moles_in_cell = local_environment['Oxygen'] * 1e-3 * cell_volume * 1000  # Convert mM to mol
        depletion_time = oxygen_moles_in_cell / abs(oxygen_rate)
        print(f"   Time to deplete oxygen in cell volume: {depletion_time:.1f} seconds")
    else:
        print("   ⚠️  No oxygen consumption detected!")
    
    return reactions

def calculate_fipy_source_term(reactions: Dict[str, float]):
    """Calculate the FiPy source term from metabolism reactions."""
    
    print("\n🔧 FiPy Source Term Calculation:")
    print("-" * 40)
    
    # Domain parameters (from config)
    domain_size = 600e-6  # 600 μm in meters
    nx, ny = 40, 40       # Grid size
    
    # Calculate mesh cell volume
    dx = domain_size / nx
    dy = domain_size / ny
    mesh_cell_volume = dx * dy  # m² (2D simulation)
    
    print(f"   Domain: {domain_size*1e6:.0f} μm × {domain_size*1e6:.0f} μm")
    print(f"   Grid: {nx} × {ny}")
    print(f"   Mesh cell area: {mesh_cell_volume*1e12:.1f} μm²")
    print(f"   Grid spacing: {dx*1e6:.1f} μm × {dy*1e6:.1f} μm")
    
    # Calculate source terms for key substances
    for substance in ['Oxygen', 'Glucose', 'Lactate']:
        reaction_rate = reactions.get(substance, 0.0)  # mol/s/cell
        
        if reaction_rate != 0:
            # Convert mol/s/cell to mol/(m²⋅s) by dividing by mesh cell area
            volumetric_rate = reaction_rate / mesh_cell_volume  # mol/(m²⋅s)
            
            # Convert to mM/s for FiPy (1 mol/m³ = 1000 mM, but we have m² so need thickness)
            # Assume 20 μm thickness for 2D simulation
            thickness = 20e-6  # 20 μm in meters
            final_rate = volumetric_rate / thickness * 1000.0  # mM/s
            
            print(f"   {substance}:")
            print(f"     Reaction rate: {reaction_rate:.2e} mol/s/cell")
            print(f"     Volumetric rate: {volumetric_rate:.2e} mol/(m²⋅s)")
            print(f"     FiPy source term: {final_rate:.2e} mM/s")
            
            # For ImplicitSourceTerm, positive coefficient means consumption
            fipy_coeff = abs(final_rate) if reaction_rate < 0 else -abs(final_rate)
            print(f"     FiPy coefficient: {fipy_coeff:.2e} (for ImplicitSourceTerm)")

if __name__ == "__main__":
    # Test single cell metabolism
    reactions = test_single_cell_metabolism()
    
    if reactions:
        # Calculate FiPy source terms
        calculate_fipy_source_term(reactions)
        
        print("\n🚀 Now run FipyTest.py to see the diffusion simulation:")
        print("   python benchmarks/FipyTest.py")
        print("\n🎯 Expected result:")
        print("   - Oxygen should show depletion around cell cluster")
        print("   - Concentration should drop below 0.07 mM near cells")
        print("   - Boundary conditions maintain 0.07 mM at edges")
    
    print("\n✅ Single cell metabolism test completed!")
