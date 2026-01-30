"""
Workflow functions for OpenCellComms.

This module provides granular workflow functions organized by stage.
Each function is in its own file for easy viewing and editing in the GUI.

For backward compatibility, all functions are re-exported from this module.
"""

# Import granular intracellular functions
from .intracellular.update_metabolism import update_metabolism
from .intracellular.update_gene_networks import update_gene_networks
from .intracellular.update_gene_networks_v2 import update_gene_networks_v2

# Import granular diffusion functions
from .diffusion.run_diffusion_solver import run_diffusion_solver
from .diffusion.run_diffusion_solver_clamped import run_diffusion_solver_clamped
from .diffusion.run_diffusion_solver_coupled import run_diffusion_solver_coupled

# Import granular intercellular functions
from .intercellular.update_cell_division import update_cell_division
from .intercellular.update_cell_migration import update_cell_migration
from .intercellular.mark_necrotic_cells import mark_necrotic_cells
from .intercellular.mark_growth_arrest_cells import mark_growth_arrest_cells
from .intercellular.mark_apoptotic_cells import mark_apoptotic_cells
from .intercellular.mark_proliferating_cells import mark_proliferating_cells

# Import granular finalization functions
from .finalization.generate_initial_plots import generate_initial_plots
from .finalization.generate_summary_plots import generate_summary_plots
from .finalization.print_simulation_summary import print_simulation_summary
from .finalization.save_simulation_data import save_simulation_data
from .finalization.export_final_state import export_final_state
from .finalization.collect_statistics import collect_statistics

__all__ = [
    # Intracellular
    'update_metabolism',
    'update_gene_networks',
    'update_gene_networks_v2',
    # Diffusion
    'run_diffusion_solver',
    'run_diffusion_solver_clamped',
    'run_diffusion_solver_coupled',
    # Intercellular
    'update_cell_division',
    'update_cell_migration',
    'mark_necrotic_cells',
    'mark_growth_arrest_cells',
    'mark_apoptotic_cells',
    'mark_proliferating_cells',
    # Finalization
    'generate_initial_plots',
    'generate_summary_plots',
    'print_simulation_summary',
    'save_simulation_data',
    'export_final_state',
    'collect_statistics',
]

