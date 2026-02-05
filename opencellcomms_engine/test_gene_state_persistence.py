#!/usr/bin/env python
"""Test that gene_states persist correctly through the workflow.

NOTE: Gene networks are stored in context['gene_networks'] (dict mapping cell_id → BooleanNetwork),
not in cell.state. This test validates the new context-based architecture.
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from src.biology.cell import Cell, CellState
from src.biology.gene_network import BooleanNetwork
from pathlib import Path

print("="*60)
print("TEST: Gene State Persistence Through Cell Updates")
print("="*60)

# 1. Create a cell
cell = Cell(position=(50, 75), phenotype="Growth_Arrest")
cell_id = cell.state.id
print(f"1. Created cell at position {cell.state.position}")
print(f"   Cell ID: {cell_id}")
print(f"   Initial gene_states: {cell.state.gene_states}")

# 2. Create a gene network and store it in context (NOT in cell.state)
bnd_path = Path("tests/maboss_example/cell_fate.bnd")
if not bnd_path.exists():
    print(f"   ERROR: BND file not found at {bnd_path}")
    sys.exit(1)

class MockGeneNetworkConfig:
    def __init__(self):
        self.bnd_file = str(bnd_path)
        self.random_initialization = True
        self.propagation_steps = 20
        self.output_nodes = ["Proliferation", "Apoptosis", "Growth_Arrest", "Necrosis"]
        self.nodes = {}

class MockConfig:
    def __init__(self):
        self.gene_network = MockGeneNetworkConfig()

config = MockConfig()
gene_network = BooleanNetwork(config=config)

# Store gene network in context (new architecture - gene networks in context, not cell.state)
context = {'gene_networks': {}}
context['gene_networks'][cell_id] = gene_network
print(f"2. Stored gene network in context['gene_networks']['{cell_id}']")
print(f"   gene_network in context: {cell_id in context['gene_networks']}")

# 3. Set input states (simulating what update_gene_networks does)
input_states = {
    'Oxygen_supply': True,  # Above threshold
    'Glucose_supply': True,  # Above threshold
}
context['gene_networks'][cell_id].set_input_states(input_states)
print(f"3. Set input states: {input_states}")

# 4. Propagate gene network (access from context)
gene_states = context['gene_networks'][cell_id].step(20, mode="synchronous")
print(f"4. Propagated gene network, got {len(gene_states)} gene states")
print(f"   glycoATP = {gene_states.get('glycoATP')}")
print(f"   mitoATP = {gene_states.get('mitoATP')}")

# 5. Update cell state with gene_states (exactly as update_gene_networks does)
cell.state = cell.state.with_updates(gene_states=gene_states)
print(f"5. Updated cell.state.gene_states")
print(f"   cell.state.gene_states['glycoATP'] = {cell.state.gene_states.get('glycoATP')}")
print(f"   cell.state.gene_states['mitoATP'] = {cell.state.gene_states.get('mitoATP')}")

# 6. Simulate what population.state.with_updates does
updated_cells = {'test_cell': cell}
print(f"6. Stored cell in updated_cells dict")

# 7. Retrieve cell and check gene_states
retrieved_cell = updated_cells['test_cell']
print(f"7. Retrieved cell from dict")
print(f"   retrieved_cell.state.gene_states['glycoATP'] = {retrieved_cell.state.gene_states.get('glycoATP')}")
print(f"   retrieved_cell.state.gene_states['mitoATP'] = {retrieved_cell.state.gene_states.get('mitoATP')}")

# 8. Check if population.state.with_updates copies correctly
from src.biology.population import PopulationState

pop_state = PopulationState(
    cells={'test_cell': cell},
    spatial_grid={(50, 75): 'test_cell'},
    total_cells=1
)
print(f"8. Created PopulationState with cell")

# 9. Create new state with with_updates
new_pop_state = pop_state.with_updates(cells=updated_cells)
print(f"9. Called pop_state.with_updates(cells=updated_cells)")

# 10. Check if gene_states survived
cell_from_new_state = new_pop_state.cells['test_cell']
print(f"10. Retrieved cell from new_pop_state")
print(f"   cell.state.gene_states['glycoATP'] = {cell_from_new_state.state.gene_states.get('glycoATP')}")
print(f"   cell.state.gene_states['mitoATP'] = {cell_from_new_state.state.gene_states.get('mitoATP')}")

print("\n" + "="*60)
if cell_from_new_state.state.gene_states.get('glycoATP') and cell_from_new_state.state.gene_states.get('mitoATP'):
    print("SUCCESS: Gene states persisted correctly!")
else:
    print("FAILURE: Gene states were lost!")
print("="*60)

