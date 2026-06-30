"""Stage 2 GO/NO-GO gate for the MicroC ABM migration: the new motor's
cell -> reaction -> diffusion coupling deposits oxygen sinks on the SAME
substance cells as the legacy solver.

A few static cells consume oxygen at a fixed rate (no Michaelis-Menten, no
Picard loop yet -- that's Stage 4). We compare two paths:

  legacy:  reactions {bio_pos: {Oxygen: -rate}}  ->  simulator.update
  new:     abm agents placed at bio_pos  ->  reactions read from agent.position
           ->  DiffusingResource.diffuse  ->  simulator.update

The crux is coordinates: cells live on a 75x75 bio-grid, substances on a 50x50
mesh; the solver scales raw cell positions into the mesh when depositing sources.
The new motor matches legacy with zero conversion iff agents live on the bio-grid
(LatticeWorld tile_size == cell_height) and reactions are keyed by raw
agent.position. This test proves that end to end.

See docs/MICROC_ABM_MIGRATION_PLAN.md (Stage 2). Needs FiPy.
"""
import sys
from pathlib import Path

import pytest

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

pytest.importorskip("fipy")

import numpy as np  # noqa: E402

from src.abm import DiffusingResource, Domain, LatticeWorld, Population  # noqa: E402
from src.config.config import DiffusionConfig, DomainConfig, SubstanceConfig  # noqa: E402
from src.core.domain import MeshManager  # noqa: E402
from src.core.units import Concentration, Length  # noqa: E402
from src.simulation.multi_substance_simulator import MultiSubstanceSimulator  # noqa: E402

SIZE_UM = 1500
CELL_UM = 20
NX = 50
BIO = SIZE_UM // CELL_UM                  # 75
RATE = 3.0e-16                           # fixed oxygen uptake per cell (mol/s)
CELLS = [(38, 23), (36, 53), (26, 30)]   # bio-grid positions


def _build_sim():
    domain = DomainConfig(size_x=Length(SIZE_UM, "um"), size_y=Length(SIZE_UM, "um"),
                          nx=NX, ny=NX, dimensions=2, cell_height=Length(CELL_UM, "um"))

    class Cfg:
        pass

    cfg = Cfg()
    cfg.domain = domain
    cfg.diffusion = DiffusionConfig()
    cfg.substances = {
        "Oxygen": SubstanceConfig(
            name="Oxygen", diffusion_coeff=1e-9, production_rate=0.0, uptake_rate=0.0,
            initial_value=Concentration(0.28, "mM"),
            boundary_value=Concentration(0.28, "mM"), boundary_type="fixed"),
    }
    return MultiSubstanceSimulator(cfg, MeshManager(domain, verbose=False), verbose=False)


def test_oxygen_slice_new_motor_matches_legacy():
    # --- legacy path: reactions keyed by raw position, direct solver call ---
    legacy = _build_sim()
    legacy.update({pos: {"Oxygen": -RATE} for pos in CELLS})
    legacy_field = legacy.state.substances["Oxygen"].concentrations.copy()

    # --- new motor: agents on the 75x75 bio-grid world ---
    world = LatticeWorld(SIZE_UM, SIZE_UM, CELL_UM, "bounded", "bounded")
    assert (world.nx, world.ny) == (BIO, BIO)            # tile_size == cell_height

    sim = _build_sim()
    dom = Domain(world)
    dom.add_resource(DiffusingResource("Oxygen", world, sim))
    pop = Population(world, seed=0)
    pop.domain = dom
    for (px, py) in CELLS:
        a = pop.spawn((px, py), oxygen_consumption=RATE)
        assert a is not None and a.position == (px, py)   # placement round-trips

    # Collective coupling (seed of the Stage-3 diffuse behaviour): RAW positions,
    # exactly like the legacy _collect_reactions_from_cells.
    reactions = {a.position: {"Oxygen": -a.get("oxygen_consumption", 0.0)}
                 for a in pop.agents()}
    dom.resource("Oxygen").diffuse(reactions)
    new_field = dom.resource("Oxygen").values()

    # (1) GATE: new-motor field is bit-identical to the legacy solver
    assert np.array_equal(legacy_field, new_field)

    # (2) coordinate crux: each source landed at the bio->substance scaled cell
    for (px, py) in CELLS:
        i, j = int(px * NX / BIO), int(py * NX / BIO)
        assert new_field[j, i] < 0.28
