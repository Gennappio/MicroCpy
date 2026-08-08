"""Move a forager to the best visible sugar tile."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Move to Best Sugar",
    description="Agent moves to the most sugar within its vision",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=["abm_population", "domain"],
    operates_on=["sugar"],
    parameters=[
        {"name": "strategy", "type": "STRING",
         "description": "best = go to the richest visible tile; nearest = settle on the closest tile that improves on the current one (stops at the first sugar border it reaches)",
         "default": "best"},
        {"name": "explore_when_tied", "type": "BOOL",
         "description": "When no strictly richer tile is visible, hop to a random equally-good free tile instead of standing still (keeps foragers roaming on a uniform field)",
         "default": False},
    ],
)
def move_to_best_sugar(env: BiologicalContext, strategy: str = "best",
                       explore_when_tied: bool = False, **kwargs):
    agent = env.agent
    if agent is None:
        return True

    world = env.world
    sugar = env.resource("sugar")
    pos = agent.position
    vision = int(agent.get("vision", 1))
    best, best_sugar, best_distance = pos, sugar.at(pos), 0.0

    # Scan visible tiles in random order: neighbors() lists the downward ray
    # first, and exact ties (same sugar, same distance) keep the first tile
    # scanned — a fixed order would bias every tie toward "down".
    cells = world.neighbors(pos, vision, "axial")
    rng = env.raw_context.get("_rng")
    if rng is not None:
        cells = [cells[i] for i in rng.permutation(len(cells))]

    if strategy == "nearest":
        # Satisficer: settle on the closest free tile that improves on the
        # current one at all — foragers stop at the first sugar border they
        # reach instead of trekking to the summit.
        own_sugar = best_sugar
        nearest_distance = None
        for cell in cells:
            if not world.is_free(cell):
                continue
            if sugar.at(cell) > own_sugar:
                distance = world.distance(pos, cell)
                if nearest_distance is None or distance < nearest_distance:
                    best, nearest_distance = cell, distance
    else:
        for cell in cells:
            if not world.is_free(cell):
                continue
            visible_sugar = sugar.at(cell)
            distance = world.distance(pos, cell)
            if visible_sugar > best_sugar or (
                visible_sugar == best_sugar and distance < best_distance
            ):
                best, best_sugar, best_distance = cell, visible_sugar, distance

    # Queue the move only; reconciliation arbitrates contested tiles and eating
    # happens at the agent's actual post-move tile (see eat_sugar).
    if best != pos:
        env.request_move(target=best)
    elif explore_when_tied:
        # Nothing strictly richer in sight: roam among the equally-best free
        # tiles so foragers keep scanning plateaus instead of parking. Uses the
        # run RNG (no typed accessor exists for it) so runs stay seed-reproducible.
        ties = [
            cell
            for cell in world.neighbors(pos, vision, "axial")
            if world.is_free(cell) and sugar.at(cell) == best_sugar
        ]
        rng = env.raw_context.get("_rng")
        if ties and rng is not None:
            env.request_move(target=ties[int(rng.integers(len(ties)))])
    return True
