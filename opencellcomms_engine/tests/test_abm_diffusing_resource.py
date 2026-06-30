"""Stage 1 gate for the MicroC ABM migration: DiffusingResource faithfully wraps
the legacy FiPy solver.

A DiffusingResource is a Resource-shaped view over a shared
MultiSubstanceSimulator (the existing diffusion solver). This proves:
  1. driving the solve through the resource yields the SAME field as the legacy
     solver invoked directly (faithful wrap — numerics identical by construction);
  2. the field<->position bridge is the documented 1:1 (values()[y, x] == at(x, y)),
     including asymmetric points;
  3. the solve actually diffuses (non-trivial, depleted at a sink tile).

See docs/MICROC_ABM_MIGRATION_PLAN.md (Stage 1). Needs FiPy.
"""
import sys
from pathlib import Path

import pytest

# The simulation/config layer uses bare `config.*` / `core.*` imports, so `src/`
# must be importable as a root (conftest only adds the engine root).
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

pytest.importorskip("fipy")

import numpy as np  # noqa: E402

from src.abm import DiffusingResource, LatticeWorld  # noqa: E402
from src.config.config import DiffusionConfig, DomainConfig, SubstanceConfig  # noqa: E402
from src.core.domain import MeshManager  # noqa: E402
from src.core.units import Concentration, Length  # noqa: E402
from src.simulation.multi_substance_simulator import MultiSubstanceSimulator  # noqa: E402

N = 20                                   # 20x20 grid, dx = 400um / 20 = 20um
SOURCE = {(5, 13): {"O2": -3.0e-16}}     # asymmetric sink at world (x=5, y=13)


def _build_sim():
    domain = DomainConfig(size_x=Length(400, "um"), size_y=Length(400, "um"),
                          nx=N, ny=N, dimensions=2, cell_height=Length(20, "um"))

    class Cfg:  # only the attrs the diffusion path reads
        pass

    cfg = Cfg()
    cfg.domain = domain
    cfg.diffusion = DiffusionConfig()
    cfg.substances = {
        "O2": SubstanceConfig(
            name="O2", diffusion_coeff=1e-9, production_rate=0.0, uptake_rate=0.0,
            initial_value=Concentration(0.28, "mM"),
            boundary_value=Concentration(0.28, "mM"), boundary_type="fixed"),
    }
    return MultiSubstanceSimulator(cfg, MeshManager(domain, verbose=False), verbose=False)


def test_diffusing_resource_matches_legacy_solver():
    # legacy reference: solve directly on the simulator
    legacy = _build_sim()
    legacy.update(SOURCE)
    legacy_field = legacy.state.substances["O2"].concentrations.copy()

    # resource path: drive the same solve through DiffusingResource
    sim = _build_sim()
    world = LatticeWorld(N, N, 1.0, "bounded", "bounded")
    res = DiffusingResource("O2", world, sim)
    res.diffuse(SOURCE)
    res_field = res.values()

    # (1) faithful wrap: bit-identical field
    assert np.array_equal(legacy_field, res_field)

    # (2) 1:1 bridge: at(x, y) == values()[y, x], incl. asymmetric points
    for (x, y) in [(5, 13), (0, 0), (N - 1, N - 1), (3, 17)]:
        assert res.at((x, y)) == res_field[y, x]

    # (3) the solve actually diffused: non-trivial, depleted at the sink tile
    assert not np.allclose(res_field, res_field.flat[0])
    assert res_field[13, 5] < res_field[0, 0]
