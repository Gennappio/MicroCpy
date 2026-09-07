#!/usr/bin/env python3
"""Tabulate every sensitivity-suite run under runs/ into one CSV.

Each run folder carries the executed workflow (runs/<label>/workflow.json, with
the Planner overrides baked in) and the reporter's time series
(runs/<label>/sensitivity_summary/timeseries/sensitivity_metrics_over_time.csv).
A run belongs to the suite when its workflow_source_path names a p53_sa_* file.

The suite's shared baseline (the override-free Planner tab) is executed once,
whether the five files run as one batch or as separate jobs. Its rows are
reported on every axis that has an override-free tab, with the same run_id,
and a run is never listed twice for the same axis.

Output: one row per run with the control-variable values read from the executed
workflow, the first-iteration tumour radius / relative size, and every metric of
the last recorded iteration. Sorted by axis, then level.

Usage:
    python collect_sensitivity_results.py                 # runs/ -> runs/sensitivity_summary.csv
    python collect_sensitivity_results.py --runs /path/to/runs --out summary.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
SUITE_PREFIX = "p53_sa_"
REPORTER = "record_sensitivity_metrics"
DEFAULT_CSV = "sensitivity_metrics_over_time.csv"

# column name -> (parameter node id, key inside its "parameters")
CONTROL_NODES = {
    "glucose_conversion_factor": ("diffusion_step-param_glucose_conversion_factor",
                                  "glucose_conversion_factor"),
    "oxygen_conversion_factor": ("diffusion_step-param_oxygen_conversion_factor",
                                 "oxygen_conversion_factor"),
    "domain_size_x_um": ("envinit-Setup_simulation-param_domain_size_x", "size_x"),
    "domain_size_y_um": ("envinit-Setup_simulation-param_domain_size_y", "size_y"),
    "nx": ("envinit-Setup_simulation-param_domain_nx", "nx"),
    "ny": ("envinit-Setup_simulation-param_domain_ny", "ny"),
    "cell_height_um": ("envinit-Setup_simulation-param_domain_cell_height", "cell_height"),
    "propagation_steps": ("gene_update-param_propagation_steps", "propagation_steps"),
    "steps_planned": ("steps_param-__scheduler__", "steps"),
}
GLUCOSE_NODE = "glucose_init-param_substances"
LEVEL_COLUMN = {
    "glucose_consumption": "glucose_conversion_factor",
    "oxygen_consumption": "oxygen_conversion_factor",
    "glucose_boundary": "glucose_boundary_mM",
    "relative_tumor_size": "relative_tumor_size_initial",
    "propagation_steps": "propagation_steps",
}
LEAD_COLUMNS = ["run_dir", "axis", "level", "workflow_source_path",
                "glucose_conversion_factor", "oxygen_conversion_factor",
                "glucose_boundary_mM", "glucose_initial_mM",
                "domain_size_x_um", "domain_size_y_um", "nx", "ny", "cell_height_um",
                "propagation_steps", "steps_planned", "n_iterations",
                "tumor_radius_um_initial", "relative_tumor_size_initial"]


def _param_nodes(doc: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {node["id"]: node for sw in doc.get("subworkflows", {}).values()
            for node in (sw.get("parameters") or []) if node.get("id")}


def _reporter_location(doc: Dict[str, Any]) -> Optional[tuple]:
    for name, sw in doc.get("subworkflows", {}).items():
        for fn in sw.get("functions") or []:
            if fn.get("function_name") == REPORTER and fn.get("enabled", True):
                return name, (fn.get("parameters") or {}).get("csv_filename", DEFAULT_CSV)
    return None


def _read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def collect_run(run_dir: Path, source_override=None) -> Optional[Dict[str, Any]]:
    wf_path = run_dir / "workflow.json"
    if not wf_path.is_file():
        return None
    doc = json.loads(wf_path.read_text(encoding="utf-8"))
    execution_path = run_dir / 'execution.json'
    execution = json.loads(execution_path.read_text()) if execution_path.is_file() else {}
    if execution.get('status') != 'completed' or execution.get('numerical_valid') is not True:
        print(f'[collect] excluding {run_dir}: completion/numerical validity not verified')
        return None
    source = str(source_override or (doc.get("metadata") or {}).get("workflow_source_path") or "")
    stem = Path(source).stem
    if not stem.startswith(SUITE_PREFIX):
        return None

    nodes = _param_nodes(doc)
    replicate = doc.get("metadata", {}).get("replicate", {})
    row: Dict[str, Any] = {"batch_id": replicate.get("batch_id", ""),
                           "run_id": replicate.get("id", ""), "seed": execution.get("seed", ""),
                           "replicate": replicate.get("replicate", ""),
                           "status": execution["status"], "numerical_valid": True,
                           "run_dir": str(run_dir), "axis": stem[len(SUITE_PREFIX):],
                           "workflow_source_path": source}
    for column, (node_id, key) in CONTROL_NODES.items():
        row[column] = (nodes.get(node_id, {}).get("parameters") or {}).get(key, "")
    glucose = nodes.get(GLUCOSE_NODE, {}).get("items") or []
    if glucose:
        sub = json.loads(glucose[0])
        row["glucose_boundary_mM"] = sub.get("boundary_value", "")
        row["glucose_initial_mM"] = sub.get("initial_value", "")

    location = _reporter_location(doc)
    rows: List[Dict[str, str]] = []
    if location is None:
        print(f"[collect] {run_dir.name}: no enabled {REPORTER} node in its workflow")
    else:
        csv_path = run_dir / location[0] / "timeseries" / location[1]
        if csv_path.is_file():
            rows = _read_rows(csv_path)
        if not rows:
            print(f"[collect] {run_dir.name}: no rows in {csv_path}")
    if not rows:
        return None
    if rows:
        first, last = rows[0], rows[-1]
        row["n_iterations"] = last.get("iteration", "")
        row["tumor_radius_um_initial"] = first.get("tumor_radius_um", "")
        row["relative_tumor_size_initial"] = first.get("relative_tumor_size", "")
        row.update({k: v for k, v in last.items() if k != "iteration"})
    row["level"] = row.get(LEVEL_COLUMN.get(row["axis"], ""), "")
    return row


def _baseline_sources(suite_dir: Path) -> Dict[str, tuple]:
    """file name -> (override-free tab id, resolved path) for suite files with a baseline tab."""
    result: Dict[str, tuple] = {}
    for path in sorted(suite_dir.glob(f"{SUITE_PREFIX}*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        tabs = ((doc.get("metadata") or {}).get("gui") or {}).get("planner", {}).get("tabs") or []
        free = [t["id"] for t in tabs if t.get("id") and not t.get("parameterOverrides")]
        if free:
            result[path.name] = (free[0], str(path.resolve()))
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", type=Path, default=REPO_ROOT / "runs")
    ap.add_argument("--suite", type=Path, default=HERE,
                    help="folder of the p53_sa_*.json files (to spread the baseline over axes)")
    ap.add_argument("--out", type=Path, default=None,
                    help="output CSV (default: <runs>/sensitivity_summary.csv)")
    args = ap.parse_args(argv)
    out = args.out or (args.runs / "sensitivity_summary.csv")

    sys.path.insert(0, str(REPO_ROOT / 'opencellcomms_engine'))
    from src.workflow.replication import batch_status, execution_record_path
    baselines = _baseline_sources(args.suite)
    collected = []
    listed = set()   # (run_id, axis): the same run is one observation per axis
    for directory in sorted(args.runs.iterdir()):
        if not directory.is_dir():
            continue
        if execution_record_path(directory).is_file():
            batch = batch_status(directory)
            for run in batch['runs']:
                if run['status'] != 'completed' or run.get('numerical_valid') is not True:
                    print(f"[collect] excluding {run['id']}: {run['status']}")
                    continue
                # Shared baselines appear on every requested axis, with the
                # SAME run ID. They are never extra independent observations.
                specs = [spec for spec in batch['requests']
                         if spec['configuration_id'] == run['configuration_id']]
                sources = {spec.get('source') for spec in specs}
                # The override-free baseline is enabled in one file only; report it
                # on every axis whose baseline it is.
                if any(baselines.get(Path(spec.get('source') or '').name, (None,))[0] == spec.get('tab_id')
                       for spec in specs):
                    sources.update(path for _, path in baselines.values())
                for source in sorted(sources, key=str):
                    key = (run['id'], Path(str(source)).stem)
                    if key in listed:
                        continue
                    row = collect_run(directory / run['attempt_dir'], source)
                    if row:
                        listed.add(key)
                        collected.append(row)
        else:
            row = collect_run(directory)
            if row:
                collected.append(row)
    if not collected:
        print(f"[collect] no {SUITE_PREFIX}* runs under {args.runs}")
        return 1

    def sort_key(r):
        try:
            return (r["axis"], float(r["level"]))
        except (TypeError, ValueError):
            return (r["axis"], float("inf"))
    collected.sort(key=sort_key)

    columns = list(LEAD_COLUMNS)
    for r in collected:
        columns += [k for k in r if k not in columns]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(collected)
    print(f"[collect] {len(collected)} run(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
