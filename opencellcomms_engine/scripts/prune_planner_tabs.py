#!/usr/bin/env python3
"""
Prune a workflow's Planner tabs to sparse diffs from the canvas base values.

Older GUI versions snapshotted EVERY connected parameter node into each Planner
tab, so a workflow JSON carried the same value in the base subworkflow AND in
every tab -- multiple sources of truth for numbers that never differed. Both
override runners (src/workflow/planner.py apply_overrides and the GUI's
applyOverridesToWorkflow) merge per parameter-node id, so an override entry
deep-equal to the base node is a no-op: dropping it cannot change any run.

What this script does, per workflow file:

  1. Drops every tab override entry whose value keys (parameters / items /
     entries / listType) deep-equal the base parameter node's. Entries whose id
     matches no base node are KEPT -- validate_workflow.py errors on those.
  2. Coerces a surviving controller-connected `steps` override to int when it
     is int-like (fixes the "80" / 80 string-int drift).
  3. With --base-steps N: sets the base loop count to N on ALL THREE places the
     engine and GUI read it from -- the controller-connected steps parameter
     node, the controller's `number_of_steps`, and the `iterations` of the
     `main` call to that subworkflow -- then prunes again, so tabs that
     overrode steps to N lose the override entirely.

Usage:
    python scripts/prune_planner_tabs.py <workflow.json> [...] [--base-steps N]

The file is rewritten in place with 2-space indentation (the repo's workflow
JSON style). Exit code 0 on success, 1 if any file could not be processed.
"""

import argparse
import json
import sys
from pathlib import Path

PLANNER_VALUE_KEYS = ("parameters", "items", "entries", "listType")
STEP_KEYS = ("steps", "step_count", "numberOfSteps")


def override_matches_base(override, base_node):
    """True when the override's value keys deep-equal the base node's."""
    return all(
        k not in override or override[k] == base_node.get(k)
        for k in PLANNER_VALUE_KEYS
    )


def base_param_nodes(data):
    """{param_node_id: node} across all subworkflows."""
    return {
        p["id"]: p
        for sw in (data.get("subworkflows") or {}).values()
        for p in (sw.get("parameters") or [])
        if p.get("id")
    }


def controller_param_ids(data):
    """Ids of parameter nodes wired to a subworkflow controller (loop counts),
    mapped to their subworkflow name."""
    out = {}
    for name, sw in (data.get("subworkflows") or {}).items():
        ctrl = sw.get("controller") or {}
        for pid in ctrl.get("parameter_nodes") or []:
            out[pid] = name
    return out


def as_int(value):
    """int(value) via float for '80'/'80.0'; None when not int-like."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return int(f) if f == int(f) else None


def set_base_steps(data, n):
    """Set the loop count to n on the steps parameter node, the controller, and
    the main call's iterations, for every subworkflow whose controller is
    driven by a steps parameter node (in practice: __scheduler__)."""
    ctrl_params = controller_param_ids(data)
    nodes = base_param_nodes(data)
    touched_subworkflows = set()
    for pid, sw_name in ctrl_params.items():
        node = nodes.get(pid)
        params = (node or {}).get("parameters")
        if not isinstance(params, dict) or not any(k in params for k in STEP_KEYS):
            continue
        for k in STEP_KEYS:
            if k in params:
                params[k] = n
        sw = data["subworkflows"][sw_name]
        (sw.get("controller") or {})["number_of_steps"] = n
        touched_subworkflows.add(sw_name)
    for sw in (data.get("subworkflows") or {}).values():
        for call in sw.get("subworkflow_calls") or []:
            if call.get("subworkflow_name") in touched_subworkflows and "iterations" in call:
                call["iterations"] = n
    return touched_subworkflows


def prune_file(path, base_steps=None):
    data = json.loads(path.read_text(encoding="utf-8"))
    tabs = (
        (((data.get("metadata") or {}).get("gui") or {}).get("planner") or {}).get("tabs")
    ) or []
    if not tabs and base_steps is None:
        print(f"{path}: no planner tabs, nothing to do")
        return

    if base_steps is not None:
        touched = set_base_steps(data, base_steps)
        if touched:
            print(f"{path}: base loop count set to {base_steps} on {sorted(touched)}")
        else:
            print(f"{path}: --base-steps given but no controller-connected steps "
                  f"parameter node found", file=sys.stderr)

    nodes = base_param_nodes(data)
    ctrl_params = controller_param_ids(data)
    dropped = 0
    for tab in tabs:
        overrides = tab.get("parameterOverrides") or {}
        kept = {}
        for pid, ov in overrides.items():
            base = nodes.get(pid)
            # Normalize int-like steps overrides before comparing, so "80"
            # written by the GUI equals an int 80 in the base.
            if pid in ctrl_params and isinstance(ov.get("parameters"), dict):
                for k in STEP_KEYS:
                    if k in ov["parameters"]:
                        n = as_int(ov["parameters"][k])
                        if n is not None:
                            ov["parameters"][k] = n
            if base is not None and override_matches_base(ov, base):
                dropped += 1
                continue
            kept[pid] = ov
        tab["parameterOverrides"] = kept
    print(f"{path}: dropped {dropped} redundant override entr{'y' if dropped == 1 else 'ies'} "
          f"across {len(tabs)} tab(s)")

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("workflows", nargs="+", type=Path)
    ap.add_argument("--base-steps", type=int, default=None,
                    help="also set the base loop count (steps param node + "
                         "controller + main iterations) to this value before pruning")
    args = ap.parse_args()

    failed = False
    for path in args.workflows:
        try:
            prune_file(path, args.base_steps)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
