"""Tests for the composable PhysiCell facade pattern (Phase 4.5).

Validates that the define_* nodes accumulate spec into context, that
run_physicell_simulation reads it back, and that summarize_physicell_events
consumes the resulting events JSONL.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from opencellcomms_adapters.PhysiBoSS.functions.define_cell_type import define_cell_type
from opencellcomms_adapters.PhysiBoSS.functions.define_hill_rule import define_hill_rule
from opencellcomms_adapters.PhysiBoSS.functions.define_substrate import define_substrate
from opencellcomms_adapters.PhysiBoSS.functions.summarize_physicell_events import (
    summarize_physicell_events,
)


# --- define_* accumulate into context['physicell_spec'] ---------------------

def test_define_substrate_appends_to_spec():
    ctx: Dict[str, Any] = {}
    ok = define_substrate(context=ctx, substrate={"name": "oxygen", "diffusion_coefficient": 1.0,
                                                  "decay_rate": 0.1, "initial_condition": 38.0})
    assert ok is True
    assert ctx["physicell_spec"]["substrates"] == [{
        "name": "oxygen", "diffusion_coefficient": 1.0,
        "decay_rate": 0.1, "initial_condition": 38.0
    }]


def test_define_cell_type_assigns_sequential_ids_when_missing():
    ctx: Dict[str, Any] = {}
    define_cell_type(context=ctx, cell_type={"name": "tumor"})
    define_cell_type(context=ctx, cell_type={"name": "stroma"})
    cts = ctx["physicell_spec"]["cell_types"]
    assert [c["name"] for c in cts] == ["tumor", "stroma"]
    assert [c["id"] for c in cts] == [0, 1]


def test_define_hill_rule_preserves_explicit_id():
    ctx: Dict[str, Any] = {}
    define_cell_type(context=ctx, cell_type={"name": "tumor", "id": 7})
    assert ctx["physicell_spec"]["cell_types"][0]["id"] == 7


def test_three_define_calls_share_spec():
    ctx: Dict[str, Any] = {}
    define_substrate(context=ctx, substrate={"name": "oxygen",
                                             "diffusion_coefficient": 1,
                                             "decay_rate": 0, "initial_condition": 0})
    define_cell_type(context=ctx, cell_type={"name": "tumor"})
    define_hill_rule(context=ctx, rule={
        "cell_type": "tumor", "signal": "oxygen", "direction": "increases",
        "behavior": "necrosis", "max_response": 0.5, "half_max": 5,
        "hill_power": 8, "use_on_dead": 0,
    })
    spec = ctx["physicell_spec"]
    assert len(spec["substrates"]) == 1
    assert len(spec["cell_types"]) == 1
    assert len(spec["hill_rules"]) == 1


def test_define_with_no_context_fails_cleanly():
    assert define_substrate(context=None, substrate={"name": "x"}) is False
    assert define_substrate(context={}, substrate=None) is False


# --- summarize reads context['physicell']['events_jsonl'] -------------------

def test_summarize_tallies_events(tmp_path: Path):
    jsonl = tmp_path / "occ_events.jsonl"
    events = [
        {"event": "rule_engine_changed", "cell_id": 1, "t": 0.1, "rate": 0, "from": 0, "to": 0.5},
        {"event": "rule_engine_changed", "cell_id": 1, "t": 0.2, "rate": 1, "from": 0, "to": 0.1},
        {"event": "rule_engine_changed", "cell_id": 2, "t": 0.1, "rate": 0, "from": 0, "to": 0.4},
        {"event": "cell_snapshot",       "cell_id": 1, "t": 1.0, "x": 0, "y": 0, "z": 0, "volume": 2494},
    ]
    jsonl.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    ctx = {"physicell": {"events_jsonl": str(jsonl)}}
    ok = summarize_physicell_events(context=ctx, max_lines_to_show=2)
    assert ok is True

    summary = ctx["physicell_event_summary"]
    assert summary["total_events"] == 4
    assert summary["by_event"]["rule_engine_changed"] == 3
    assert summary["by_event"]["cell_snapshot"] == 1
    assert summary["by_rate"]["apoptosis"] == 2
    assert summary["by_rate"]["necrosis"] == 1
    assert summary["distinct_cells"] == 2


def test_summarize_without_physicell_results_fails():
    assert summarize_physicell_events(context={}) is False
    assert summarize_physicell_events(
        context={"physicell": {"events_jsonl": "/nonexistent"}}
    ) is False
