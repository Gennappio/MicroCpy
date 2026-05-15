"""Post-processing example: summarize the occ_events.jsonl stream.

Demonstrates the composable contract: anything after
``run_physicell_simulation`` reads from ``context['physicell']`` —
specifically ``events_jsonl`` here.

The rate-tag mapping (0=apoptosis, 1=necrosis, 2=migration_speed) mirrors
the constants in ``src/codegen/physicell/runtime/occ_observability.cpp``.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path
from typing import Any, Dict

from src.workflow.decorators import register_function

_RATE_LABELS = {
    0.0: "apoptosis",
    1.0: "necrosis",
    2.0: "migration_speed",
}


@register_function(
    display_name="Summarize PhysiCell Events",
    description=(
        "Read context['physicell']['events_jsonl'] and print a per-event-type "
        "and per-rate-tag summary. Drop this node after "
        "run_physicell_simulation in any workflow to get a quick textual "
        "report. Writes context['physicell_event_summary']."
    ),
    category="FINALIZATION",
    parameters=[
        {
            "name": "max_lines_to_show",
            "type": "INT",
            "description": "Show the first N rule_engine_changed events verbatim (0 = none).",
            "default": 5,
            "min_value": 0,
            "max_value": 1000,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    compatible_kernels=["biophysics", "physicell"],
)
def summarize_physicell_events(
    context: Dict[str, Any] = None,
    max_lines_to_show: int = 5,
    **kwargs,
) -> bool:
    if context is None:
        print("[ERROR] [summarize_physicell_events] no context")
        return False
    info = context.get("physicell") or {}
    jsonl_path_str = info.get("events_jsonl")
    if not jsonl_path_str:
        print("[ERROR] [summarize_physicell_events] context['physicell']"
              "['events_jsonl'] missing. Put a run_physicell_simulation "
              "node before this one.")
        return False

    jsonl_path = Path(jsonl_path_str)
    if not jsonl_path.exists():
        print(f"[ERROR] [summarize_physicell_events] {jsonl_path} not found")
        return False

    by_event: collections.Counter = collections.Counter()
    by_rate: collections.Counter = collections.Counter()
    by_cell: collections.Counter = collections.Counter()
    first_rule_fires = []

    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = evt.get("event", "?")
            by_event[kind] += 1
            by_cell[evt.get("cell_id", -1)] += 1
            if kind == "rule_engine_changed":
                rate = evt.get("rate")
                label = _RATE_LABELS.get(rate, f"rate={rate}")
                by_rate[label] += 1
                if len(first_rule_fires) < max_lines_to_show:
                    first_rule_fires.append(evt)

    total = sum(by_event.values())
    print("")
    print("─" * 60)
    print(f"PhysiCell event summary  ({jsonl_path})")
    print("─" * 60)
    print(f"  total events: {total}")
    for kind, n in by_event.most_common():
        print(f"    {kind:24s} {n}")
    if by_rate:
        print("  rule_engine_changed by rate tag:")
        for label, n in by_rate.most_common():
            print(f"    {label:24s} {n}")
    print(f"  distinct cells touched: {len(by_cell)}")
    if first_rule_fires:
        print(f"  first {len(first_rule_fires)} rule fire(s):")
        for evt in first_rule_fires:
            print(f"    {json.dumps(evt)}")
    print("─" * 60)

    context["physicell_event_summary"] = {
        "by_event": dict(by_event),
        "by_rate": dict(by_rate),
        "distinct_cells": len(by_cell),
        "total_events": total,
    }
    return True
