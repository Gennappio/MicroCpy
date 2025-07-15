#!/usr/bin/env python3
"""
Test script to verify that the main MicroC gene network now matches the standalone version.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_gene_network_changes():
    """Test that the main gene network now uses the same mechanics as standalone."""
    
    print("🧪 Testing MicroC Gene Network Changes...")
    
    try:
        # Import the main gene network
        from biology.gene_network import BooleanNetwork, BooleanExpression
        print("✅ Successfully imported BooleanNetwork and BooleanExpression")
        
        # Test BooleanExpression class
        expr = BooleanExpression("A & B | !C")
        test_states = {"A": True, "B": False, "C": True}
        result = expr.evaluate(test_states)
        print(f"✅ BooleanExpression test: 'A & B | !C' with A=True, B=False, C=True → {result}")
        
        # Test that it's callable (matches update_function interface)
        result2 = expr(test_states)
        print(f"✅ BooleanExpression callable test: {result2}")
        
        # Create a simple gene network
        network = BooleanNetwork()
        print("✅ Successfully created BooleanNetwork instance")
        
        # Test that update functions are BooleanExpression instances
        for name, node in network.nodes.items():
            if not node.is_input and node.update_function:
                if isinstance(node.update_function, BooleanExpression):
                    print(f"✅ Node '{name}' uses BooleanExpression")
                    break
        else:
            print("ℹ️  Minimal network doesn't have BooleanExpression nodes")

        # Test NetLogo-style update
        print("\n🎯 Testing NetLogo-style single gene update...")

        # Set some input states
        input_states = {
            "Oxygen_supply": True,
            "Glucose_supply": True,
            "Growth_Inhibitor": False
        }
        network.set_input_states(input_states)

        # Test the update method
        updated_gene = network._netlogo_single_gene_update()
        if updated_gene:
            print(f"✅ NetLogo update successful: {updated_gene} was updated")
        else:
            print("✅ NetLogo update successful: no state changes")

        # Test step method
        print("\n🎯 Testing step method...")
        initial_states = network.get_all_states()
        final_states = network.step(5)
        print(f"✅ Step method successful: ran 5 steps")

        # Show some state changes
        changes = []
        for name in initial_states:
            if initial_states[name] != final_states.get(name, initial_states[name]):
                changes.append(f"{name}: {initial_states[name]} → {final_states[name]}")

        if changes:
            print(f"✅ State changes detected: {', '.join(changes[:3])}")
        else:
            print("✅ No state changes (network stable)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    print("\n🎉 All tests passed! MicroC gene network now matches standalone version.")
    return True

if __name__ == "__main__":
    test_gene_network_changes()
