#!/usr/bin/env python3
"""
Analyze gene network pathways to determine optimal input combinations for minimizing apoptosis.
"""

from gene_network_standalone import StandaloneGeneNetwork
from collections import defaultdict, deque
import itertools

def trace_gene_dependencies(network, target_gene, max_depth=5):
    """Trace all dependencies for a target gene up to max_depth."""
    dependencies = defaultdict(set)
    queue = deque([(target_gene, 0)])
    visited = set()
    
    while queue:
        gene, depth = queue.popleft()
        if gene in visited or depth > max_depth:
            continue
        visited.add(gene)
        
        if gene not in network.nodes:
            continue
            
        node = network.nodes[gene]
        if node.is_input:
            dependencies[depth].add(gene)
        else:
            # Parse logic to find dependencies
            logic = node.logic_rule
            if logic:
                # Simple parsing - find gene names in logic
                for other_gene in network.nodes:
                    if other_gene != gene and other_gene in logic:
                        dependencies[depth].add(other_gene)
                        queue.append((other_gene, depth + 1))
    
    return dependencies

def analyze_apoptosis_pathways(bnd_file):
    """Analyze pathways affecting apoptosis."""
    network = StandaloneGeneNetwork()
    network.load_bnd_file(bnd_file)
    
    print("🎯 APOPTOSIS PATHWAY ANALYSIS")
    print("=" * 50)
    
    # Get apoptosis logic
    apoptosis_node = network.nodes.get('Apoptosis')
    if not apoptosis_node:
        print("❌ Apoptosis node not found!")
        return
    
    print(f"Apoptosis logic: {apoptosis_node.logic_rule}")
    print()

    # Analyze key survival genes
    key_genes = ['BCL2', 'ERK', 'FOXO3', 'p53', 'AKT']

    for gene in key_genes:
        if gene in network.nodes:
            node = network.nodes[gene]
            print(f"🧬 {gene}:")
            print(f"   Logic: {node.logic_rule}")

            # Find direct dependencies
            deps = []
            if node.logic_rule:
                for other_gene in network.nodes:
                    if other_gene != gene and other_gene in node.logic_rule:
                        deps.append(other_gene)
            print(f"   Direct deps: {deps}")
            print()
    
    # Find all input nodes
    input_nodes = [name for name, node in network.nodes.items() if node.is_input]
    print(f"📥 Input nodes ({len(input_nodes)}):")
    for inp in sorted(input_nodes):
        print(f"   {inp}")
    print()
    
    return network, input_nodes

def test_input_combinations(network, input_nodes, max_combinations=50):
    """Test different input combinations to find optimal anti-apoptosis settings."""
    print("🧪 TESTING INPUT COMBINATIONS")
    print("=" * 50)
    
    # Test some strategic combinations
    test_cases = [
        # Baseline: all survival factors ON, stress factors OFF
        {
            'name': 'Optimal Survival',
            'inputs': {
                'Oxygen_supply': True,
                'Glucose_supply': True,
                'FGFR_stimulus': True,
                'EGFR_stimulus': True,
                'cMET_stimulus': True,
                'DNA_damage': False,
                'Growth_Inhibitor': False,
                'EGFRI': False,
                'FGFRI': False,
                'cMETI': False,
                'MCT1I': False,
                'MCT4I': False,
                'GLUT1I': False,
                'MCT4I': False
            }
        },
        # Stress condition: DNA damage ON
        {
            'name': 'DNA Damage Stress',
            'inputs': {
                'Oxygen_supply': True,
                'Glucose_supply': True,
                'FGFR_stimulus': True,
                'EGFR_stimulus': True,
                'cMET_stimulus': True,
                'DNA_damage': True,  # STRESS
                'Growth_Inhibitor': False,
                'EGFRI': False,
                'FGFRI': False,
                'cMETI': False
            }
        },
        # Hypoxia condition
        {
            'name': 'Hypoxia',
            'inputs': {
                'Oxygen_supply': False,  # STRESS
                'Glucose_supply': True,
                'FGFR_stimulus': True,
                'EGFR_stimulus': True,
                'cMET_stimulus': True,
                'DNA_damage': False,
                'Growth_Inhibitor': False
            }
        },
        # Growth factor withdrawal
        {
            'name': 'No Growth Factors',
            'inputs': {
                'Oxygen_supply': True,
                'Glucose_supply': True,
                'FGFR_stimulus': False,  # NO GROWTH FACTORS
                'EGFR_stimulus': False,
                'cMET_stimulus': False,
                'DNA_damage': False,
                'Growth_Inhibitor': False
            }
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🔬 Testing: {test_case['name']}")
        
        # Set inputs
        network.reset(random_init=True)  # NetLogo-style initialization
        
        # Set only the inputs specified in test case
        for input_name, state in test_case['inputs'].items():
            if input_name in network.nodes:
                network.nodes[input_name].state = state
        
        # Run simulation
        final_states = network.simulate(50)  # 50 steps like our optimized config
        
        # Check key genes
        apoptosis = final_states.get('Apoptosis', False)
        bcl2 = final_states.get('BCL2', False)
        erk = final_states.get('ERK', False)
        foxo3 = final_states.get('FOXO3', False)
        p53 = final_states.get('p53', False)
        akt = final_states.get('AKT', False)
        
        print(f"   Apoptosis: {apoptosis}")
        print(f"   Survival: BCL2={bcl2}, ERK={erk}, AKT={akt}")
        print(f"   Stress: FOXO3={foxo3}, p53={p53}")
        
        results.append({
            'name': test_case['name'],
            'inputs': test_case['inputs'],
            'apoptosis': apoptosis,
            'survival_score': sum([bcl2, erk, akt]),
            'stress_score': sum([foxo3, p53])
        })
    
    return results

def main():
    bnd_file = "tests/jayatilake_experiment/jaya_microc.bnd"
    
    # Analyze pathways
    network, input_nodes = analyze_apoptosis_pathways(bnd_file)
    
    # Test combinations
    results = test_input_combinations(network, input_nodes)
    
    # Summary
    print("\n📊 SUMMARY")
    print("=" * 50)
    for result in results:
        print(f"{result['name']:20} | Apoptosis: {result['apoptosis']:5} | Survival: {result['survival_score']}/3 | Stress: {result['stress_score']}/2")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS FOR MINIMAL APOPTOSIS:")
    print("=" * 50)
    print("✅ TURN ON (survival factors):")
    print("   - Oxygen_supply: True")
    print("   - Glucose_supply: True") 
    print("   - FGFR_stimulus: True (FGF growth factor)")
    print("   - EGFR_stimulus: True (EGF growth factor)")
    print("   - cMET_stimulus: True (HGF growth factor)")
    print("   - MCT1_stimulus: True (lactate for metabolic flexibility)")
    print()
    print("❌ TURN OFF (stress factors):")
    print("   - DNA_damage: False")
    print("   - Growth_Inhibitor: False")
    print("   - All inhibitor drugs: EGFRI, FGFRI, cMETI, MCT1I, MCT4I, GLUT1I = False")
    print()
    print("🎯 OPTIMAL ANTI-APOPTOSIS INPUT COMBINATION:")
    optimal_inputs = {
        'Oxygen_supply': True,
        'Glucose_supply': True,
        'FGFR_stimulus': True,
        'EGFR_stimulus': True,
        'cMET_stimulus': True,
        'MCT1_stimulus': True,
        'DNA_damage': False,
        'Growth_Inhibitor': False,
        'EGFRI': False,
        'FGFRI': False,
        'cMETI': False,
        'MCT1I': False,
        'MCT4I': False,
        'GLUT1I': False
    }
    
    for input_name, state in optimal_inputs.items():
        print(f"   {input_name}: {state}")

if __name__ == "__main__":
    main()
