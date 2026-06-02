"""Initialization biology primitives extracted from the engine.

Population / cell / gene-network creation that the engine no longer owns
(engine = kernel + spatial + IO only).
"""
from .setup_population import setup_population
from .generate_initial_cells import generate_initial_cells
from .setup_gene_network import setup_gene_network
from .setup_associations import setup_associations, add_association
from .setup_maboss import setup_maboss
from .initialize_gene_states import initialize_gene_states
from .load_cells_from_csv import load_cells_from_csv
from .load_cells_from_vtk import load_cells_from_vtk

__all__ = [
    'setup_population',
    'generate_initial_cells',
    'setup_gene_network',
    'setup_associations',
    'add_association',
    'setup_maboss',
    'initialize_gene_states',
    'load_cells_from_csv',
    'load_cells_from_vtk',
]
