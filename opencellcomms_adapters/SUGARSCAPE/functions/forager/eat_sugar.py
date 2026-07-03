"""Let a forager consume sugar on its current tile."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Eat Sugar",
    description="Agent eats all sugar on its tile",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=["abm_population", "domain"],
    operates_on=["sugar"],
)
def eat_sugar(env: BiologicalContext, **kwargs):
    agent = env.agent
    if agent is None:
        return True

    # No position: reconciliation credits sugar at the agent's post-move tile,
    # after move arbitration has decided where it actually ends up.
    env.request_consume_resource("sugar", store_as="sugar")
    return True
