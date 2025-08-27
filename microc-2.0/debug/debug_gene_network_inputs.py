#!/usr/bin/env python3
"""
Debug script to test gene network with exact same inputs as MicroC simulation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np
from src.config.config import MicroCConfig
from src.simulation.multi_substance_simulator import MultiSubstanceSimulator
from src.core.domain import MeshManager
from src.biology.gene_network import BooleanNetwork
from pathlib import Path

def main():
    # Load config
    config_path = "tests/jayatilake_experiment/jayatilake_experiment_config.yaml"
    config = MicroCConfig.load_from_yaml(Path(config_path))
    
    print("=== GENE NETWORK INPUT DEBUG ===")
    print(f"Config: {config_path}")
    print()
    
    # Initialize simulator
    print("[RUN] INITIALIZING SIMULATOR...")
    mesh_manager = MeshManager(config.domain)
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    
    # Initialize gene network
    print(" INITIALIZING GENE NETWORK...")
    gene_network = BooleanNetwork(config=config)
    
    # Get gene inputs from simulator at center position
    center_x = config.domain.nx // 2
    center_y = config.domain.ny // 2
    center_pos = (center_x, center_y)
    
    print(f"\n TESTING AT CENTER POSITION: {center_pos}")
    
    # Get inputs from simulator
    gene_inputs = simulator.get_gene_network_inputs_for_position(center_pos)
    
    print(f"\n GENE INPUTS FROM SIMULATOR:")
    for key, value in sorted(gene_inputs.items()):
        print(f"  {key}: {value}")
    
    # Test gene network with these inputs
    print(f"\n TESTING GENE NETWORK WITH THESE INPUTS:")
    print(f"  Propagation steps: {config.gene_network.propagation_steps}")

    # Set inputs and run gene network
    gene_network.set_input_states(gene_inputs)
    final_states = gene_network.step(config.gene_network.propagation_steps)
    
    print(f"\n[CHART] GENE NETWORK RESULTS:")
    for key, value in sorted(final_states.items()):
        print(f"  {key}: {value}")
    
    # Check specific metabolic states
    print(f"\n[SEARCH] METABOLIC STATE ANALYSIS:")
    oxygen_supply = gene_inputs.get('Oxygen_supply', False)
    mct1_stimulus = gene_inputs.get('MCT1_stimulus', False)
    mito_atp = final_states.get('mitoATP', False)
    glyco_atp = final_states.get('glycoATP', False)
    
    print(f"  Oxygen_supply: {oxygen_supply}")
    print(f"  MCT1_stimulus: {mct1_stimulus}")
    print(f"  mitoATP: {mito_atp}")
    print(f"  glycoATP: {glyco_atp}")
    
    if mito_atp and glyco_atp:
        print(f"  [RUN] BOTH ATP pathways active!")
    elif mito_atp:
        print(f"  [FAST] Only mitoATP active")
    elif glyco_atp:
        print(f"   Only glycoATP active")
    else:
        print(f"   No ATP production")
    
    # Test multiple runs to check for stochasticity
    print(f"\n TESTING MULTIPLE RUNS (checking for stochasticity):")
    results = []
    for i in range(10):
        # Create fresh gene network for each run
        test_network = BooleanNetwork(config=config)
        test_network.set_input_states(gene_inputs)
        test_states = test_network.step(config.gene_network.propagation_steps)
        
        mito = test_states.get('mitoATP', False)
        glyco = test_states.get('glycoATP', False)
        
        if mito and glyco:
            state = "BOTH"
        elif mito:
            state = "MITO"
        elif glyco:
            state = "GLYCO"
        else:
            state = "NONE"
        
        results.append(state)
        print(f"  Run {i+1}: mitoATP={mito}, glycoATP={glyco} -> {state}")
    
    # Count results
    from collections import Counter
    counts = Counter(results)
    print(f"\n[GRAPH] SUMMARY OF 10 RUNS:")
    for state, count in counts.items():
        print(f"  {state}: {count} times ({count/10*100:.0f}%)")
    
    # Test with manually set inputs to match standalone test
    print(f"\n[TOOL] TESTING WITH MANUALLY SET INPUTS (like standalone):")
    manual_inputs = {
        'Oxygen_supply': True,  # We know this is true from oxygen debug
        'Glucose_supply': True,  # Should be true (glucose = 5.0 > 4.0 threshold)
        'MCT1_stimulus': False,  # Should be false (lactate = 1.0 < 1.5 threshold)
        'Proton_level': False,   # Should be false (H = 4e-5 < 8e-5 threshold)
        'FGFR_stimulus': False,  # Should be false (FGF = 0.0 < 1e-6 threshold)
        'EGFR_stimulus': False,  # Should be false (EGF = 5e-7 < 1e-6 threshold)
        'cMET_stimulus': False,  # Should be false (HGF = 2e-6 > 1e-6 threshold) - wait, this should be True!
        'Growth_Inhibitor': False,  # Should be false (GI = 0.0 < 5e-5 threshold)
        'DNA_damage': False,     # Should be false (no DNA damage)
        'TGFBR_stimulus': False, # Should be false (TGFA = 0.0 < 0.5 threshold)
    }
    
    print(f"  Manual inputs:")
    for key, value in sorted(manual_inputs.items()):
        print(f"    {key}: {value}")
    
    # Test with manual inputs
    manual_network = BooleanNetwork(config=config)
    manual_network.set_input_states(manual_inputs)
    manual_states = manual_network.step(config.gene_network.propagation_steps)
    
    manual_mito = manual_states.get('mitoATP', False)
    manual_glyco = manual_states.get('glycoATP', False)
    
    print(f"\n  Results with manual inputs:")
    print(f"    mitoATP: {manual_mito}")
    print(f"    glycoATP: {manual_glyco}")
    
    if manual_mito and manual_glyco:
        print(f"    [RUN] BOTH ATP pathways active with manual inputs!")
    elif manual_mito:
        print(f"    [FAST] Only mitoATP active with manual inputs")
    elif manual_glyco:
        print(f"     Only glycoATP active with manual inputs")
    else:
        print(f"     No ATP production with manual inputs")

if __name__ == "__main__":
    main()
