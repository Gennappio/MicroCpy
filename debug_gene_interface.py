#!/usr/bin/env python3
"""
Debug script to compare MicroC gene network interface with standalone simulator.
"""

import sys
import os
sys.path.append('src')

from config.config import MicroCConfig
from biology.gene_network import BooleanNetwork

def debug_microc_gene_interface():
    """Debug MicroC's gene network interface"""
    
    print("🔍 DEBUGGING MICROC GENE NETWORK INTERFACE")
    print("="*60)
    
    # Load the exact config used in the problematic simulation
    config_path = "tests/multitest/config_O2high_Lachigh_Gluchigh_TGFAlow.yaml"
    from pathlib import Path
    config = MicroCConfig.load_from_yaml(Path(config_path))
    
    print(f"📁 Loaded config: {config_path}")
    
    # Environmental concentrations from the config file
    env_concentrations = {}

    # Read concentrations from config.substances
    for substance_name, substance_config in config.substances.items():
        # Use boundary_value if available, otherwise initial_value
        if hasattr(substance_config, 'boundary_value'):
            concentration = substance_config.boundary_value
        else:
            concentration = substance_config.initial_value

        # Extract the numeric value from Concentration object
        if hasattr(concentration, 'value'):
            concentration = concentration.value

        env_concentrations[substance_name.lower()] = concentration
    
    print("\n🌍 Environmental concentrations:")
    for substance, conc in env_concentrations.items():
        print(f"  {substance}: {conc}")
    
    # Calculate gene inputs using MicroC's logic
    print("\n🧬 MicroC Gene Input Calculation:")
    gene_inputs = {}
    
    for substance_name, gene_input_name in config.associations.items():
        substance_conc = env_concentrations.get(substance_name.lower())
        
        if substance_conc is None:
            print(f"  ⚠️  {substance_name} not found in environment")
            continue
            
        if gene_input_name not in config.thresholds:
            print(f"  ⚠️  No threshold for {gene_input_name}")
            continue
            
        threshold_config = config.thresholds[gene_input_name]
        gene_input_value = substance_conc > threshold_config.threshold
        gene_inputs[gene_input_name] = gene_input_value
        
        print(f"  {substance_name} ({substance_conc}) -> {gene_input_name}: {gene_input_value} (threshold: {threshold_config.threshold})")
    
    # Initialize MicroC's gene network
    print("\n🔬 Initializing MicroC Gene Network:")
    gene_network = BooleanNetwork(config=config, network_file=config.gene_network.bnd_file)
    
    print(f"  Loaded {len(gene_network.nodes)} nodes")
    print(f"  Input nodes: {len(gene_network.input_nodes)}")
    print(f"  Output nodes: {len(gene_network.output_nodes)}")
    
    # Set input states
    gene_network.set_input_states(gene_inputs)
    
    # Get initial states
    initial_states = gene_network.get_all_states()
    print(f"\n📊 Initial Gene States:")
    for node, state in sorted(initial_states.items()):
        if node in ['glycoATP', 'mitoATP', 'Apoptosis', 'Necrosis', 'Proliferation', 'Growth_Arrest']:
            print(f"  {node}: {state}")
    
    # Run gene network for several steps
    print(f"\n🔄 Running Gene Network (steps: {config.gene_network.propagation_steps}):")
    final_states = gene_network.step(config.gene_network.propagation_steps)
    
    print(f"📊 Final Gene States:")
    for node, state in sorted(final_states.items()):
        if node in ['glycoATP', 'mitoATP', 'Apoptosis', 'Necrosis', 'Proliferation', 'Growth_Arrest']:
            print(f"  {node}: {state}")
    
    # Compare with standalone simulator results
    print(f"\n🔍 COMPARISON WITH STANDALONE SIMULATOR:")
    print(f"  Standalone results (O2high_Lachigh_Gluchigh_TGFAlow):")
    print(f"    glycoATP: OFF (0.0%)")
    print(f"    mitoATP: ON (100.0%)")  # CORRECTED: mitoATP should be ON
    print(f"    Apoptosis: OFF (0.0%)")
    print(f"    Necrosis: OFF (0.0%)")
    print(f"    Proliferation: OFF (0.0%)")
    print(f"    Growth_Arrest: OFF (0.0%)")

    print(f"\n  MicroC results:")
    print(f"    glycoATP: {'ON' if final_states.get('glycoATP', False) else 'OFF'}")
    print(f"    mitoATP: {'ON' if final_states.get('mitoATP', False) else 'OFF'}")
    print(f"    Apoptosis: {'ON' if final_states.get('Apoptosis', False) else 'OFF'}")
    print(f"    Necrosis: {'ON' if final_states.get('Necrosis', False) else 'OFF'}")
    print(f"    Proliferation: {'ON' if final_states.get('Proliferation', False) else 'OFF'}")
    print(f"    Growth_Arrest: {'ON' if final_states.get('Growth_Arrest', False) else 'OFF'}")

    # Check for discrepancies
    discrepancies = []
    expected = {'glycoATP': False, 'mitoATP': True, 'Apoptosis': False, 'Necrosis': False, 'Proliferation': False, 'Growth_Arrest': False}  # CORRECTED: mitoATP should be True
    
    for node, expected_state in expected.items():
        actual_state = final_states.get(node, False)
        if actual_state != expected_state:
            discrepancies.append(f"{node}: expected {expected_state}, got {actual_state}")
    
    if discrepancies:
        print(f"\n❌ DISCREPANCIES FOUND:")
        for disc in discrepancies:
            print(f"  {disc}")
    else:
        print(f"\n✅ NO DISCREPANCIES - Results match standalone simulator")
    
    return gene_inputs, final_states, discrepancies

if __name__ == "__main__":
    debug_microc_gene_interface()
