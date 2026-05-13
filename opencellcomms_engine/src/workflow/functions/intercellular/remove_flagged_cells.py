"""
Remove cells flagged for removal by the PhysiCell death kernel.

Complements ``update_death_physicell``. Kills + compacts any cell whose
``flagged_for_removal`` column is True (CellContainer path) or whose
phenotype is 'removed' (legacy Dict path).
"""

from typing import Any, Dict, Optional

from src.workflow.decorators import register_function
from src.workflow.logging import log


@register_function(
    display_name="Remove Flagged Cells",
    description=(
        "Remove cells whose 'flagged_for_removal' column is True. "
        "Works with the CellContainer SoA layout; pairs with "
        "update_death_physicell."
    ),
    category="INTERCELLULAR",
    parameters=[
        {"name": "compact", "type": "BOOL",
         "description": "Compact the container after killing (reclaim space).",
         "default": True},
        {"name": "verbose", "type": "BOOL",
         "description": "Enable detailed logging.",
         "default": None},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def remove_flagged_cells(
    context: Dict[str, Any],
    compact: bool = True,
    verbose: Optional[bool] = None,
    **kwargs,
) -> bool:
    from src.biology.cell_container import CellContainer

    container = context.get("cell_container")
    if not isinstance(container, CellContainer):
        return True  # legacy path handled by remove_apoptotic_cells

    if "flagged_for_removal" not in container._bool_columns:
        return True

    N = container.count
    flag = container.get_bool("flagged_for_removal")[:N]
    alive = container.alive[:N]
    to_kill = flag & alive
    n_kill = int(to_kill.sum())
    if n_kill == 0:
        return True

    container.kill(to_kill)
    if compact:
        container.compact()

    log(context, f"removed {n_kill} cells (flagged)", prefix="[Rem]", node_verbose=verbose)
    return True
