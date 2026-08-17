"""
Mark cells as necrotic based on user-defined environmental conditions.

Necrotic cells remain in the population but do nothing (no metabolism,
no gene network updates, no phenotype changes). Necrosis is a terminal
fate: the other markers skip necrotic cells. Pair with
remove_necrotic_cells to take them out of the population after a
configurable number of steps.

The thresholds are published to results['necrosis_thresholds'] so the
plotting nodes can draw them as isolines on the substance heatmaps.

USAGE:
The 'necrosis_params' dictionary can contain any parameters the user needs.
Example configuration:

   {
       "oxygen_threshold": 0.022,
       "glucose_threshold": 0.23,
       "require_both": true,
       "require_gene": true
   }

NETLOGO REFERENCE (microC_Metabolic_Symbiosis.nlogo3d): necrosis is
double-gated. The gene network's Necrosis fate node firing calls
-FATE-NECROSIS-20, which then applies the environmental gate
(O2 < the-necrosis-threshold AND Glucose < the-necrosis-threshold-g,
slider defaults 0.011 / 3.9) before committing my-fate = "Necrosis".
Set "require_gene": true to reproduce that double gate; false (default)
keeps the environment-only behavior.
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
    require_gene = params.get('require_gene', False)
    if isinstance(require_gene, str):
        require_gene = require_gene.strip().lower() in ('true', '1', 'yes')

    # Publish the thresholds so the plotting nodes can draw necrosis isolines
    # on the Oxygen/Glucose heatmaps. Idempotent, so safe under a per-agent ask.
    env.results.store('necrosis_thresholds', {
        'Oxygen': oxygen_threshold,
        'Glucose': glucose_threshold,
    })

    # Per-cell when bound (env.cell); else the whole-population loop.
    targets = [env.cell] if env.cell is not None else list(env.cells)

    newly_necrotic = 0
    already_necrotic = 0

    for cell in targets:
        if cell.is_necrotic:
            already_necrotic += 1
            continue

        # NetLogo double gate: the Necrosis fate node must fire before the
        # environmental check is even applied.
        if require_gene:
            gene = cell.gene('Necrosis')
            if not (gene and gene.is_on()):
                continue

        oxygen_below = env.concentration('Oxygen', cell) < oxygen_threshold
        glucose_below = env.concentration('Glucose', cell) < glucose_threshold

        should_mark = (oxygen_below and glucose_below) if require_both else (oxygen_below or glucose_below)
        if should_mark:
            cell.mark_necrotic()
            newly_necrotic += 1

    if env.cell is None:
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
