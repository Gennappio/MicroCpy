"""Single config node — sets the PhysiCell run configuration as grouped dicts.

This is the one place a scientist sets the simulation's domain, timing, save
cadence, options, parallelism, and user parameters. Each group is a DICT
parameter, so it renders as an editable table in the GUI and can be driven by
a plugged-in dictParameterNode. The node writes its groups into
``context['physicell_spec']`` (the same accumulator the define_* nodes use);
both ``run_physicell_simulation`` and the kernel-dispatch backend read them
from there.

Replaces the invisible ``kernel_config['physicell']`` JSON block: putting the
config on the canvas makes the workflow self-describing and portable.
"""
from __future__ import annotations

from typing import Any, Dict

from src.workflow.decorators import register_function

# The six config groups this node owns. Keep in sync with
# spec_from_workflow.CONFIG_GROUPS and scaffold._DEFAULT_*.
_CONFIG_GROUPS = (
    "domain", "overall", "save", "options", "parallel", "user_parameters",
)

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
_DEFAULT_PARALLEL = {"omp_num_threads": 4}
_DEFAULT_USER_PARAMETERS = {"number_of_cells": 5}


def _ensure_spec(context: Dict[str, Any]) -> Dict[str, Any]:
    spec = context.setdefault("physicell_spec", {})
    spec.setdefault("substrates", [])
    spec.setdefault("cell_types", [])
    spec.setdefault("hill_rules", [])
    return spec


@register_function(
    typed_env_exempt=True,
    display_name="Set PhysiCell Config",
    description=(
        "Set the whole PhysiCell run configuration in one node. Each group "
        "(domain, overall timing, save cadence, options, parallel, user "
        "parameters) is a DICT you can edit as a table or drive with a "
        "dictParameterNode. Writes the groups into context['physicell_spec']; "
        "run_physicell_simulation and the kernel-dispatch backend read them "
        "from there. Omitted groups fall back to scaffold defaults."
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
            "description": "Timing (minutes). Keys: max_time, dt_diffusion, dt_mechanics, dt_phenotype.",
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
            "description": "Exposed as <user_parameters> in the generated XML. Keys: number_of_cells, random_seed.",
            "default": _DEFAULT_USER_PARAMETERS,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics", "physicell"],
)
def set_physicell_config(
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
        print("[ERROR] [set_physicell_config] no context")
        return False

    spec = _ensure_spec(context)
    groups = {
        "domain": domain,
        "overall": overall,
        "save": save,
        "options": options,
        "parallel": parallel,
        "user_parameters": user_parameters,
    }
    written = []
    for name, value in groups.items():
        if value:
            spec[name] = dict(value)
            written.append(name)
    print(f"[PHYSICELL] config groups set: {', '.join(written) or '(none)'}")
    return True


__all__ = ["set_physicell_config"]
