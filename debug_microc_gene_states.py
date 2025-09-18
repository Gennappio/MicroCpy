#!/usr/bin/env python3
"""
Debug script to check actual gene network states in MicroC simulation
"""

import sys
import os
sys.path.append('./src')

from biology.gene_network import BooleanNetwork
from config.config import MicroCConfig

def debug_microc_gene_states():
    """Debug gene network states exactly as MicroC does"""
    
    # Load the EXACT config used by MicroC
    config_path = "tests/multitest/config_O2high_Lachigh_Gluchigh_TGFAlow.yaml"
    config = MicroCConfig.load_from_yaml(config_path)
    
    print(f"=== MicroC Gene Network Debug ===")
    print(f"Config: {config_path}")
    print(f"Propagation steps: {config.gene_network.propagation_steps}")
    print(f"Random initialization: {config.gene_network.random_initialization}")
    
    # Create gene network exactly like MicroC does
    gene_network = BooleanNetwork(config)
    
    # Calculate gene inputs exactly like MicroC does
    # These are the substance concentrations from the config
    substance_concentrations = {
        'Oxygen': 0.06,      # High oxygen
        'Glucose': 6.0,      # High glucose  
        'Lactate': 3.0,      # High lactate
        'H': 4e-05,          # Normal pH
        'FGF': 5e-07,        # Low growth factors
        'EGF': 5e-07,
        'TGFA': 5e-07,
        'HGF': 5e-07,
        'EGFRD': 0.0,
        'FGFRD': 0.0,
        'GI': 0.0,
        'cMETD': 0.0,
        'MCT1D': 0.0,
        'GLUT1D': 0.0,
        'MCT4D': 0.0
    }
    
    # Convert to gene inputs using MicroC's threshold logic
    gene_inputs = {}
    
    # Apply thresholds exactly like MicroC
    for substance, concentration in substance_concentrations.items():
        if substance in config.associations:
            gene_input_name = config.associations[substance]
            if gene_input_name in config.thresholds:
                threshold_config = config.thresholds[gene_input_name]
                threshold = threshold_config.threshold
                gene_inputs[gene_input_name] = concentration > threshold
                print(f"{substance} ({concentration}) -> {gene_input_name}: {gene_inputs[gene_input_name]} (threshold: {threshold})")
    
    # Add other gene inputs from config
    for gene_name, gene_config in config.gene_network.nodes.items():
        if gene_config.is_input and gene_name not in gene_inputs:
            gene_inputs[gene_name] = gene_config.default_state
            print(f"{gene_name}: {gene_inputs[gene_name]} (default)")
    
    print(f"\n=== Gene Network Inputs ===")
    for name, state in sorted(gene_inputs.items()):
        print(f"{name}: {state}")
    
    # Reset with random initialization like MicroC
    gene_network.reset(random_init=config.gene_network.random_initialization)
    
    print(f"\n=== Initial Gene States (after reset) ===")
    initial_states = gene_network.get_all_states()
    key_genes = ['GLUT1', 'Cell_Glucose', 'G6P', 'PEP', 'Pyruvate', 'AcetylCoA', 'TCA', 'ETC', 'mitoATP', 'ATP_Production_Rate', 'Proliferation']
    for gene in key_genes:
        if gene in initial_states:
            print(f"{gene}: {initial_states[gene]}")
    
    # Set input states
    gene_network.set_input_states(gene_inputs)
    
    print(f"\n=== Running {config.gene_network.propagation_steps} gene network steps ===")
    
    # Run exactly the same number of steps as MicroC
    final_states = gene_network.step(config.gene_network.propagation_steps)
    
    print(f"\n=== Final Gene States ===")
    for gene in key_genes:
        if gene in final_states:
            print(f"{gene}: {final_states[gene]}")
    
    print(f"\n=== ATP Pathway Analysis ===")
    print(f"Glucose pathway:")
    print(f"  Glucose_supply: {gene_inputs.get('Glucose_supply', 'N/A')}")
    print(f"  GLUT1: {final_states.get('GLUT1', 'N/A')}")
    print(f"  Cell_Glucose: {final_states.get('Cell_Glucose', 'N/A')}")
    print(f"  G6P: {final_states.get('G6P', 'N/A')}")
    print(f"  PEP: {final_states.get('PEP', 'N/A')}")
    print(f"  Pyruvate: {final_states.get('Pyruvate', 'N/A')}")
    
    print(f"\nOxygen pathway:")
    print(f"  Oxygen_supply: {gene_inputs.get('Oxygen_supply', 'N/A')}")
    print(f"  AcetylCoA: {final_states.get('AcetylCoA', 'N/A')}")
    print(f"  TCA: {final_states.get('TCA', 'N/A')}")
    print(f"  ETC: {final_states.get('ETC', 'N/A')}")
    print(f"  mitoATP: {final_states.get('mitoATP', 'N/A')}")
    
    print(f"\nOverall:")
    print(f"  ATP_Production_Rate: {final_states.get('ATP_Production_Rate', 'N/A')}")
    print(f"  Proliferation: {final_states.get('Proliferation', 'N/A')}")
    
    # Compare with standalone expectations
    print(f"\n=== Comparison with Standalone ===")
    print(f"Expected (standalone with 20000 steps):")
    print(f"  mitoATP: ON")
    print(f"  ATP_Production_Rate: ON") 
    print(f"  Proliferation: OFF (no growth factors)")
    
    print(f"Actual (MicroC with {config.gene_network.propagation_steps} steps):")
    print(f"  mitoATP: {final_states.get('mitoATP', 'N/A')}")
    print(f"  ATP_Production_Rate: {final_states.get('ATP_Production_Rate', 'N/A')}")
    print(f"  Proliferation: {final_states.get('Proliferation', 'N/A')}")

if __name__ == "__main__":
    debug_microc_gene_states()
