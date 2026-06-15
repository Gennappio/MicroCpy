"""Regrow the Sugarscape resource field."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Grow Sugar",
    description="Regrow sugar toward its internal carrying-capacity landscape",
    category="ENVIRONMENT",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=[],
    operates_on=["sugar"],
    parameters=[
        {"name": "resource", "type": "STRING", "default": "sugar"},
        {"name": "rate", "type": "FLOAT", "default": 1.0},
    ],
)
def grow_sugar(
    env: BiologicalContext,
    resource: str = "sugar",
    rate: float = 1.0,
    **kwargs,
):
    sugar = env.resource(resource)
    if sugar.capacity is None:
        print(f"[grow_sugar] Resource '{resource}' has no capacity; run seed_sugar_capacity first")
        return False
    sugar.grow_to(sugar.capacity, float(rate))
    return True
