"""
Setup World — create the discrete tile-grid world for a class-layer ABM model.

A single INITIALIZATION node that builds the World (the grid + topology), the
Domain (which owns resources), and the Population (which owns agents), and puts
them in the context. Resources are added by `setup_resource` nodes; agents are
placed by per-kind placement nodes. Visible and observable like any node.
"""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function
from src.workflow.logging import log_always


@register_function(
    display_name="Setup World",
    description="Create the tile-grid world (World + Domain + Population) in the context",
    category="INITIALIZATION",
    parameters=[
        {"name": "size_x", "type": "INT", "description": "Grid width (tiles)", "default": 50},
        {"name": "size_y", "type": "INT", "description": "Grid height (tiles)", "default": 50},
        {"name": "tile_size", "type": "FLOAT", "description": "Physical tile size", "default": 1.0},
        {"name": "topology_x", "type": "STRING", "description": "X topology", "default": "toroidal", "options": ["bounded", "toroidal"]},
        {"name": "topology_y", "type": "STRING", "description": "Y topology", "default": "toroidal", "options": ["bounded", "toroidal"]},
        {"name": "seed", "type": "INT", "description": "RNG seed override (0 = use the workflow top-level 'seed')", "default": 0},
    ],
    inputs=["context"],
    outputs=["domain", "abm_population"],
    cloneable=False,
    compatible_kernels=["*"],
    requires=[],
)
def setup_world(env: BiologicalContext, size_x: int = 50, size_y: int = 50, tile_size: float = 1.0,
                topology_x: str = "toroidal", topology_y: str = "toroidal", seed: int = 0, **kwargs) -> bool:
    from src.abm import Domain, LatticeWorld, Population

    world = LatticeWorld(int(size_x), int(size_y), float(tile_size), topology_x, topology_y)
    domain = Domain(world)
    # The run-level seed (workflow top-level "seed", resolved in execute_main and
    # stored in context['seed']) is authoritative. The node's own `seed` param is
    # an override used only when explicitly set non-zero.
    effective_seed = int(seed) if int(seed) else int(env.raw_context.get("seed", 0) or 0)
    population = Population(world, config=env.raw_context.get("config"), context=env.raw_context, seed=effective_seed)
    population.domain = domain

    env.raw_context["domain"] = domain
    env.raw_context["abm_population"] = population
    print(f"[setup_world] {world.nx}x{world.ny} world ({topology_x}/{topology_y})")
    return True
