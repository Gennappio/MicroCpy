#!/usr/bin/env python3
"""Derive the p53 sensitivity-analysis workflows from microc_p53_experiment.json.

One workflow per control variable, each a full copy of the baseline with:
  * the baseline's ``p53off`` Planner arm baked into the canvas (so every tab
    below is a sparse, single-parameter diff -- docs/READABILITY.md R2.2);
  * the run length and the plot cadence derived from one gene-step budget:
    every arm runs GENE_STEPS_TOTAL single-gene updates per cell (scheduler
    steps = budget / propagation steps) and draws a quadrant plot plus a
    checkpoint every PLOT_EVERY_GENE_STEPS gene updates, so arms with
    different propagation step counts share the same x axis and the same
    number of snapshots; the two intervals become parameter nodes on the
    iteration_plots canvas so a Planner tab can set them;
  * ``symbiosis_summary`` replaced by ``sensitivity_summary`` running
    ``record_sensitivity_metrics`` (``fate_summary`` is kept);
  * Record Lactate Balance at the end of diffusion_step, capturing viable-cell
    exchange before gene/fate updates for the sensitivity CSV;
  * the two ``../data/`` paths rewritten for this subfolder;
  * ``metadata.workflow_source_path`` set to the repo-relative path, so a
    Planner arm executed from a temp copy still resolves those paths;
  * one enabled Planner tab per level, named uniquely across the suite
    (GUI runs write to runs/<tab>/, CLI runs to runs/<file stem>_<tab>/).

Usage (from anywhere):
    python build_sensitivity_workflows.py                       # regenerate the suite in place
    python build_sensitivity_workflows.py --steps 3 --prefix smoke_ --out /tmp/sa_smoke
                                                                # throwaway short copies

The output is a normalised re-serialisation of the baseline (json.dumps with
indent=2), so numbers keep their values but not their spelling (1e-06 for
0.000001). Regenerate rather than hand-edit the suite files.
"""

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT / "opencellcomms_engine"))

from src.workflow.planner import apply_overrides, planner_tabs  # noqa: E402

BASELINE = HERE.parent / "microc_p53_experiment.json"
BAKED_TAB = "p53off"
SOURCE_DIR = "opencellcomms_adapters/MicroC/workflows/sensitivity_analysis"
SOLVER_SPACING_UM = 50  # size / nx of the baseline; kept constant across domain sizes

# The gene-step budget every arm covers, and the snapshot cadence, both in
# single-gene updates per cell. Scheduler steps and plot/checkpoint intervals
# are derived from these per propagation step count (2000 steps, one snapshot
# every 10 iterations at the baseline's 5 steps). --steps overrides the run
# length for throwaway smoke copies only.
GENE_STEPS_TOTAL = 10_000
PLOT_EVERY_GENE_STEPS = 50

STEPS_NODE = "steps_param-__scheduler__"
PROPAGATION_NODE = "gene_update-param_propagation_steps"
PLOT_INTERVAL_NODE = "iteration_plots-param_plot_interval"
CHECKPOINT_INTERVAL_NODE = "iteration_plots-param_checkpoint_interval"
QUADRANT_PLOT_FUNCTION = "iteration_plots-gen_quadrant_plots"
CHECKPOINT_FUNCTION = "iteration_plots-save_state_checkpoint"
GLUCOSE_NODE = "glucose_init-param_substances"
DOMAIN_NODES = {
    "size_x": "envinit-Setup_simulation-param_domain_size_x",
    "size_y": "envinit-Setup_simulation-param_domain_size_y",
    "nx": "envinit-Setup_simulation-param_domain_nx",
    "ny": "envinit-Setup_simulation-param_domain_ny",
}
CELL_HEIGHT_NODE = "envinit-Setup_simulation-param_domain_cell_height"


def _scalar(node_id: str, label: str, key: str, value: str) -> Dict[str, Any]:
    return {node_id: {"label": label, "parameters": {key: value}}}


def _glucose_items(level: float, doc: Dict[str, Any]) -> Dict[str, Any]:
    base = json.loads(_param_node(doc, GLUCOSE_NODE)["items"][0])
    base["initial_value"] = level
    base["boundary_value"] = level
    return {GLUCOSE_NODE: {"label": "Substance (JSON)", "listType": "string",
                           "items": [json.dumps(base, separators=(",", ":"))]}}


def _domain(level: int, doc: Dict[str, Any]) -> Dict[str, Any]:
    cell_height = float(_param_node(doc, CELL_HEIGHT_NODE)["parameters"]["cell_height"])
    if level % SOLVER_SPACING_UM:
        raise SystemExit(f"domain {level} um is not a multiple of the {SOLVER_SPACING_UM} um "
                         f"solver spacing (DomainConfig needs a square grid)")
    if level % cell_height:
        raise SystemExit(f"domain {level} um is not a multiple of the {cell_height:g} um "
                         f"cell height (the biological grid would be truncated)")
    n = str(level // SOLVER_SPACING_UM)
    return {
        **_scalar(DOMAIN_NODES["size_x"], "Size X (μm)", "size_x", str(level)),
        **_scalar(DOMAIN_NODES["size_y"], "Size Y (μm)", "size_y", str(level)),
        **_scalar(DOMAIN_NODES["nx"], "Grid NX", "nx", n),
        **_scalar(DOMAIN_NODES["ny"], "Grid NY", "ny", n),
    }


def _per_step(total_gene_steps: int, propagation_steps: int, what: str) -> int:
    if propagation_steps <= 0 or total_gene_steps % propagation_steps:
        raise SystemExit(f"{what}: {total_gene_steps} gene steps is not a whole number of "
                         f"scheduler steps at propagation_steps={propagation_steps}")
    return total_gene_steps // propagation_steps


def _clock_overrides(propagation_steps: int, doc: Dict[str, Any]) -> Dict[str, Any]:
    """A propagation step count and everything that follows from it.

    The run length and the snapshot intervals are fixed in gene updates, not
    scheduler iterations, so an arm with more updates per iteration runs fewer
    iterations and plots less often per iteration: same x axis, same number of
    snapshots.
    """
    steps = _per_step(GENE_STEPS_TOTAL, propagation_steps, "run length")
    interval = str(_per_step(PLOT_EVERY_GENE_STEPS, propagation_steps, "plot cadence"))
    return {
        **_scalar(PROPAGATION_NODE, "Propagation Steps", "propagation_steps",
                  str(propagation_steps)),
        STEPS_NODE: {"label": "Simulation Steps", "parameters": {"steps": steps}},
        **_scalar(PLOT_INTERVAL_NODE, "Plot Interval (iterations)", "plot_interval", interval),
        **_scalar(CHECKPOINT_INTERVAL_NODE, "Checkpoint Interval (iterations)", "interval",
                  interval),
    }


AXES: List[Dict[str, Any]] = [
    {
        "file": "p53_sa_glucose_consumption",
        "title": "glucose consumption scale",
        "tab_prefix": "glc_cons",
        "levels": [5.6, 7.0, 8.4], "baseline": 7.0,
        "label": lambda v: f"{v:.1f}",
        "overrides": lambda v, doc: _scalar(
            "diffusion_step-param_glucose_conversion_factor", "Glucose Consumption Scale",
            "glucose_conversion_factor", f"{v:g}"),
    },
    {
        "file": "p53_sa_oxygen_consumption",
        "title": "oxygen consumption scale",
        "tab_prefix": "o2_cons",
        "levels": [8.8, 11.0, 13.2], "baseline": 11.0,
        "label": lambda v: f"{v:.1f}",
        "overrides": lambda v, doc: _scalar(
            "diffusion_step-param_oxygen_conversion_factor", "Oxygen Consumption Scale",
            "oxygen_conversion_factor", f"{v:g}"),
    },
    {
        "file": "p53_sa_glucose_boundary",
        "title": "glucose boundary concentration (mM)",
        "tab_prefix": "glc_bnd",
        "levels": [4.5, 5.0, 5.5], "baseline": 5.0,
        "label": lambda v: f"{v:.1f}",
        "overrides": _glucose_items,
    },
    {
        "file": "p53_sa_relative_tumor_size",
        "title": "relative tumour size (domain size, same seed)",
        "tab_prefix": "domain",
        "levels": [1200, 1500, 1800], "baseline": 1500,
        "label": lambda v: str(v),
        "overrides": _domain,
    },
    {
        "file": "p53_sa_propagation_steps",
        "title": "gene propagation steps per scheduler step",
        "tab_prefix": "prop",
        "levels": [1, 10, 50], "baseline": 5,   # the baked value is not a level: no override-free tab
        "label": lambda v: str(v),
        "overrides": _clock_overrides,
    },
]


def _param_node(doc: Dict[str, Any], node_id: str) -> Dict[str, Any]:
    for sw in doc["subworkflows"].values():
        for node in sw.get("parameters") or []:
            if node.get("id") == node_id:
                return node
    raise SystemExit(f"parameter node '{node_id}' not found")


def _param_ids(doc: Dict[str, Any]) -> set:
    return {node.get("id") for sw in doc["subworkflows"].values()
            for node in (sw.get("parameters") or [])}


def _rewrite_relative_paths(doc: Dict[str, Any]) -> int:
    """Prefix every '../' path with one more '../' (the suite is one folder deeper)."""
    rewritten = 0
    for sw in doc["subworkflows"].values():
        holders = [fn.get("parameters") or {} for fn in sw.get("functions") or []]
        holders += [node.get("parameters") or {} for node in sw.get("parameters") or []]
        for params in holders:
            for key, value in params.items():
                if isinstance(value, str) and value.startswith("../"):
                    params[key] = "../" + value
                    rewritten += 1
    return rewritten


def _function_node(doc: Dict[str, Any], subworkflow: str, node_id: str) -> Dict[str, Any]:
    for fn in doc["subworkflows"][subworkflow]["functions"]:
        if fn.get("id") == node_id:
            return fn
    raise SystemExit(f"function node '{node_id}' not found in '{subworkflow}'")


def _expose_snapshot_cadence(doc: Dict[str, Any], interval: int) -> None:
    """Turn the inline plot/checkpoint intervals into wired parameter nodes.

    Inline function parameters win over parameter nodes when the executor
    merges them, so the inline keys are removed, not just shadowed. Both nodes
    start at ``interval`` (the baseline propagation's cadence); the propagation
    tabs override them.
    """
    plots = doc["subworkflows"]["iteration_plots"]
    for fn_id, key, node_id, label in (
        (QUADRANT_PLOT_FUNCTION, "plot_interval", PLOT_INTERVAL_NODE, "Plot Interval (iterations)"),
        (CHECKPOINT_FUNCTION, "interval", CHECKPOINT_INTERVAL_NODE, "Checkpoint Interval (iterations)"),
    ):
        fn = _function_node(doc, "iteration_plots", fn_id)
        if key not in fn["parameters"]:
            raise SystemExit(f"'{fn_id}' carries no inline '{key}' to expose")
        del fn["parameters"][key]
        fn["parameter_nodes"].append(node_id)
    plots["parameters"] += [
        {"id": PLOT_INTERVAL_NODE, "label": "Plot Interval (iterations)",
         "parameters": {"plot_interval": str(interval)}, "position": {"x": 100, "y": 560}},
        {"id": CHECKPOINT_INTERVAL_NODE, "label": "Checkpoint Interval (iterations)",
         "parameters": {"interval": str(interval)}, "position": {"x": 100, "y": 760}},
    ]


def _sensitivity_summary() -> Dict[str, Any]:
    owner = {"type": "agent", "kind": "tumor_cell"}
    reads = ["agent.collection", "agent.self.gene_states", "resource.fields",
             "simulation.results", "simulation.config"]
    return {
        "description": (
            "MicroC: sensitivity_summary (per-iteration CSV of the sensitivity-analysis "
            "metrics: phenotype census and fractions, mitoATP/glycoATP counts and R_MG, "
            "ATP-gate pass fraction of viable cells, oxygen-region census and MSI, "
            "lactate production/consumption/balance from the post-diffusion snapshot, "
            "whole-field Glucose/Oxygen minima, tumour radius and relative tumour size)"),
        "enabled": True,
        "deletable": True,
        "contract": {
            "participants": [owner, {"type": "resource"}],
            "reads": reads, "writes": [], "emits": [], "owner": owner,
        },
        "controller": {
            "id": "controller-sensitivity_summary", "type": "controller",
            "label": "SENSITIVITY SUMMARY", "position": {"x": 100, "y": 100},
            "number_of_steps": 1,
        },
        "functions": [{
            "id": "sensitivity_summary-record_metrics",
            "function_name": "record_sensitivity_metrics",
            "function_file": "",
            "parameters": {"csv_filename": "sensitivity_metrics_over_time.csv"},
            "enabled": True,
            "position": {"x": 400, "y": 100},
            "description": (
                "One CSV row per iteration (timeseries/sensitivity_metrics_over_time.csv): "
                "N_total; N_viable (phenotype not Necrosis/Apoptosis); phenotype counts and "
                "fractions of N_total (Quiescent and Growth_Arrest separately; F_inactive = "
                "1 - F_proliferating); N_mitoATP / N_glycoATP and R_MG = N_mitoATP/N_glycoATP; "
                "N_atp_ok / F_ATP = viable cells with atp_rate > atp_threshold1 x atp_rate_max, "
                "the Proliferation Gate's own law and value read from results['proliferation_gate'] "
                "as published by the gated proliferation node in fate_update; N_oxygenated / "
                "N_hypoxic / F_hypoxic with hypoxic = Oxygen at the cell below the Hypoxia "
                "Threshold node on the left; MSI_mct1 and MSI_mito (the metabolic symbiosis "
                "index law of Record Metabolic Symbiosis); lactate_production_mol_s, "
                "lactate_consumption_mol_s and lactate_balance_mol_s from Record Lactate "
                "Balance on diffusion_step (viable-cell totals before gene/fate updates; "
                "balance = production - consumption, positive release / negative uptake; "
                "blank without a valid snapshot this iteration); glucose_min_mM / oxygen_min_mM over "
                "the whole solver field; tumor_radius_um = max distance of a cell (bio-grid index "
                "x Cell Height) from the domain centre; domain_size_um; relative_tumor_size = "
                "tumor_radius_um / (domain_size_um / 2)."),
            "custom_name": "record_sensitivity_metrics",
            "step_count": 1,
            "parameter_nodes": ["sensitivity_summary-param_hypoxia_threshold"],
            "contract": {"owner": owner, "reads": reads, "writes": [], "emits": []},
        }],
        "subworkflow_calls": [],
        "parameters": [{
            "id": "sensitivity_summary-param_hypoxia_threshold",
            "label": "Hypoxia Threshold (mM)",
            "parameters": {"hypoxia_threshold": 0.022},
            "position": {"x": 100, "y": 240},
        }],
        "execution_order": ["sensitivity_summary-record_metrics"],
        "input_parameters": [],
    }


def _scheduler_call() -> Dict[str, Any]:
    return {
        "id": "sched-call-sensitivity_summary",
        "type": "subworkflow_call",
        "subworkflow_name": "sensitivity_summary",
        "iterations": 1,
        "parameters": {},
        "enabled": True,
        "position": {"x": 400, "y": 500},
        "description": (
            "sensitivity_summary (collective, no for_each: record_sensitivity_metrics is a "
            "whole-population reporter writing one row per iteration). After fate_update, so "
            "results['proliferation_gate'] is published and the census matches the fates just "
            "marked; before division, which consumes them."),
        "parameter_nodes": [],
    }


def _replace_reporter(doc: Dict[str, Any]) -> None:
    subworkflows = doc["subworkflows"]
    if "symbiosis_summary" not in subworkflows:
        raise SystemExit("baseline has no 'symbiosis_summary' subworkflow to replace")
    doc["subworkflows"] = {
        ("sensitivity_summary" if name == "symbiosis_summary" else name):
        (_sensitivity_summary() if name == "symbiosis_summary" else sw)
        for name, sw in subworkflows.items()
    }

    kinds = doc["metadata"]["gui"]["agent_kinds"]
    for kind in kinds:
        kind["behavior_subworkflows"] = [
            "sensitivity_summary" if b == "symbiosis_summary" else b
            for b in kind["behavior_subworkflows"]]

    scheduler = doc["subworkflows"]["__scheduler__"]
    calls = scheduler["subworkflow_calls"]
    idx = [i for i, c in enumerate(calls) if c["id"] == "sched-call-symbiosis_summary"]
    if len(idx) != 1:
        raise SystemExit("baseline scheduler has no 'sched-call-symbiosis_summary' call")
    calls[idx[0]] = _scheduler_call()
    scheduler["execution_order"] = [
        "sched-call-sensitivity_summary" if c == "sched-call-symbiosis_summary" else c
        for c in scheduler["execution_order"]]


def _add_lactate_balance(doc: Dict[str, Any]) -> None:
    # This phase still has the gene states and viability that supplied the solve.
    diffusion = doc['subworkflows']['diffusion_step']
    node_id = 'diffusion_step-record_lactate_balance'
    diffusion['functions'].append({
        'id': node_id,
        'function_name': 'record_lactate_balance',
        'function_file': '',
        'parameters': {},
        'enabled': True,
        'position': {'x': 40, 'y': 1780},
        'description': (
            'Record Lactate Balance: viable-cell production minus consumption (mol/s), '
            'positive release / negative uptake. Captures the metabolic rates after '
            'diffusion, before gene/fate updates. Uses the metabolism node\'s rates '
            'and weights; excludes Necrosis and Apoptosis. Missing rates or a '
            'non-converged solve leave the values undefined. The sensitivity CSV '
            'includes gross production and consumption alongside the balance.'),
        'custom_name': 'Record Lactate Balance',
        'step_count': 1,
        'parameter_nodes': [],
    })
    diffusion['execution_order'].append(node_id)
    diffusion['description'] += (
        ' Record Lactate Balance captures viable-cell exchange at the end of these '
        'solves, before gene/fate updates, for the sensitivity CSV.')


def derive(baseline: Dict[str, Any], axis: Dict[str, Any], file_stem: str,
           steps: int = None) -> Dict[str, Any]:
    tabs = [t for t in planner_tabs(baseline) if t.get("name") == BAKED_TAB]
    if len(tabs) != 1:
        raise SystemExit(f"baseline must carry exactly one '{BAKED_TAB}' Planner tab")
    doc = apply_overrides(copy.deepcopy(baseline), tabs[0].get("parameterOverrides") or {})

    rewritten = _rewrite_relative_paths(doc)
    if rewritten != 2:
        raise SystemExit(f"expected to rewrite 2 '../' paths (bnd_file, checkpoint), got {rewritten}")

    _replace_reporter(doc)
    _add_lactate_balance(doc)

    # Run length and snapshot cadence on the gene-step clock of the baked arm.
    baked_propagation = int(_param_node(doc, PROPAGATION_NODE)["parameters"]["propagation_steps"])
    canvas_steps = _per_step(GENE_STEPS_TOTAL, baked_propagation, "run length")
    _param_node(doc, STEPS_NODE)["parameters"]["steps"] = (
        canvas_steps if steps is None else int(steps))
    _expose_snapshot_cadence(
        doc, _per_step(PLOT_EVERY_GENE_STEPS, baked_propagation, "plot cadence"))

    label: Callable[[Any], str] = axis["label"]
    names = [f"{axis['tab_prefix']}_{label(v)}" for v in axis["levels"]]
    if axis["baseline"] in axis["levels"]:
        baseline_txt = f"the baseline level {axis['baseline']} carries no override"
    else:
        baseline_txt = (f"the baseline value {axis['baseline']} is the canvas value and is run "
                        f"by the other suite files' baseline tabs")
    doc["name"] = f"MicroC p53 SA: {axis['title']}"
    doc["description"] = (
        f"Sensitivity analysis of the p53-knockout MicroC model, one factor at a time. This "
        f"file sweeps the {axis['title']} over {axis['levels']} (Planner tabs "
        f"{', '.join(names)}; {baseline_txt}). The canvas holds the "
        f"microc_p53_experiment.json '{BAKED_TAB}' arm baked in: p53 clamped OFF, cell height "
        f"15 um, consumption scales O2 11 / lactate 11 / glucose 7, gene propagation "
        f"{baked_propagation} steps, ATP gate 0.5 with cell cycle 2. Every arm covers "
        f"{GENE_STEPS_TOTAL} single-gene updates per cell (scheduler steps = "
        f"{GENE_STEPS_TOTAL} / propagation steps, {canvas_steps} here) and draws a quadrant "
        f"plot plus a checkpoint every {PLOT_EVERY_GENE_STEPS} gene updates (Plot Interval and "
        f"Checkpoint Interval nodes on the iteration_plots canvas), so arms with different "
        f"propagation step counts share the same gene_steps axis and the same number of "
        f"snapshots. symbiosis_summary is replaced by sensitivity_summary "
        f"(record_sensitivity_metrics); fate_summary is kept. Generated by "
        f"sensitivity_analysis/build_sensitivity_workflows.py -- regenerate, do not hand-edit."
        f"\n\nBaseline description follows.\n\n" + baseline.get("description", ""))
    doc["metadata"]["author"] = (
        f"build_sensitivity_workflows.py from microc_p53_experiment.json ({BAKED_TAB} arm)")
    doc["metadata"]["workflow_source_path"] = f"{SOURCE_DIR}/{axis['file']}.json"

    param_ids = _param_ids(doc)
    tab_list = []
    for level, name in zip(axis["levels"], names):
        overrides = {} if level == axis["baseline"] else axis["overrides"](level, doc)
        if steps is not None:
            overrides.pop(STEPS_NODE, None)   # smoke copies keep the forced short run
        unknown = set(overrides) - param_ids
        if unknown:
            raise SystemExit(f"override targets unknown parameter nodes: {sorted(unknown)}")
        tab_list.append({
            "id": f"sa-tab-{axis['file'][len('p53_sa_'):]}-{label(level)}",
            "name": name,
            "enabled": True,
            "parameterOverrides": overrides,
        })
    doc["metadata"]["gui"]["planner"] = {
        "version": 2,
        "replication": {
            "replicates": 10,
            "seedMode": "generated",
            "masterSeed": "42",
            "pairing": "shared",
            "pairingGroup": "default",
            "seeds": [],
        },
        "tabs": tab_list,
    }

    structure = {k: v for k, v in doc.items() if k != "description"}
    if "symbiosis_summary" in json.dumps(structure):
        raise SystemExit("a 'symbiosis_summary' reference survived the replacement")
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--baseline", type=Path, default=BASELINE)
    ap.add_argument("--out", type=Path, default=HERE, help="output folder (default: this folder)")
    ap.add_argument("--steps", type=int, default=None,
                    help="override the scheduler step count (smoke copies only)")
    ap.add_argument("--prefix", default="", help="file-name prefix for throwaway copies")
    args = ap.parse_args(argv)

    if (args.steps is not None or args.prefix) and args.out.resolve() == HERE:
        raise SystemExit("--steps/--prefix produce throwaway copies: pass --out elsewhere")

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)

    seen = set()
    for axis in AXES:
        doc = derive(baseline, axis, axis["file"], steps=args.steps)
        names = [t["name"] for t in doc["metadata"]["gui"]["planner"]["tabs"]]
        clash = seen.intersection(names)
        if clash:
            raise SystemExit(f"tab names must be unique across the suite: {sorted(clash)}")
        seen.update(names)
        path = args.out / f"{args.prefix}{axis['file']}.json"
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path}  tabs: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
