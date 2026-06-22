"""Unit tests for the ABM Agent + Population (occupancy, ask, cull, coupling)."""

import warnings

warnings.simplefilter("ignore")

from src.abm.domain import Domain
from src.abm.population import Population
from src.abm.resource import FieldResource
from src.abm.world import LatticeWorld
from src.biology.context import BiologicalContext


def world():
    sp = LatticeWorld(8, 8, 1, "toroidal", "toroidal")
    pop = Population(sp, seed=1)
    dom = Domain(sp)
    dom.add_resource(FieldResource("sugar", sp, initial=1.0))
    pop.domain = dom
    return sp, pop, dom


def test_spawn_and_occupancy():
    sp, pop, _ = world()
    a = pop.spawn((2, 2), sugar=10.0)
    assert a is not None and pop.count() == 1 and not sp.is_free((2, 2))
    assert pop.spawn((2, 2)) is None  # occupied tile rejected


def test_move_updates_occupancy():
    sp, pop, _ = world()
    a = pop.spawn((2, 2))
    a.move_to((3, 3))
    assert sp.is_free((2, 2)) and not sp.is_free((3, 3)) and a.position == (3, 3)


def test_consume_deposits_and_applies():
    sp, pop, dom = world()
    a = pop.spawn((1, 1))
    a.consume("sugar", 1.0)
    dom.resource("sugar").apply_sources()
    assert dom.resource("sugar").at((1, 1)) == 0.0


def test_sense_reads_field_at_position():
    sp, pop, dom = world()
    a = pop.spawn((4, 4))
    dom.resource("sugar").set_at((4, 4), 7.0)
    assert a.sense("sugar") == 7.0


def test_die_then_cull_removes():
    sp, pop, _ = world()
    a = pop.spawn((0, 0))
    pop.spawn((1, 0))
    a.die()
    assert pop.cull() == 1 and pop.count() == 1 and sp.is_free((0, 0))


def test_cull_predicate():
    sp, pop, _ = world()
    pop.spawn((0, 0), sugar=-1.0)
    pop.spawn((1, 0), sugar=5.0)
    pop.cull(lambda ag: ag.get("sugar", 0) < 0)
    assert pop.count() == 1


def test_ask_visits_every_agent_once():
    sp, pop, dom = world()
    for i in range(5):
        pop.spawn((i, 0))
    env = BiologicalContext({"domain": dom, "abm_population": pop})
    seen = []
    pop.on_agent_step(lambda e: seen.append(e.agent.id))
    pop.run_agent_step(env, order="sequential")
    assert len(seen) == 5 and len(set(seen)) == 5


def test_populate_constant_trait():
    sp, pop, _ = world()
    placed = pop.populate(10, sugar=3.0)
    assert placed == 10 and pop.count() == 10
    assert all(a.get("sugar") == 3.0 for a in pop.agents())
