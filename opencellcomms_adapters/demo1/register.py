"""demo1 adapter registration.

Importing this module runs the @register_function decorators in each function
module, putting them in the registry so the GUI/engine can find them.
One file = one function (matching the other adapters' convention).
"""

import opencellcomms_adapters.demo1.prima_func            # func1  # noqa: F401
import opencellcomms_adapters.demo1.opencellcomms_adapters  # func2  # noqa: F401
