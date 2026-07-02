"""Regression tests for per-entity `for_each` binding save/restore.

The scheduler's per-agent ask binds ``context['_current_agent']`` /
``_current_cell`` for the duration of the ask. The bug these tests guard: on
exit the executor used to blank those bindings to ``None`` unconditionally, so
(a) a nested ask clobbered the *outer* agent binding, and (b) an exception
mid-loop leaked a stale binding into post-loop nodes. The fix saves the prior
binding before the loop and restores it in a ``finally``.
"""

from types import SimpleNamespace

import pytest

from src.workflow.schema import WorkflowDefinition
from src.workflow.executor import WorkflowExecutor


def _executor():
    wf = WorkflowDefinition(version="2.0", name="for-each-binding-test")
    return WorkflowExecutor(wf, observability_enabled=False)


class _FakeAgent:
    def __init__(self, aid):
        self.id = aid
        self.cell = SimpleNamespace(id=aid)

    def is_alive(self):
        return True


class _FakePop:
    def __init__(self, agents):
        self._agents = agents

    def agents(self):
        return list(self._agents)

    def agents_of_kind(self, kind):
        return list(self._agents)


def test_agent_binding_restored_to_prior_value():
    """A per-agent ask restores whatever agent was bound before it ran."""
    ex = _executor()
    node = SimpleNamespace(subworkflow_name="step")
    seen = []

    def fake_exec(name, context, **kwargs):
        seen.append(context["_current_agent"].id)
        return context

    ex.execute_subworkflow = fake_exec

    sentinel = _FakeAgent("outer")
    context = {
        "abm_population": _FakePop([_FakeAgent("a"), _FakeAgent("b")]),
        "_rng": __import__("numpy").random.default_rng(0),
        "_current_agent": sentinel,
        "_current_cell": sentinel.cell,
    }
    ex._run_for_each_entity(node, {"type": "agent", "kind": "k"}, context, {})

    # Each inner agent was bound during the ask...
    assert set(seen) == {"a", "b"}
    # ...and the outer binding is restored afterwards (not blanked to None).
    assert context["_current_agent"] is sentinel
    assert context["_current_cell"] is sentinel.cell


def test_nested_for_each_does_not_clobber_outer_binding():
    """An inner ask nested inside an outer ask leaves the outer agent bound."""
    ex = _executor()
    inner_pop = _FakePop([_FakeAgent("inner1")])
    outer_after_inner = []

    def fake_exec(name, context, **kwargs):
        outer = context["_current_agent"]
        # Simulate the outer behaviour containing a nested per-agent ask.
        ex._run_for_each_entity(
            SimpleNamespace(subworkflow_name="inner"),
            {"type": "agent", "kind": "k"},
            {**context, "abm_population": inner_pop},
            {},
        )
        # After the nested ask returns, the outer agent must still be bound.
        outer_after_inner.append(context["_current_agent"] is outer)
        return context

    # The nested call runs execute_subworkflow too; give it a no-op for depth 2.
    real_exec = fake_exec

    def dispatch(name, context, **kwargs):
        if name == "inner":
            return context
        return real_exec(name, context, **kwargs)

    ex.execute_subworkflow = dispatch

    context = {
        "abm_population": _FakePop([_FakeAgent("outer1")]),
        "_rng": __import__("numpy").random.default_rng(0),
    }
    ex._run_for_each_entity(node := SimpleNamespace(subworkflow_name="outer"),
                            {"type": "agent", "kind": "k"}, context, {})

    assert outer_after_inner == [True]
    # Top-level ask restores to the prior value (None here).
    assert context["_current_agent"] is None


def test_binding_restored_even_when_subworkflow_raises():
    """An exception mid-ask still restores the prior binding (try/finally)."""
    ex = _executor()

    def boom(name, context, **kwargs):
        raise RuntimeError("boom")

    ex.execute_subworkflow = boom

    sentinel = _FakeAgent("outer")
    context = {
        "abm_population": _FakePop([_FakeAgent("a")]),
        "_rng": __import__("numpy").random.default_rng(0),
        "_current_agent": sentinel,
        "_current_cell": sentinel.cell,
    }
    with pytest.raises(RuntimeError):
        ex._run_for_each_entity(SimpleNamespace(subworkflow_name="step"),
                                {"type": "agent", "kind": "k"}, context, {})

    assert context["_current_agent"] is sentinel
    assert context["_current_cell"] is sentinel.cell
