"""
Workflow functions for OpenCellComms.

This module provides generic workflow functions organized by stage.
Each function is in its own file for easy viewing and editing in the GUI.

Biology functions (gene networks, metabolism, cell division/migration/death,
population & gene-network setup) have been moved to
opencellcomms_adapters/common/. The engine keeps only kernel / spatial / IO
functions.
"""

# Import diffusion functions
from .diffusion.run_diffusion_solver import run_diffusion_solver
from .diffusion.run_diffusion_solver_clamped import run_diffusion_solver_clamped
from .diffusion.run_diffusion_solver_coupled import run_diffusion_solver_coupled

# Import generic finalization functions
from .finalization.print_simulation_summary import print_simulation_summary
from .finalization.save_simulation_data import save_simulation_data
from .finalization.export_final_state import export_final_state
from .finalization.collect_statistics import collect_statistics
from .reconciliation.apply_reconciliation import apply_reconciliation

__all__ = [
    # Diffusion
    'run_diffusion_solver',
    'run_diffusion_solver_clamped',
    'run_diffusion_solver_coupled',
    # Finalization
    'print_simulation_summary',
    'save_simulation_data',
    'export_final_state',
    'collect_statistics',
    # Reconciliation
    'apply_reconciliation',
]
