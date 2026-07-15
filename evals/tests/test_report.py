"""The dossier is the harness's headline deliverable: defect -> reasoning -> root
cause. These tests prove the composition holds end-to-end — including the one that
matters most, that a code defect is tied back to the thinking block that produced
it via the transcript."""
import json

from evals.harness import report as RPT
from evals.tests import corruptions as C
from evals.tests.test_conformance import DOUBLE_ITER_SRC, _abm_doc, _plugin_with


def _write_json(tmp_path, doc, name):
    p = tmp_path / name
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


def test_clean_self_comparison_is_pass(canonical_case):
    name, wf, plugin = canonical_case
    d = RPT.build_dossier(
        case=name, condition="full", tier="spec2code",
        candidate_workflow=str(wf), benchmark_workflow=str(wf), plugin_dir=str(plugin),
    )
    assert d.conformant and d.structurally_isomorphic
    assert [x for x in d.defects if x.severity == "error"] == []


def test_corrupted_workflow_produces_defects(tmp_path, canonical_case):
    name, wf, plugin = canonical_case
    doc = json.loads(wf.read_text())
    cand = _write_json(tmp_path, C.inject_orphan(doc), "cand.json")
    d = RPT.build_dossier(
        case=name, condition="full", tier="spec2code",
        candidate_workflow=cand, benchmark_workflow=str(wf),
    )
    assert not d.conformant
    assert any("orphan" in df.root_cause for df in d.defects)


def test_dossier_attributes_code_defect_to_reasoning(tmp_path):
    """A double-iteration bug in a .py must surface as a defect whose reasoning
    quotes the thinking block that wrote it."""
    plugin = _plugin_with(tmp_path, "migrate.py", DOUBLE_ITER_SRC)
    doc = _abm_doc(step_funcs=["migrate"])
    wf = _write_json(tmp_path, doc, "wf.json")

    # synthetic transcript: the agent reasons, then writes the defective file
    migrate_path = str(plugin / "functions" / "cat" / "migrate.py")
    transcript = tmp_path / "trace.jsonl"
    transcript.write_text("\n".join(json.dumps(r) for r in [
        {"type": "assistant", "message": {"content": [
            {"type": "thinking", "thinking": "I'll iterate over env.cells in the step to move each cell."},
            {"type": "tool_use", "name": "Write", "id": "t1",
             "input": {"file_path": migrate_path, "content": DOUBLE_ITER_SRC}},
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}},
    ]), encoding="utf-8")

    d = RPT.build_dossier(
        case="synthetic", condition="naked", tier="spec2code",
        candidate_workflow=wf, benchmark_workflow=wf, plugin_dir=str(plugin),
        transcript=str(transcript),
    )
    hits = [df for df in d.defects if df.root_cause == "double-iteration"]
    assert hits, "double-iteration defect not found"
    quoted = " ".join(t for r in hits[0].reasoning for t in r.get("thinking", []))
    assert "env.cells" in quoted, "defect not tied to the reasoning that produced it"
    assert hits[0].guard, "no guard (constraint that should have caught it) attached"

    md = RPT.render_markdown(d)
    assert "double-iteration" in md and "env.cells" in md


def test_dossier_flags_contamination(tmp_path):
    doc = _abm_doc(step_funcs=[])
    wf = _write_json(tmp_path, doc, "wf.json")
    transcript = tmp_path / "trace.jsonl"
    transcript.write_text(json.dumps(
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "id": "t1",
             "input": {"file_path": "/repo/opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json"}}]}}
    ), encoding="utf-8")
    d = RPT.build_dossier(
        case="sugarscape", condition="full", tier="spec2code",
        candidate_workflow=wf, benchmark_workflow=wf,
        transcript=str(transcript), quarantined_paths=["sugarscape.json"],
    )
    assert d.contaminated is True
    assert any("INVALID" in n for n in d.notes)
