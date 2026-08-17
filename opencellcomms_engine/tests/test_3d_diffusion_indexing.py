"""3D solver indexing: deposit → solve → read-back must agree on ANY grid.

FiPy orders cells x-fastest (flat id = k*nx*ny + j*nx + i). The 3D path uses
that native ordering; these tests pin it on a deliberately ASYMMETRIC grid
(nx, ny, nz = 5, 4, 3), where any transposed labeling scrambles the field.
The 2D path's historical transposed-but-square-exact convention is asserted
unchanged.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

pytest.importorskip("fipy")

import numpy as np  # noqa: E402

from src.config.config import DiffusionConfig, DomainConfig, SubstanceConfig  # noqa: E402
from src.core.domain import MeshManager  # noqa: E402
from src.core.units import Concentration, Length  # noqa: E402
from src.simulation.multi_substance_simulator import (  # noqa: E402
    MultiSubstanceSimulator,
    field_to_fipy_order,
)

NX, NY, NZ = 5, 4, 3
CELL_UM = 20.0
# 1:1 bio-to-voxel mapping: sizes = n * cell_height
SIZE_X, SIZE_Y, SIZE_Z = NX * CELL_UM, NY * CELL_UM, NZ * CELL_UM


def _build_sim_3d(boundary_value=1.0):
    domain = DomainConfig(
        dimensions=3,
        size_x=Length(SIZE_X, "um"), size_y=Length(SIZE_Y, "um"),
        size_z=Length(SIZE_Z, "um"),
        nx=NX, ny=NY, nz=NZ,
        cell_height=Length(CELL_UM, "um"),
    )

    class Cfg:
        pass

    cfg = Cfg()
    cfg.domain = domain
    cfg.diffusion = DiffusionConfig()
    cfg.substances = {
        "Oxygen": SubstanceConfig(
            name="Oxygen", diffusion_coeff=1e-9,
            production_rate=0.0, uptake_rate=0.0,
            initial_value=Concentration(boundary_value, "mM"),
            boundary_value=Concentration(boundary_value, "mM"),
            boundary_type="fixed"),
    }
    return MultiSubstanceSimulator(cfg, MeshManager(domain, verbose=False), verbose=False)


def test_3d_field_initialized_with_3d_shape():
    sim = _build_sim_3d()
    field = sim.state.substances["Oxygen"].concentrations
    assert field.shape == (NZ, NY, NX)
    assert np.allclose(field, 1.0)


def test_asymmetric_point_sink_lands_at_deposited_voxel():
    """Deposit a sink at bio (x=1, y=2, z=0); the field minimum after the
    solve must sit at arr[z=0, y=2, x=1]. Fails under any transposition."""
    sim = _build_sim_3d()
    sink_pos = (1, 2, 0)  # bio grid == voxel grid (1:1 sizes)
    sim.update({sink_pos: {"Oxygen": -3.0e-16}})

    field = sim.state.substances["Oxygen"].concentrations
    assert field.shape == (NZ, NY, NX)
    z, y, x = np.unravel_index(np.argmin(field), field.shape)
    assert (x, y, z) == sink_pos
    assert field[z, y, x] < 1.0


def test_field_to_fipy_order_round_trip():
    arr3 = np.arange(NZ * NY * NX, dtype=float).reshape((NZ, NY, NX))
    flat = field_to_fipy_order(arr3)
    assert np.array_equal(flat.reshape((NZ, NY, NX), order='C'), arr3)

    arr2 = np.arange(NY * NX, dtype=float).reshape((NY, NX))
    assert np.array_equal(field_to_fipy_order(arr2), arr2.flatten(order='F'))


def test_concentration_keys_3d_are_per_voxel():
    sim = _build_sim_3d()
    # Stamp a recognizable value at a known voxel
    sim.state.substances["Oxygen"].concentrations[2, 1, 3] = 42.0
    conc = sim.get_substance_concentrations()["Oxygen"]
    assert len(conc) == NX * NY * NZ
    assert all(len(k) == 3 for k in conc)
    assert conc[(3, 1, 2)] == 42.0


def test_concentration_keys_2d_unchanged():
    domain = DomainConfig(dimensions=2,
                          size_x=Length(100.0, "um"), size_y=Length(80.0, "um"),
                          nx=5, ny=4, cell_height=Length(20.0, "um"))

    class Cfg:
        pass

    cfg = Cfg()
    cfg.domain = domain
    cfg.diffusion = DiffusionConfig()
    cfg.substances = {
        "Oxygen": SubstanceConfig(
            name="Oxygen", diffusion_coeff=1e-9, production_rate=0.0,
            uptake_rate=0.0, initial_value=Concentration(0.07, "mM"),
            boundary_value=Concentration(0.07, "mM"), boundary_type="fixed"),
    }
    sim = MultiSubstanceSimulator(cfg, MeshManager(domain, verbose=False), verbose=False)
    conc = sim.get_substance_concentrations()["Oxygen"]
    assert len(conc) == 20
    assert all(len(k) == 2 for k in conc)


def test_3d_implicit_sink_solve_is_finite_and_bounded():
    sim = _build_sim_3d()
    positions = [(1, 2, 0), (2, 1, 1), (3, 2, 2)]
    production = {p: {"Oxygen": 1.0e-18} for p in positions}
    sinks = {p: {"Oxygen": 2.0e-17} for p in positions}
    sim.update(production, implicit_sinks=sinks)
    field = sim.state.substances["Oxygen"].concentrations
    assert np.all(np.isfinite(field))
    assert field.min() >= 0.0
