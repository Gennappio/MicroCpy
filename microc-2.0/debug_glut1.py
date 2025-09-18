#!/usr/bin/env python3
"""
Debug GLUT1 logic specifically
"""

import sys
sys.path.append('.')
from gene_network_standalone import StandaloneGeneNetwork

def debug_glut1():
    """Debug GLUT1 logic evaluation"""
    
    print("🔍 DEBUGGING GLUT1 LOGIC")
    print("=" * 40)
    
    # Load network
    network = StandaloneGeneNetwork()
    network.load_bnd_file('tests/jayatilake_experiment/jaya_microc.bnd')
    input_states = network.load_input_states('corrected_mitoATP_test.txt')
    network.set_input_states(input_states)
    
    # Get all gene states
    gene_states = {name: node.state for name, node in network.nodes.items()}
    
    # Focus on GLUT1
    node = network.nodes['GLUT1']
    print(f"GLUT1 logic: {node.update_function.expression}")
    print(f"Current state: {node.state}")
    
    # Break down the logic: (HIF1 | ! p53 | MYC) & ! GLUT1I
    dependencies = ['HIF1', 'p53', 'MYC', 'GLUT1I']
    
    print(f"\nDependency states:")
    for dep in dependencies:
        if dep in gene_states:
            print(f"  {dep}: {gene_states[dep]}")
        else:
            print(f"  {dep}: NOT FOUND")
    
    # Manual step-by-step evaluation
    print(f"\nStep-by-step evaluation:")
    
    # Get values
    HIF1 = gene_states.get('HIF1', False)
    p53 = gene_states.get('p53', False)
    MYC = gene_states.get('MYC', False)
    GLUT1I = gene_states.get('GLUT1I', False)
    
    print(f"  HIF1 = {HIF1}")
    print(f"  p53 = {p53}")
    print(f"  MYC = {MYC}")
    print(f"  GLUT1I = {GLUT1I}")
    
    # Evaluate parts
    part1 = HIF1
    part2 = not p53
    part3 = MYC
    part4 = not GLUT1I
    
    print(f"\n  HIF1 = {part1}")
    print(f"  ! p53 = {part2}")
    print(f"  MYC = {part3}")
    print(f"  ! GLUT1I = {part4}")
    
    # Combine
    left_side = part1 or part2 or part3  # (HIF1 | ! p53 | MYC)
    final_result = left_side and part4   # & ! GLUT1I
    
    print(f"\n  (HIF1 | ! p53 | MYC) = ({part1} | {part2} | {part3}) = {left_side}")
    print(f"  Final: {left_side} & {part4} = {final_result}")
    
    # Compare with node evaluation
    node_result = node.update_function.evaluate(gene_states)
    print(f"\n  Node evaluation: {node_result}")
    print(f"  Manual calculation: {final_result}")
    
    if node_result == final_result:
        print(f"  ✅ Evaluations match")
    else:
        print(f"  🚨 Evaluation mismatch!")
    
    # The key insight: if GLUT1 should be True, why isn't it being updated?
    print(f"\n🔍 WHY ISN'T GLUT1 BEING UPDATED?")
    print("-" * 40)
    
    if final_result and not node.state:
        print(f"GLUT1 should be True but is False!")
        print(f"This means the gene update mechanism is not working!")
        
        # Check if GLUT1 can be selected for updates
        non_input_genes = [name for name, node in network.nodes.items() 
                          if not node.is_input and node.update_function]
        
        if 'GLUT1' in non_input_genes:
            print(f"✅ GLUT1 can be selected for updates")
        else:
            print(f"🚨 GLUT1 cannot be selected for updates!")
            
        # Try to manually update GLUT1
        print(f"\nTrying manual update...")
        old_state = node.state
        
        # This is what should happen in netlogo_single_gene_update
        new_state = node.update_function.evaluate(gene_states)
        print(f"  Old state: {old_state}")
        print(f"  New state: {new_state}")
        
        if old_state != new_state:
            print(f"  📝 Should update: {old_state} -> {new_state}")
            # Actually update it
            node.state = new_state
            print(f"  ✅ Updated GLUT1 to {node.state}")
            
            # Now check downstream effects
            print(f"\n🔄 CHECKING DOWNSTREAM EFFECTS")
            print("-" * 30)
            
            # Update gene_states with new GLUT1 value
            gene_states['GLUT1'] = new_state
            
            # Check Cell_Glucose
            cell_glucose_node = network.nodes['Cell_Glucose']
            cell_glucose_expected = cell_glucose_node.update_function.evaluate(gene_states)
            print(f"  Cell_Glucose: current={cell_glucose_node.state}, expected={cell_glucose_expected}")
            
            if cell_glucose_node.state != cell_glucose_expected:
                print(f"  📝 Cell_Glucose should be: {cell_glucose_expected}")
                cell_glucose_node.state = cell_glucose_expected
                gene_states['Cell_Glucose'] = cell_glucose_expected
                
                # Check G6P
                g6p_node = network.nodes['G6P']
                g6p_expected = g6p_node.update_function.evaluate(gene_states)
                print(f"  G6P: current={g6p_node.state}, expected={g6p_expected}")
                
                if g6p_node.state != g6p_expected:
                    print(f"  📝 G6P should be: {g6p_expected}")

if __name__ == "__main__":
    debug_glut1()
