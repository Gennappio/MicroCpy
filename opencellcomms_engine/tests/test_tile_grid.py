"""Unit tests for the tile-grid resource-field abstraction."""

import numpy as np
import pytest

from src.core.tile_grid import (
    TileGrid,
    get_field_value,
    set_field_value,
)


def _grid(topology_x="bounded", topology_y="bounded"):
    return TileGrid(size_x=100.0, size_y=100.0, nx_t=10, ny_t=10,
                    topology_x=topology_x, topology_y=topology_y)


def test_field_roundtrip():
    g = _grid()
    g.add_field("sugar", 0.0)
    g.set_value("sugar", 3, 4, 9.0)
    assert g.value("sugar", 3, 4) == 9.0
    assert g.get("sugar").shape == (10, 10)
    assert g.get("sugar")[4, 3] == 9.0  # indexed [tj, ti]


def test_initial_value_fill():
    g = _grid()
    g.add_field("sugar", 2.5)
    assert np.all(g.get("sugar") == 2.5)


def test_tile_of_center_of_roundtrip():
    g = _grid()
    for ti in range(g.nx_t):
        for tj in range(g.ny_t):
            assert g.tile_of(g.center_of(ti, tj)) == (ti, tj)


def test_neighbors_bounded_clips_edges():
    g = _grid("bounded", "bounded")
    n = g.neighbors(0, 0, radius=1)
    # No negative / wrapped indices on a bounded grid.
    assert all(0 <= ni < g.nx_t and 0 <= nj < g.ny_t for ni, nj in n)
    assert (0, 0) not in n  # center excluded
    assert set(n) == {(1, 0), (0, 1), (1, 1)}


def test_neighbors_toroidal_wraps():
    g = _grid("toroidal", "toroidal")
    n = g.neighbors(0, 0, radius=1)
    assert (9, 9) in n and (9, 0) in n and (0, 9) in n  # corners wrap around
    assert len(n) == 8


def test_topology_normalizes_index_access():
    g = _grid("toroidal", "bounded")
    g.add_field("sugar", 0.0)
    g.set_value("sugar", 3, 4, 7.0)
    assert g.value("sugar", 13, 4) == 7.0   # x wraps (toroidal)
    assert g.value("sugar", 3, -1) == g.value("sugar", 3, 0)  # y clamps (bounded)


def test_context_helpers():
    g = _grid()
    g.add_field("sugar", 1.0)
    ctx = {"tile_grid": g}
    set_field_value(ctx, "sugar", 2, 2, 5.0)
    assert get_field_value(ctx, "sugar", 2, 2) == 5.0


def test_bad_topology_rejected():
    with pytest.raises(ValueError):
        TileGrid(100.0, 100.0, 10, 10, topology_x="spherical")


def test_missing_field_raises():
    g = _grid()
    with pytest.raises(KeyError):
        g.get("nope")
