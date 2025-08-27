#!/usr/bin/env python3
"""
Debug script to check gene network states in high oxygen conditions
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from biology.gene_network import BooleanNetwork
from config.config_loader import ConfigLoader

def debug_gene_states():
    """Debug gene network states with high oxygen"""
    
    # Load config
    config_path = "tests/jayatilake_experiment/jayatilake_experiment_config.yaml"
    config = ConfigLoader.load_config(config_path)
    
    # Create gene network
    gene_network = BooleanNetwork(config.gene_network)
    
    # Set high oxygen conditions (like in the simulation)
    inputs = {
        'Oxygen_supply': True,      # 0.07 > 0.022 threshold
        'Glucose_supply': True,     # 5.0 > 4.0 threshold  
        'MCT1_stimulus': True,      # Assume some lactate present
        'Proton_level': False,      # Normal pH
        'FGFR_stimulus': False,     # No growth factors
        'EGFR_stimulus': False,
        'cMET_stimulus': False,
        'Growth_Inhibitor': False,  # No growth inhibition
        'DNA_damage': False,        # No DNA damage
        'TGFBR_stimulus': False,
        'GLUT1I': False,           # No inhibitors
        'GLUT1D': False,
        'EGFRI': False,
        'FGFRI': False,
        'cMETI': False,
        'MCT1I': False,
        'MCT4I': False
    }
    
    print("=== Initial Input States ===")
    for name, state in inputs.items():
        print(f"{name}: {state}")
    
    # Set input states
    gene_network.set_input_states(inputs)
    
    print("\n=== Initial Gene States ===")
    states = gene_network.get_all_states()
    for name, state in sorted(states.items()):
        print(f"{name}: {state}")
    
    print("\n=== Running 50 gene network steps ===")
    # Run several steps to let network stabilize
    for i in range(50):
        gene_network.step(1)
    
    print("\n=== Final Gene States ===")
    final_states = gene_network.get_all_states()
    
    # Focus on key metabolic genes
    key_genes = ['Oxygen_supply', 'Glucose_supply', 'HIF1', 'GLUT1', 'Cell_Glucose', 
                 'G6P', 'PEP', 'Pyruvate', 'AcetylCoA', 'TCA', 'ETC', 'mitoATP', 
                 'MCT1', 'LDHB', 'glycoATP', 'ATP_Production_Rate']
    
    print("\n=== Key Metabolic Genes ===")
    for gene in key_genes:
        if gene in final_states:
            print(f"{gene}: {final_states[gene]}")
    
    print("\n=== ATP Pathway Analysis ===")
    print(f"mitoATP pathway:")
    print(f"  Oxygen_supply: {final_states.get('Oxygen_supply', 'N/A')}")
    print(f"  AcetylCoA: {final_states.get('AcetylCoA', 'N/A')}")
    print(f"  TCA: {final_states.get('TCA', 'N/A')}")
    print(f"  ETC: {final_states.get('ETC', 'N/A')}")
    print(f"  mitoATP: {final_states.get('mitoATP', 'N/A')}")
    
    print(f"\ngycoATP pathway:")
    print(f"  PEP: {final_states.get('PEP', 'N/A')}")
    print(f"  LDHB: {final_states.get('LDHB', 'N/A')}")
    print(f"  glycoATP: {final_states.get('glycoATP', 'N/A')}")
    
    print(f"\nOverall:")
    print(f"  ATP_Production_Rate: {final_states.get('ATP_Production_Rate', 'N/A')}")

if __name__ == "__main__":
    debug_gene_states()
