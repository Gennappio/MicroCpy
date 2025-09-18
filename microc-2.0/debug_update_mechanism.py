#!/usr/bin/env python3
"""
Debug the gene update mechanism
"""

import sys
import random
sys.path.append('.')
from gene_network_standalone import StandaloneGeneNetwork

def debug_update_mechanism():
    """Debug why genes aren't being updated"""
    
    print("🔍 DEBUGGING UPDATE MECHANISM")
    print("=" * 50)
    
    # Load network
    network = StandaloneGeneNetwork()
    network.load_bnd_file('tests/jayatilake_experiment/jaya_microc.bnd')
    input_states = network.load_input_states('corrected_mitoATP_test.txt')
    network.set_input_states(input_states)
    
    # Check what genes can be updated
    non_input_genes = [name for name, node in network.nodes.items()
                      if not node.is_input and node.update_function]
    
    print(f"Non-input genes with update functions: {len(non_input_genes)}")
    print(f"First 10: {non_input_genes[:10]}")
    
    # Check current states
    current_states = {name: node.state for name, node in network.nodes.items()}
    
    # Find genes that need updating
    genes_needing_update = []
    
    print(f"\n🔍 CHECKING WHICH GENES NEED UPDATES")
    print("-" * 40)
    
    for gene_name in non_input_genes[:20]:  # Check first 20
        node = network.nodes[gene_name]
        current_state = node.state
        
        try:
            expected_state = node.update_function.evaluate(current_states)
            
            if current_state != expected_state:
                genes_needing_update.append((gene_name, current_state, expected_state))
                print(f"  {gene_name}: {current_state} -> {expected_state} ⚠️")
            else:
                print(f"  {gene_name}: {current_state} ✅")
                
        except Exception as e:
            print(f"  {gene_name}: ERROR - {e}")
    
    print(f"\nGenes needing updates: {len(genes_needing_update)}")
    
    if genes_needing_update:
        print(f"Genes that should change:")
        for gene, current, expected in genes_needing_update:
            print(f"  {gene}: {current} -> {expected}")
    else:
        print("❌ No genes need updating! This explains why 'Updated None'")
    
    # Test the update mechanism manually
    print(f"\n🔧 TESTING UPDATE MECHANISM")
    print("-" * 40)
    
    # Try 10 manual updates
    for i in range(10):
        print(f"\nUpdate attempt {i+1}:")
        
        # Get available genes
        available_genes = [name for name, node in network.nodes.items()
                          if not node.is_input and node.update_function]
        
        if not available_genes:
            print("  No genes available for update")
            break
        
        # Select random gene
        selected_gene = random.choice(available_genes)
        gene_node = network.nodes[selected_gene]
        
        print(f"  Selected: {selected_gene}")
        print(f"  Current state: {gene_node.state}")
        
        # Get current states for evaluation
        current_states = {name: node.state for name, node in network.nodes.items()}
        
        # Evaluate
        try:
            new_state = gene_node.update_function.evaluate(current_states)
            print(f"  Expected state: {new_state}")
            
            if gene_node.state != new_state:
                print(f"  📝 UPDATING: {gene_node.state} -> {new_state}")
                gene_node.state = new_state
                print(f"  ✅ Updated {selected_gene}")
                
                # Check if this creates cascade updates
                print(f"  🔄 Checking for cascade effects...")
                cascade_updates = []
                
                for other_gene in non_input_genes[:10]:  # Check first 10 for cascades
                    if other_gene != selected_gene:
                        other_node = network.nodes[other_gene]
                        current_states_updated = {name: node.state for name, node in network.nodes.items()}
                        
                        try:
                            other_expected = other_node.update_function.evaluate(current_states_updated)
                            if other_node.state != other_expected:
                                cascade_updates.append((other_gene, other_node.state, other_expected))
                        except:
                            pass
                
                if cascade_updates:
                    print(f"    Cascade effects found: {len(cascade_updates)}")
                    for gene, current, expected in cascade_updates[:3]:  # Show first 3
                        print(f"      {gene}: {current} -> {expected}")
                else:
                    print(f"    No cascade effects")
                
                break  # Stop after first successful update
            else:
                print(f"  ✅ No change needed")
                
        except Exception as e:
            print(f"  ❌ Error evaluating: {e}")
    
    # Final state check
    print(f"\n📊 FINAL STATE CHECK")
    print("-" * 30)
    
    key_genes = ['GLUT1', 'Cell_Glucose', 'G6P', 'PEP', 'Pyruvate', 'mitoATP', 'glycoATP']
    
    for gene in key_genes:
        if gene in network.nodes:
            node = network.nodes[gene]
            print(f"  {gene}: {node.state}")

if __name__ == "__main__":
    debug_update_mechanism()
