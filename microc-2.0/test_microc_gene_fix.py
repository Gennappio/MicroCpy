#!/usr/bin/env python3
"""
Test the MicroC gene network logic initialization fix
"""

import sys
sys.path.append('src')

from biology.gene_network import BooleanNetwork
from config.config import MicroCConfig

def test_microc_gene_fix():
    """Test that MicroC gene network now initializes logic correctly"""
    
    print("🔍 TESTING MICROC GENE NETWORK FIX")
    print("=" * 50)
    
    # Load config
    from pathlib import Path
    config_path = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    config = MicroCConfig.load_from_yaml(config_path)
    
    # Create gene network
    print("Loading gene network...")
    gene_network = BooleanNetwork(config=config, network_file=config.gene_network.bnd_file)
    
    print(f"Loaded {len(gene_network.nodes)} nodes")
    print(f"Input nodes: {len(gene_network.input_nodes)}")
    
    # Test case 1: No glucose/oxygen (should have no ATP)
    print(f"\n🧪 TEST 1: No glucose, no oxygen")
    print("-" * 30)
    
    # Reset with random initialization
    gene_network.reset(random_init=True)
    
    # Set input states
    inputs_no_fuel = {
        'Oxygen_supply': False,
        'Glucose_supply': False,
        'MCT1_stimulus': False,
        'Glucose': False
    }
    gene_network.set_input_states(inputs_no_fuel)
    
    # Check states before logic initialization
    print("Before logic initialization:")
    key_genes = ['GLUT1', 'Cell_Glucose', 'G6P', 'mitoATP', 'glycoATP']
    for gene in key_genes:
        if gene in gene_network.nodes:
            print(f"  {gene}: {gene_network.nodes[gene].current_state}")
    
    # Apply logic initialization
    updates = gene_network.initialize_logic_states(verbose=True)
    print(f"Logic initialization made {updates} updates")
    
    # Check states after logic initialization
    print("After logic initialization:")
    for gene in key_genes:
        if gene in gene_network.nodes:
            print(f"  {gene}: {gene_network.nodes[gene].current_state}")
    
    # Test case 2: With glucose and oxygen (should have ATP)
    print(f"\n🧪 TEST 2: With glucose and oxygen")
    print("-" * 30)
    
    # Reset with random initialization
    gene_network.reset(random_init=True)
    
    # Set input states
    inputs_with_fuel = {
        'Oxygen_supply': True,
        'Glucose_supply': True,
        'MCT1_stimulus': True,
        'Glucose': True
    }
    gene_network.set_input_states(inputs_with_fuel)
    
    # Check states before logic initialization
    print("Before logic initialization:")
    for gene in key_genes:
        if gene in gene_network.nodes:
            print(f"  {gene}: {gene_network.nodes[gene].current_state}")
    
    # Apply logic initialization
    updates = gene_network.initialize_logic_states(verbose=True)
    print(f"Logic initialization made {updates} updates")
    
    # Check states after logic initialization
    print("After logic initialization:")
    for gene in key_genes:
        if gene in gene_network.nodes:
            print(f"  {gene}: {gene_network.nodes[gene].current_state}")
    
    # Test case 3: Verify logic consistency
    print(f"\n🧪 TEST 3: Logic consistency check")
    print("-" * 30)
    
    # Check that Cell_Glucose logic is correct
    glut1_state = gene_network.nodes['GLUT1'].current_state
    glucose_supply = inputs_with_fuel['Glucose_supply']
    cell_glucose_expected = glut1_state and glucose_supply
    cell_glucose_actual = gene_network.nodes['Cell_Glucose'].current_state
    
    print(f"GLUT1: {glut1_state}")
    print(f"Glucose_supply: {glucose_supply}")
    print(f"Cell_Glucose expected (GLUT1 & Glucose_supply): {cell_glucose_expected}")
    print(f"Cell_Glucose actual: {cell_glucose_actual}")
    
    if cell_glucose_actual == cell_glucose_expected:
        print("✅ Cell_Glucose logic is CORRECT")
    else:
        print("🚨 Cell_Glucose logic is WRONG")
    
    # Test case 4: Run gene network steps
    print(f"\n🧪 TEST 4: Gene network dynamics")
    print("-" * 30)
    
    print("Running 10 gene network steps...")
    states_before = gene_network.get_all_states()
    
    # Run steps
    final_states = gene_network.step(10)
    
    print("Key gene states after 10 steps:")
    for gene in key_genes:
        if gene in final_states:
            before = states_before.get(gene, 'N/A')
            after = final_states[gene]
            change = "→" if before != after else "="
            print(f"  {gene}: {before} {change} {after}")
    
    print(f"\n✅ MicroC gene network fix test completed!")

if __name__ == "__main__":
    test_microc_gene_fix()
