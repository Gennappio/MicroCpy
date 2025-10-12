#!/usr/bin/env python3
"""
Debug script to check if all cells get the same number of gene network propagation steps.
This investigates why center cells behave differently in the organoid simulation.

SIMPLIFIED VERSION: Just check the core issue without running full simulation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Let's just analyze the code structure to understand the problem

def analyze_gene_network_sharing_problem():
    """
    Analyze the core problem: All cells share the same gene network instance.

    This is the root cause of the center cell behavior issue.
    """

    print("[SEARCH] GENE NETWORK SHARING PROBLEM ANALYSIS")
    print("=" * 50)

    print("\n PROBLEM DESCRIPTION:")
    print("In CellPopulation.update_gene_networks(), all cells share the same gene network instance.")
    print("This means:")
    print("  1. Cell A sets input states on shared gene network")
    print("  2. Cell A runs N propagation steps")
    print("  3. Cell B sets input states on SAME gene network (overwrites A's state)")
    print("  4. Cell B runs N propagation steps")
    print("  5. Cell C sets input states on SAME gene network (overwrites B's state)")
    print("  6. ...")
    print("  7. Last cell processed determines final gene network state for ALL cells")

    print("\n[TARGET] WHY CENTER CELLS BEHAVE DIFFERENTLY:")
    print("The order in which cells are processed matters:")
    print("  - If center cells are processed LAST, they get the 'correct' gene network state")
    print("  - If center cells are processed EARLY, their state gets overwritten by later cells")
    print("  - Dictionary iteration order in Python can be influenced by:")
    print("    * Cell creation order")
    print("    * Cell ID hash values")
    print("    * Memory layout")

    print("\n[TOOL] EVIDENCE FROM CODE:")
    print("In src/biology/population.py, line 699:")
    print("  for cell_id, cell in self.state.cells.items():")
    print("    # ... calculate gene_inputs for this cell ...")
    print("    self.gene_network.set_input_states(gene_inputs)  # OVERWRITES previous cell's inputs!")
    print("    gene_states = self.gene_network.step(steps)      # Uses current inputs only")

    print("\n[IDEA] SOLUTION:")
    print("Each cell needs its own gene network instance, OR")
    print("Gene network state needs to be saved/restored for each cell.")

    print("\n VERIFICATION:")
    print("To verify this is the problem:")
    print("  1. Add logging to see cell processing order")
    print("  2. Check if center cells are consistently processed in a different order")
    print("  3. Verify that increasing propagation steps helps because it gives")
    print("     more time for the gene network to reach the same final state")
    print("     regardless of the specific input sequence")

    print("\n[WARNING]  CURRENT WORKAROUND:")
    print("Increasing propagation_steps helps because:")
    print("  - More steps = more gene updates per cell")
    print("  - Gene networks have more time to converge to stable states")
    print("  - Reduces sensitivity to the exact input sequence")
    print("  - But this is inefficient and doesn't fix the root cause")

    print("\n[TARGET] NEXT STEPS:")
    print("1. Confirm this analysis by checking cell processing order")
    print("2. Implement proper fix: separate gene network instances per cell")
    print("3. Test that the fix resolves the center cell behavior issue")

if __name__ == "__main__":
    analyze_gene_network_sharing_problem()
