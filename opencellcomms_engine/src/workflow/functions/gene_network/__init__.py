"""
REUSABLE gene network functions for workflows.

Each function is in its own file for easy viewing and editing in the GUI.

Gene networks are stored in context['gene_networks'] as a dict mapping
cell_id → BooleanNetwork instance. This keeps cell state clean and allows
gene network operations to be fully controlled by workflow functions.

Functions:
- initialize_population: creates N cells (without gene networks)
- initialize_gene_networks: creates gene networks for all cells (stored in context)
- set_gene_network_inputs: sets input nodes for all cells (FIXED during propagation)
- apply_associations_to_inputs: sets inputs based on substance concentrations
- update_gene_networks_standalone: propagates gene networks
- propagate_gene_networks: configurable propagation with update mode selection
- get_gene_network_states: retrieves current gene states from context
- print_gene_network_states: prints statistics

Helper functions:
- get_gene_network(context, cell_id): get a cell's gene network from context
- set_gene_network(context, cell_id, gn): set a cell's gene network in context
- remove_gene_network(context, cell_id): remove a cell's gene network

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
# Experiment-specific functions (initialize_netlogo_gene_networks,
# initialize_hierarchical_gene_networks, propagate_gene_networks_netlogo,
# update_gene_networks_standalone, propagate_and_update_gene_networks)
# have been moved to opencellcomms_adapters/jayatilake/functions/gene_network/.
from .initialize_population import initialize_population
from .initialize_gene_networks import initialize_gene_networks, get_gene_network, set_gene_network
from .set_gene_network_inputs import set_gene_network_inputs
from .apply_associations_to_inputs import apply_associations_to_inputs
from .propagate_gene_networks import propagate_gene_networks
from .get_gene_network_states import get_gene_network_states, remove_gene_network
from .print_gene_network_states import print_gene_network_states


__all__ = [
    # Workflow functions
    'initialize_population',
    'initialize_gene_networks',
    'set_gene_network_inputs',
    'apply_associations_to_inputs',
    'propagate_gene_networks',
    'get_gene_network_states',
    'print_gene_network_states',
    # Helper functions
    'get_gene_network',
    'set_gene_network',
    'remove_gene_network',
    # Mock helpers
    'MockPopulation',
    'MockPopulationState',
    'MockCell',
    'MockCellState',
    'MockPosition',
    'MockSimulator',
    'MockConfig',
]
