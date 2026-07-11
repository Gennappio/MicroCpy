"""Regression tests for the agent-creation structural checks in the workflow
validator (`scripts/validate_workflow.py`).

Agent kinds have two canvases: a collective Creation (create_subworkflow, runs once)
and per-agent Steps. Per-agent agent init was removed from the model, so these enforce:
  - a leftover per-agent init_subworkflow -> hard error (no longer supported),
  - INV2 (error): a create_subworkflow scheduled WITH for_each (creation is collective),
  - INV1 (warn): agent kinds exist but no creation is scheduled anywhere,
  - execution_order completeness (a partial order silently drops calls).

The validator lives in `scripts/` (not `src/`), so it is loaded from its path.
"""

import importlib.util
import json
from pathlib import Path

import pytest

_ENGINE = Path(__file__).resolve().parents[2]  # opencellcomms_engine/
_SCRIPT = _ENGINE / "scripts" / "validate_workflow.py"
_spec = importlib.util.spec_from_file_location("validate_workflow", _SCRIPT)
vw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vw)

FE = {"type": "agent", "kind": "cell", "order": "random"}


def _model(agent_kinds, init_calls, scheduler=True):
    """Build (gui, subworkflows). init_calls: list of (name, id, for_each|None) in order."""
    gui = {"init_sequence": {"subworkflow": "__init_sequence__"}, "agent_kinds": agent_kinds}
    if scheduler:
        gui["scheduler"] = {"subworkflow": "__scheduler__"}
    calls = []
    for name, cid, fe in init_calls:
        call = {"id": cid, "subworkflow_name": name}
        if fe:
            call["for_each"] = fe
        calls.append(call)
    subs = {"__init_sequence__": {
        "subworkflow_calls": calls,
        "execution_order": [c["id"] for c in calls],
    }}
    return gui, subs


def _run(gui, subs):
    errors, warnings = [], []
    vw.check_no_agent_init(gui, errors)
    vw.check_agent_creation_structure(gui, subs, errors, warnings)
    return errors, warnings


# ── clean case ────────────────────────────────────────────────────────────────

def test_create_only_kind_is_clean():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []}],
        [("cell_create", "i1", None)],
    )
    errors, warnings = _run(gui, subs)
    assert errors == []
    assert warnings == []


# ── per-agent agent init is forbidden ─────────────────────────────────────────

def test_agent_init_is_forbidden():
    # A create + a per-agent init: the init is no longer supported.
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create",
          "init_subworkflow": "cell_init", "behavior_subworkflows": []}],
        [("cell_create", "i1", None), ("cell_init", "i2", FE)],
    )
    errors, _ = _run(gui, subs)
    assert any("cell_init" in e and "no longer supported" in e for e in errors)


def test_agent_init_only_kind_is_forbidden():
    # Legacy init-only shape (no create) is also forbidden.
    gui, subs = _model(
        [{"name": "cell", "init_subworkflow": "cell_init", "behavior_subworkflows": []}],
        [("cell_init", "i1", FE)],
    )
    errors, _ = _run(gui, subs)
    assert any("cell_init" in e and "no longer supported" in e for e in errors)


# ── INV2 / INV1 ───────────────────────────────────────────────────────────────

def test_inv2_creation_with_for_each_errors():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []}],
        [("cell_create", "i1", FE)],   # creation must NOT carry for_each
    )
    errors, _ = _run(gui, subs)
    assert any("creation canvas 'cell_create'" in e and "for_each" in e for e in errors)


def test_inv1_no_creation_scheduled_warns():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []}],
        [("__world__", "i0", None)],   # create declared but not scheduled
    )
    errors, warnings = _run(gui, subs)
    assert errors == []
    assert any("no create_subworkflow is scheduled" in w for w in warnings)


def test_collectively_created_kind_with_no_own_canvases_is_not_errored():
    # A kind created inside another kind's creation canvas (neither create nor init,
    # like tcell_corral's dendritic_cell) must not be errored; INV1 doesn't fire
    # because a creation IS scheduled.
    gui, subs = _model(
        [
            {"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []},
            {"name": "scenery", "behavior_subworkflows": ["scenery_step"]},
        ],
        [("cell_create", "i1", None)],
    )
    errors, warnings = _run(gui, subs)
    assert errors == []
    assert warnings == []


def test_no_scheduler_is_not_checked():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []}],
        [("__world__", "i0", None)],
        scheduler=False,
    )
    errors, warnings = [], []
    vw.check_agent_creation_structure(gui, subs, errors, warnings)
    assert errors == [] and warnings == []


# ── real workflows ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("rel", [
    "opencellcomms_adapters/MicroC/workflows/microc.json",
    "opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json",
    "opencellcomms_adapters/TCELL_CORRAL/workflows/tcell_corral.json",
])
def test_canonical_workflows_have_no_creation_errors(rel):
    """Headline workflows are all create-only now (tcell_corral's init was folded in)."""
    errors, warnings, skip = vw.check_workflow(str(vw.REPO_ROOT / rel), None)
    assert skip is None
    assert errors == [], f"{rel} unexpectedly errored: {errors}"


def test_negative_example_is_caught_by_the_check():
    """gene_network_update_test.json (skip-marked, excluded from --all) has a
    tumor_cell init_subworkflow -- the removed per-agent init. Run the check directly
    (bypassing the skip) and confirm it hard-errors."""
    path = vw.REPO_ROOT / "opencellcomms_adapters/MicroC/workflows/gene_network_update_test.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = []
    vw.check_no_agent_init(data["metadata"]["gui"], errors)
    assert any("no longer supported" in e for e in errors)


# ── execution_order completeness ──────────────────────────────────────────────

def test_execution_order_completeness_warns_on_dropped_call():
    subs = {"seq": {
        "subworkflow_calls": [
            {"id": "c1", "subworkflow_name": "a"},
            {"id": "c2", "subworkflow_name": "b"},  # in calls, absent from order
        ],
        "execution_order": ["c1"],
    }}
    warnings = []
    vw.check_execution_order_complete(subs, warnings)
    assert any("execution_order omits" in w and "c2" in w for w in warnings)


def test_execution_order_empty_is_not_flagged():
    subs = {"seq": {"subworkflow_calls": [{"id": "c1", "subworkflow_name": "a"}], "execution_order": []}}
    warnings = []
    vw.check_execution_order_complete(subs, warnings)
    assert warnings == []


def test_execution_order_ignores_disabled_nodes():
    subs = {"seq": {
        "subworkflow_calls": [
            {"id": "c1", "subworkflow_name": "a"},
            {"id": "c2", "subworkflow_name": "b", "enabled": False},  # wouldn't run anyway
        ],
        "execution_order": ["c1"],
    }}
    warnings = []
    vw.check_execution_order_complete(subs, warnings)
    assert warnings == []
