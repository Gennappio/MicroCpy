"""Tests for scripts/validate_workflow.py — the GUI-readability linter.

Covers the two gating rules (orphan behaviours, inlined dict/list parameters)
plus the non-ABM skip. The check functions operate on plain dicts, so these run
without loading the registry (except the one test that passes a fake registry to
exercise the ERROR path deterministically).
"""

import sys
from pathlib import Path

# scripts/ is not a package; import validate_workflow.py by path.
SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import validate_workflow as vw  # noqa: E402


def _abm_gui():
    """A minimal, clean ABM metadata.gui: one agent kind with an init + step."""
    return {
        "agent_kinds": [
            {
                "name": "cell",
                "init_subworkflow": "cell_init",
                "behavior_subworkflows": ["cell_step"],
            }
        ],
        "resource_kinds": [],
        "world": {"subworkflow": "__world__", "behavior_subworkflows": []},
        "init_sequence": {"subworkflow": "__init_sequence__"},
        "scheduler": {"subworkflow": "__scheduler__"},
        "processing": {"behavior_subworkflows": []},
    }


def _abm_subs(scheduler_calls):
    return {
        "main": {
            "subworkflow_calls": [
                {"subworkflow_name": "__init_sequence__"},
                {"subworkflow_name": "__scheduler__"},
            ]
        },
        "__init_sequence__": {
            "subworkflow_calls": [
                {"subworkflow_name": "__world__"},
                {"subworkflow_name": "cell_init"},
            ]
        },
        "__scheduler__": {
            "subworkflow_calls": [
                {"subworkflow_name": n} for n in scheduler_calls
            ]
        },
        "__world__": {"functions": []},
        "cell_init": {"functions": []},
        "cell_step": {"functions": []},
    }


def test_clean_workflow_has_no_errors():
    errors = []
    vw.check_orphans(_abm_gui(), _abm_subs(["cell_step"]), errors)
    assert errors == []


def test_orphan_behaviour_flagged():
    # orphan_step runs in the scheduler but is homed under no tab.
    subs = _abm_subs(["cell_step", "orphan_step"])
    subs["orphan_step"] = {"functions": []}
    errors = []
    vw.check_orphans(_abm_gui(), subs, errors)
    assert any("orphan_step" in e for e in errors)


def test_environment_behaviours_flagged():
    gui = _abm_gui()
    gui["environment"] = {"init_subworkflow": None, "behavior_subworkflows": ["sneaky"]}
    errors = []
    vw.check_orphans(gui, _abm_subs(["cell_step"]), errors)
    assert any("environment.behavior_subworkflows" in e for e in errors)


def test_environment_init_subworkflow_is_allowed():
    # environment.init_subworkflow (world setup) is legitimate, not an orphan.
    gui = _abm_gui()
    gui["environment"] = {"init_subworkflow": "env_setup", "behavior_subworkflows": []}
    subs = _abm_subs(["cell_step"])
    subs["__init_sequence__"]["subworkflow_calls"].append({"subworkflow_name": "env_setup"})
    subs["env_setup"] = {"functions": []}
    errors = []
    vw.check_orphans(gui, subs, errors)
    assert errors == []


def test_non_abm_workflow_skips_orphan_check():
    # No scheduler => not an ABM model => main's children are generic composers,
    # not orphaned behaviours.
    gui = {"processing": {"behavior_subworkflows": []}}
    subs = {
        "main": {"subworkflow_calls": [{"subworkflow_name": "child"}]},
        "child": {"functions": []},
    }
    errors = []
    vw.check_orphans(gui, subs, errors)
    assert errors == []


class _FakeParam:
    def __init__(self, name, type_value):
        self.name = name
        self.type = type_value


class _FakeMeta:
    def __init__(self, params):
        self.parameters = params


class _FakeRegistry:
    def __init__(self, functions):
        self.functions = functions


def _inline_subs():
    return {
        "sw": {
            "functions": [
                {
                    "id": "n1",
                    "function_name": "fn",
                    "parameters": {"cfg": {"a": 1}},
                }
            ]
        }
    }


def test_inlined_dict_errors_when_registry_types_it_dict():
    registry = _FakeRegistry({"fn": _FakeMeta([_FakeParam("cfg", "dict")])})
    errors, warnings = [], []
    vw.check_inlined_params(_inline_subs(), registry, errors, warnings)
    assert errors and not warnings


def test_inlined_dict_warns_when_function_unregistered():
    errors, warnings = [], []
    vw.check_inlined_params(_inline_subs(), None, errors, warnings)
    assert warnings and not errors


def test_empty_dict_parameter_is_not_flagged():
    subs = {
        "sw": {
            "functions": [
                {"id": "n1", "function_name": "fn", "parameters": {"cfg": {}}}
            ]
        }
    }
    errors, warnings = [], []
    vw.check_inlined_params(subs, None, errors, warnings)
    assert not errors and not warnings
