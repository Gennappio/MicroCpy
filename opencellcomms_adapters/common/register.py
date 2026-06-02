"""Common adapter — generic biology / ABM primitives extracted from the engine.

The engine is **kernel + spatial + IO only**; everything that creates or evolves
cells, populations and gene networks lives here and is shared by the experiment
adapters (MicroC, jayatilake, PhysiBoSS). Experiment adapters may import from
`common`; they must not import each other.

Importing this module registers every function via `@register_function`.
"""

# Importing each package triggers its __init__, which imports the individual
# function modules (1 file = 1 function) and runs their decorators.
import opencellcomms_adapters.common.functions.gene_network      # noqa: F401
import opencellcomms_adapters.common.functions.intracellular     # noqa: F401
import opencellcomms_adapters.common.functions.intercellular     # noqa: F401
import opencellcomms_adapters.common.functions.initialization    # noqa: F401
import opencellcomms_adapters.common.functions.orchestrators     # noqa: F401
