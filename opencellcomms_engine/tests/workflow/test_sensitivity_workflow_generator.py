"""The sensitivity-suite generator keeps every arm on one gene-step budget.

Regenerates the suite into a temp folder and checks the invariants a scientist
relies on: each arm covers GENE_STEPS_TOTAL single-gene updates per cell and
snapshots every PLOT_EVERY_GENE_STEPS of them, tab names are unique across the
suite, the snapshot intervals are wired parameter nodes (no inline copy left to
shadow them), and every file passes the workflow validator without warnings.
"""
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SUITE = REPO / "opencellcomms_adapters" / "MicroC" / "workflows" / "sensitivity_analysis"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = _load("build_sensitivity_workflows", SUITE / "build_sensitivity_workflows.py")
validator = _load("validate_workflow", REPO / "opencellcomms_engine" / "scripts" / "validate_workflow.py")


def _effective(nodes, overrides, node_id, key):
    override = overrides.get(node_id, {}).get("parameters", {})
    return override.get(key, nodes[node_id]["parameters"][key])


def test_generated_suite_invariants(tmp_path):
    assert generator.main(["--out", str(tmp_path)]) == 0
    files = sorted(tmp_path.glob("p53_sa_*.json"))
    assert len(files) == len(generator.AXES) == 5

    registry = validator.load_registry()
    seen_tabs = set()
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        nodes = {p["id"]: p for sw in doc["subworkflows"].values()
                 for p in sw.get("parameters", [])}
        assert doc["metadata"]["workflow_source_path"] == \
            f"{generator.SOURCE_DIR}/{path.name}"

        # The inline intervals were removed, not shadowed.
        plots = doc["subworkflows"]["iteration_plots"]["functions"]
        by_id = {fn["id"]: fn for fn in plots}
        assert "plot_interval" not in by_id[generator.QUADRANT_PLOT_FUNCTION]["parameters"]
        assert generator.PLOT_INTERVAL_NODE in by_id[generator.QUADRANT_PLOT_FUNCTION]["parameter_nodes"]
        assert "interval" not in by_id[generator.CHECKPOINT_FUNCTION]["parameters"]
        assert generator.CHECKPOINT_INTERVAL_NODE in by_id[generator.CHECKPOINT_FUNCTION]["parameter_nodes"]

        tabs = doc["metadata"]["gui"]["planner"]["tabs"]
        assert len(tabs) == 3
        for tab in tabs:
            assert tab["name"] not in seen_tabs
            seen_tabs.add(tab["name"])
            ov = tab["parameterOverrides"]
            prop = int(_effective(nodes, ov, generator.PROPAGATION_NODE, "propagation_steps"))
            steps = int(_effective(nodes, ov, generator.STEPS_NODE, "steps"))
            plot = int(_effective(nodes, ov, generator.PLOT_INTERVAL_NODE, "plot_interval"))
            ckpt = int(_effective(nodes, ov, generator.CHECKPOINT_INTERVAL_NODE, "interval"))
            assert steps * prop == generator.GENE_STEPS_TOTAL, (path.name, tab["name"])
            assert plot * prop == generator.PLOT_EVERY_GENE_STEPS, (path.name, tab["name"])
            assert ckpt == plot

        errors, warnings, skipped = validator.check_workflow(str(path), registry)
        assert skipped is None
        assert errors == [] and warnings == [], (path.name, errors, warnings)

    prop_doc = json.loads((tmp_path / "p53_sa_propagation_steps.json").read_text())
    by_name = {t["name"]: t["parameterOverrides"] for t in prop_doc["metadata"]["gui"]["planner"]["tabs"]}
    assert by_name["prop_1"][generator.STEPS_NODE]["parameters"]["steps"] == 10000
    assert by_name["prop_50"][generator.STEPS_NODE]["parameters"]["steps"] == 200
    assert by_name["prop_50"][generator.PLOT_INTERVAL_NODE]["parameters"]["plot_interval"] == "1"


def test_smoke_copies_keep_the_forced_run_length(tmp_path):
    out = tmp_path / "smoke"
    assert generator.main(["--out", str(out), "--steps", "3", "--prefix", "smoke_"]) == 0
    doc = json.loads((out / "smoke_p53_sa_propagation_steps.json").read_text())
    nodes = {p["id"]: p for sw in doc["subworkflows"].values() for p in sw.get("parameters", [])}
    assert nodes[generator.STEPS_NODE]["parameters"]["steps"] == 3
    for tab in doc["metadata"]["gui"]["planner"]["tabs"]:
        assert generator.STEPS_NODE not in tab["parameterOverrides"]
