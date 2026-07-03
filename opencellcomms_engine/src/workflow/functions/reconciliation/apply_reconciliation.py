"""Commit pending ABM intents in a standard reconciliation phase."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


# Intent kinds this standard reconciler knows how to commit. A model that emits
# a *custom* intent kind (env.emit_intent("my_kind", ...)) authors its own
# collective reconciler node; this one leaves unrecognized kinds untouched so
# that downstream node can still see and commit them (see module docstring).
HANDLED_INTENTS = ("resource_delta", "move", "consume_resource", "add_agent", "remove_agent")


@register_function(
    display_name="Apply Reconciliation",
    description="Commit pending move, resource, birth, and removal intents.",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=["abm_population"],
    contract={
        "reads": ["intent.*", "agent.collection", "resource.collection", "world.self"],
        "writes": ["agent.collection", "resource.self", "world.self"],
        "consumes": ["intent.*"],
        "emits": [],
    },
)
def apply_reconciliation(env: BiologicalContext, cull_dead: bool = True, **kwargs):
    """Apply queued intents without adding domain decisions to the workflow node.

    The function is deliberately mechanical: it commits requests that previous
    behavior/coupling nodes already expressed. Existing direct-mutation models
    still work; when ``cull_dead`` is true, agents marked dead by older behavior
    functions are also removed here.

    Move arbitration
    ----------------
    Moves are committed with one-agent-per-tile exclusion: intents are processed
    in the (already random, seeded) order agents were asked, and a move lands only
    if the target tile is still free. Contenders that lose a tile stay put. Without
    this, two agents that independently pick the same tile in the same round would
    both relocate onto it, desyncing the occupancy index.

    Position resolution
    -------------------
    A consume intent with no explicit position is resolved to the agent's position
    *after* moves commit, so "eat where I end up" is correct even when the agent's
    chosen move was denied by arbitration.

    Custom intents
    --------------
    Only the kinds in ``HANDLED_INTENTS`` are consumed here; any other kind an
    author emitted (``env.emit_intent("my_kind", ...)``) is left in place for a
    downstream custom reconciler node to commit and clear.
    """
    pop = env.population
    domain = env.domain
    intents = env.intents

    if pop is None:
        _clear_handled(env)
        return True

    # Resource deltas are source/sink terms; commit after all deltas are queued.
    if domain is not None:
        for intent in intents.get("resource_delta", []):
            resource = domain.resource(intent["resource"])
            resource.deposit(intent["position"], float(intent.get("amount", 0.0)))
        for resource in domain.resources():
            resource.apply_sources()

    # Moves: commit with one-agent-per-tile exclusion (see docstring).
    world = pop.world
    for intent in intents.get("move", []):
        agent = pop.agent_by_id(intent["agent_id"])
        if agent is None:
            continue
        target = world.normalize(intent["target"])
        if target == agent.position:
            continue
        if world.is_free(target):
            pop.relocate(agent, target)
        # else: tile taken this round — agent stays put.

    # Consume intents transfer a resource amount to an agent state variable.
    if domain is not None:
        for intent in intents.get("consume_resource", []):
            agent = pop.agent_by_id(intent["agent_id"])
            if agent is None:
                continue
            resource = domain.resource(intent["resource"])
            # Resolve position at commit time (post-move) when not pinned.
            pos = intent.get("position") or agent.position
            available = float(resource.at(pos))
            requested = intent.get("amount")
            taken = available if requested is None else min(max(float(requested), 0.0), available)
            if hasattr(resource, "set_at"):
                resource.set_at(pos, available - taken)
            else:
                resource.deposit(pos, -taken)
                resource.apply_sources()
            store_as = intent.get("store_as") or intent["resource"]
            agent.set(store_as, agent.get(store_as, 0.0) + taken)

    for intent in intents.get("add_agent", []):
        state = intent.get("state") or {}
        pop.spawn(intent["position"], kind=intent.get("kind"), **state)

    remove_ids = {intent["agent_id"] for intent in intents.get("remove_agent", [])}
    if remove_ids:
        pop.cull(lambda agent: agent.id in remove_ids)

    if cull_dead:
        pop.cull()

    _clear_handled(env)
    return True


def _clear_handled(env: BiologicalContext) -> None:
    """Drop only the intent kinds this reconciler consumed, so a custom reconciler
    node downstream can still see and commit its own kinds."""
    intents = env.intents
    for kind in HANDLED_INTENTS:
        intents.pop(kind, None)
