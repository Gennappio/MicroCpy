"""
REUSABLE gene network functions for workflows.

These are REUSABLE, GRANULAR nodes:
- Initialize Population: creates N cells (without gene networks)
- Initialize Gene Networks: attaches gene networks to all cells
- Set Gene Network Input States: sets input nodes for all cells (FIXED during propagation)
- Print Gene Network States: prints statistics

Input nodes (is_input=True) are NEVER updated during propagation.
"""

from .standalone_gene_network import (
    # REUSABLE nodes
    initialize_population,
    add_mock_substance,
    add_mock_association,
    initialize_gene_networks,
    set_gene_network_inputs,
    apply_associations_to_inputs,
    update_gene_networks_standalone,
    print_gene_network_states,
    # Mock classes for building test context
    MockPopulation,
    MockPopulationState,
    MockCell,
    MockCellState,
    MockPosition,
    MockSimulator,
    MockConfig,
    UniformConcentration,
)

__all__ = [
    # REUSABLE nodes
    'initialize_population',
    'add_mock_substance',
    'add_mock_association',
    'initialize_gene_networks',
    'set_gene_network_inputs',
    'apply_associations_to_inputs',
    'update_gene_networks_standalone',
    'print_gene_network_states',
    # Mock classes
    'MockPopulation',
    'MockPopulationState',
    'MockCell',
    'MockCellState',
    'MockPosition',
    'MockSimulator',
    'MockConfig',
    'UniformConcentration',
]
