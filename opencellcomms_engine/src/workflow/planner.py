"""Planner tabs: one workflow file, several planned experiments.

A Planner tab is a named set of parameter-node overrides stored under
``metadata.gui.planner.tabs``. Running the workflow means running every enabled
tab -- they are the experiment arms a scientist laid out on the Planner, not
decoration.

The GUI has always done this: it patches the workflow once per enabled tab and
submits each separately. This module is that same logic, so the CLI can do it
too and a batch run of a file produces the same set of experiments as pressing
Run in the browser. Keep the two in step -- the reference implementation is
``applyOverridesToWorkflow`` in
``opencellcomms_gui/src/components/WorkflowConsole.jsx``.
"""

import copy
from typing import Any, Dict, List

__all__ = ["planner_tabs", "enabled_tabs", "apply_overrides"]


def planner_tabs(workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every Planner tab in the workflow document, enabled or not."""
    tabs = (workflow.get("metadata", {}).get("gui", {})
            .get("planner", {}).get("tabs", []))
    return tabs if isinstance(tabs, list) else []


def enabled_tabs(workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The tabs that should actually run, in the order the Planner lists them."""
    return [t for t in planner_tabs(workflow) if t.get("enabled")]


def apply_overrides(workflow: Dict[str, Any],
                    overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``workflow`` with one tab's overrides baked in.

    ``overrides`` maps a parameter-node id to the values that node should take
    for this arm. Only value-bearing keys are copied across, so a tab can change
    what a node holds but never move or rename it on the canvas.
    """
    patched = copy.deepcopy(workflow)

    for sw in patched.get("subworkflows", {}).values():
        params = sw.get("parameters")
        if not params:
            continue
        for i, param in enumerate(params):
            override = overrides.get(param.get("id"))
            if not override:
                continue
            merged = dict(param)
            for key in ("parameters", "items", "entries", "listType"):
                if key in override:
                    merged[key] = override[key]
            params[i] = merged

    _propagate_step_counts(patched, overrides)
    return patched


def _propagate_step_counts(patched: Dict[str, Any],
                           overrides: Dict[str, Any]) -> None:
    """Push an overridden loop count into the places the run actually reads.

    A scheduler's "Simulation Steps" parameter node is wired to its controller,
    but the executor takes the loop count from ``controller.number_of_steps``
    and the synthesized main's call ``iterations`` -- not from the node. Patch
    the node alone and a tab's step count is silently ignored.
    """
    for sw_name, sw in patched.get("subworkflows", {}).items():
        ctrl = sw.get("controller") or {}
        overridden = next((pid for pid in ctrl.get("parameter_nodes", [])
                           if pid in overrides), None)
        if not overridden:
            continue

        node = next((p for p in sw.get("parameters", [])
                     if p.get("id") == overridden), None)
        node_params = (node or {}).get("parameters", {})
        raw = (node_params.get("steps")
               or node_params.get("step_count")
               or node_params.get("numberOfSteps"))
        try:
            steps = int(float(raw))
        except (TypeError, ValueError):
            continue

        ctrl["number_of_steps"] = steps
        main = patched.get("subworkflows", {}).get("main", {})
        for call in main.get("subworkflow_calls", []):
            if call.get("subworkflow_name") == sw_name:
                call["iterations"] = steps
