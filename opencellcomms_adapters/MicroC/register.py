"""
MicroC adapter — registers the v7 microc model functions in the new ABM workflow format.

This adapter is a standalone re-expression of the jayatilake v7 model. It contains
its own copies of the adapter-side Python functions so it can be used without the
jayatilake adapter present.

When both jayatilake and MicroC are imported, the second registration of a given
function name is a benign overwrite (same code, same signature).
"""

# Gene network functions
import opencellcomms_adapters.MicroC.functions.gene_network.initialize_netlogo_gene_networks  # noqa: F401
import opencellcomms_adapters.MicroC.functions.gene_network.propagate_gene_networks_netlogo  # noqa: F401

# Fate functions
import opencellcomms_adapters.MicroC.functions.fate.mark_necrotic_cells  # noqa: F401
import opencellcomms_adapters.MicroC.functions.fate.mark_apoptotic_cells  # noqa: F401
import opencellcomms_adapters.MicroC.functions.fate.mark_growth_arrest_cells  # noqa: F401
import opencellcomms_adapters.MicroC.functions.fate.mark_proliferating_cells  # noqa: F401

# Reporting plots
import opencellcomms_adapters.MicroC.functions.reporting.generate_iteration_plots  # noqa: F401
import opencellcomms_adapters.MicroC.functions.reporting.generate_summary_plots  # noqa: F401
