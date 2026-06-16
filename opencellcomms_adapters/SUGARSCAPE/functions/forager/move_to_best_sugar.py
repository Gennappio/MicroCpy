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
    requires=[],
    operates_on=["sugar"],
)
def move_to_best_sugar(env: BiologicalContext, **kwargs):
    agent = env.agent
    if agent is None:
        return True

    space = env.space
    sugar = env.resource("sugar")
    pos = agent.position
    vision = int(agent.get("vision", 1))
    best, best_sugar, best_distance = pos, sugar.at(pos), 0.0

    for cell in space.neighbors(pos, vision, "axial"):
        if not space.is_free(cell):
            continue
        visible_sugar = sugar.at(cell)
        distance = space.distance(pos, cell)
        if visible_sugar > best_sugar or (
            visible_sugar == best_sugar and distance < best_distance
        ):
            best, best_sugar, best_distance = cell, visible_sugar, distance

    agent.set("_pending_position", best)
    if best != pos:
        env.request_move(target=best)
    return True
