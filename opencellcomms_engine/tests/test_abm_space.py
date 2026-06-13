"""Unit tests for the ABM LatticeSpace (geometry, topology, occupancy)."""

import numpy as np

from src.abm.space import LatticeSpace


def space(tx="bounded", ty="bounded"):
    return LatticeSpace(10, 10, 1, tx, ty)


def test_shape_and_bounds():
    sp = space()
    assert sp.shape == (10, 10)
    assert sp.bounds() == ((0, 0), (10, 10))


def test_normalize_wrap_vs_clamp():
    sp = space("toroidal", "bounded")
    assert sp.normalize((-1, -1)) == (9, 0)   # x wraps, y clamps
    assert sp.normalize((10, 10)) == (0, 9)


def test_neighbors_patterns():
    sp = space()
    assert len(sp.neighbors((5, 5), 1, "moore")) == 8
    assert set(sp.neighbors((5, 5), 1, "vonneumann")) == {(4, 5), (6, 5), (5, 4), (5, 6)}
    axial = sp.neighbors((5, 5), 2, "axial")
    assert (7, 5) in axial and (5, 7) in axial and (6, 6) not in axial


def test_neighbors_toroidal_wraps():
    sp = space("toroidal", "toroidal")
    n = sp.neighbors((0, 0), 1, "moore")
    assert (9, 9) in n and len(n) == 8


def test_neighbors_bounded_clips():
    sp = space()
    n = sp.neighbors((0, 0), 1, "moore")
    assert all(0 <= i < 10 and 0 <= j < 10 for i, j in n)
    assert len(n) == 3


def test_distance_toroidal():
    sp = space("toroidal", "toroidal")
    assert sp.distance((0, 0), (9, 0)) == 1.0


def test_interpolate_nearest():
    sp = space()
    vals = np.zeros((10, 10))
    vals[3, 4] = 7.0
    assert sp.interpolate(vals, (4, 3)) == 7.0  # indexed [tj=3, ti=4]


def test_occupancy_read_side():
    sp = space()
    occ = {}
    sp.bind_occupancy(occ)
    assert sp.is_free((2, 2))
    occ[(2, 2)] = "a"
    assert not sp.is_free((2, 2))
    assert sp.occupants((2, 2)) == ["a"]
    assert "a" in sp.within((2, 3), 1)


def test_random_position_empty():
    sp = space()
    occ = {(i, j): "x" for i in range(10) for j in range(10) if (i, j) != (5, 5)}
    sp.bind_occupancy(occ)
    rng = np.random.default_rng(0)
    assert sp.random_position(rng, empty=True) == (5, 5)
