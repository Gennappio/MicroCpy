"""Dendritic-cell chemotaxis up the CCL21 gradient, stopping on T0 contact.

Each dendritic cell reads CCL21 in its Moore neighbourhood (via the shared
diffusion field) and, with probability ``bias`` (the PhysiCell migration bias),
requests a move to the free neighbour tile holding the most CCL21 — climbing
toward the endothelial source, which sits by the T0 cluster. A DC already
adjacent to a T0 stops migrating (the contact that triggers differentiation).

Movement is queued as an intent; ``apply_reconciliation`` arbitrates contested
tiles (one agent per tile). The PhysiCell rule "CCL21 decreases migration bias"
is approximated here by the local-maximum stop (a DC at a CCL21 peak has no
higher neighbour, so it stays) plus the contact stop — the literal Hill half-max
(=2, in physical units) does not transfer to the lattice field's arbitrary scale.
"""
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Chemotax up CCL21",
    description="Dendritic cell climbs the CCL21 gradient (migration bias), stopping when "
                "adjacent to a T0 cell.",
    category="INTERCELLULAR",
    parameters=[
        {"name": "bias", "type": "FLOAT",
         "description": "Migration bias: fraction of steps moved up-gradient vs random walk (PhysiCell 0.8)",
         "default": 0.8, "min_value": 0.0, "max_value": 1.0},
        {"name": "vision", "type": "INT",
         "description": "Sensing radius (tiles). >1 so the DC sees across the coarser CCL21 mesh.",
         "default": 4, "min_value": 1},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["abm_population", "simulator"],
)
def chemotax_ccl21(env: BiologicalContext, bias: float = 0.8, vision: int = 4, **kwargs) -> bool:
    agent = env.agent
    if agent is None:
        return True

    # Contact stop: once next to a T0, stay put so differentiation can proceed.
    for nb in agent.neighbors(radius=1):
        if nb.kind == "tcell":
            return True

    world = env.world
    pos = agent.position
    free = [t for t in world.neighbors(pos, 1, "moore") if world.is_free(t)]
    if not free:
        return True                                    # boxed in

    # Find the highest-CCL21 tile within vision -- a radius > 1 is needed because
    # the bio-grid is finer than the CCL21 mesh, so immediate neighbours often read
    # the same value (a plateau the DC would otherwise stall on).
    best, best_c = pos, env.concentration("CCL21", at=pos)
    for tile in world.neighbors(pos, vision, "moore"):
        c = env.concentration("CCL21", at=tile)
        if c > best_c:
            best, best_c = tile, c

    # Migration bias: step one tile toward the peak with probability `bias`;
    # otherwise wander (the random-walk fraction, which also escapes flat regions
    # near the no-flux boundary where the gradient vanishes).
    if best != pos and env.rng.random() < bias:
        target = min(free, key=lambda t: world.distance(t, best))
    else:
        target = free[int(env.rng.integers(len(free)))]
    env.request_move(target=target)
    return True
