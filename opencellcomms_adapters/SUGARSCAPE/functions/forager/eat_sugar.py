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
    requires=[],
    operates_on=["sugar"],
)
def eat_sugar(env: BiologicalContext, **kwargs):
    agent = env.agent
    if agent is None:
        return True

    target = agent.get("_pending_position", agent.position)
    env.request_consume_resource("sugar", position=target, store_as="sugar")
    return True
