"""Burn forager sugar and mark depleted agents for removal."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Metabolize",
    description="Agent burns sugar (death is decided later, by cull_starved)",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=["abm_population"],
)
def metabolize(env: BiologicalContext, **kwargs):
    agent = env.agent
    if agent is None:
        return True

    # Self-state write (order-independent). Death is NOT decided here: eating is
    # deferred to reconciliation, so the balance is not final until this step's
    # sugar has been credited. cull_starved makes the starvation call afterwards.
    agent.set("sugar", agent.get("sugar", 0.0) - agent.get("metabolism", 1.0))
    return True
