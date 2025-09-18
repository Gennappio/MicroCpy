#!/usr/bin/env python3
"""
Debug timing issue - when do gene states change?
"""

import sys
sys.path.append('.')
from gene_network_standalone import StandaloneGeneNetwork

def debug_timing_issue():
    """Debug when gene states change during initialization"""
    
    print("🔍 DEBUGGING TIMING ISSUE")
    print("=" * 50)
    
    # Step 1: Load network without inputs
    print("STEP 1: Loading network (no inputs)")
    network = StandaloneGeneNetwork()
    network.load_bnd_file('tests/jayatilake_experiment/jaya_microc.bnd')
    
    # Check GLUT1 state immediately after loading
    glut1_node = network.nodes['GLUT1']
    print(f"  GLUT1 initial state: {glut1_node.state}")
    
    # Check dependencies
    deps = ['HIF1', 'p53', 'MYC', 'GLUT1I']
    print(f"  Dependencies after loading:")
    for dep in deps:
        if dep in network.nodes:
            print(f"    {dep}: {network.nodes[dep].state}")
    
    # Manual evaluation at this point
    current_states = {name: node.state for name, node in network.nodes.items()}
    try:
        glut1_expected = glut1_node.update_function.evaluate(current_states)
        print(f"  GLUT1 expected: {glut1_expected}")
    except Exception as e:
        print(f"  GLUT1 evaluation error: {e}")
    
    # Step 2: Load input states
    print(f"\nSTEP 2: Loading input states")
    input_states = network.load_input_states('corrected_mitoATP_test.txt')
    
    # Check GLUT1 state after loading inputs (before setting)
    print(f"  GLUT1 state after loading inputs: {glut1_node.state}")
    
    # Step 3: Set input states
    print(f"\nSTEP 3: Setting input states")
    network.set_input_states(input_states)
    
    # Check GLUT1 state after setting inputs
    print(f"  GLUT1 state after setting inputs: {glut1_node.state}")
    
    # Check dependencies again
    print(f"  Dependencies after setting inputs:")
    for dep in deps:
        if dep in network.nodes:
            print(f"    {dep}: {network.nodes[dep].state}")
    
    # Manual evaluation after setting inputs
    current_states = {name: node.state for name, node in network.nodes.items()}
    try:
        glut1_expected = glut1_node.update_function.evaluate(current_states)
        print(f"  GLUT1 expected after inputs: {glut1_expected}")
        
        # Break down the evaluation
        HIF1 = current_states.get('HIF1', False)
        p53 = current_states.get('p53', False)
        MYC = current_states.get('MYC', False)
        GLUT1I = current_states.get('GLUT1I', False)
        
        print(f"  Detailed evaluation:")
        print(f"    HIF1 = {HIF1}")
        print(f"    p53 = {p53} -> !p53 = {not p53}")
        print(f"    MYC = {MYC}")
        print(f"    GLUT1I = {GLUT1I} -> !GLUT1I = {not GLUT1I}")
        
        left_part = HIF1 or (not p53) or MYC
        final_result = left_part and (not GLUT1I)
        
        print(f"    (HIF1 | !p53 | MYC) = {left_part}")
        print(f"    Final: {left_part} & {not GLUT1I} = {final_result}")
        
    except Exception as e:
        print(f"  GLUT1 evaluation error: {e}")
    
    # Step 4: Check if there's a hidden initialization step
    print(f"\nSTEP 4: Checking for hidden initialization")
    
    # Look for any initialization methods
    methods = [method for method in dir(network) if 'init' in method.lower()]
    print(f"  Methods with 'init': {methods}")
    
    # Check if there's a method that resets states
    reset_methods = [method for method in dir(network) if 'reset' in method.lower() or 'clear' in method.lower()]
    print(f"  Methods with 'reset/clear': {reset_methods}")
    
    # Step 5: Test what happens during simulation initialization
    print(f"\nSTEP 5: Testing simulation initialization")
    
    # This is what happens in run_gene_network_simulation
    print("  Simulating run_gene_network_simulation initialization...")
    
    # Reset to random states (this might be the issue!)
    print("  Before random initialization:")
    print(f"    GLUT1: {network.nodes['GLUT1'].state}")
    print(f"    HIF1: {network.nodes['HIF1'].state}")
    print(f"    p53: {network.nodes['p53'].state}")
    print(f"    MYC: {network.nodes['MYC'].state}")
    
    # Check if there's random initialization in the simulation
    # Look at the simulate method or run_gene_network_simulation
    
    # Step 6: Check what the actual simulation does
    print(f"\nSTEP 6: What does the simulation actually do?")
    
    # Try to run one step of simulation and see what changes
    print("  Running one simulation step...")
    
    # Record states before
    before_states = {name: node.state for name, node in network.nodes.items()}
    
    # Run one step
    try:
        updated_gene = network.netlogo_single_gene_update()
        print(f"  Updated gene: {updated_gene}")
    except Exception as e:
        print(f"  Error in update: {e}")
    
    # Record states after
    after_states = {name: node.state for name, node in network.nodes.items()}
    
    # Check for changes
    changes = []
    for name in before_states:
        if before_states[name] != after_states[name]:
            changes.append(f"{name}: {before_states[name]} -> {after_states[name]}")
    
    if changes:
        print(f"  Changes detected: {changes}")
    else:
        print(f"  No changes detected")
    
    print(f"\n  Final GLUT1 state: {network.nodes['GLUT1'].state}")

if __name__ == "__main__":
    debug_timing_issue()
