"""Cross-step census/totals history + env.plot_timeseries.

Nothing accumulated population or resource state across steps before this; a
"population over time" plot required a hand-rolled accumulator. These cover the
opt-in Population.record_census / Domain.record_totals buffers and the typed
env.plot_timeseries helper.
"""

import warnings

warnings.simplefilter("ignore")

from src.abm.domain import Domain
from src.abm.population import Population
from src.abm.resource import FieldResource
from src.abm.world import LatticeWorld
from src.biology.context import BiologicalContext


def _world():
    sp = LatticeWorld(8, 8, 1, "toroidal", "toroidal")
    pop = Population(sp, seed=1)
    dom = Domain(sp)
    dom.add_resource(FieldResource("sugar", sp, initial=2.0))
    pop.domain = dom
    return sp, pop, dom


def test_record_census_accumulates_across_steps():
    sp, pop, _ = _world()
    pop.spawn((1, 1), kind="forager")
    pop.record_census(step=0)
    pop.spawn((2, 2), kind="forager")
    pop.record_census(step=1)

    assert len(pop.history) == 2
    assert pop.history[0] == {"step": 0, "count": 1, "by_kind": {"forager": 1}}
    assert pop.history[1]["count"] == 2


def test_record_totals_tracks_resource_over_time():
    sp, _, dom = _world()
    # 8x8 grid @ initial 2.0 -> total 128.0
    dom.record_totals(step=0)
    dom.resource("sugar").set_at((0, 0), 0.0)
    dom.record_totals(step=1)

    assert len(dom.history) == 2
    assert dom.history[0]["totals"]["sugar"] == 128.0
    assert dom.history[1]["totals"]["sugar"] == 126.0


def test_plot_timeseries_writes_file(tmp_path):
    sp, pop, _ = _world()
    env = BiologicalContext({"plots_dir": str(tmp_path)})
    assert str(env.plots_dir) == str(tmp_path)

    counts = [1, 2, 3]
    out = env.plot_timeseries({"population": counts}, "pop_over_time.png",
                              title="Population", ylabel="count")
    assert out.exists()
    assert out.name == "pop_over_time.png"
