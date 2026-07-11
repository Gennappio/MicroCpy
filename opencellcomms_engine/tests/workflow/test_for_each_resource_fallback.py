"""Regression tests for the resource `for_each` fallback gate.

`_run_for_each_entity` runs a resource behaviour once per registered ABM domain
resource. When the named `kind` is NOT a domain resource, `domain.resource(kind)`
raises KeyError; the executor tolerates this ONLY for a real FiPy-solved substance
field (CCL21, MicroC substances) on the simulator, running the behaviour once as a
collective field solve. A `kind` that is neither a resource nor a substance is a
misspelling and must fail loudly rather than silently run once with a bogus name.
"""

from types import SimpleNamespace

import pytest

from src.workflow.schema import WorkflowDefinition
from src.workflow.executor import WorkflowExecutor


def _executor():
    wf = WorkflowDefinition(version="2.0", name="for-each-resource-fallback-test")
    return WorkflowExecutor(wf, observability_enabled=False)


class _FakeDomain:
    """A domain with named ABM resources; resource(name) raises KeyError for
    anything not registered (mirrors src/abm/domain.py)."""

    def __init__(self, names):
        self._names = list(names)

    def resource(self, name):
        if name not in self._names:
            raise KeyError(f"No resource '{name}' (have: {sorted(self._names)})")
        return SimpleNamespace(name=name)

    def resources(self):
        return [SimpleNamespace(name=n) for n in self._names]


def _simulator_with(*substance_names):
    return SimpleNamespace(
        state=SimpleNamespace(substances={n: object() for n in substance_names})
    )


def test_substance_field_runs_once_as_collective_solve():
    """A FiPy substance (not an ABM resource) runs the behaviour once, bound to
    its name, rather than raising."""
    ex = _executor()
    calls = []

    def fake_exec(name, context, **kwargs):
        calls.append((name, kwargs.get("parameters", {}).get("resource")))
        return context

    ex.execute_subworkflow = fake_exec

    context = {
        "domain": _FakeDomain(["sugar"]),       # ABM resources
        "simulator": _simulator_with("CCL21"),  # FiPy substances
    }
    node = SimpleNamespace(subworkflow_name="diffuse_ccl21")
    ex._run_for_each_entity(node, {"type": "resource", "kind": "CCL21"}, context, {})

    assert calls == [("diffuse_ccl21", "CCL21")]
    # The current-resource-kind binding is restored (not leaked to post-loop nodes).
    assert context.get("_current_resource_kind") is None


def test_misspelled_resource_kind_raises():
    """A kind that is neither an ABM resource nor a substance fails loudly, and
    the error lists the valid resources and substances."""
    ex = _executor()
    ex.execute_subworkflow = lambda *a, **k: pytest.fail("subworkflow must not run")

    context = {
        "domain": _FakeDomain(["sugar"]),
        "simulator": _simulator_with("CCL21"),
    }
    node = SimpleNamespace(subworkflow_name="diffuse_ccl21")
    with pytest.raises(KeyError) as exc:
        ex._run_for_each_entity(node, {"type": "resource", "kind": "Oxygenn"}, context, {})

    msg = str(exc.value)
    assert "Oxygenn" in msg
    assert "sugar" in msg   # valid ABM resources are listed
    assert "CCL21" in msg   # valid substances are listed


def test_missing_simulator_still_raises_for_unknown_kind():
    """Pure-ABM run (no simulator in context): an unknown kind is a misspelling,
    not a silent run-once."""
    ex = _executor()
    ex.execute_subworkflow = lambda *a, **k: pytest.fail("subworkflow must not run")

    context = {"domain": _FakeDomain(["sugar"])}  # no 'simulator'
    node = SimpleNamespace(subworkflow_name="grow_sugar")
    with pytest.raises(KeyError):
        ex._run_for_each_entity(node, {"type": "resource", "kind": "sugarr"}, context, {})
