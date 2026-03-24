"""
Import all Jayatilake adapter functions to trigger @register_function
decorator execution. This module is imported by the engine's registry.py
so that experiment-specific functions appear in the function palette.
"""

# Gene network functions (hardcoded NetLogo/hierarchical node names)
from opencellcomms_adapters.jayatilake.functions.gene_network.initialize_netlogo_gene_networks import initialize_netlogo_gene_networks
# from opencellcomms_adapters.jayatilake.functions.gene_network.initialize_hierarchical_gene_networks import initialize_hierarchical_gene_networks  # legacy
from opencellcomms_adapters.jayatilake.functions.gene_network.propagate_gene_networks_netlogo import propagate_gene_networks_netlogo
# from opencellcomms_adapters.jayatilake.functions.gene_network.update_gene_networks_standalone import update_gene_networks_standalone  # legacy
# from opencellcomms_adapters.jayatilake.functions.gene_network.propagate_and_update_gene_networks import propagate_and_update_gene_networks  # legacy

# Intracellular functions (hardcoded substance/gene mappings)
from opencellcomms_adapters.jayatilake.functions.intracellular.update_gene_networks import update_gene_networks
from opencellcomms_adapters.jayatilake.functions.intracellular.update_gene_networks_v2 import update_gene_networks_v2
# from opencellcomms_adapters.jayatilake.functions.intracellular.update_gene_networks_hierarchical import update_gene_networks_hierarchical  # legacy
# from opencellcomms_adapters.jayatilake.functions.intracellular.run_maboss_step import run_maboss_step  # legacy

# Intercellular functions (hardcoded phenotype markers)
from opencellcomms_adapters.jayatilake.functions.intercellular.mark_necrotic_cells import mark_necrotic_cells
from opencellcomms_adapters.jayatilake.functions.intercellular.mark_apoptotic_cells import mark_apoptotic_cells
from opencellcomms_adapters.jayatilake.functions.intercellular.mark_growth_arrest_cells import mark_growth_arrest_cells
from opencellcomms_adapters.jayatilake.functions.intercellular.mark_proliferating_cells import mark_proliferating_cells
from opencellcomms_adapters.jayatilake.functions.intercellular.force_proliferation import force_proliferation

# Finalization functions (experiment-specific plots)
# from opencellcomms_adapters.jayatilake.functions.finalization.generate_atp_plots import generate_atp_plots  # legacy
# from opencellcomms_adapters.jayatilake.functions.finalization.generate_cell_plots import generate_cell_plots  # legacy
# from opencellcomms_adapters.jayatilake.functions.finalization.generate_initial_plots import generate_initial_plots  # legacy
from opencellcomms_adapters.jayatilake.functions.finalization.generate_iteration_plots import generate_iteration_plots
from opencellcomms_adapters.jayatilake.functions.finalization.generate_summary_plots import generate_summary_plots
# from opencellcomms_adapters.jayatilake.functions.finalization.plot_concentration_heatmaps import plot_concentration_heatmaps  # legacy
# from opencellcomms_adapters.jayatilake.functions.finalization.save_maboss_results import save_maboss_results  # legacy
