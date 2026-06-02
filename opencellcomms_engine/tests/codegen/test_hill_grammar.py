"""Tests for the Hill-rule grammar validator (Phase 3)."""
from __future__ import annotations

import pytest

from opencellcomms_adapters.PhysiBoSS.codegen.hill_grammar import (
    PHASE5_HINT,
    normalize_rule,
    validate_rule,
    validate_rules,
)

_SUBSTRATES = ["oxygen", "glucose", "apoptotic debris"]
_CELLS = ["tumor", "M0 macrophage"]


def _good() -> dict:
    return {
        "cell_type": "tumor", "signal": "oxygen", "direction": "decreases",
        "behavior": "necrosis", "half_max": 5.0, "hill_power": 8.0,
        "max_response": 0.5, "use_on_dead": 0,
    }


def test_accepts_minimal_valid_rule():
    assert validate_rule(_good(), _SUBSTRATES, _CELLS) is None


def test_accepts_substrate_secretion_behavior():
    r = _good()
    r["behavior"] = "apoptotic debris secretion"
    r["signal"] = "apoptotic"
    assert validate_rule(r, _SUBSTRATES, _CELLS + ["apoptotic"]) is None or \
           validate_rule({**r, "signal": "oxygen"}, _SUBSTRATES, _CELLS) is None


def test_accepts_transform_to_celltype():
    r = _good()
    r["behavior"] = "transform to M0 macrophage"
    assert validate_rule(r, _SUBSTRATES, _CELLS) is None


def test_rejects_unknown_direction():
    r = _good()
    r["direction"] = "bumps"
    err = validate_rule(r, _SUBSTRATES, _CELLS)
    assert err and "direction" in err and PHASE5_HINT in err


def test_rejects_unknown_celltype():
    r = _good()
    r["cell_type"] = "ghost"
    err = validate_rule(r, _SUBSTRATES, _CELLS)
    assert err and "cell_type" in err


def test_rejects_unknown_behavior():
    r = _good()
    r["behavior"] = "summon dragon"
    err = validate_rule(r, _SUBSTRATES, _CELLS)
    assert err and "behavior" in err and PHASE5_HINT in err


def test_rejects_unknown_signal():
    r = _good()
    r["signal"] = "vibes"
    err = validate_rule(r, _SUBSTRATES, _CELLS)
    assert err and "signal" in err and PHASE5_HINT in err


def test_rejects_non_numeric_half_max():
    r = _good()
    r["half_max"] = "abc"
    err = validate_rule(r, _SUBSTRATES, _CELLS)
    assert err and "half_max" in err


def test_rejects_missing_max_response():
    r = _good()
    del r["max_response"]
    err = validate_rule(r, _SUBSTRATES, _CELLS)
    assert err and "max_response" in err


def test_missing_field_is_caught():
    r = _good()
    del r["hill_power"]
    err = validate_rule(r, _SUBSTRATES, _CELLS)
    assert err and "hill_power" in err


@pytest.mark.parametrize("v,want", [(0, 0), (1, 1), (True, 1), (False, 0),
                                     ("0", 0), ("true", 1), ("yes", 1)])
def test_use_on_dead_coercions(v, want):
    r = _good()
    r["use_on_dead"] = v
    assert validate_rule(r, _SUBSTRATES, _CELLS) is None
    assert normalize_rule(r)["use_on_dead"] == want


def test_use_on_dead_rejects_garbage():
    r = _good()
    r["use_on_dead"] = "maybe"
    err = validate_rule(r, _SUBSTRATES, _CELLS)
    assert err and "use_on_dead" in err


def test_validate_rules_indexes_errors():
    rules = [_good(), {**_good(), "direction": "sideways"}, _good()]
    errs = validate_rules(rules, _SUBSTRATES, _CELLS)
    assert len(errs) == 1
    assert errs[0].startswith("hill_rules[1]:")
