"""Seed the Sugarscape resource capacity landscape."""

import numpy as np

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Seed Sugar Capacity",
    description="Create the sugar carrying-capacity landscape and fill current sugar",
    category="INITIALIZATION",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=[],
    operates_on=["sugar"],
    parameters=[
        {"name": "resource", "type": "STRING", "default": "sugar"},
        {"name": "peak", "type": "FLOAT", "default": 4.0},
        {"name": "radius_frac", "type": "FLOAT", "default": 0.45},
        {"name": "fill_current", "type": "BOOL", "default": True},
    ],
)
def seed_sugar_capacity(
    env: BiologicalContext,
    resource: str = "sugar",
    peak: float = 4.0,
    radius_frac: float = 0.45,
    fill_current: bool = True,
    **kwargs,
):
    sp = env.world
    sugar = env.resource(resource)
    capacity = np.zeros_like(sugar.values())
    nx, ny = sp.nx, sp.ny
    centers = [(0.3 * nx, 0.7 * ny), (0.7 * nx, 0.3 * ny)]
    radius = max(1.0, radius_frac * nx)
    for tj in range(ny):
        for ti in range(nx):
            cap = 0.0
            for cx, cy in centers:
                d = ((ti - cx) ** 2 + (tj - cy) ** 2) ** 0.5
                cap = max(cap, peak * max(0.0, 1.0 - d / radius))
            capacity[tj, ti] = float(round(cap))
    sugar.capacity = capacity
    if fill_current:
        sugar.values()[:] = capacity
    return True
