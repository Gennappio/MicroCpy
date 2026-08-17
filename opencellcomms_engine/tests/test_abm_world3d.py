"""LatticeWorld3D: the 3D sibling of LatticeWorld.

Pins neighbor counts (26 moore / 6 vonneumann / 6 axial rays), bounded corner
clipping, toroidal wrap, (nz, ny, nx) field shape + interpolate orientation,
occupancy reads, and FieldResource 3D set/deposit — with the 2D FieldResource
behavior asserted unchanged.
"""
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import numpy as np  # noqa: E402

from src.abm import FieldResource, LatticeWorld, LatticeWorld3D  # noqa: E402


def _world(topology=("bounded", "bounded", "bounded")):
    # 100x80x60 um, 20 um tiles -> nx, ny, nz = 5, 4, 3
    return LatticeWorld3D(100.0, 80.0, 60.0, 20.0, *topology)


def test_grid_dimensions_and_shape():
    w = _world()
    assert (w.nx, w.ny, w.nz) == (5, 4, 3)
    assert w.dimension == 3
    assert w.shape == (3, 4, 5)  # (nz, ny, nx)
    assert w.bounds() == ((0, 0, 0), (5, 4, 3))


def test_moore_neighbors_interior_and_corner():
    w = _world()
    interior = w.neighbors((2, 2, 1), pattern="moore")
    assert len(interior) == 26
    corner = w.neighbors((0, 0, 0), pattern="moore")
    assert len(corner) == 7  # bounded corner keeps the 2x2x2 block minus self
    assert all(w.contains(p) for p in corner)


def test_vonneumann_and_axial_neighbors():
    w = _world()
    vn = w.neighbors((2, 2, 1), pattern="vonneumann")
    assert sorted(vn) == sorted([(1, 2, 1), (3, 2, 1), (2, 1, 1),
                                 (2, 3, 1), (2, 2, 0), (2, 2, 2)])
    ax = w.neighbors((2, 2, 1), pattern="axial", radius=1)
    assert sorted(ax) == sorted(vn)  # at radius 1 the six rays == von Neumann


def test_toroidal_wrap_and_distance():
    w = _world(("toroidal", "bounded", "toroidal"))
    assert w.normalize((-1, 0, 3)) == (4, 0, 0)
    # min-image distance on wrapped axes
    assert w.distance((0, 0, 0), (4, 0, 2)) == np.sqrt(1 + 0 + 1)
    ns = w.neighbors((0, 0, 0), pattern="moore")
    assert (4, 0, 2) in ns  # wrapped x and z corner neighbor
    assert len(ns) == 17  # y bounded at 0 clips the dj=-1 layer: 26 - 9


def test_interpolate_orientation():
    w = _world()
    values = np.zeros(w.shape)
    values[2, 3, 1] = 7.0  # z=2, y=3, x=1
    assert w.interpolate(values, (1, 3, 2)) == 7.0
    assert w.interpolate(values, (1, 3, 0)) == 0.0


def test_occupancy_reads():
    w = _world()
    occ = {(1, 2, 0): "cell_a"}
    w.bind_occupancy(occ)
    assert w.occupants((1, 2, 0)) == ["cell_a"]
    assert not w.is_free((1, 2, 0))
    assert w.is_free((0, 0, 0))
    assert "cell_a" in w.within((2, 2, 0), radius=1)


def test_field_resource_3d_set_deposit_apply():
    w = _world()
    f = FieldResource("sugar", w, initial=0.0)
    assert f.values().shape == (3, 4, 5)
    f.set_at((1, 3, 2), 5.0)
    assert f.values()[2, 3, 1] == 5.0
    assert f.at((1, 3, 2)) == 5.0
    f.deposit((1, 3, 2), 2.5)
    f.apply_sources()
    assert f.at((1, 3, 2)) == 7.5


def test_field_resource_2d_unchanged():
    w2 = LatticeWorld(100.0, 80.0, 20.0, "bounded", "bounded")
    f = FieldResource("sugar", w2, initial=1.0)
    assert f.values().shape == (4, 5)
    f.set_at((1, 3), 9.0)
    assert f.values()[3, 1] == 9.0
    f.deposit((1, 3), 1.0)
    f.apply_sources()
    assert f.at((1, 3)) == 10.0


def test_random_position_empty_respects_occupancy():
    w = LatticeWorld3D(40.0, 40.0, 20.0, 20.0)  # 2x2x1 = 4 sites
    occ = {(0, 0, 0): "a", (1, 0, 0): "b", (0, 1, 0): "c"}
    w.bind_occupancy(occ)
    rng = np.random.default_rng(0)
    assert w.random_position(rng, empty=True) == (1, 1, 0)
