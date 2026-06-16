"""Commit pending ABM intents in a standard reconciliation phase."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="Apply Reconciliation",
    description="Commit pending move, resource, birth, and removal intents.",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],
    requires=[],
    contract={
        "phase": "reconciliation",
        "reads": ["intent.*", "agent.collection", "resource.collection", "space.self"],
        "writes": ["agent.collection", "resource.self", "space.self"],
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
    """
    pop = env.population
    domain = env.domain
    intents = env.intents

    if pop is None:
        env.clear_intents()
        return True

    # Resource deltas are source/sink terms; commit after all deltas are queued.
    if domain is not None:
        for intent in intents.get("resource_delta", []):
            resource = domain.resource(intent["resource"])
            resource.deposit(intent["position"], float(intent.get("amount", 0.0)))
        for resource in domain.resources():
            resource.apply_sources()

    for intent in intents.get("move", []):
        agent = pop.agent_by_id(intent["agent_id"])
        if agent is not None:
            pop.relocate(agent, pop.space.normalize(intent["target"]))

    # Consume intents transfer a resource amount to an agent state variable.
    if domain is not None:
        for intent in intents.get("consume_resource", []):
            agent = pop.agent_by_id(intent["agent_id"])
            if agent is None:
                continue
            resource = domain.resource(intent["resource"])
            pos = intent.get("position", agent.position)
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

    env.clear_intents()
    return True
