"""Reconciliation semantics for the executor's intent path.

These pin the behaviour that the shipped ABM run depends on and that previously
had no coverage: move arbitration (one agent per tile), post-move resolution of
an unpinned consume, and pass-through of custom intent kinds.
"""

import numpy as np

from src.abm.domain import Domain
from src.abm.population import Population
from src.abm.resource import FieldResource
from src.abm.world import LatticeWorld
from src.biology.context import BiologicalContext
from src.workflow.functions.reconciliation.apply_reconciliation import apply_reconciliation


def _ctx(nx=6, ny=1, topology="bounded"):
    world = LatticeWorld(nx, ny, 1, topology, topology)
    pop = Population(world, context={}, seed=1)
    dom = Domain(world)
    dom.add_resource(FieldResource("sugar", world, initial=0.0))
    pop.domain = dom
    ctx = {"domain": dom, "abm_population": pop, "_rng": np.random.default_rng(0)}
    return ctx, world, dom, pop


def _positions(pop):
    return [c.state.position for c in pop.cellpop.state.cells.values()]


def test_move_arbitration_one_agent_per_tile():
    ctx, world, dom, pop = _ctx()
    a = pop.spawn((1, 0), kind="x")
    b = pop.spawn((3, 0), kind="x")
    for ag in (a, b):  # both aim for the same tile
        ctx["_current_agent"] = ag
        BiologicalContext(ctx).request_move(target=(2, 0))
    ctx["_current_agent"] = None

    apply_reconciliation(BiologicalContext(ctx))

    positions = _positions(pop)
    assert len(positions) == len(set(positions))          # no two agents share a tile
    assert len(pop.cellpop.state.spatial_grid) == pop.count()  # occupancy index consistent
    assert (2, 0) in positions                            # exactly one agent claimed it


def test_consume_resolves_at_post_move_tile():
    ctx, world, dom, pop = _ctx()
    sugar = dom.resource("sugar")
    sugar.set_at((2, 0), 10.0)
    a = pop.spawn((1, 0), kind="x", sugar=0.0)

    ctx["_current_agent"] = a
    env = BiologicalContext(ctx)
    env.request_move(target=(2, 0))
    env.request_consume_resource("sugar", store_as="sugar")  # no pinned position
    ctx["_current_agent"] = None

    apply_reconciliation(BiologicalContext(ctx))

    assert pop.agent_by_id(a.id).position == (2, 0)
    assert pop.agent_by_id(a.id).get("sugar") == 10.0     # ate at the tile it moved to
    assert sugar.at((2, 0)) == 0.0


def test_denied_move_consumes_at_actual_tile():
    """The loser of a contested move eats its actual tile, not the one it aimed at."""
    ctx, world, dom, pop = _ctx()
    sugar = dom.resource("sugar")
    sugar.set_at((2, 0), 10.0)
    sugar.set_at((3, 0), 4.0)
    a = pop.spawn((1, 0), kind="x", sugar=0.0)  # emitted first -> wins (2,0)
    b = pop.spawn((3, 0), kind="x", sugar=0.0)
    for ag in (a, b):
        ctx["_current_agent"] = ag
        env = BiologicalContext(ctx)
        env.request_move(target=(2, 0))
        env.request_consume_resource("sugar", store_as="sugar")
    ctx["_current_agent"] = None

    apply_reconciliation(BiologicalContext(ctx))

    assert pop.agent_by_id(a.id).position == (2, 0)
    assert pop.agent_by_id(a.id).get("sugar") == 10.0
    assert pop.agent_by_id(b.id).position == (3, 0)       # move denied, stayed put
    assert pop.agent_by_id(b.id).get("sugar") == 4.0      # ate its own tile


def test_custom_intent_is_preserved_for_downstream_reconciler():
    """apply_reconciliation clears only the kinds it handles, so a model's custom
    intent survives for its own reconciler node to commit."""
    ctx, world, dom, pop = _ctx()
    pop.spawn((1, 0), kind="x")
    env = BiologicalContext(ctx)
    env.emit_intent("paint_tile", color="red")
    env.request_remove_agent(agent_id="nobody")           # a handled kind, will be cleared

    apply_reconciliation(env)

    assert env.intents.get("paint_tile") == [{"color": "red"}]
    assert "remove_agent" not in env.intents              # handled kind was consumed


def test_remove_agent_intent_commits():
    ctx, world, dom, pop = _ctx()
    a = pop.spawn((0, 0), kind="x")
    pop.spawn((1, 0), kind="x")
    ctx["_current_agent"] = a
    BiologicalContext(ctx).request_remove_agent(reason="test")
    ctx["_current_agent"] = None

    apply_reconciliation(BiologicalContext(ctx))

    assert pop.count() == 1
    assert pop.agent_by_id(a.id) is None
