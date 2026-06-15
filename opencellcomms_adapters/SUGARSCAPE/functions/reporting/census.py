"""Print a compact Sugarscape population/resource census."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Census",
    description="Print a one-line census (agents + resource totals)",
    category="FINALIZATION",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=[],
)
def census(env: BiologicalContext, **kwargs):
    pop, domain = env.population, env.domain
    parts = [f"agents={pop.count()}"] + [
        f"{resource.name}={resource.total():.0f}" for resource in domain.resources()
    ]
    print("[census] " + "  ".join(parts))
    return True
