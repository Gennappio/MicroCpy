"""ABM library extensions: 2D guard, boundary consistency, env conveniences,
plotting surface, and the generic recording layer."""

import warnings

warnings.simplefilter("ignore")

import numpy as np
import pytest

from src.abm.domain import Domain
from src.abm.population import Population
from src.abm.resource import DiffusingResource, FieldResource
from src.abm.world import LatticeWorld
from src.biology.context import BiologicalContext


def _world():
    sp = LatticeWorld(8, 8, 1, "toroidal", "toroidal")
    pop = Population(sp, seed=1)
    dom = Domain(sp)
    dom.add_resource(FieldResource("sugar", sp, initial=2.0))
    pop.domain = dom
    return sp, pop, dom


# --- #1 2D guard -------------------------------------------------------------
def test_lattice_world_rejects_3d():
    with pytest.raises(NotImplementedError):
        LatticeWorld(8, 8, 1, dimension=3)
    # 2D still constructs fine.
    assert LatticeWorld(8, 8, 1, dimension=2).dimension == 2


# --- #4 DiffusingResource normalizes boundary queries ------------------------
class _FakeSubstance:
    def __init__(self):
        self.seen = None

    def get_concentration_at(self, pos):
        self.seen = pos
        return 0.0


class _FakeSim:
    def __init__(self, name):
        self.state = type("S", (), {"substances": {name: _FakeSubstance()}})()


def test_diffusing_resource_at_normalizes():
    sp = LatticeWorld(8, 8, 1, "toroidal", "toroidal")
    sim = _FakeSim("o2")
    r = DiffusingResource("o2", sp, sim)
    r.at((-1, 0))
    # -1 wraps to nx-1 = 7 on a toroidal axis; the substance sees the normalized pos.
    assert sim.state.substances["o2"].seen == (7, 0)


def test_diffusing_resource_deposit_normalizes():
    sp = LatticeWorld(8, 8, 1, "toroidal", "toroidal")
    r = DiffusingResource("o2", sp, _FakeSim("o2"))
    r.deposit((-1, 0), 5.0)
    assert (7, 0) in r._pending and r._pending[(7, 0)] == 5.0


# --- #5 env conveniences -----------------------------------------------------
def test_env_rng_stable_and_matches_context():
    rng = np.random.default_rng(0)
    env = BiologicalContext({"_rng": rng})
    assert env.rng is rng
    assert env.rng is env.rng  # stable across calls


def test_env_rng_falls_back_and_persists():
    env = BiologicalContext({})
    r = env.rng
    assert r is not None and env.raw_context["_rng"] is r  # stored back


def test_env_resources_mirrors_domain():
    sp, pop, dom = _world()
    env = BiologicalContext({"domain": dom, "abm_population": pop})
    assert [r.name for r in env.resources] == ["sugar"]
    assert BiologicalContext({}).resources == []


# --- #2 plotting surface -----------------------------------------------------
def test_field_resource_heatmap_returns_axes():
    sp, _, dom = _world()
    ax = dom.resource("sugar").heatmap()
    assert ax is not None and hasattr(ax, "imshow")


def test_population_snapshot_groups_by_kind():
    sp, pop, _ = _world()
    pop.spawn((1, 1), kind="forager")
    pop.spawn((2, 3), kind="forager")
    pop.spawn((4, 4), kind="predator")
    snap = pop.snapshot()
    assert set(snap) == {"forager", "predator"}
    assert len(snap["forager"][0]) == 2 and len(snap["predator"][0]) == 1


def test_env_plot_field_writes_png(tmp_path):
    sp, pop, dom = _world()
    env = BiologicalContext({"domain": dom, "abm_population": pop, "plots_dir": str(tmp_path)})
    out = env.plot_field("sugar")
    assert out.exists() and out.name == "sugar.png"


# --- #3 recording layer ------------------------------------------------------
def test_env_record_accumulates_and_plots(tmp_path):
    env = BiologicalContext({"plots_dir": str(tmp_path), "current_step": 0})
    env.record("pop", 10, step=0)
    env.record("pop", 12, step=1)
    assert [e["value"] for e in env.records["pop"]] == [10, 12]
    out = env.plot_records(["pop"], "pop.png", title="Population")
    assert out.exists()
