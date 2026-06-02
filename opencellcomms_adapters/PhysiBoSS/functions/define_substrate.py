"""Declare a PhysiCell substrate; accumulates into context['physicell_spec'].

When this node runs, it appends its `substrate` DICT to
``context['physicell_spec']['substrates']``. A downstream
``run_physicell_simulation`` node reads that list and emits the
``<microenvironment_setup>`` block of the generated XML.
"""
from __future__ import annotations

from typing import Any, Dict

from src.workflow.decorators import register_function


def _ensure_spec(context: Dict[str, Any]) -> Dict[str, Any]:
    spec = context.setdefault("physicell_spec", {})
    spec.setdefault("substrates", [])
    spec.setdefault("cell_types", [])
    spec.setdefault("hill_rules", [])
    return spec


@register_function(
    display_name="Define Substrate (PhysiCell)",
    description=(
        "Append a diffusible substrate to the PhysiCell spec being assembled "
        "in context['physicell_spec']. Consumed downstream by "
        "run_physicell_simulation."
    ),
    category="INITIALIZATION",
    parameters=[
        {
            "name": "substrate",
            "type": "DICT",
            "description": (
                "Keys: name, units, diffusion_coefficient, decay_rate, "
                "initial_condition, dirichlet_enabled, dirichlet_value."
            ),
            "default": {
                "name": "oxygen",
                "units": "mmHg",
                "diffusion_coefficient": 100000.0,
                "decay_rate": 0.1,
                "initial_condition": 38.0,
                "dirichlet_enabled": True,
                "dirichlet_value": 38.0,
            },
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    compatible_kernels=["biophysics", "physicell"],
)
def define_substrate(
    context: Dict[str, Any] = None,
    substrate: Dict[str, Any] = None,
    **kwargs,
) -> bool:
    if context is None or not substrate:
        return False
    spec = _ensure_spec(context)
    spec["substrates"].append(dict(substrate))
    print(f"[PHYSICELL] +substrate {substrate.get('name')!r} "
          f"(total: {len(spec['substrates'])})")
    return True
