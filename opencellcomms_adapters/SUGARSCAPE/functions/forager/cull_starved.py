"""Remove foragers that ended the step with negative sugar."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Cull Starved Agents",
    description="Remove foragers whose sugar went negative this step",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=["abm_population"],
)
def cull_starved(env: BiologicalContext, **kwargs):
    # Runs AFTER apply_reconciliation, so each forager's sugar already reflects
    # this step's eat minus metabolism. A forager on a rich tile therefore is not
    # culled on its pre-eat balance (the classic Sugarscape order: eat, then die
    # if still broke).
    pop = env.population
    if pop is None:
        return True
    pop.cull(lambda a: a.get("sugar", 0.0) < 0)
    return True
