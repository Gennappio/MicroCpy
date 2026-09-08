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
The 'necrosis_params' dictionary holds the environmental thresholds:

   {
       "oxygen_threshold": 0.022,
       "glucose_threshold": 0.23,
       "require_both": true
   }

The gene gate is a separate, canvas-visible BOOL slot on this node
(`require_gene`), never a key inside the dict (R1.6: a mode switch buried
in a dict entry is hidden biology). A dict that still carries
"require_gene" is rejected with a message pointing to the slot.

NETLOGO REFERENCE (microC_Metabolic_Symbiosis.nlogo3d): necrosis is
double-gated. The gene network's Necrosis fate node firing calls
-FATE-NECROSIS-20, which then applies the environmental gate
(O2 < the-necrosis-threshold AND Glucose < the-necrosis-threshold-g,
slider defaults 0.011 / 3.9) before committing my-fate = "Necrosis".
Set require_gene = true to reproduce that double gate; false (default)
keeps the environment-only behavior.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    requires=['population', 'simulator'],
    display_name="Mark Necrotic Cells",
    description="Mark cells as necrotic when local Oxygen and Glucose fall below "
                "the necrosis thresholds. The require_gene slot switches on the "
                "NetLogo double gate: the gene network's Necrosis node must be ON "
                "before the environmental check is applied.",
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "necrosis_params",
            "type": "DICT",
            "description": "Environmental necrosis thresholds: oxygen_threshold, "
                           "glucose_threshold (mM) and require_both (AND vs OR).",
            "default": {
                "oxygen_threshold": 0.022,
                "glucose_threshold": 0.23,
                "require_both": True
            }
        },
        {
            "name": "require_gene",
            "type": "BOOL",
            "description": "Gene gate (NetLogo double gate). ON: a cell is checked "
                           "against the thresholds only while its Necrosis gene node "
                           "is ON, so death is delayed by gene-network propagation. "
                           "OFF: environment-only, every cell below the thresholds "
                           "dies the step it crosses them.",
            "default": False
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_necrotic_cells(
    env: BiologicalContext,
    necrosis_params: Dict[str, Any] = None,
    require_gene: bool = False,
    **kwargs
) -> None:
    params = necrosis_params or {}
    if 'require_gene' in params:
        raise ValueError(
            "mark_necrotic_cells: 'require_gene' inside necrosis_params is no "
            "longer read (R1.6: a mode switch must be visible on the canvas). "
            "Remove it from the Necrosis Parameters dict and set the node's own "
            "'require_gene' parameter slot instead.")
    oxygen_threshold = params.get('oxygen_threshold', 0.022)
    glucose_threshold = params.get('glucose_threshold', 0.23)
    require_both = params.get('require_both', True)
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
        gate_str = ("gene gate ON: Necrosis node must be ON, then "
                    if require_gene else "environment-only: ")
        if newly_necrotic > 0:
            print(f"[NECROSIS] Marked {newly_necrotic} cells as necrotic "
                  f"({gate_str}O2 < {oxygen_threshold} {condition_str} "
                  f"Glc < {glucose_threshold})")
        env.results.record_change('necrosis', {
            'newly_marked': newly_necrotic,
            'already_necrotic': already_necrotic,
            'params': params,
            'require_gene': require_gene,
        })
