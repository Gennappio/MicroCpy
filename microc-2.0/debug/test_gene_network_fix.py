#!/usr/bin/env python3
"""
Test the gene network fix: each cell should have its own gene network instance.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.biology.gene_network import BooleanNetwork
from pathlib import Path

def test_gene_network_copy():
    """Test that the gene network copy method works correctly"""

    print(" TESTING GENE NETWORK COPY METHOD")
    print("=" * 50)

    # Create a gene network from the BND file
    bnd_file = Path("tests/jayatilake_experiment/jaya_microc.bnd")
    if not bnd_file.exists():
        print(f"[!] BND file not found: {bnd_file}")
        return False

    # Create original network
    original_network = BooleanNetwork(network_file=bnd_file)
    print(f"[+] Created original network with {len(original_network.nodes)} nodes")

    # Test copy method
    copied_network = original_network.copy()
    print(f"[+] Created copied network with {len(copied_network.nodes)} nodes")

    # Verify they are different instances
    if id(original_network) == id(copied_network):
        print("[!] FAILURE: Copy returned same instance!")
        return False

    print(f"[+] Networks are different instances: {id(original_network)} vs {id(copied_network)}")

    # Verify they have the same structure
    if len(original_network.nodes) != len(copied_network.nodes):
        print("[!] FAILURE: Different number of nodes!")
        return False

    # Test independence by setting different input states
    original_network.set_input_states({"Oxygen_supply": True, "Glucose_supply": False})
    copied_network.set_input_states({"Oxygen_supply": False, "Glucose_supply": True})

    # Check that they have different states
    orig_states = original_network.get_all_states()
    copy_states = copied_network.get_all_states()

    orig_oxygen = orig_states.get("Oxygen_supply", False)
    copy_oxygen = copy_states.get("Oxygen_supply", False)
    orig_glucose = orig_states.get("Glucose_supply", False)
    copy_glucose = copy_states.get("Glucose_supply", False)

    print(f"\n INDEPENDENCE TEST:")
    print(f"Original: Oxygen_supply={orig_oxygen}, Glucose_supply={orig_glucose}")
    print(f"Copy:     Oxygen_supply={copy_oxygen}, Glucose_supply={copy_glucose}")

    if orig_oxygen != copy_oxygen and orig_glucose != copy_glucose:
        print("[+] SUCCESS: Gene networks are independent!")
        return True
    else:
        print("[!] FAILURE: Gene networks are not independent!")
        return False

if __name__ == "__main__":
    success = test_gene_network_copy()
    if success:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        print("The gene network copy method is working correctly.")
        print("Each cell can now have its own independent gene network!")
    else:
        print("\n TESTS FAILED!")
        print("The gene network copy method needs more work.")
