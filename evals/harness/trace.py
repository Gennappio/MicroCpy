"""Reasoning capture — turn a coding-agent transcript into an explanation of
*where the reasoning broke*. This is the part the user emphasized most.

The Claude Code transcript (a ``.jsonl``, one record per line — either a persisted
session file under ``~/.claude/projects/`` or a tee'd ``--output-format stream-json``
run) interleaves the agent's ``thinking`` blocks with its ``tool_use`` calls and
their ``tool_result`` returns. That interleaving is what makes attribution
possible: a defect in a generated file can be tied to the ``Write`` that produced
it, and thence to the ``thinking`` block that immediately preceded that Write.

What this module produces:
  * ``parse_transcript``  — a flat, ordered ``Event`` timeline
  * ``provenance``        — every artifact -> the Write/Edit events that touched it
  * ``attribute``         — a defect (file, optional line) -> those Writes + the
                            reasoning quoted just before them
  * ``detect_leaks``      — reads of quarantined paths / benchmark identifiers, which
                            invalidate a run (contamination is the #1 validity threat)
  * ``process_metrics``   — did it read the docs before writing? run the validator
                            unprompted? follow protocol order (IR before code)?

Nothing here needs the engine; it is pure transcript analysis.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_WRITE_TOOLS = {"Write", "Edit", "NotebookEdit", "MultiEdit"}
_READ_TOOLS = {"Read", "Grep", "Glob", "Bash", "LS"}


@dataclass
class Event:
    index: int
    kind: str                         # "thinking" | "text" | "tool_use" | "tool_result"
    record_type: str                  # "assistant" | "user" | ...
    timestamp: Optional[str] = None
    # thinking/text
    text: str = ""
    # tool_use
    tool_name: Optional[str] = None
    tool_id: Optional[str] = None
    tool_input: Dict[str, Any] = field(default_factory=dict)
    # tool_result
    tool_use_id: Optional[str] = None
    result_text: str = ""
    is_error: bool = False

    def to_dict(self) -> dict:
        d = {"index": self.index, "kind": self.kind, "record_type": self.record_type}
        if self.kind in ("thinking", "text"):
            d["text"] = self.text
        elif self.kind == "tool_use":
            d.update(tool_name=self.tool_name, tool_id=self.tool_id, tool_input=self.tool_input)
        elif self.kind == "tool_result":
            d.update(tool_use_id=self.tool_use_id, is_error=self.is_error,
                     result_preview=self.result_text[:200])
        return d


# --------------------------------------------------------------------------- parse
def _blocks(record: dict) -> List[dict]:
    msg = record.get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    if isinstance(content, str):  # plain-text user/assistant turn
        return [{"type": "text", "text": content}]
    return []


def _result_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                parts.append(b.get("text") or b.get("content") or "")
            else:
                parts.append(str(b))
        return "\n".join(p for p in parts if p)
    return "" if content is None else str(content)


def parse_transcript(path) -> List[Event]:
    """Flatten a ``.jsonl`` transcript into an ordered event timeline."""
    events: List[Event] = []
    i = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        rtype = rec.get("type", "")
        ts = rec.get("timestamp")
        for b in _blocks(rec):
            bt = b.get("type")
            if bt == "thinking":
                events.append(Event(i, "thinking", rtype, ts, text=b.get("thinking", "")))
            elif bt == "text":
                events.append(Event(i, "text", rtype, ts, text=b.get("text", "")))
            elif bt == "tool_use":
                events.append(Event(i, "tool_use", rtype, ts,
                                    tool_name=b.get("name"), tool_id=b.get("id"),
                                    tool_input=b.get("input") or {}))
            elif bt == "tool_result":
                events.append(Event(i, "tool_result", rtype, ts,
                                    tool_use_id=b.get("tool_use_id"),
                                    result_text=_result_to_text(b.get("content")),
                                    is_error=bool(b.get("is_error"))))
            else:
                continue
            i += 1
    return events


# --------------------------------------------------------------------------- provenance
def _artifact_path(ev: Event) -> Optional[str]:
    if ev.kind != "tool_use" or ev.tool_name not in _WRITE_TOOLS:
        return None
    return ev.tool_input.get("file_path") or ev.tool_input.get("notebook_path")


def provenance(events: List[Event]) -> Dict[str, List[Event]]:
    """artifact path -> ordered Write/Edit events that touched it."""
    out: Dict[str, List[Event]] = {}
    for ev in events:
        p = _artifact_path(ev)
        if p:
            out.setdefault(p, []).append(ev)
    return out


def thinking_before(events: List[Event], target_index: int, window: int = 3) -> List[str]:
    """The thinking block(s) immediately preceding an event, back to the previous
    tool_use (the reasoning that produced this action)."""
    out: List[str] = []
    for ev in reversed([e for e in events if e.index < target_index]):
        if ev.kind == "tool_use":
            break
        if ev.kind == "thinking" and ev.text.strip():
            out.append(ev.text.strip())
            if len(out) >= window:
                break
    return list(reversed(out))


# --------------------------------------------------------------------------- attribution
def attribute(events: List[Event], file_path: str, line: Optional[int] = None) -> dict:
    """Tie a defect in ``file_path`` to the Write/Edit that introduced it and the
    reasoning quoted just before that Write.

    Path matching is by suffix so a quarantined-workspace absolute path lines up
    with the repo-relative path a comparator reports."""
    prov = provenance(events)
    writes = [ev for p, evs in prov.items() if _same_file(p, file_path) for ev in evs]
    if not writes:
        return {"file": file_path, "line": line, "writes": [], "reasoning": [],
                "note": "no Write/Edit for this artifact in the transcript"}
    # The introducing write for a specific line is best-effort the last edit whose
    # new content mentions the line's neighbourhood; without the line we use all.
    chosen = writes if line is None else writes
    reasoning = []
    for w in chosen:
        reasoning.append({"write_index": w.index, "tool": w.tool_name,
                          "thinking": thinking_before(events, w.index)})
    return {"file": file_path, "line": line,
            "writes": [w.index for w in chosen], "reasoning": reasoning}


def _same_file(a: str, b: str) -> bool:
    a, b = str(a), str(b)
    if a == b:
        return True
    na, nb = Path(a).name, Path(b).name
    if na != nb:
        return False
    # match on a shared tail (plugin/functions/cat/f.py) to survive workspace roots
    pa, pb = Path(a).parts, Path(b).parts
    k = min(len(pa), len(pb), 4)
    return pa[-k:] == pb[-k:]


# --------------------------------------------------------------------------- leaks
def detect_leaks(events: List[Event], quarantined_paths: List[str],
                 identifiers: Optional[List[str]] = None) -> List[dict]:
    """Reads (Read/Grep/Glob/Bash/LS) that touch a quarantined path, or that surface
    a benchmark-distinctive identifier. Any hit invalidates the run."""
    identifiers = identifiers or []
    q_names = {Path(p).name for p in quarantined_paths}
    q_strs = [str(p) for p in quarantined_paths]
    leaks: List[dict] = []
    for ev in events:
        if ev.kind != "tool_use" or ev.tool_name not in _READ_TOOLS:
            continue
        blob = json.dumps(ev.tool_input)
        hit = None
        for qs in q_strs:
            if qs and qs in blob:
                hit = qs
                break
        if hit is None:
            for qn in q_names:
                # a bare filename reference (e.g. reading sugarscape.json directly)
                if qn and re.search(rf"\b{re.escape(qn)}\b", blob):
                    hit = qn
                    break
        if hit is None:
            for ident in identifiers:
                if ident and ident in blob:
                    hit = f"identifier:{ident}"
                    break
        if hit:
            leaks.append({"index": ev.index, "tool": ev.tool_name,
                          "matched": hit, "input": ev.tool_input})
    return leaks


# --------------------------------------------------------------------------- process metrics
def process_metrics(events: List[Event], doc_names: Optional[List[str]] = None) -> dict:
    """Behavioural counters over the trace, each a paper metric."""
    doc_names = doc_names or ["CLAUDE.md", "AGENT_ASSISTED_ABM_AUTHORING.md",
                              "occ_new-model", "sugarscape.json", "tcell_corral.json", "microc.json"]
    tool_uses = [e for e in events if e.kind == "tool_use"]

    writes = [e for e in tool_uses if e.tool_name in _WRITE_TOOLS]
    first_write_index = writes[0].index if writes else None

    def _first_index(pred) -> Optional[int]:
        for e in tool_uses:
            if pred(e):
                return e.index
        return None

    first_json_write = _first_index(lambda e: e.tool_name in _WRITE_TOOLS
                                    and str(_artifact_path(e) or "").endswith(".json"))
    first_py_write = _first_index(lambda e: e.tool_name in _WRITE_TOOLS
                                   and str(_artifact_path(e) or "").endswith(".py"))

    validator_runs = [e for e in tool_uses if e.tool_name == "Bash"
                      and "validate_workflow" in json.dumps(e.tool_input)]

    docs_read = {}
    for name in doc_names:
        idx = _first_index(lambda e, n=name: e.tool_name in _READ_TOOLS
                           and n in json.dumps(e.tool_input))
        if idx is not None:
            docs_read[name] = idx

    return {
        "n_tool_uses": len(tool_uses),
        "n_writes": len(writes),
        "first_write_index": first_write_index,
        "read_docs_before_first_write": {n: i for n, i in docs_read.items()
                                         if first_write_index is None or i < first_write_index},
        "ran_validator": bool(validator_runs),
        "n_validator_runs": len(validator_runs),
        # protocol order: the /occ_new-model contract is skeleton JSON before any .py
        "wrote_json_before_py": (first_json_write is not None and
                                 (first_py_write is None or first_json_write < first_py_write)),
        "first_json_write_index": first_json_write,
        "first_py_write_index": first_py_write,
    }


# --------------------------------------------------------------------------- summary
def summarize(path, quarantined_paths=None, identifiers=None) -> dict:
    events = parse_transcript(path)
    prov = provenance(events)
    leaks = detect_leaks(events, quarantined_paths or [], identifiers or [])
    return {
        "transcript": str(path),
        "n_events": len(events),
        "n_thinking": sum(1 for e in events if e.kind == "thinking"),
        "n_tool_use": sum(1 for e in events if e.kind == "tool_use"),
        "artifacts_written": sorted(prov),
        "leaks": leaks,
        "contaminated": bool(leaks),
        "process": process_metrics(events),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Analyze a coding-agent transcript.")
    ap.add_argument("transcript")
    ap.add_argument("--quarantined", nargs="*", default=[], help="paths that must NOT be read")
    ap.add_argument("--identifiers", nargs="*", default=[], help="benchmark-distinctive strings")
    ap.add_argument("--attribute", help="file path of a defect to attribute to reasoning")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.attribute:
        events = parse_transcript(args.transcript)
        print(json.dumps(attribute(events, args.attribute), indent=2))
        return 0

    summary = summarize(args.transcript, args.quarantined, args.identifiers)
    if args.json:
        print(json.dumps(summary, indent=2))
        return 1 if summary["contaminated"] else 0

    print(f"transcript : {Path(args.transcript).name}")
    print(f"events     : {summary['n_events']} ({summary['n_thinking']} thinking, "
          f"{summary['n_tool_use']} tool calls)")
    print(f"artifacts  : {len(summary['artifacts_written'])} written")
    p = summary["process"]
    print(f"protocol   : wrote_json_before_py={p['wrote_json_before_py']} "
          f"ran_validator={p['ran_validator']} ({p['n_validator_runs']}x)")
    print(f"docs read before first write: {list(p['read_docs_before_first_write'])}")
    if summary["contaminated"]:
        print(f"\n!! CONTAMINATED — {len(summary['leaks'])} leak(s); run is INVALID:")
        for lk in summary["leaks"][:5]:
            print(f"   [{lk['index']}] {lk['tool']} matched {lk['matched']}")
    else:
        print("\nno leaks detected.")
    return 1 if summary["contaminated"] else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
