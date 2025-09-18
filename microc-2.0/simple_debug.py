#!/usr/bin/env python3
"""
Simple debug script to check the three key issues
"""

import sys
sys.path.append('.')
from gene_network_standalone import StandaloneGeneNetwork

def simple_debug():
    """Simple debug of key issues"""
    
    print("🔍 SIMPLE GENE NETWORK DEBUG")
    print("=" * 50)
    
    # Load network
    network = StandaloneGeneNetwork()
    network.load_bnd_file('tests/jayatilake_experiment/jaya_microc.bnd')
    
    # Load input states
    input_states = network.load_input_states('corrected_mitoATP_test.txt')
    
    print(f"\n1️⃣ INPUT NODES CHECK")
    print("-" * 30)
    
    # Set input states
    network.set_input_states(input_states)
    
    # Check key nodes initial states
    key_nodes = ['Oxygen_supply', 'Glucose_supply', 'Glucose', 'GLUT1', 'Cell_Glucose', 'G6P', 'PEP', 'Pyruvate', 'mitoATP', 'glycoATP']
    
    print("Initial states:")
    for node_name in key_nodes:
        if node_name in network.nodes:
            node = network.nodes[node_name]
            print(f"  {node_name}: {node.state} (input: {node.is_input})")
    
    print(f"\n2️⃣ LOGIC RULES CHECK")
    print("-" * 30)
    
    # Check logic rules for key nodes
    logic_nodes = ['GLUT1', 'Cell_Glucose', 'G6P', 'PEP', 'Pyruvate', 'mitoATP', 'glycoATP']
    
    for node_name in logic_nodes:
        if node_name in network.nodes:
            node = network.nodes[node_name]
            print(f"\n{node_name}:")
            print(f"  Current state: {node.state}")
            if hasattr(node, 'update_function') and node.update_function:
                print(f"  Logic rule: {node.update_function.expression}")
                
                # Try to evaluate the logic
                try:
                    result = node.update_function.evaluate(network.nodes)
                    print(f"  Logic result: {result}")
                    if node.state != result:
                        print(f"  🚨 MISMATCH! Current={node.state}, Expected={result}")
                    else:
                        print(f"  ✅ Correct")
                except Exception as e:
                    print(f"  ❌ Error evaluating: {e}")
    
    print(f"\n3️⃣ INPUT STABILITY TEST")
    print("-" * 30)
    
    # Record initial input states
    input_nodes = [name for name, node in network.nodes.items() if node.is_input]
    initial_states = {name: network.nodes[name].state for name in input_nodes}
    
    print("Initial input states:")
    for name, state in initial_states.items():
        print(f"  {name}: {state}")
    
    # Run 10 steps and check for input changes
    print(f"\nRunning 10 steps...")
    changes = []
    
    for step in range(10):
        # Record before
        before = {name: network.nodes[name].state for name in input_nodes}
        
        # Update
        updated = network.netlogo_single_gene_update()
        
        # Re-enforce inputs (should happen automatically)
        network.set_input_states(input_states)
        
        # Record after
        after = {name: network.nodes[name].state for name in input_nodes}
        
        # Check changes
        for name in input_nodes:
            if before[name] != after[name]:
                change = f"Step {step+1}: {name} {before[name]} -> {after[name]}"
                changes.append(change)
                print(f"  🚨 {change}")
        
        if step < 3:  # Show first few updates
            print(f"  Step {step+1}: Updated {updated}")
    
    if not changes:
        print("  ✅ No input changes detected")
    
    print(f"\n4️⃣ FINAL STATES CHECK")
    print("-" * 30)
    
    print("Final states after 10 steps:")
    for node_name in key_nodes:
        if node_name in network.nodes:
            node = network.nodes[node_name]
            print(f"  {node_name}: {node.state}")
    
    print(f"\n5️⃣ RANDOM INITIALIZATION CHECK")
    print("-" * 30)
    
    # Create a fresh network to check initialization
    fresh_network = StandaloneGeneNetwork()
    fresh_network.load_bnd_file('tests/jayatilake_experiment/jaya_microc.bnd')
    
    print("Fresh network states (before setting inputs):")
    for node_name in key_nodes:
        if node_name in fresh_network.nodes:
            node = fresh_network.nodes[node_name]
            print(f"  {node_name}: {node.state} (input: {node.is_input})")
    
    # Check if non-input nodes are randomly initialized
    non_input_states = []
    for i in range(5):  # Create 5 fresh networks
        test_network = StandaloneGeneNetwork()
        test_network.load_bnd_file('tests/jayatilake_experiment/jaya_microc.bnd')
        
        states = {}
        for node_name in ['GLUT1', 'Cell_Glucose', 'G6P']:
            if node_name in test_network.nodes:
                states[node_name] = test_network.nodes[node_name].state
        non_input_states.append(states)
    
    print(f"\nNon-input node states across 5 fresh networks:")
    for i, states in enumerate(non_input_states):
        print(f"  Network {i+1}: {states}")
    
    # Check if they're all the same (deterministic) or different (random)
    all_same = all(states == non_input_states[0] for states in non_input_states)
    if all_same:
        print("  ✅ Deterministic initialization")
    else:
        print("  🎲 Random initialization detected")

if __name__ == "__main__":
    simple_debug()
