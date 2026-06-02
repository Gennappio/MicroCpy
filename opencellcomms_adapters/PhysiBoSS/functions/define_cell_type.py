"""Declare a PhysiCell cell type; accumulates into context['physicell_spec']."""
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
    display_name="Define Cell Type (PhysiCell)",
    description=(
        "Append a cell type to context['physicell_spec']. Phase 3 keeps the "
        "definition minimal — only `name` and optional `id`; the generated "
        "<cell_definition> uses the upstream template's default phenotype "
        "values. Per-cell-type phenotype overrides are Phase 5."
    ),
    category="INITIALIZATION",
    parameters=[
        {
            "name": "cell_type",
            "type": "DICT",
            "description": (
                "Keys: name (str, required), id (int, optional — defaults to "
                "appearance order in the workflow)."
            ),
            "default": {"name": "tumor"},
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    compatible_kernels=["biophysics", "physicell"],
)
def define_cell_type(
    context: Dict[str, Any] = None,
    cell_type: Dict[str, Any] = None,
    **kwargs,
) -> bool:
    if context is None or not cell_type:
        return False
    spec = _ensure_spec(context)
    payload = dict(cell_type)
    payload.setdefault("id", len(spec["cell_types"]))
    spec["cell_types"].append(payload)
    print(f"[PHYSICELL] +cell_type {payload.get('name')!r} "
          f"(total: {len(spec['cell_types'])})")
    return True
