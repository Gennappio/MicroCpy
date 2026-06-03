#!/usr/bin/env python3
"""Compact OpenCellComms v2.0 workflow / subworkflow JSON files losslessly.

The GUI exporter writes every field of every node, including empty containers
and values that are already the loader default (parameters: {}, enabled: true,
step_count: 1, function_file: "", subworkflow_calls: [], ...). Both the engine
parser (src/workflow/schema.py, all `.get(key, DEFAULT)`) and the GUI loader
(workflowIOSlice.js, all `field || DEFAULT`) substitute exactly those defaults
when a key is absent. So dropping a key whose value equals that shared default
is a *semantically null* edit.

Two fields are deliberately KEPT even when at their nominal default:
  * `position` — the GUI has no auto-layout; a missing position loads at
    {0,0}, stacking every node at the origin and wrecking the canvas.
  * non-empty `description` — human-readable note shown/round-tripped by the GUI.

Safety: before writing, each file is parsed by the engine schema both before
and after compaction and the canonical `to_dict()` forms are compared. If they
differ, the file is left untouched and the discrepancy is reported.

Usage:
    python tools/compact_workflow.py --check  file1.json [file2.json ...]
    python tools/compact_workflow.py --write  file1.json [file2.json ...]
"""
import argparse
import json
import sys
from pathlib import Path

# Engine schema oracle
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.workflow.schema import WorkflowDefinition, SubWorkflow  # noqa: E402


# (key, default) pairs that are safe to drop when the value equals the default.
# `position` and a non-empty `description` are intentionally absent here.
_FUNC_DEFAULTS = {
    "parameters": {},
    "parameter_nodes": [],
    "enabled": True,
    "verbose": False,
    "function_file": "",
    "custom_name": "",
    "step_count": 1,
    "description": "",      # only dropped when "" (empty)
}
_CALL_DEFAULTS = {
    "parameters": {},
    "parameter_nodes": [],
    "enabled": True,
    "verbose": False,
    "iterations": 1,
    "description": "",
    "results": "",
    "context_mapping": {},
}
_SW_DEFAULTS = {
    "functions": [],
    "subworkflow_calls": [],
    "parameters": [],
    "input_parameters": [],
    "list_parameters": [],
    "dict_parameters": [],
    "execution_order": [],
    "enabled": True,
    "deletable": True,
    "description": "",
}


def _drop_defaults(node: dict, defaults: dict) -> dict:
    out = {}
    for k, v in node.items():
        if k in defaults and v == defaults[k] and k != "function_file":
            continue
        # function_file: drop when "" or None
        if k == "function_file" and v in ("", None):
            continue
        out[k] = v
    return out


def compact_subworkflow(sw: dict) -> dict:
    sw = _drop_defaults(sw, _SW_DEFAULTS)
    if "functions" in sw:
        sw["functions"] = [_drop_defaults(f, _FUNC_DEFAULTS) for f in sw["functions"]]
    if "subworkflow_calls" in sw:
        sw["subworkflow_calls"] = [_drop_defaults(c, _CALL_DEFAULTS) for c in sw["subworkflow_calls"]]
    return sw


def compact_doc(doc: dict) -> dict:
    """Compact either a full workflow (has 'subworkflows') or a standalone
    subworkflow export (has 'subworkflow' + 'format')."""
    if "subworkflows" in doc:
        doc = dict(doc)
        doc["subworkflows"] = {
            name: compact_subworkflow(sw) for name, sw in doc["subworkflows"].items()
        }
        return doc
    if "subworkflow" in doc:
        doc = dict(doc)
        doc["subworkflow"] = compact_subworkflow(doc["subworkflow"])
        return doc
    raise ValueError("not a workflow or subworkflow document")


def _oracle(doc: dict):
    """Canonical engine view of a document, used to prove equivalence."""
    if "subworkflows" in doc:
        return WorkflowDefinition.from_dict(doc).to_dict()
    name = doc.get("name", "sw")
    return SubWorkflow.from_dict(name, doc["subworkflow"]).to_dict()


def process(path: Path, write: bool) -> tuple[bool, int, int, str]:
    original = json.loads(path.read_text())
    compacted = compact_doc(json.loads(json.dumps(original)))  # deep copy

    before = _oracle(original)
    after = _oracle(compacted)
    if before != after:
        return False, 0, 0, "ORACLE MISMATCH — not equivalent, skipped"

    old_text = json.dumps(original, indent=2, ensure_ascii=False) + "\n"
    new_text = json.dumps(compacted, indent=2, ensure_ascii=False) + "\n"
    old_n, new_n = len(old_text.encode()), len(new_text.encode())
    if write:
        path.write_text(new_text)
    return True, old_n, new_n, "ok"


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()

    tot_old = tot_new = 0
    fail = 0
    for f in args.files:
        p = Path(f)
        ok, old_n, new_n, msg = process(p, write=args.write)
        if not ok:
            fail += 1
            print(f"  [FAIL] {p.name}: {msg}")
            continue
        tot_old += old_n
        tot_new += new_n
        pct = (1 - new_n / old_n) * 100 if old_n else 0
        print(f"  [{'WROTE' if args.write else 'OK'}] {p.name}: {old_n} -> {new_n} bytes ({pct:.0f}% smaller)")

    print(f"\nTotal: {tot_old} -> {tot_new} bytes "
          f"({(1 - tot_new / tot_old) * 100:.0f}% smaller), {fail} failures")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
