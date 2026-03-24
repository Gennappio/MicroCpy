"""Intracellular workflow functions.

Experiment-specific functions (update_gene_networks, update_gene_networks_v2,
update_gene_networks_hierarchical, run_maboss_step) have been moved to
opencellcomms_adapters/jayatilake/functions/intracellular/.
"""

from .update_metabolism import update_metabolism

__all__ = [
    'update_metabolism',
]

