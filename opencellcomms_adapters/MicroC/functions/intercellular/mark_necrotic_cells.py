"""
Mark cells as necrotic based on user-defined environmental conditions.

Necrotic cells remain in the population but do nothing (no metabolism,
no gene network updates, no phenotype changes).

USAGE:
The 'necrosis_params' dictionary can contain any parameters the user needs.
Example configuration:

   {
       "oxygen_threshold": 0.022,
       "glucose_threshold": 0.23,
       "require_both": true
   }
"""

from typing import Dict, Any
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    requires=['population', 'simulator'],
    display_name="Mark Necrotic Cells",
    description="Mark cells as necrotic based on user-defined conditions in necrosis_params",
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "necrosis_params",
            "type": "DICT",
            "description": "Dictionary of necrosis parameters (e.g., thresholds, mode, conditions)",
            "default": {
                "oxygen_threshold": 0.022,
                "glucose_threshold": 0.23,
                "require_both": True
            }
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_necrotic_cells(
    env: BiologicalContext,
    necrosis_params: Dict[str, Any] = None,
    **kwargs
) -> None:
    params = necrosis_params or {}
    oxygen_threshold = params.get('oxygen_threshold', 0.022)
    glucose_threshold = params.get('glucose_threshold', 0.23)
    require_both = params.get('require_both', True)

    newly_necrotic = 0
    already_necrotic = 0

    for cell in env.cells:
        if cell.is_necrotic:
            already_necrotic += 1
            continue

        oxygen_below = env.concentration('Oxygen', cell) < oxygen_threshold
        glucose_below = env.concentration('Glucose', cell) < glucose_threshold

        should_mark = (oxygen_below and glucose_below) if require_both else (oxygen_below or glucose_below)
        if should_mark:
            cell.mark_necrotic()
            newly_necrotic += 1

    condition_str = "AND" if require_both else "OR"
    total = len(env.cells)
    print(f"[NECROSIS] Cell count: {total} (marked {newly_necrotic}, already {already_necrotic})")
    if newly_necrotic > 0:
        print(f"[NECROSIS] Marked {newly_necrotic} cells as necrotic "
              f"(O2 < {oxygen_threshold} {condition_str} Glc < {glucose_threshold})")

    env.results.record_change('necrosis', {
        'newly_marked': newly_necrotic,
        'already_necrotic': already_necrotic,
        'params': params,
    })
