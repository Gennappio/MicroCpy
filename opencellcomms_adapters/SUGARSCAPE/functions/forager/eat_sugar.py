"""Let a forager consume sugar on its current tile."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Eat Sugar",
    description="Agent eats sugar on its tile: everything, or a fixed amount per step",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=["abm_population", "domain"],
    operates_on=["sugar"],
    parameters=[
        {"name": "eat_all", "type": "BOOL",
         "description": "Eat everything on the tile (when on, amount is ignored)",
         "default": True},
        {"name": "amount", "type": "FLOAT",
         "description": "Sugar units eaten per step when eat_all is off (capped by what the tile holds)",
         "default": 1.0},
    ],
)
def eat_sugar(env: BiologicalContext, eat_all: bool = True, amount: float = 1.0, **kwargs):
    agent = env.agent
    if agent is None:
        return True

    # No position: reconciliation credits sugar at the agent's post-move tile,
    # after move arbitration has decided where it actually ends up.
    if eat_all:
        env.request_consume_resource("sugar", store_as="sugar")
    else:
        env.request_consume_resource("sugar", amount=float(amount), store_as="sugar")
    return True
