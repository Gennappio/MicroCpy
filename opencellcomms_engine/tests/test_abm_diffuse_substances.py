"""Stage 3 gate for the MicroC ABM migration: all 8 substances as
DiffusingResources + the env-style diffuse_substances behaviour.

Proves:
  1. add_diffusing_resources wraps every substance of a MultiSubstanceSimulator as
     a DiffusingResource on a Domain, each exposing its field 1:1;
  2. the resource-driven COLLECTIVE solve (all 8 coupled substances at once) is
     bit-identical to the legacy simulator on the same multi-substance reactions,
     including cross-substance effects (oxygen consumed / lactate produced);
  3. diffuse_substances(env) delegates to the existing coupled Picard solver, so
     it produces the same fields as the legacy node on an identical context.

(The full Picard-with-live-cells run is validated end to end in Stage 4 against
the golden reference.) See docs/MICROC_ABM_MIGRATION_PLAN.md. Needs FiPy.
"""
import sys
from pathlib import Path

import pytest

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

pytest.importorskip("fipy")

import numpy as np  # noqa: E402

from src.abm import (  # noqa: E402
    DiffusingResource, Domain, LatticeWorld, Population, add_diffusing_resources,
)
from src.biology.context import BiologicalContext  # noqa: E402
from src.config.config import DiffusionConfig, DomainConfig, SubstanceConfig  # noqa: E402
from src.core.domain import MeshManager  # noqa: E402
from src.core.units import Concentration, Length  # noqa: E402
from src.simulation.multi_substance_simulator import MultiSubstanceSimulator  # noqa: E402
from src.workflow.functions.diffusion.diffuse_substances import diffuse_substances  # noqa: E402
from src.workflow.functions.diffusion.run_diffusion_solver_coupled import (  # noqa: E402
    run_diffusion_solver_coupled,
)

SIZE_UM, CELL_UM, NX = 1500, 20, 50
BIO = SIZE_UM // CELL_UM                  # 75

# The 8 MicroC substances (name, D, production_rate, initial, boundary, BC type).
SUBSTANCES = [
    ("Oxygen", 3.0e-11, 0.0, 0.07, 0.07, "fixed"),
    ("Glucose", 6.70e-11, 0.0, 0.1, 5.0, "fixed"),
    ("Lactate", 6.70e-13, 3.0e-09, 1.0, 1.0, "fixed"),
    ("H", 1.0e-9, 2.0e-20, 4.0e-5, 4.0e-5, "fixed"),
    ("TGFA", 5.18e-11, 2.0e-20, 0.0, 0.0, "neumann"),
    ("FGF", 2.2e-10, 0.0, 0.0, 0.0, "neumann"),
    ("HGF", 8.50e-11, 0.0, 2.0e-6, 2.0e-6, "fixed"),
    ("GI", 5.18e-11, 0.0, 0.0, 0.0, "neumann"),
]
NAMES = [n for (n, *_rest) in SUBSTANCES]

REACTIONS = {(38, 23): {"Oxygen": -3.0e-16, "Glucose": -3.0e-17, "Lactate": 3.0e-16},
             (26, 30): {"Oxygen": -2.0e-16}}


def _build_sim():
    domain = DomainConfig(size_x=Length(SIZE_UM, "um"), size_y=Length(SIZE_UM, "um"),
                          nx=NX, ny=NX, dimensions=2, cell_height=Length(CELL_UM, "um"))

    class Cfg:
        pass

    cfg = Cfg()
    cfg.domain = domain
    cfg.diffusion = DiffusionConfig()
    cfg.substances = {
        n: SubstanceConfig(name=n, diffusion_coeff=D, production_rate=p, uptake_rate=0.0,
                           initial_value=Concentration(iv, "mM"),
                           boundary_value=Concentration(bv, "mM"), boundary_type=bt)
        for (n, D, p, iv, bv, bt) in SUBSTANCES
    }
    return MultiSubstanceSimulator(cfg, MeshManager(domain, verbose=False), verbose=False)


def _world():
    return LatticeWorld(SIZE_UM, SIZE_UM, CELL_UM, "bounded", "bounded")


def test_eight_substances_wrap_as_resources():
    sim = _build_sim()
    dom = Domain(_world())
    add_diffusing_resources(dom, _world(), sim)
    assert {r.name for r in dom.resources()} == set(NAMES)
    for r in dom.resources():
        assert isinstance(r, DiffusingResource)
        assert np.array_equal(r.values(), sim.state.substances[r.name].concentrations)


def test_collective_solve_matches_legacy():
    sim = _build_sim()
    dom = Domain(_world())
    add_diffusing_resources(dom, _world(), sim)
    dom.resource("Oxygen").diffuse(REACTIONS)        # one collective solve, all 8

    legacy = _build_sim()
    legacy.update(REACTIONS)

    for n in NAMES:
        assert np.array_equal(dom.resource(n).values(),
                              legacy.state.substances[n].concentrations)

    # cross-substance effect at the bio->substance scaled cell of (38, 23)
    i, j = int(38 * NX / BIO), int(23 * NX / BIO)
    assert dom.resource("Oxygen").values()[j, i] < 0.07     # consumed below boundary
    assert dom.resource("Lactate").values()[j, i] > 1.0     # produced above boundary


@pytest.mark.slow   # ~4s: the Picard loop over 8 substances
def test_diffuse_substances_delegates():
    world = _world()

    sim_a = _build_sim()
    dom_a = Domain(world)
    add_diffusing_resources(dom_a, world, sim_a)
    pop_a = Population(world, seed=0)
    pop_a.domain = dom_a
    diffuse_substances(BiologicalContext({
        "simulator": sim_a, "population": pop_a.cellpop,
        "domain": dom_a, "abm_population": pop_a,
    }))

    sim_b = _build_sim()
    pop_b = Population(world, seed=0)
    run_diffusion_solver_coupled({"simulator": sim_b, "population": pop_b.cellpop})

    for n in NAMES:
        assert np.array_equal(sim_a.state.substances[n].concentrations,
                              sim_b.state.substances[n].concentrations)
