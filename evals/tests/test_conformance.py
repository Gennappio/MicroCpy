"""conformance must (a) pass the clean canonical benchmarks and (b) catch each
injected rule violation with the right taxonomy token. The AST anti-pattern
checks are exercised on synthetic bad code because the benchmarks are (correctly)
clean — the whole point is that they don't trip the detector."""
import json

from evals.harness import conformance as CF
from evals.harness.conformance import (
    Finding,
    code_findings,
    conformance_report,
    scan_plugin_functions,
)
from evals.tests import corruptions as C


def _write(tmp_path, doc, name="wf.json"):
    p = tmp_path / name
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


# ------------------------------------------------------------------- clean benchmarks
def test_canonical_benchmarks_have_no_hard_errors(canonical_case):
    name, wf, plugin = canonical_case
    rep = conformance_report(str(wf), str(plugin))
    assert rep.validator_errors == [], f"{name}: {rep.validator_errors}"
    hard = [f for f in rep.findings if f.severity == "error"]
    assert hard == [], f"{name} unexpected hard findings: {[f.to_dict() for f in hard]}"


# ------------------------------------------------------------------- validator layer
def test_orphan_detected(tmp_path, canonical_case):
    name, wf, _ = canonical_case
    doc = json.loads(wf.read_text())
    path = _write(tmp_path, C.inject_orphan(doc))
    rep = conformance_report(path)
    assert not rep.conformant
    assert any("orphan" in e for e in rep.validator_errors)


def test_environment_behavior_detected(tmp_path, canonical_case):
    name, wf, _ = canonical_case
    doc = json.loads(wf.read_text())
    path = _write(tmp_path, C.inject_environment_behavior(doc))
    rep = conformance_report(path)
    assert not rep.conformant
    assert any("environment.behavior_subworkflows" in e for e in rep.validator_errors)


def test_for_each_on_creation_detected(tmp_path, canonical_case):
    name, wf, _ = canonical_case
    doc = json.loads(wf.read_text())
    try:
        corrupted = C.inject_for_each_on_creation(doc)
    except ValueError:
        return
    path = _write(tmp_path, corrupted)
    rep = conformance_report(path)
    assert not rep.conformant
    assert any("for_each" in e for e in rep.validator_errors)


def test_leftover_agent_init_detected(tmp_path, canonical_case):
    name, wf, _ = canonical_case
    doc = json.loads(wf.read_text())
    path = _write(tmp_path, C.inject_leftover_agent_init(doc))
    rep = conformance_report(path)
    assert not rep.conformant
    assert any("no longer supported" in e or "init" in e for e in rep.validator_errors)


# ------------------------------------------------------------------- AST anti-patterns
_STEP_CANVAS = "tumor_step"
_CREATE_CANVAS = "tumor_create"


def _abm_doc(step_funcs=(), create_funcs=()):
    """Minimal workflow doc that homes given function names on a per-agent Step
    and a collective Creation canvas for one agent kind."""
    subs = {
        _STEP_CANVAS: {"functions": [{"id": f"s{i}", "function_name": fn} for i, fn in enumerate(step_funcs)]},
        _CREATE_CANVAS: {"functions": [{"id": f"c{i}", "function_name": fn} for i, fn in enumerate(create_funcs)]},
    }
    gui = {
        "agent_kinds": [{
            "name": "tumor_cell",
            "create_subworkflow": _CREATE_CANVAS,
            "behavior_subworkflows": [_STEP_CANVAS],
        }],
        "scheduler": {"subworkflow": "__scheduler__"},
    }
    return {"metadata": {"gui": gui}, "subworkflows": subs}


def _plugin_with(tmp_path, filename, source):
    d = tmp_path / "PLUGIN"
    (d / "functions" / "cat").mkdir(parents=True, exist_ok=True)
    (d / "functions" / "cat" / filename).write_text(source, encoding="utf-8")
    return d


DOUBLE_ITER_SRC = '''
from src.workflow.registry import register_function

@register_function(name="migrate", stage="intercellular")
def migrate(env, **kwargs):
    for cell in env.cells:          # WRONG: collective loop in a per-agent Step
        cell.state.phenotype = "migrating"
    return True
'''

GOOD_STEP_SRC = '''
from src.workflow.registry import register_function

@register_function(name="migrate", stage="intercellular")
def migrate(env, **kwargs):
    agent = env.agent
    if agent is None:               # correct per-agent shape
        return True
    agent.request_move(target=agent.position)
    return True
'''

UNGUARDED_CREATE_SRC = '''
from src.workflow.registry import register_function

@register_function(name="setup_cell", stage="initialization")
def setup_cell(env, **kwargs):
    env.agent.state.age = 0          # WRONG: env.agent is None on a Creation canvas
    return True
'''

GUARDED_CREATE_SRC = '''
from src.workflow.registry import register_function

@register_function(name="setup_cell", stage="initialization")
def setup_cell(env, **kwargs):
    for cell in ([env.cell] if env.cell is not None else env.cells):
        cell.state.age = 0           # dual-convention guard -> safe, must NOT flag
    return True
'''


def _has(findings, root_cause):
    return [f for f in findings if f.root_cause == root_cause]


def test_double_iteration_detected(tmp_path):
    plugin = _plugin_with(tmp_path, "migrate.py", DOUBLE_ITER_SRC)
    doc = _abm_doc(step_funcs=["migrate"])
    found = code_findings(doc, plugin)
    hits = _has(found, "double-iteration")
    assert hits and hits[0].severity == "error", [f.to_dict() for f in found]


def test_good_step_not_flagged(tmp_path):
    plugin = _plugin_with(tmp_path, "migrate.py", GOOD_STEP_SRC)
    doc = _abm_doc(step_funcs=["migrate"])
    found = code_findings(doc, plugin)
    assert not _has(found, "double-iteration")


def test_unguarded_env_agent_on_creation_detected(tmp_path):
    plugin = _plugin_with(tmp_path, "setup_cell.py", UNGUARDED_CREATE_SRC)
    doc = _abm_doc(create_funcs=["setup_cell"])
    found = code_findings(doc, plugin)
    hits = _has(found, "env.agent-on-collective")
    assert hits and hits[0].severity == "error", [f.to_dict() for f in found]


def test_guarded_env_agent_on_creation_not_flagged(tmp_path):
    """The exact benchmark pattern (dual-convention guard) must stay clean."""
    plugin = _plugin_with(tmp_path, "setup_cell.py", GUARDED_CREATE_SRC)
    doc = _abm_doc(create_funcs=["setup_cell"])
    found = code_findings(doc, plugin)
    assert not _has(found, "env.agent-on-collective"), [f.to_dict() for f in found]


def test_registered_name_scan(tmp_path):
    plugin = _plugin_with(tmp_path, "migrate.py", DOUBLE_ITER_SRC)
    scanned = scan_plugin_functions(plugin)
    assert "migrate" in scanned
