"""Burn forager sugar and mark depleted agents for removal."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Metabolize",
    description="Agent burns sugar; dies (requests removal) if it runs out",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=[],
)
def metabolize(env: BiologicalContext, **kwargs):
    agent = env.agent
    if agent is None:
        return True

    agent.set("sugar", agent.get("sugar", 0.0) - agent.get("metabolism", 1.0))
    if agent.get("sugar", 0.0) < 0:
        agent.die()
    return True
