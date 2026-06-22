"""
Setup Resource — create one scalar resource field on the world.

An INITIALIZATION node that adds a named ``FieldResource`` to the Domain. Put it
on a resource's Setup canvas, followed by the seed behaviour that fills it.
"""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function
from src.workflow.logging import log_always


@register_function(
    display_name="Setup Resource",
    description="Add a named scalar resource field to the world",
    category="INITIALIZATION",
    parameters=[
        {"name": "name", "type": "STRING", "description": "Resource field name", "default": "field"},
        {"name": "initial", "type": "FLOAT", "description": "Initial value everywhere", "default": 0.0},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["*"],
    requires=[],
)
def setup_resource(env: BiologicalContext, name: str = "field", initial: float = 0.0, **kwargs) -> bool:
    from src.abm import FieldResource

    domain = env.domain
    if domain is None:
        log_always("[ERROR] [setup_resource] No 'domain' in context — run setup_world first")
        return False
    domain.add_resource(FieldResource(name, domain.world, initial=float(initial)))
    print(f"[setup_resource] '{name}' (initial={initial})")
    return True
