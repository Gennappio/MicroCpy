"""Regression tests for the agent-creation structural checks in the workflow
validator (`scripts/validate_workflow.py`).

These enforce the creation-in-World model as HARD ERRORS so a coding agent cannot
ship a model whose agents are never (properly) created:
  - INV2 (error): a create_subworkflow scheduled WITH for_each (creation is collective).
  - INV3 (error): creation scheduled at/after a kind's per-agent init.
  - INV4 (error): a per-agent init_subworkflow scheduled WITHOUT for_each.
  - INV1 (warn, model-level): agent kinds exist but no creation is scheduled anywhere.

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
    gui = {
        "init_sequence": {"subworkflow": "__init_sequence__"},
        "agent_kinds": agent_kinds,
    }
    if scheduler:
        gui["scheduler"] = {"subworkflow": "__scheduler__"}
    calls = []
    for name, cid, fe in init_calls:
        call = {"id": cid, "subworkflow_name": name}
        if fe:
            call["for_each"] = fe
        calls.append(call)
    subs = {
        "__init_sequence__": {
            "subworkflow_calls": calls,
            "execution_order": [c["id"] for c in calls],
        }
    }
    return gui, subs


def _run(gui, subs):
    errors, warnings = [], []
    vw.check_agent_init_per_agent(gui, subs, errors)
    vw.check_agent_creation_structure(gui, subs, errors, warnings)
    return errors, warnings


# ── clean cases (no errors, no warnings) ──────────────────────────────────────

def test_create_only_kind_is_clean():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []}],
        [("cell_create", "i1", None)],
    )
    errors, warnings = _run(gui, subs)
    assert errors == []
    assert warnings == []


def test_create_plus_per_agent_init_is_clean():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create",
          "init_subworkflow": "cell_init", "behavior_subworkflows": []}],
        [("cell_create", "i1", None), ("cell_init", "i2", FE)],
    )
    errors, warnings = _run(gui, subs)
    assert errors == []
    assert warnings == []


# ── each invariant fires ──────────────────────────────────────────────────────

def test_inv2_creation_with_for_each_errors():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []}],
        [("cell_create", "i1", FE)],   # creation must NOT carry for_each
    )
    errors, _ = _run(gui, subs)
    assert any("creation canvas 'cell_create' is scheduled with for_each" in e for e in errors)


def test_inv3_creation_after_init_errors():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create",
          "init_subworkflow": "cell_init", "behavior_subworkflows": []}],
        [("cell_init", "i1", FE), ("cell_create", "i2", None)],  # init before create — wrong
    )
    errors, _ = _run(gui, subs)
    assert any("before their" in e and "cell_create" in e for e in errors)


def test_inv4_init_without_for_each_errors():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create",
          "init_subworkflow": "cell_init", "behavior_subworkflows": []}],
        [("cell_create", "i1", None), ("cell_init", "i2", None)],  # init missing for_each
    )
    errors, _ = _run(gui, subs)
    assert any("without for_each" in e for e in errors)


def test_inv1_no_creation_scheduled_warns():
    # create_subworkflow declared but never scheduled → no agents created.
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []}],
        [("__world__", "i0", None)],
    )
    errors, warnings = _run(gui, subs)
    assert errors == []
    assert any("no create_subworkflow is scheduled" in w for w in warnings)


def test_inv5_legacy_init_only_kind_errors():
    # Legacy shape: a per-agent init (with for_each, so INV4 is clean) but no
    # collective creation. INV5 hard-errors it (decision B: flag + block).
    gui, subs = _model(
        [{"name": "cell", "init_subworkflow": "cell_init", "behavior_subworkflows": []}],
        [("cell_init", "i1", FE)],
    )
    errors, _ = _run(gui, subs)
    assert any("has a per-agent init 'cell_init' but no" in e for e in errors)


def test_collectively_created_kind_with_no_own_canvases_is_not_errored():
    # A kind created inside another kind's creation canvas has NEITHER create nor
    # init (like tcell_corral's dendritic_cell). It must not be INV5-errored; at
    # most the model-level INV1 warn applies (and here a creation IS scheduled).
    gui, subs = _model(
        [
            {"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []},
            {"name": "scenery", "behavior_subworkflows": ["scenery_step"]},  # no create, no init
        ],
        [("cell_create", "i1", None)],
    )
    errors, warnings = _run(gui, subs)
    assert errors == []
    assert warnings == []  # cell_create is scheduled → no INV1 warn


# ── gating: non-ABM files are untouched ───────────────────────────────────────

def test_no_scheduler_is_not_checked():
    gui, subs = _model(
        [{"name": "cell", "create_subworkflow": "cell_create", "behavior_subworkflows": []}],
        [("__world__", "i0", None)],   # creation not scheduled, but...
        scheduler=False,               # ...no scheduler → not an ABM model
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
    """Migrated headline workflows (incl. tcell_corral's collectively-created
    dendritic/endothelial kinds) must not be flagged as errors."""
    errors, warnings, skip = vw.check_workflow(str(vw.REPO_ROOT / rel), None)
    assert skip is None
    assert errors == [], f"{rel} unexpectedly errored: {errors}"


def test_negative_example_is_caught_by_the_check():
    """gene_network_update_test.json is skip-marked (excluded from --all), but its
    structure is the canonical mislabeled-init bug: tumor_cell's init is scheduled
    without for_each. Run the check directly (bypassing the skip) and confirm it
    hard-errors."""
    path = vw.REPO_ROOT / "opencellcomms_adapters/MicroC/workflows/gene_network_update_test.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    gui = data["metadata"]["gui"]
    subs = data["subworkflows"]
    errors = []
    vw.check_agent_init_per_agent(gui, subs, errors)
    assert any("without for_each" in e for e in errors)


# ── execution_order completeness (partial order silently drops calls) ─────────

def test_execution_order_completeness_warns_on_dropped_call():
    subs = {
        "seq": {
            "subworkflow_calls": [
                {"id": "c1", "subworkflow_name": "a"},
                {"id": "c2", "subworkflow_name": "b"},  # in calls, absent from order
            ],
            "execution_order": ["c1"],
        }
    }
    warnings = []
    vw.check_execution_order_complete(subs, warnings)
    assert any("execution_order omits" in w and "c2" in w for w in warnings)


def test_execution_order_empty_is_not_flagged():
    # A fully empty order uses the engine's definition-order fallback -> not flagged.
    subs = {"seq": {"subworkflow_calls": [{"id": "c1", "subworkflow_name": "a"}], "execution_order": []}}
    warnings = []
    vw.check_execution_order_complete(subs, warnings)
    assert warnings == []


def test_execution_order_ignores_disabled_nodes():
    subs = {
        "seq": {
            "subworkflow_calls": [
                {"id": "c1", "subworkflow_name": "a"},
                {"id": "c2", "subworkflow_name": "b", "enabled": False},  # wouldn't run anyway
            ],
            "execution_order": ["c1"],
        }
    }
    warnings = []
    vw.check_execution_order_complete(subs, warnings)
    assert warnings == []
