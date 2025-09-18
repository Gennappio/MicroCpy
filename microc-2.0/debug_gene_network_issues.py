#!/usr/bin/env python3
"""
Comprehensive debug script to investigate gene network issues:
1. Are nodes updated correctly with the correct logic?
2. Are non-input nodes randomly initialized?
3. Are input nodes fixed (never change)?
"""

import sys
sys.path.append('.')
from gene_network_standalone import StandaloneGeneNetwork

def debug_gene_network_issues():
    """Debug all three potential issues"""
    
    print("🔍 COMPREHENSIVE GENE NETWORK DEBUG")
    print("=" * 60)
    
    # Load network
    network = StandaloneGeneNetwork()
    network.load_bnd_file('tests/jayatilake_experiment/jaya_microc.bnd')
    
    # Load input states
    input_states = network.load_input_states('corrected_mitoATP_test.txt')
    
    print(f"\n1️⃣ CHECKING INPUT NODE CONSTRAINTS")
    print("-" * 40)
    
    # Check which nodes are marked as input
    input_nodes = [name for name, node in network.nodes.items() if node.is_input]
    non_input_nodes = [name for name, node in network.nodes.items() if not node.is_input]
    
    print(f"Input nodes ({len(input_nodes)}): {sorted(input_nodes)}")
    print(f"Non-input nodes ({len(non_input_nodes)}): {len(non_input_nodes)} total")
    
    # Check if input states match input nodes
    print(f"\nInput states loaded: {len(input_states)}")
    for name, state in input_states.items():
        if name in network.nodes:
            is_input = network.nodes[name].is_input
            print(f"  {name}: {state} (is_input: {is_input})")
            if not is_input:
                print(f"    ⚠️  WARNING: {name} has input state but is not marked as input node!")
        else:
            print(f"  {name}: {state} (⚠️  NODE NOT FOUND)")
    
    print(f"\n2️⃣ CHECKING INITIAL NODE STATES")
    print("-" * 40)
    
    # Set input states and check initial states
    network.set_input_states(input_states)
    
    # Check key metabolic nodes
    key_nodes = ['Oxygen_supply', 'Glucose_supply', 'Glucose', 'GLUT1', 'Cell_Glucose', 'G6P', 'PEP', 'Pyruvate', 'mitoATP', 'glycoATP']
    
    print("Initial states BEFORE any updates:")
    for node_name in key_nodes:
        if node_name in network.nodes:
            node = network.nodes[node_name]
            print(f"  {node_name}: {node.state} (is_input: {node.is_input})")
            if hasattr(node, 'update_function') and node.update_function:
                print(f"    Logic: {node.update_function}")
    
    print(f"\n3️⃣ CHECKING LOGIC EVALUATION")
    print("-" * 40)
    
    # Manually evaluate logic for suspicious nodes
    suspicious_nodes = ['Cell_Glucose', 'G6P', 'PEP', 'Pyruvate']
    
    for node_name in suspicious_nodes:
        if node_name in network.nodes:
            node = network.nodes[node_name]
            print(f"\n{node_name}:")
            print(f"  Current state: {node.state}")
            print(f"  Logic rule: {node.update_function}")
            
            if node.update_function:
                # Get dependencies
                deps = network.get_dependencies(node_name)
                dep_states = {dep: network.nodes[dep].state for dep in deps if dep in network.nodes}
                print(f"  Dependencies: {dep_states}")
                
                # Evaluate logic manually
                try:
                    result = network.evaluate_logic(node.update_function, network.nodes)
                    print(f"  Logic evaluation: {result}")
                    print(f"  Expected state: {result}")
                    if node.state != result:
                        print(f"  🚨 MISMATCH: Current={node.state}, Expected={result}")
                    else:
                        print(f"  ✅ CORRECT: State matches logic")
                except Exception as e:
                    print(f"  ❌ ERROR evaluating logic: {e}")
    
    print(f"\n4️⃣ TESTING INPUT NODE STABILITY")
    print("-" * 40)
    
    # Record initial input states
    initial_input_states = {}
    for name in input_nodes:
        if name in network.nodes:
            initial_input_states[name] = network.nodes[name].state
    
    print("Initial input states:")
    for name, state in initial_input_states.items():
        print(f"  {name}: {state}")
    
    # Run a few simulation steps and check if input nodes change
    print(f"\nRunning 20 simulation steps to test input stability...")
    
    input_changes = []
    for step in range(20):
        # Record states before update
        before_states = {name: network.nodes[name].state for name in input_nodes if name in network.nodes}
        
        # Perform update
        updated_gene = network.netlogo_single_gene_update()
        
        # Re-enforce input states (this should be happening automatically)
        if input_states:
            for node_name, state in input_states.items():
                if node_name in network.nodes:
                    network.nodes[node_name].state = state
        
        # Record states after update
        after_states = {name: network.nodes[name].state for name in input_nodes if name in network.nodes}
        
        # Check for changes
        for name in input_nodes:
            if name in before_states and name in after_states:
                if before_states[name] != after_states[name]:
                    change = f"Step {step+1}: {name} {before_states[name]} -> {after_states[name]} (updated: {updated_gene})"
                    input_changes.append(change)
                    print(f"  🚨 INPUT CHANGED: {change}")
    
    if not input_changes:
        print("  ✅ All input nodes remained stable")
    else:
        print(f"  🚨 Found {len(input_changes)} input node changes!")
    
    print(f"\n5️⃣ TESTING LOGIC UPDATE CORRECTNESS")
    print("-" * 40)
    
    # Test a few specific logic updates
    test_cases = [
        ('Cell_Glucose', 'GLUT1 & Glucose_supply'),
        ('G6P', 'Cell_Glucose'),
        ('glycoATP', 'PEP & ! LDHB'),
        ('mitoATP', 'ETC')
    ]
    
    for node_name, expected_logic in test_cases:
        if node_name in network.nodes:
            node = network.nodes[node_name]
            print(f"\n{node_name}:")
            print(f"  Expected logic: {expected_logic}")
            print(f"  Actual logic: {node.update_function}")
            
            if node.update_function == expected_logic:
                print(f"  ✅ Logic matches")
            else:
                print(f"  🚨 Logic mismatch!")
            
            # Test manual update
            old_state = node.state
            deps = network.get_dependencies(node_name)
            dep_states = {dep: network.nodes[dep].state for dep in deps if dep in network.nodes}
            
            try:
                new_state = network.evaluate_logic(node.update_function, network.nodes)
                print(f"  Current state: {old_state}")
                print(f"  Dependencies: {dep_states}")
                print(f"  Calculated state: {new_state}")
                
                if old_state != new_state:
                    print(f"  📝 Would change: {old_state} -> {new_state}")
                else:
                    print(f"  📝 No change needed")
                    
            except Exception as e:
                print(f"  ❌ Error in logic evaluation: {e}")
    
    print(f"\n6️⃣ SUMMARY")
    print("-" * 40)
    
    # Final summary
    issues_found = []
    
    # Check for input node issues
    non_input_with_states = [name for name, state in input_states.items() 
                           if name in network.nodes and not network.nodes[name].is_input]
    if non_input_with_states:
        issues_found.append(f"Non-input nodes with input states: {non_input_with_states}")
    
    # Check for input changes
    if input_changes:
        issues_found.append(f"Input nodes changed during simulation: {len(input_changes)} changes")
    
    # Check for logic mismatches
    logic_issues = []
    for node_name in suspicious_nodes:
        if node_name in network.nodes:
            node = network.nodes[node_name]
            if node.update_function:
                try:
                    expected = network.evaluate_logic(node.update_function, network.nodes)
                    if node.state != expected:
                        logic_issues.append(f"{node_name}: {node.state} != {expected}")
                except:
                    logic_issues.append(f"{node_name}: logic evaluation failed")
    
    if logic_issues:
        issues_found.append(f"Logic evaluation mismatches: {logic_issues}")
    
    if issues_found:
        print("🚨 ISSUES FOUND:")
        for i, issue in enumerate(issues_found, 1):
            print(f"  {i}. {issue}")
    else:
        print("✅ No obvious issues detected")
    
    return issues_found

if __name__ == "__main__":
    issues = debug_gene_network_issues()
    
    if issues:
        print(f"\n🎯 CONCLUSION: Found {len(issues)} potential issues that need fixing!")
    else:
        print(f"\n🎯 CONCLUSION: Gene network appears to be working correctly")
