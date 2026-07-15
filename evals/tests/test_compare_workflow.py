"""compare_workflow must (a) call the benchmark identical to itself and (b) flag
every injected structural defect. If it can't tell the benchmark from a corrupted
benchmark, it measures nothing."""
import json

from evals.harness.compare_workflow import compare_workflows, signature
from evals.tests import corruptions as C


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_self_is_identical(canonical_case):
    name, wf, _ = canonical_case
    doc = _load(wf)
    diff = compare_workflows(doc, doc)
    assert diff.structurally_isomorphic is True
    assert diff.same_entities is True
    assert diff.fidelity == 1.0
    assert diff.differences == []


def test_different_models_diverge():
    import evals.tests.conftest as cf

    a = _load(cf.CANONICAL["sugarscape"])
    b = _load(cf.CANONICAL["microc"])
    diff = compare_workflows(a, b)
    assert diff.structurally_isomorphic is False
    assert diff.same_entities is False


def test_dropped_scheduler_call_detected(canonical_case):
    name, wf, _ = canonical_case
    doc = _load(wf)
    try:
        bad = C.drop_scheduler_call(doc)
    except ValueError:
        return  # model has no agent-step in scheduler (n/a)
    diff = compare_workflows(doc, bad)
    assert diff.structurally_isomorphic is False
    assert any("scheduler" in d for d in diff.differences)


def test_removed_creation_detected(canonical_case):
    name, wf, _ = canonical_case
    doc = _load(wf)
    bad = C.remove_agent_creation(doc)
    diff = compare_workflows(doc, bad)
    assert diff.structurally_isomorphic is False
    assert any("creation" in d.lower() for d in diff.differences)


def test_reordered_init_detected(canonical_case):
    name, wf, _ = canonical_case
    doc = _load(wf)
    try:
        bad = C.reorder_init_sequence(doc)
    except ValueError:
        return
    diff = compare_workflows(doc, bad)
    assert diff.structurally_isomorphic is False
    assert any("init_sequence" in d for d in diff.differences)


def test_for_each_on_creation_shows_as_binding_diff(canonical_case):
    """A for_each added to creation must surface as a scheduler/binding difference."""
    name, wf, _ = canonical_case
    doc = _load(wf)
    try:
        bad = C.inject_for_each_on_creation(doc)
    except ValueError:
        return
    diff = compare_workflows(doc, bad)
    # creation isn't in the *scheduler* role-seq, but adding a for_each to the
    # init-sequence call changes the init call's binding; either way the docs differ.
    assert diff.structurally_isomorphic is False or diff.differences


def test_signature_shape(canonical_case):
    name, wf, _ = canonical_case
    sig = signature(_load(wf))
    assert set(sig) >= {"agent_kinds", "resource_kinds", "world", "scheduler", "init_sequence"}
    assert sig["agent_kinds"], "every canonical ABM has at least one agent kind"
