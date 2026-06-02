"""Tests for the workflow-JSON → spec converter (Phase 3)."""
from __future__ import annotations

import pytest

from opencellcomms_adapters.PhysiBoSS.codegen.spec_from_workflow import (
    WorkflowSpecError,
    spec_from_workflow,
)


def _workflow_inline():
    """Smallest workflow that uses inline `parameters` on each node."""
    return {
        "version": "2.0",
        "kernel": "physicell",
        "subworkflows": {
            "main": {
                "execution_order": ["setup"],
                "subworkflows": {
                    "setup": {
                        "functions": [
                            {"id": "sub_o2", "function_name": "define_substrate",
                             "parameters": {"substrate": {
                                 "name": "oxygen", "diffusion_coefficient": 1e5,
                                 "decay_rate": 0.1, "initial_condition": 38.0,
                             }}},
                            {"id": "ct_tumor", "function_name": "define_cell_type",
                             "parameters": {"cell_type": {"name": "tumor"}}},
                            {"id": "r1", "function_name": "define_hill_rule",
                             "parameters": {"rule": {
                                 "cell_type": "tumor", "signal": "oxygen",
                                 "direction": "decreases", "behavior": "necrosis",
                                 "max_response": 0.5, "half_max": 5.0,
                                 "hill_power": 8.0, "use_on_dead": 0,
                             }}},
                        ],
                    }
                }
            }
        }
    }


def _workflow_param_nodes():
    """A workflow that wires DICT params through dictParameterNode references."""
    return {
        "version": "2.0",
        "kernel": "physicell",
        "subworkflows": {
            "main": {
                "execution_order": ["setup"],
                "subworkflows": {
                    "setup": {
                        "functions": [
                            {"id": "sub_o2", "function_name": "define_substrate",
                             "parameter_nodes": ["pn_o2"]},
                            {"id": "ct_tumor", "function_name": "define_cell_type",
                             "parameter_nodes": ["pn_tumor"]},
                        ],
                        "parameters": [
                            {"id": "pn_o2", "type": "dictParameterNode",
                             "target_param": "substrate",
                             "entries": [
                                 {"key": "name", "value": "oxygen"},
                                 {"key": "diffusion_coefficient", "value": 1e5},
                                 {"key": "decay_rate", "value": 0.1},
                                 {"key": "initial_condition", "value": 38.0},
                             ]},
                            {"id": "pn_tumor", "type": "dictParameterNode",
                             "target_param": "cell_type",
                             "entries": [{"key": "name", "value": "tumor"}]},
                        ],
                    }
                }
            }
        }
    }


def test_lifts_inline_parameters():
    spec = spec_from_workflow(_workflow_inline())
    assert [s["name"] for s in spec["substrates"]] == ["oxygen"]
    assert [c["name"] for c in spec["cell_types"]] == ["tumor"]
    assert len(spec["hill_rules"]) == 1
    assert spec["hill_rules"][0]["behavior"] == "necrosis"


def test_resolves_dictparameternode_refs():
    spec = spec_from_workflow(_workflow_param_nodes())
    assert spec["substrates"][0]["diffusion_coefficient"] == 1e5
    assert spec["cell_types"][0]["name"] == "tumor"
    assert spec["hill_rules"] == []  # none defined in this workflow


def test_skips_disabled_nodes():
    wf = _workflow_inline()
    wf["subworkflows"]["main"]["subworkflows"]["setup"]["functions"][2]["enabled"] = False
    spec = spec_from_workflow(wf)
    assert spec["hill_rules"] == []


def test_missing_substrate_raises():
    wf = _workflow_inline()
    fns = wf["subworkflows"]["main"]["subworkflows"]["setup"]["functions"]
    fns[:] = [n for n in fns if n["function_name"] != "define_substrate"]
    with pytest.raises(WorkflowSpecError, match="substrate"):
        spec_from_workflow(wf)


def test_missing_celltype_raises():
    wf = _workflow_inline()
    fns = wf["subworkflows"]["main"]["subworkflows"]["setup"]["functions"]
    fns[:] = [n for n in fns if n["function_name"] != "define_cell_type"]
    with pytest.raises(WorkflowSpecError, match="cell type"):
        spec_from_workflow(wf)


def test_physicell_overrides_passed_through():
    wf = _workflow_inline()
    wf["physicell"] = {
        "domain": {"x_min": -1, "x_max": 1, "y_min": -1, "y_max": 1,
                   "z_min": -1, "z_max": 1, "dx": 1, "dy": 1, "dz": 1, "use_2D": False},
        "overall": {"max_time": 5.0},
    }
    spec = spec_from_workflow(wf)
    assert spec["domain"]["x_max"] == 1
    assert spec["overall"]["max_time"] == 5.0
