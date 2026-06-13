"""
SUGARSCAPE adapter — Sugarscape on the ABM class layer.

The canonical proof of the Space/Agent/Population/Resource/Domain library: a
non-diffusing "sugar" field that grows back in place, and agents that move
toward sugar and eat it. Every per-step rule (growback, agent move/eat, cull)
is an ordinary, visible behaviour authored against the typed ``env`` classes.
"""

import opencellcomms_adapters.SUGARSCAPE.functions.behaviours.sugarscape  # noqa: F401
