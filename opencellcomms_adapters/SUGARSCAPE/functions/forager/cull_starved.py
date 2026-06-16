"""Remove foragers marked dead during the current step."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Cull Starved Agents",
    description="Remove agents that ran out of sugar this step",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=[],
)
def cull_starved(env: BiologicalContext, **kwargs):
    from src.workflow.functions.reconciliation.apply_reconciliation import apply_reconciliation

    apply_reconciliation(env)
    return True
