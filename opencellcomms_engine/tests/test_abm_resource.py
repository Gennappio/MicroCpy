"""Unit tests for the ABM FieldResource (sampling, source terms, growback)."""

import numpy as np

from src.abm.resource import FieldResource
from src.abm.space import LatticeSpace


def space():
    return LatticeSpace(5, 5, 1, "bounded", "bounded")


def test_at_and_set():
    r = FieldResource("s", space(), initial=2.0)
    assert r.at((1, 1)) == 2.0
    r.set_at((1, 1), 9.0)
    assert r.at((1, 1)) == 9.0


def test_deposit_sink_clamps_at_zero():
    r = FieldResource("s", space(), initial=3.0)
    r.deposit((1, 1), -10.0)
    r.apply_sources()
    assert r.at((1, 1)) == 0.0  # consumption can't drive the field negative


def test_deposit_source():
    r = FieldResource("s", space(), initial=0.0)
    r.deposit((0, 0), 5.0)
    r.apply_sources()
    assert r.at((0, 0)) == 5.0


def test_apply_sources_resets_accumulator():
    r = FieldResource("s", space(), initial=0.0)
    r.deposit((0, 0), 2.0)
    r.apply_sources()
    r.apply_sources()  # no pending sources -> no further change
    assert r.at((0, 0)) == 2.0


def test_grow_to_capacity():
    r = FieldResource("s", space(), initial=0.0)
    cap = np.full((5, 5), 3.0)
    r.grow_to(cap, 1.0)
    assert r.at((0, 0)) == 1.0
    for _ in range(5):
        r.grow_to(cap, 1.0)
    assert r.at((0, 0)) == 3.0  # clamped at capacity


def test_totals():
    r = FieldResource("s", space(), initial=1.0)
    assert r.total() == 25.0 and r.max() == 1.0 and r.min() == 1.0
