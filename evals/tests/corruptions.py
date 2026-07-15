"""Inject a *single, named* structural defect into a workflow document.

These are the harness's own adversarial fixtures: a comparator that cannot tell
the benchmark from a benchmark with an injected orphan is not a comparator
(plan, Phase 1). Each function deep-copies its input and returns a corrupted doc
carrying exactly one known defect, so a test can assert the defect is both
*detected* and *classified* with the right taxonomy token.

Each corruption documents the rule it should trip:
  inject_orphan                 -> validator WFV-2 (orphan behaviour)
  inject_environment_behavior   -> validator WFV-3 (environment.behavior_subworkflows)
  inject_for_each_on_creation   -> validator WFV-7 (creation scheduled with for_each)
  inject_leftover_agent_init    -> validator WFV-6 (per-agent init removed)
  drop_scheduler_call           -> compare_workflow (scheduler role-sequence differs)
  remove_agent_creation         -> compare_workflow (missing creation) + validator warn
  reorder_init_sequence         -> compare_workflow (init order differs)
"""
from __future__ import annotations

import copy
from typing import Optional


def _gui(doc):
    return doc.setdefault("metadata", {}).setdefault("gui", {})


def _find_call(subworkflows, orchestrator, target):
    sw = subworkflows.get(orchestrator) or {}
    for c in sw.get("subworkflow_calls") or []:
        if c.get("subworkflow_name") == target:
            return c
    return None


def _first_agent_kind(doc) -> Optional[dict]:
    aks = _gui(doc).get("agent_kinds") or []
    return aks[0] if aks else None


def inject_orphan(doc: dict, name: str = "secret_behavior") -> dict:
    """Add a subworkflow the scheduler calls but no GUI tab homes -> WFV-2."""
    doc = copy.deepcopy(doc)
    gui = _gui(doc)
    sched_name = (gui.get("scheduler") or {}).get("subworkflow") or "__scheduler__"
    subs = doc.setdefault("subworkflows", {})
    subs[name] = {
        "controller": {"id": f"controller-{name}", "type": "initNode", "label": name.upper()},
        "functions": [], "subworkflow_calls": [], "execution_order": [],
    }
    call = {"id": f"orphan-call-{name}", "type": "subworkflow_call", "subworkflow_name": name}
    sched = subs.setdefault(sched_name, {"subworkflow_calls": [], "execution_order": []})
    sched.setdefault("subworkflow_calls", []).append(call)
    if sched.get("execution_order"):
        sched["execution_order"].append(call["id"])
    return doc


def inject_environment_behavior(doc: dict, name: str = "stray") -> dict:
    """Park a behaviour under environment.behavior_subworkflows -> WFV-3."""
    doc = copy.deepcopy(doc)
    _gui(doc).setdefault("environment", {}).setdefault("behavior_subworkflows", []).append(name)
    return doc


def inject_for_each_on_creation(doc: dict) -> dict:
    """Add a for_each to a scheduled create_subworkflow -> WFV-7."""
    doc = copy.deepcopy(doc)
    gui = _gui(doc)
    ak = _first_agent_kind(doc)
    if not ak or not ak.get("create_subworkflow"):
        raise ValueError("no agent kind with a create_subworkflow to corrupt")
    create = ak["create_subworkflow"]
    init_name = (gui.get("init_sequence") or {}).get("subworkflow")
    subs = doc.get("subworkflows") or {}
    call = _find_call(subs, init_name, create) or _find_call(subs, "main", create)
    if call is None:
        raise ValueError(f"creation '{create}' is not scheduled anywhere to corrupt")
    call["for_each"] = {"type": "agent", "kind": ak.get("name"), "order": "random"}
    return doc


def inject_leftover_agent_init(doc: dict, name: str = "tumor_init") -> dict:
    """Give an agent kind a leftover per-agent init_subworkflow -> WFV-6."""
    doc = copy.deepcopy(doc)
    ak = _first_agent_kind(doc)
    if not ak:
        raise ValueError("no agent kind to corrupt")
    ak["init_subworkflow"] = name
    return doc


def drop_scheduler_call(doc: dict) -> dict:
    """Remove the first per-agent Step call from the scheduler -> role-seq differs."""
    doc = copy.deepcopy(doc)
    gui = _gui(doc)
    sched_name = (gui.get("scheduler") or {}).get("subworkflow") or "__scheduler__"
    step_names = set()
    for ak in gui.get("agent_kinds") or []:
        step_names |= set(ak.get("behavior_subworkflows") or [])
    sched = (doc.get("subworkflows") or {}).get(sched_name) or {}
    calls = sched.get("subworkflow_calls") or []
    for i, c in enumerate(calls):
        if c.get("subworkflow_name") in step_names:
            removed = calls.pop(i)
            order = sched.get("execution_order") or []
            if removed.get("id") in order:
                order.remove(removed["id"])
            return doc
    raise ValueError("no agent-step call in the scheduler to drop")


def remove_agent_creation(doc: dict) -> dict:
    """Null out the first agent kind's create_subworkflow -> creation missing."""
    doc = copy.deepcopy(doc)
    ak = _first_agent_kind(doc)
    if not ak:
        raise ValueError("no agent kind to corrupt")
    ak["create_subworkflow"] = None
    return doc


def reorder_init_sequence(doc: dict) -> dict:
    """Reverse the init sequence -> world/resources/agents order violated."""
    doc = copy.deepcopy(doc)
    gui = _gui(doc)
    init_name = (gui.get("init_sequence") or {}).get("subworkflow")
    sw = (doc.get("subworkflows") or {}).get(init_name) or {}
    calls = sw.get("subworkflow_calls") or []
    if len(calls) < 2:
        raise ValueError("init sequence too short to reorder")
    calls.reverse()
    order = sw.get("execution_order") or []
    if order:
        order.reverse()
    return doc
