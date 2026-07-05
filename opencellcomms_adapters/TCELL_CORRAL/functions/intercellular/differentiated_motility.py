"""Fate-specific motility for naive and differentiated T cells.

Each cell moves at a per-fate speed (the probability of stepping one tile this
step): naive 0.8, Treg 0.5, Th1 0.0 (arrested), Th17 0.5 — the PhysiCell motility
speeds. A naive cell currently held in a dendritic-cell contact does not move (the
immunological synapse), so it stays put long enough to commit a fate. Th17 CCL21
uptake is handled separately in ``diffuse_ccl21``.

Moves are queued as intents; ``apply_reconciliation`` arbitrates contested tiles.
"""
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext

_SPEED = {"naive": 0.8, "Treg": 0.5, "Th1": 0.0, "Th17": 0.5}


@register_function(
    display_name="Differentiated Motility",
    description="Move a T cell at its fate-specific speed (Th1 arrested); a naive cell in "
                "DC contact is held so it can commit.",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["abm_population"],
)
def differentiated_motility(env: BiologicalContext, **kwargs) -> bool:
    agent = env.agent
    if agent is None:
        return True

    fate = agent.get("fate", "naive")
    speed = _SPEED.get(fate, 0.5)
    if speed <= 0.0:
        return True                                 # Th1: arrested

    # A naive cell in DC contact is held (immunological synapse) so it can commit.
    if fate == "naive" and any(nb.kind == "dendritic_cell" for nb in agent.neighbors(radius=1)):
        return True

    if env.rng.random() >= speed:
        return True                                 # did not move this step

    world = env.world
    free = [t for t in world.neighbors(agent.position, 1, "moore") if world.is_free(t)]
    if free:
        env.request_move(target=free[int(env.rng.integers(len(free)))])
    return True
