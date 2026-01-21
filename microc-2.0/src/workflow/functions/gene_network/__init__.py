"""
REUSABLE gene network functions for workflows.

Each function is in its own file for easy viewing and editing in the GUI.

Functions:
- initialize_population: creates N cells (without gene networks)
- initialize_gene_networks: attaches gene networks to all cells
- set_gene_network_inputs: sets input nodes for all cells (FIXED during propagation)
- apply_associations_to_inputs: sets inputs based on substance concentrations
- update_gene_networks_standalone: propagates gene networks
- print_gene_network_states: prints statistics

Input nodes (is_input=True) are NEVER updated during propagation.
"""

# Mock helpers (for testing without full simulation)
from ._mock_helpers import (
    MockPopulation,
    MockPopulationState,
    MockCell,
    MockCellState,
    MockPosition,
    MockSimulator,
    MockConfig,
)

# Workflow functions (1 file = 1 function)
from .initialize_population import initialize_population
from .initialize_gene_networks import initialize_gene_networks
from .set_gene_network_inputs import set_gene_network_inputs
from .apply_associations_to_inputs import apply_associations_to_inputs
from .update_gene_networks_standalone import update_gene_networks_standalone
from .print_gene_network_states import print_gene_network_states

__all__ = [
    # Workflow functions
    'initialize_population',
    'initialize_gene_networks',
    'set_gene_network_inputs',
    'apply_associations_to_inputs',
    'update_gene_networks_standalone',
    'print_gene_network_states',
    # Mock helpers
    'MockPopulation',
    'MockPopulationState',
    'MockCell',
    'MockCellState',
    'MockPosition',
    'MockSimulator',
    'MockConfig',
]
