"""Declare a CBHG v3.0 Hill rule; accumulates into context['physicell_spec']."""
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
    display_name="Define Hill Rule (PhysiCell)",
    description=(
        "Append a CBHG-grammar Hill rule to context['physicell_spec']. "
        "Validated against the grammar at run_physicell_simulation time."
    ),
    category="INITIALIZATION",
    parameters=[
        {
            "name": "rule",
            "type": "DICT",
            "description": (
                "Keys: cell_type, signal, direction (increases|decreases), "
                "behavior, max_response, half_max, hill_power, use_on_dead "
                "(0|1). max_response is the behavior value at signal "
                "saturation (column 4 of the upstream CSV)."
            ),
            "default": {
                "cell_type": "tumor",
                "signal": "oxygen",
                "direction": "decreases",
                "behavior": "necrosis",
                "max_response": 0.0,
                "half_max": 5.0,
                "hill_power": 8.0,
                "use_on_dead": 0,
            },
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    compatible_kernels=["biophysics", "physicell"],
)
def define_hill_rule(
    context: Dict[str, Any] = None,
    rule: Dict[str, Any] = None,
    **kwargs,
) -> bool:
    if context is None or not rule:
        return False
    spec = _ensure_spec(context)
    spec["hill_rules"].append(dict(rule))
    print(f"[PHYSICELL] +hill_rule {rule.get('cell_type')!r}: "
          f"{rule.get('signal')!r} {rule.get('direction')} "
          f"{rule.get('behavior')!r} (total: {len(spec['hill_rules'])})")
    return True
