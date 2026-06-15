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

    sugar = env.resource("sugar")
    got = sugar.at(agent.position)
    sugar.set_at(agent.position, 0.0)
    agent.set("sugar", agent.get("sugar", 0.0) + got)
    return True
