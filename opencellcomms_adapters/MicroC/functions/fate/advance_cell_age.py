"""
Advance each cell's age by one scheduler step.

WHAT AGE MEANS HERE
    Age counts SCHEDULER STEPS, not hours. ``update_cell_division`` resets age to
    0 on the parent and creates the daughter at 0, so ``cell.age`` is the number
    of steps since the cell last divided (or since it was seeded from the
    checkpoint). That is exactly NetLogo's ``ticks - my-cell-age``.

    The engine's ``CellHandle.set_age`` names its argument ``hours``; it applies
    no conversion, it just writes the number. This node writes steps.

WHY IT IS A NODE
    Nothing else in the MicroC pipeline advances age -- without this node on the
    canvas ``cell.age`` stays 0.0 for the whole run and any cell-cycle gate is
    silently inert. Place it FIRST in the per-agent fate behavior, so a cell born
    at step T first satisfies ``age > cell_cycle_time`` at step T + cycle + 1.

    Its partner is ``mark_proliferating_cells_gated``, which consumes the age.
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    requires=['population'],
    display_name="Advance Cell Age",
    description="Increment each cell's age by one scheduler step. Division resets "
                "age to 0 on both parent and daughter, so age is the number of steps "
                "since the cell last divided.",
    category="INTRACELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def advance_cell_age(env: BiologicalContext, **kwargs) -> None:
    # Per-cell when the executor's per-cell ask bound a cell (env.cell); else
    # fall back to the whole-population loop.
    targets = [env.cell] if env.cell is not None else list(env.cells)

    for cell in targets:
        cell.set_age(cell.age + 1.0)
