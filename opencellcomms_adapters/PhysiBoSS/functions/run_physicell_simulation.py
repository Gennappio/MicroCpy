"""Composable runtime node — runs PhysiCell as one step in a larger workflow.

Reads the spec accumulated by prior ``define_substrate`` /
``define_cell_type`` / ``define_hill_rule`` nodes from
``context['physicell_spec']``, plus its own DICT parameters for the
domain / overall-timing / save / options / parallel / user_parameters
blocks. Calls
``opencellcomms.workflow.backends.physicell_backend.run_with_spec`` —
that's the same codegen + make + spawn + tail pipeline the kernel-dispatch
path uses.

Writes results to ``context['physicell']`` so downstream nodes (plotting,
analysis, coupling) can find:

- ``project_dir`` — the generated PhysiCell project tree
- ``binary_path`` — the built ``./<name>_project`` executable
- ``events_jsonl`` — the JSON-Lines event stream
- ``exit_code`` — process exit code (0 on success)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from src.workflow.decorators import register_function

_DEFAULT_DOMAIN = {
    "x_min": -150.0, "x_max": 150.0,
    "y_min": -150.0, "y_max": 150.0,
    "z_min": -10.0, "z_max": 10.0,
    "dx": 20.0, "dy": 20.0, "dz": 20.0,
    "use_2D": True,
}
_DEFAULT_OVERALL = {
    "max_time": 60.0,
    "dt_diffusion": 0.01,
    "dt_mechanics": 0.1,
    "dt_phenotype": 6.0,
}
_DEFAULT_SAVE = {
    "folder": "output",
    "full_data_interval": 30.0,
    "svg_interval": 30.0,
    "svg_enabled": False,
}
_DEFAULT_OPTIONS = {"random_seed": 0, "virtual_wall_at_domain_edge": True}
_DEFAULT_PARALLEL = {"omp_num_threads": 2}
_DEFAULT_USER_PARAMETERS = {"number_of_cells": 5}


@register_function(
    typed_env_exempt=True,
    display_name="Run PhysiCell Simulation",
    description=(
        "Codegen → make → spawn → tail. Reads substrates / cell types / "
        "Hill rules from context['physicell_spec'] (populated by upstream "
        "define_* nodes), uses its own DICT params for the domain / "
        "overall / save / options / parallel / user_parameters blocks, "
        "builds a PhysiCell project against unmodified PhysiBoSS-master, "
        "and runs the native binary. Writes context['physicell']."
    ),
    category="INITIALIZATION",
    parameters=[
        {
            "name": "domain",
            "type": "DICT",
            "description": "Spatial domain. Keys: x_min/x_max/y_min/y_max/z_min/z_max, dx/dy/dz, use_2D.",
            "default": _DEFAULT_DOMAIN,
        },
        {
            "name": "overall",
            "type": "DICT",
            "description": "Timing. Keys: max_time, dt_diffusion, dt_mechanics, dt_phenotype (minutes).",
            "default": _DEFAULT_OVERALL,
        },
        {
            "name": "save",
            "type": "DICT",
            "description": "Save cadence. Keys: folder, full_data_interval, svg_interval, svg_enabled.",
            "default": _DEFAULT_SAVE,
        },
        {
            "name": "options",
            "type": "DICT",
            "description": "Misc. Keys: random_seed, virtual_wall_at_domain_edge.",
            "default": _DEFAULT_OPTIONS,
        },
        {
            "name": "parallel",
            "type": "DICT",
            "description": "OpenMP. Keys: omp_num_threads.",
            "default": _DEFAULT_PARALLEL,
        },
        {
            "name": "user_parameters",
            "type": "DICT",
            "description": "Exposed as <user_parameters> in the generated XML. Keys: number_of_cells (used by setup_tissue to place initial cells), random_seed.",
            "default": _DEFAULT_USER_PARAMETERS,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics", "physicell"],
)
def run_physicell_simulation(
    context: Dict[str, Any] = None,
    domain: Dict[str, Any] = None,
    overall: Dict[str, Any] = None,
    save: Dict[str, Any] = None,
    options: Dict[str, Any] = None,
    parallel: Dict[str, Any] = None,
    user_parameters: Dict[str, Any] = None,
    **kwargs,
) -> bool:
    if context is None:
        print("[ERROR] [run_physicell_simulation] no context")
        return False

    accumulated = context.get("physicell_spec") or {}
    substrates = accumulated.get("substrates") or []
    cell_types = accumulated.get("cell_types") or []
    hill_rules = accumulated.get("hill_rules") or []

    if not substrates:
        print("[ERROR] [run_physicell_simulation] context['physicell_spec']"
              " has no substrates. Add at least one define_substrate node"
              " upstream of this one.")
        return False
    if not cell_types:
        print("[ERROR] [run_physicell_simulation] context['physicell_spec']"
              " has no cell types. Add at least one define_cell_type node"
              " upstream of this one.")
        return False

    # A set_physicell_config node upstream writes config groups into the spec;
    # those win over this node's own params, which win over the defaults.
    def _group(name: str, param_value, default):
        return dict(accumulated.get(name) or param_value or default)

    spec = {
        "domain": _group("domain", domain, _DEFAULT_DOMAIN),
        "overall": _group("overall", overall, _DEFAULT_OVERALL),
        "save": _group("save", save, _DEFAULT_SAVE),
        "options": _group("options", options, _DEFAULT_OPTIONS),
        "parallel": _group("parallel", parallel, _DEFAULT_PARALLEL),
        "user_parameters": _group("user_parameters", user_parameters, _DEFAULT_USER_PARAMETERS),
        "substrates": substrates,
        "cell_types": cell_types,
        "hill_rules": hill_rules,
    }
    custom_modules_source = accumulated.get("custom_modules_source")
    if custom_modules_source:
        spec["custom_modules_source"] = custom_modules_source
    custom_code = accumulated.get("custom_code")
    if custom_code:
        spec["custom_code"] = custom_code

    from opencellcomms_adapters.PhysiBoSS.backend import physicell_backend

    name = context.get("workflow_name") or "physicell_workflow"
    output_dir = Path(
        context.get("output_dir")
        or context.get("results_dir")
        or f"./results/physicell_{physicell_backend._sanitize_name(name)}"
    )

    try:
        results = physicell_backend.run_with_spec(
            spec=spec, output_dir=output_dir, name=name,
        )
    except physicell_backend.PhysiCellBackendError as e:
        print(f"[ERROR] [run_physicell_simulation] {e}")
        return False

    context["physicell"] = results
    return True
