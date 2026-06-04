#!/usr/bin/env python
"""
Simple MaBoSS Demo Script
========================

This script demonstrates the basic usage of pyMaBoSS for Boolean network simulation.
It simulates a simple cell fate decision model with the following nodes:
- DNA_damage: Input signal representing DNA damage
- p53: Tumor suppressor gene activated by DNA damage  
- Apoptosis: Cell death triggered by p53
- Proliferation: Cell division (inhibited by p53)
- Survival: Cell survival signal

Usage:
    python run_maboss_demo.py

Requirements:
    pip install maboss (or conda install -c colomoto pymaboss)
"""

import os
import sys

# Get the directory of this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    """Run the MaBoSS simulation demo."""
    
    print("=" * 60)
    print("MaBoSS Boolean Network Simulation Demo")
    print("=" * 60)
    
    # Try to import maboss
    try:
        import maboss
        print(f"[OK] pyMaBoSS loaded successfully")
    except ImportError:
        print("[ERROR] pyMaBoSS is not installed.")
        print("Install it with: pip install maboss")
        print("Or with conda: conda install -c colomoto pymaboss")
        sys.exit(1)
    
    # Define paths to model files
    bnd_file = os.path.join(SCRIPT_DIR, "cell_fate.bnd")
    cfg_file = os.path.join(SCRIPT_DIR, "cell_fate.cfg")
    
    # Check if files exist
    if not os.path.exists(bnd_file):
        print(f"[ERROR] BND file not found: {bnd_file}")
        sys.exit(1)
    if not os.path.exists(cfg_file):
        print(f"[ERROR] CFG file not found: {cfg_file}")
        sys.exit(1)
    
    print(f"\n[INFO] Loading model files:")
    print(f"  - BND: {bnd_file}")
    print(f"  - CFG: {cfg_file}")
    
    # Load the model
    print("\n[STEP 1] Loading MaBoSS model...")
    sim = maboss.load(bnd_file, cfg_file)
    print(f"  [OK] Model loaded successfully!")
    
    # Print model information
    print(f"\n[INFO] Model nodes: {list(sim.network.keys())}")
    print(f"[INFO] Initial states:")
    for node_name, node in sim.network.items():
        print(f"  - {node_name}")
    
    # Run simulation (Scenario 1: No DNA damage)
    print("\n[STEP 2] Running simulation: No DNA damage (healthy cell)...")
    sim.network.set_istate("DNA_damage", [1.0, 0.0])  # DNA_damage = OFF (prob OFF=1, prob ON=0)
    result1 = sim.run()
    print("  [OK] Simulation completed!")

    # Print results
    print("\n[RESULTS] No DNA Damage scenario:")
    probas1 = result1.get_last_states_probtraj()
    print("  Final state probabilities:")
    # Handle both dict and DataFrame results
    if hasattr(probas1, 'items') and not hasattr(probas1, 'iloc'):
        items = list(probas1.items())
    else:
        # It's a DataFrame - get last row as dict
        last_row = probas1.iloc[-1].to_dict()
        items = [(col, val) for col, val in last_row.items() if col != 'Time']
    for state, prob in sorted(items, key=lambda x: -float(x[1])):
        if float(prob) > 0.01:  # Only show states with >1% probability
            print(f"    {state}: {float(prob):.2%}")

    # Run simulation (Scenario 2: With DNA damage)
    print("\n[STEP 3] Running simulation: DNA damage (stressed cell)...")
    sim.network.set_istate("DNA_damage", [0.0, 1.0])  # DNA_damage = ON (prob OFF=0, prob ON=1)
    result2 = sim.run()
    print("  [OK] Simulation completed!")

    # Print results
    print("\n[RESULTS] DNA Damage scenario:")
    probas2 = result2.get_last_states_probtraj()
    print("  Final state probabilities:")
    # Handle both dict and DataFrame results
    if hasattr(probas2, 'items') and not hasattr(probas2, 'iloc'):
        items = list(probas2.items())
    else:
        # It's a DataFrame - get last row as dict
        last_row = probas2.iloc[-1].to_dict()
        items = [(col, val) for col, val in last_row.items() if col != 'Time']
    for state, prob in sorted(items, key=lambda x: -float(x[1])):
        if float(prob) > 0.01:  # Only show states with >1% probability
            print(f"    {state}: {float(prob):.2%}")
    
    # Compare results
    print("\n[SUMMARY]")
    print("-" * 40)
    print("  No DNA damage -> Cell should survive and proliferate")
    print("  DNA damage    -> Cell should undergo apoptosis")
    print("-" * 40)
    
    print("\n[OK] MaBoSS demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

