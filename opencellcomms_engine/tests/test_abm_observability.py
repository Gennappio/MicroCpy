"""The observability snapshot summarizer is ABM-aware.

Population/Domain are summarized through their ``to_observation()`` (agent counts,
resource totals) instead of the constant ``<object at 0x...>`` repr, so a
step-over-step diff actually reflects the model changing.
"""

from src.abm.domain import Domain
from src.abm.population import Population
from src.abm.resource import FieldResource
from src.abm.world import LatticeWorld
from src.workflow.observability.context_snapshot import summarize_value


def _model():
    world = LatticeWorld(6, 1, 1, "bounded", "bounded")
    pop = Population(world, context={}, seed=1)
    dom = Domain(world)
    dom.add_resource(FieldResource("sugar", world, initial=0.0))
    pop.domain = dom
    return world, dom, pop


def test_population_summary_reports_counts_not_address():
    _, _, pop = _model()
    pop.spawn((0, 0), kind="forager")
    pop.spawn((1, 0), kind="forager")
    s = summarize_value(pop)
    assert s.type == "Population"
    assert s.preview["count"] == 2
    assert s.preview["by_kind"]["forager"] == 2


def test_population_summary_changes_when_agents_die():
    _, _, pop = _model()
    a = pop.spawn((0, 0), kind="forager")
    pop.spawn((1, 0), kind="forager")
    before = summarize_value(pop).preview["count"]
    a.die()
    pop.cull()
    after = summarize_value(pop).preview["count"]
    # The whole point: consecutive summaries differ, so the diff is not blind.
    assert (before, after) == (2, 1)


def test_domain_summary_reports_field_totals():
    _, dom, _ = _model()
    dom.resource("sugar").set_at((3, 0), 5.0)
    s = summarize_value(dom)
    assert s.type == "Domain"
    assert s.preview["totals"]["sugar"] == 5.0
