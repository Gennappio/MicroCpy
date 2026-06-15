"""Create the initial Sugarscape forager population."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Place Foragers",
    description="Scatter a kind's agents on empty tiles with traits",
    category="INITIALIZATION",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=[],
    parameters=[
        {"name": "kind", "type": "STRING", "default": "forager"},
        {"name": "count", "type": "INT", "default": 300},
        {"name": "sugar_min", "type": "FLOAT", "default": 5.0},
        {"name": "sugar_max", "type": "FLOAT", "default": 25.0},
        {"name": "metabolism_min", "type": "FLOAT", "default": 1.0},
        {"name": "metabolism_max", "type": "FLOAT", "default": 4.0},
        {"name": "vision_min", "type": "INT", "default": 1},
        {"name": "vision_max", "type": "INT", "default": 6},
    ],
)
def place_foragers(
    env: BiologicalContext,
    kind: str = "forager",
    count: int = 300,
    sugar_min: float = 5.0,
    sugar_max: float = 25.0,
    metabolism_min: float = 1.0,
    metabolism_max: float = 4.0,
    vision_min: int = 1,
    vision_max: int = 6,
    **kwargs,
):
    env.population.populate(
        kind,
        int(count),
        sugar=lambda rng: float(rng.uniform(sugar_min, sugar_max)),
        metabolism=lambda rng: float(rng.uniform(metabolism_min, metabolism_max)),
        vision=lambda rng: int(rng.integers(vision_min, vision_max + 1)),
    )
    return True
