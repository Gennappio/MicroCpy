"""Import all Prostate adapter functions to trigger @register_function.

Loaded by the engine's registry so the prostate-specific nodes appear in
the GUI palette and resolve in workflow JSONs.
"""

from opencellcomms_adapters.prostate.functions.initialization.setup_prostate_params import (  # noqa: F401
    setup_prostate_params,
)
from opencellcomms_adapters.prostate.functions.intracellular.apply_drug_sensitivity_inputs import (  # noqa: F401
    apply_drug_sensitivity_inputs,
)
from opencellcomms_adapters.prostate.functions.intracellular.run_prostate_physiboss_step import (  # noqa: F401
    run_prostate_physiboss_step,
)
from opencellcomms_adapters.prostate.functions.intercellular.apply_prostate_boolean_effects import (  # noqa: F401
    apply_prostate_boolean_effects,
)
