"""trace.py must (a) parse real transcripts, (b) attribute a defect to the Write
that made it and the reasoning just before, and (c) catch contamination. The
attribution/leak logic is proven on synthetic transcripts (deterministic); the
parser robustness is proven on the real session logs on disk."""
import glob
import json
import os
from pathlib import Path

import pytest

from evals.harness import trace as T

REAL_DIR = Path(os.path.expanduser(
    "~/.claude/projects/-Users-gennaroabbruzzese-Documents-BIDSA-OpenCellComms-main-MicroCpy"))


# --------------------------------------------------------------- synthetic transcript
def _rec(rtype, content):
    return {"type": rtype, "timestamp": "2026-07-14T00:00:00Z", "message": {"content": content}}


def _write_transcript(tmp_path, records):
    p = tmp_path / "trace.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return p


def _thinking(text):
    return {"type": "thinking", "thinking": text, "signature": "x"}


def _tool_use(name, tid, inp):
    return {"type": "tool_use", "name": name, "id": tid, "input": inp}


def _tool_result(tid, text, is_error=False):
    return {"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": is_error}


def test_parse_and_provenance(tmp_path):
    recs = [
        _rec("assistant", [_thinking("I'll home diffusion under the sugar resource."),
                           _tool_use("Write", "t1", {"file_path": "/ws/PLUGIN/functions/sugar/grow.py",
                                                     "content": "def grow(env): ..."})]),
        _rec("user", [_tool_result("t1", "File created")]),
    ]
    events = T.parse_transcript(_write_transcript(tmp_path, recs))
    prov = T.provenance(events)
    assert any(p.endswith("grow.py") for p in prov)


def test_attribution_links_defect_to_reasoning(tmp_path):
    """A defect in a file must resolve to the Write that made it AND the thinking
    block immediately before that Write."""
    recs = [
        _rec("assistant", [_thinking("I'll loop over env.cells inside the step."),
                           _tool_use("Write", "t1",
                                     {"file_path": "/ws/PLUGIN/functions/f/migrate.py",
                                      "content": "for cell in env.cells: ..."})]),
        _rec("user", [_tool_result("t1", "ok")]),
    ]
    events = T.parse_transcript(_write_transcript(tmp_path, recs))
    att = T.attribute(events, "opencellcomms_adapters/PLUGIN/functions/f/migrate.py")
    assert att["writes"], "defect not tied to any Write"
    joined = " ".join(t for r in att["reasoning"] for t in r["thinking"])
    assert "env.cells" in joined, "reasoning that produced the defect was not captured"


def test_leak_detection_flags_quarantined_read(tmp_path):
    recs = [
        _rec("assistant", [_tool_use("Read", "t1", {"file_path": "/repo/.../sugarscape.json"})]),
        _rec("user", [_tool_result("t1", "{...}")]),
    ]
    events = T.parse_transcript(_write_transcript(tmp_path, recs))
    leaks = T.detect_leaks(events, quarantined_paths=["sugarscape.json"])
    assert len(leaks) == 1 and "sugarscape.json" in leaks[0]["matched"]


def test_no_leak_when_reading_allowed_files(tmp_path):
    recs = [
        _rec("assistant", [_tool_use("Read", "t1", {"file_path": "/repo/CLAUDE.md"})]),
        _rec("user", [_tool_result("t1", "...")]),
    ]
    events = T.parse_transcript(_write_transcript(tmp_path, recs))
    assert T.detect_leaks(events, quarantined_paths=["sugarscape.json"]) == []


def test_identifier_leak(tmp_path):
    recs = [_rec("assistant", [_tool_use("Bash", "t1", {"command": "grep move_to_best_sugar ."})])]
    events = T.parse_transcript(_write_transcript(tmp_path, recs))
    leaks = T.detect_leaks(events, quarantined_paths=[], identifiers=["move_to_best_sugar"])
    assert leaks and "move_to_best_sugar" in leaks[0]["matched"]


def test_process_metrics_protocol_order(tmp_path):
    """JSON-before-PY and validator-run are the protocol-adherence signals."""
    recs = [
        _rec("assistant", [_tool_use("Write", "t1", {"file_path": "/ws/wf.json", "content": "{}"})]),
        _rec("user", [_tool_result("t1", "ok")]),
        _rec("assistant", [_tool_use("Bash", "t2", {"command": "python scripts/validate_workflow.py wf.json"})]),
        _rec("user", [_tool_result("t2", "OK")]),
        _rec("assistant", [_tool_use("Write", "t3", {"file_path": "/ws/f.py", "content": "def f(): ..."})]),
        _rec("user", [_tool_result("t3", "ok")]),
    ]
    events = T.parse_transcript(_write_transcript(tmp_path, recs))
    m = T.process_metrics(events)
    assert m["wrote_json_before_py"] is True
    assert m["ran_validator"] is True and m["n_validator_runs"] == 1


# --------------------------------------------------------------- real transcripts
def _real_transcripts():
    return sorted(glob.glob(str(REAL_DIR / "*.jsonl")))


@pytest.mark.skipif(not _real_transcripts(), reason="no historical transcripts on this machine")
def test_parses_every_real_transcript():
    """The parser must survive every real session log without raising."""
    for f in _real_transcripts():
        events = T.parse_transcript(f)
        assert isinstance(events, list)


@pytest.mark.skipif(not _real_transcripts(), reason="no historical transcripts on this machine")
def test_real_transcript_has_reasoning_and_tools():
    """At least one real transcript carries thinking + tool calls + written artifacts
    — the substrate the whole reasoning analysis depends on."""
    best = max(_real_transcripts(), key=lambda f: os.path.getsize(f))
    events = T.parse_transcript(best)
    assert any(e.kind == "thinking" for e in events)
    assert any(e.kind == "tool_use" for e in events)
    assert T.provenance(events), "no artifacts written in the largest transcript"
