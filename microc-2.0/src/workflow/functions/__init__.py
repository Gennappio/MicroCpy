"""
Workflow functions for MicroC.

This module provides granular workflow functions organized by stage.
Each function is in its own file for easy viewing and editing in the GUI.

For backward compatibility, all functions are re-exported from this module.
"""

# Import granular intracellular functions
from .intracellular.update_metabolism import update_metabolism
from .intracellular.update_gene_networks import update_gene_networks
from .intracellular.update_phenotypes import update_phenotypes
from .intracellular.remove_dead_cells import remove_dead_cells

# Import granular diffusion functions
from .diffusion.run_diffusion_solver import run_diffusion_solver

# Import granular intercellular functions
from .intercellular.update_cell_division import update_cell_division
from .intercellular.update_cell_migration import update_cell_migration

__all__ = [
    # Intracellular
    'update_metabolism',
    'update_gene_networks',
    'update_phenotypes',
    'remove_dead_cells',
    # Diffusion
    'run_diffusion_solver',
    # Intercellular
    'update_cell_division',
    'update_cell_migration',
]

