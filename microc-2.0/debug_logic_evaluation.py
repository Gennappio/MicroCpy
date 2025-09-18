#!/usr/bin/env python3
"""
Debug the logic evaluation issue specifically
"""

import sys
sys.path.append('.')
from gene_network_standalone import StandaloneGeneNetwork

def debug_logic_evaluation():
    """Debug why logic evaluation is wrong"""
    
    print("🔍 DEBUGGING LOGIC EVALUATION")
    print("=" * 50)
    
    # Load network
    network = StandaloneGeneNetwork()
    network.load_bnd_file('tests/jayatilake_experiment/jaya_microc.bnd')
    input_states = network.load_input_states('corrected_mitoATP_test.txt')
    network.set_input_states(input_states)
    
    # Focus on Cell_Glucose which should be False & False = False
    node_name = 'Cell_Glucose'
    node = network.nodes[node_name]
    
    print(f"\n🎯 DEBUGGING {node_name}")
    print("-" * 30)
    print(f"Logic rule: {node.update_function.expression}")
    print(f"Current state: {node.state}")
    
    # Get all gene states
    gene_states = {name: node.state for name, node in network.nodes.items()}
    
    # Check the specific dependencies
    dependencies = ['GLUT1', 'Glucose_supply']
    print(f"\nDependency states:")
    for dep in dependencies:
        if dep in gene_states:
            print(f"  {dep}: {gene_states[dep]}")
        else:
            print(f"  {dep}: NOT FOUND")
    
    # Manual evaluation step by step
    print(f"\nManual evaluation:")
    expr = node.update_function.expression
    print(f"  Original: {expr}")
    
    # Replace each dependency manually
    for dep in dependencies:
        if dep in gene_states:
            value = "True" if gene_states[dep] else "False"
            print(f"  Replace {dep} with {value}")
            expr = expr.replace(dep, value)
    
    print(f"  After replacement: {expr}")
    
    # Replace operators
    expr = expr.replace('&', ' and ')
    expr = expr.replace('|', ' or ')
    expr = expr.replace('!', ' not ')
    print(f"  After operators: {expr}")
    
    # Evaluate
    try:
        result = eval(expr)
        print(f"  Final result: {result}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Compare with node's evaluation
    node_result = node.update_function.evaluate(gene_states)
    print(f"  Node evaluation: {node_result}")
    
    # Check if there are any unexpected gene states
    print(f"\n🔍 CHECKING ALL GENE STATES")
    print("-" * 30)
    
    # Look for any True states that shouldn't be True
    true_genes = [name for name, state in gene_states.items() if state]
    print(f"Genes that are TRUE ({len(true_genes)}):")
    for gene in sorted(true_genes):
        is_input = network.nodes[gene].is_input if gene in network.nodes else False
        print(f"  {gene}: {gene_states[gene]} (input: {is_input})")
    
    # Check if any of these unexpected True genes affect our logic
    print(f"\n🔍 CHECKING UNEXPECTED TRUE GENES")
    print("-" * 30)
    
    # Expected True genes based on our input
    expected_true = ['Oxygen_supply']  # Only this should be True
    unexpected_true = [gene for gene in true_genes if gene not in expected_true]
    
    if unexpected_true:
        print(f"Unexpected TRUE genes ({len(unexpected_true)}):")
        for gene in unexpected_true:
            print(f"  {gene}: {gene_states[gene]}")
            
            # Check if this gene affects Cell_Glucose logic
            if gene in node.update_function.expression:
                print(f"    ⚠️  This gene appears in Cell_Glucose logic!")
    else:
        print("✅ No unexpected TRUE genes found")
    
    # Test a few other problematic nodes
    print(f"\n🔍 TESTING OTHER NODES")
    print("-" * 30)
    
    test_nodes = ['GLUT1', 'G6P', 'PEP', 'Pyruvate']
    
    for test_node in test_nodes:
        if test_node in network.nodes:
            node = network.nodes[test_node]
            print(f"\n{test_node}:")
            print(f"  Logic: {node.update_function.expression}")
            print(f"  Current: {node.state}")
            
            try:
                expected = node.update_function.evaluate(gene_states)
                print(f"  Expected: {expected}")
                if node.state != expected:
                    print(f"  🚨 MISMATCH!")
                else:
                    print(f"  ✅ Correct")
            except Exception as e:
                print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    debug_logic_evaluation()
