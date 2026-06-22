"""
SUGARSCAPE adapter - Sugarscape on the ABM class layer.

The canonical proof of the World/Agent/Population/Resource/Domain library: a
non-diffusing "sugar" field that grows back in place, and agents that move
toward sugar and eat it. Every per-step rule (growback, agent move/eat, cull)
is an ordinary, visible behaviour authored against the typed ``env`` classes.
"""

import opencellcomms_adapters.SUGARSCAPE.functions.forager.cull_starved  # noqa: F401
import opencellcomms_adapters.SUGARSCAPE.functions.forager.eat_sugar  # noqa: F401
import opencellcomms_adapters.SUGARSCAPE.functions.forager.metabolize  # noqa: F401
import opencellcomms_adapters.SUGARSCAPE.functions.forager.move_to_best_sugar  # noqa: F401
import opencellcomms_adapters.SUGARSCAPE.functions.forager.place_foragers  # noqa: F401
import opencellcomms_adapters.SUGARSCAPE.functions.reporting.census  # noqa: F401
import opencellcomms_adapters.SUGARSCAPE.functions.sugar.grow_sugar  # noqa: F401
import opencellcomms_adapters.SUGARSCAPE.functions.sugar.seed_sugar_capacity  # noqa: F401
