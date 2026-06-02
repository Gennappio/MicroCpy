"""Lift PhysiCell domain/cell-type/Hill-rule nodes out of a workflow JSON.

The Phase 3 workflow format places three codegen-only function nodes —
``define_substrate``, ``define_cell_type``, ``define_hill_rule`` — inside
the usual v2.0 subworkflow tree. This module walks that tree and produces
a flat ``spec`` dict consumable by
``src.codegen.physicell.scaffold.generate_project``.

Two parameter-passing styles are supported:
1. Inline ``"parameters": {"substrate": {...}}`` on the function node.
2. GUI-style ``"parameter_nodes": ["param_id"]`` pointing at a sibling
   ``dictParameterNode``. The ``target_param`` field on the parameter
   node tells us which function argument to populate.

Top-level workflow fields (``physicell`` block) carry domain / overall /
save / user_parameters. Falling back to defaults from ``scaffold._DEFAULT_*``
when omitted is fine — generate_project re-validates and defaults anyway.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

_NODES_WE_CARE_ABOUT = ("define_substrate", "define_cell_type", "define_hill_rule")
_TARGET_PARAM_BY_FUNCTION = {
    "define_substrate":  "substrate",
    "define_cell_type":  "cell_type",
    "define_hill_rule":  "rule",
}


class WorkflowSpecError(ValueError):
    """Raised when a workflow does not yield a usable PhysiCell spec."""


def _iter_subworkflows(workflow: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield every subworkflow dict in the v2.0 workflow tree (DFS)."""
    seen = set()
    stack: List[Dict[str, Any]] = []
    sws = workflow.get("subworkflows") or {}
    for sw in sws.values():
        stack.append(sw)
    while stack:
        sw = stack.pop()
        sid = id(sw)
        if sid in seen:
            continue
        seen.add(sid)
        yield sw
        nested = sw.get("subworkflows") or {}
        for child in nested.values():
            stack.append(child)


def _dict_param_entries_to_dict(entries: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Flatten a dictParameterNode's ``entries`` list back into a plain dict."""
    out: Dict[str, Any] = {}
    for entry in entries:
        k = entry.get("key")
        if k is None:
            continue
        out[k] = entry.get("value")
    return out


def _resolve_parameter_nodes(
    node: Dict[str, Any],
    param_nodes_by_id: Dict[str, Dict[str, Any]],
    function_name: str,
) -> Dict[str, Any]:
    """Return {target_param_name: value} from this node's parameter_nodes refs."""
    out: Dict[str, Any] = {}
    for pid in node.get("parameter_nodes") or ():
        pn = param_nodes_by_id.get(pid)
        if pn is None:
            continue
        target = pn.get("target_param") or pn.get("targetParam")
        if not target:
            continue
        ptype = pn.get("type", "")
        if ptype == "dictParameterNode":
            out[target] = _dict_param_entries_to_dict(pn.get("entries") or ())
        elif ptype == "listParameterNode":
            out[target] = list(pn.get("items") or ())
        else:
            out[target] = pn.get("value")
    return out


def _node_arguments(node: Dict[str, Any], param_nodes_by_id: Dict[str, Dict[str, Any]],
                    function_name: str) -> Dict[str, Any]:
    """Merge inline parameters + parameter_nodes-resolved values."""
    args: Dict[str, Any] = {}
    inline = node.get("parameters") or {}
    if isinstance(inline, dict):
        args.update(inline)
    args.update(_resolve_parameter_nodes(node, param_nodes_by_id, function_name))
    return args


def _collect_definitions(
    workflow: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Walk the workflow and return (substrates, cell_types, hill_rules)."""
    substrates: List[Dict[str, Any]] = []
    cell_types: List[Dict[str, Any]] = []
    hill_rules: List[Dict[str, Any]] = []

    for sw in _iter_subworkflows(workflow):
        params_by_id: Dict[str, Dict[str, Any]] = {
            p["id"]: p for p in (sw.get("parameters") or []) if "id" in p
        }
        # The canonical schema key is "functions" (per WorkflowFunction.to_dict);
        # accept "nodes" too for hand-written test fixtures.
        function_list = sw.get("functions") or sw.get("nodes") or ()
        for node in function_list:
            fn = node.get("function_name") or node.get("function")
            if fn not in _NODES_WE_CARE_ABOUT:
                continue
            if node.get("enabled") is False:
                continue
            args = _node_arguments(node, params_by_id, fn)
            target = _TARGET_PARAM_BY_FUNCTION[fn]
            payload = args.get(target)
            if not isinstance(payload, dict):
                raise WorkflowSpecError(
                    f"Workflow node {node.get('id', '?')!r} ({fn}) has no "
                    f"dict parameter {target!r}. Got {payload!r}."
                )
            if fn == "define_substrate":
                substrates.append(payload)
            elif fn == "define_cell_type":
                cell_types.append(payload)
            elif fn == "define_hill_rule":
                hill_rules.append(payload)

    return substrates, cell_types, hill_rules


def spec_from_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Lift the PhysiCell spec out of a workflow dict.

    The workflow may carry top-level ``physicell`` overrides for the
    domain / overall / save / options / parallel / user_parameters fields;
    anything missing is left to ``generate_project``'s defaulting.
    """
    substrates, cell_types, hill_rules = _collect_definitions(workflow)
    if not substrates:
        raise WorkflowSpecError(
            "Workflow has no define_substrate nodes — PhysiCell needs at "
            "least one substrate."
        )
    if not cell_types:
        raise WorkflowSpecError(
            "Workflow has no define_cell_type nodes — PhysiCell needs at "
            "least one cell type."
        )

    spec: Dict[str, Any] = {
        "substrates": substrates,
        "cell_types": cell_types,
        "hill_rules": hill_rules,
    }
    overrides = workflow.get("physicell") or {}
    for key in ("domain", "overall", "parallel", "save", "options",
                "user_parameters"):
        if key in overrides:
            spec[key] = overrides[key]
    return spec


__all__ = ["spec_from_workflow", "WorkflowSpecError"]
