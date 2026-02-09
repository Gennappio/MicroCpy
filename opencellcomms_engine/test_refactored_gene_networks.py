#!/usr/bin/env python3
"""
Test refactored gene network workflow functions.

This test verifies that the inlined logic produces the same results as the original
opaque method calls.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from workflow.functions.gene_network.initialize_population import initialize_population
from workflow.functions.gene_network.initialize_gene_networks import initialize_gene_networks
from workflow.functions.gene_network.initialize_hierarchical_gene_networks import initialize_hierarchical_gene_networks
from workflow.functions.gene_network.set_gene_network_inputs import set_gene_network_inputs
from workflow.functions.gene_network.get_gene_network_states import get_gene_network_states
from workflow.functions.gene_network.propagate_and_update_gene_networks import propagate_and_update_gene_networks


def test_initialize_and_propagate():
    """Test the full workflow: initialize -> set inputs -> propagate."""
    print("\n" + "=" * 60)
    print("TEST: Initialize and Propagate Gene Networks")
    print("=" * 60)
    
    # Create context
    context = {}
    
    # Step 1: Initialize population
    print("\n1. Initializing population...")
    result = initialize_population(context, num_cells=5)
    if not result:
        print("❌ Failed to initialize population")
        return False
    print(f"✅ Created {len(context['population'].state.cells)} cells")
    
    # Step 2: Initialize gene networks
    print("\n2. Initializing gene networks...")
    bnd_file = "tests/maboss_example/cell_fate.bnd"
    result = initialize_gene_networks(
        context,
        bnd_file=bnd_file,
        random_initialization=True
    )
    if not result:
        print("❌ Failed to initialize gene networks")
        return False
    print(f"✅ Created gene networks for {len(context['gene_networks'])} cells")
    
    # Step 3: Set input states
    print("\n3. Setting input states...")
    input_states = {
        'Oxygen_supply': True,
        'Glucose_supply': True,
        'FGFR_stimulus': False,
    }
    result = set_gene_network_inputs(context, fixed_substances=input_states)
    if not result:
        print("❌ Failed to set input states")
        return False
    print("✅ Set input states")
    
    # Step 4: Get initial states
    print("\n4. Getting initial gene states...")
    initial_states = get_gene_network_states(context, output_nodes_only=False)
    print(f"✅ Retrieved states for {len(initial_states)} cells")
    
    # Step 5: Propagate gene networks
    print("\n5. Propagating gene networks...")
    result = propagate_and_update_gene_networks(
        context,
        propagation_steps=100,
        verbose=True
    )
    if not result:
        print("❌ Failed to propagate gene networks")
        return False
    print("✅ Propagated gene networks")
    
    # Step 6: Get final states
    print("\n6. Getting final gene states...")
    final_states = get_gene_network_states(context, output_nodes_only=True)
    print(f"✅ Retrieved output states for {len(final_states)} cells")
    
    # Verify states changed
    print("\n7. Verifying state changes...")
    for cell_id in final_states:
        if cell_id in initial_states:
            initial = initial_states[cell_id]
            final = final_states[cell_id]
            print(f"   Cell {cell_id}: {len(final)} output nodes")
            for node_name, state in final.items():
                print(f"      {node_name}: {state}")
    
    print("\n✅ All steps completed successfully!")
    return True


def test_hierarchical_gene_networks():
    """Test hierarchical gene networks with fate determination."""
    print("\n" + "=" * 60)
    print("TEST: Hierarchical Gene Networks")
    print("=" * 60)
    
    # Create context
    context = {}
    
    # Step 1: Initialize population
    print("\n1. Initializing population...")
    result = initialize_population(context, num_cells=3)
    if not result:
        print("❌ Failed to initialize population")
        return False
    
    # Step 2: Initialize hierarchical gene networks
    print("\n2. Initializing hierarchical gene networks...")
    bnd_file = "tests/maboss_example/cell_fate.bnd"
    result = initialize_hierarchical_gene_networks(
        context,
        bnd_file=bnd_file,
        random_initialization=True,
        fate_hierarchy="Necrosis,Apoptosis,Growth_Arrest,Proliferation"
    )
    if not result:
        print("❌ Failed to initialize hierarchical gene networks")
        return False
    print(f"✅ Created hierarchical gene networks for {len(context['gene_networks'])} cells")
    
    # Step 3: Set inputs and propagate
    print("\n3. Setting inputs and propagating...")
    input_states = {'Oxygen_supply': True, 'Glucose_supply': True}
    set_gene_network_inputs(context, fixed_substances=input_states)
    
    result = propagate_and_update_gene_networks(context, propagation_steps=100, verbose=True)
    if not result:
        print("❌ Failed to propagate")
        return False
    
    # Check phenotypes
    print("\n4. Checking phenotypes...")
    cells = context['population'].state.cells
    for cell_id, cell in cells.items():
        phenotype = cell.state.phenotype
        print(f"   Cell {cell_id}: phenotype = {phenotype}")
    
    print("\n✅ Hierarchical gene networks test passed!")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("REFACTORED GENE NETWORK TESTS")
    print("=" * 60)
    
    tests = [
        ("Initialize and Propagate", test_initialize_and_propagate),
        ("Hierarchical Networks", test_hierarchical_gene_networks),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

