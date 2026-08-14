"""Planner tab expansion — the CLI must plan the same experiments as the GUI."""

import pytest

from src.workflow.planner import apply_overrides, enabled_tabs, planner_tabs
from src.workflow.schema import SubWorkflow


def _workflow():
    return {
        "metadata": {"gui": {"planner": {"tabs": [
            {"name": "wt", "enabled": True, "parameterOverrides": {}},
            {"name": "ko", "enabled": True, "parameterOverrides": {
                "p-knockouts": {"entries": [{"key": "p53", "value": "false"}]},
                "p-steps": {"parameters": {"steps": "40"}},
            }},
            {"name": "archived", "enabled": False, "parameterOverrides": {}},
        ]}}},
        "subworkflows": {
            "agent_create": {"parameters": [
                {"id": "p-knockouts", "label": "Gene Knockouts", "entries": [],
                 "position": {"x": 1, "y": 2}},
            ]},
            "__scheduler__": {
                "controller": {"id": "controller-__scheduler__",
                               "number_of_steps": 10, "parameter_nodes": ["p-steps"]},
                "parameters": [{"id": "p-steps", "parameters": {"steps": "10"}}],
            },
            "main": {"subworkflow_calls": [
                {"subworkflow_name": "__scheduler__", "iterations": 10},
            ]},
        },
    }


def test_only_enabled_tabs_run():
    wf = _workflow()
    assert len(planner_tabs(wf)) == 3
    assert [t["name"] for t in enabled_tabs(wf)] == ["wt", "ko"]


def test_overrides_replace_parameter_node_values():
    wf = _workflow()
    tab = enabled_tabs(wf)[1]
    patched = apply_overrides(wf, tab["parameterOverrides"])

    node = patched["subworkflows"]["agent_create"]["parameters"][0]
    assert node["entries"] == [{"key": "p53", "value": "false"}]
    # A tab supplies values only; it must not move or rename a node.
    assert node["position"] == {"x": 1, "y": 2}
    assert node["label"] == "Gene Knockouts"


def test_overridden_step_count_is_what_the_executor_resolves():
    """The steps parameter node is the single source of truth for the loop
    count: the executor resolves it via SubWorkflow.steps_param_value, so a
    tab that overrides the node changes the run length with no propagation
    into the controller or main's call."""
    wf = _workflow()
    patched = apply_overrides(wf, enabled_tabs(wf)[1]["parameterOverrides"])

    scheduler = SubWorkflow.from_dict(
        "__scheduler__", patched["subworkflows"]["__scheduler__"])
    assert scheduler.steps_param_value() == 40
    # The stale mirrors are untouched -- and ignored by the executor.
    assert patched["subworkflows"]["__scheduler__"]["controller"]["number_of_steps"] == 10
    assert patched["subworkflows"]["main"]["subworkflow_calls"][0]["iterations"] == 10


def test_steps_param_node_beats_controller_fallbacks():
    """Resolution order: steps node > controller.number_of_steps > iterations."""
    with_node = SubWorkflow.from_dict("__scheduler__", {
        "controller": {"id": "c", "number_of_steps": 10,
                       "parameter_nodes": ["p-steps"]},
        "parameters": [{"id": "p-steps", "parameters": {"steps": "40"}}],
    })
    assert with_node.steps_param_value() == 40

    without_node = SubWorkflow.from_dict("__scheduler__", {
        "controller": {"id": "c", "number_of_steps": 10},
    })
    assert without_node.steps_param_value() is None

    unparseable = SubWorkflow.from_dict("__scheduler__", {
        "controller": {"id": "c", "number_of_steps": 10,
                       "parameter_nodes": ["p-steps"]},
        "parameters": [{"id": "p-steps", "parameters": {"steps": "many"}}],
    })
    assert unparseable.steps_param_value() is None


def test_source_workflow_is_not_mutated():
    """Arms are applied in a loop against one document, so it must survive."""
    wf = _workflow()
    apply_overrides(wf, enabled_tabs(wf)[1]["parameterOverrides"])

    assert wf["subworkflows"]["agent_create"]["parameters"][0]["entries"] == []
    assert wf["subworkflows"]["__scheduler__"]["controller"]["number_of_steps"] == 10


@pytest.mark.parametrize("document", [{}, {"metadata": {}}, {"metadata": {"gui": {}}}])
def test_workflow_without_planner_has_no_tabs(document):
    assert planner_tabs(document) == []
    assert enabled_tabs(document) == []
