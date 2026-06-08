"""
Mark apoptotic cells based on gene network Apoptosis output.

This is the FIRST marking function in the fate cycle. It resets every cell
to Quiescent (clearing stale phenotypes from the previous iteration), then
marks cells whose Apoptosis gene is ON.

Apoptotic cells are marked but NOT removed here. Use remove_apoptotic_cells
to actually remove marked cells from the population.
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext, Phenotype


@register_function(
    requires=['population'],
    display_name="Mark Apoptotic Cells",
    description="Mark cells with Apoptosis gene ON (sets phenotype to 'Apoptosis')",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_apoptotic_cells(env: BiologicalContext, **kwargs) -> None:
    # Reset every cell to Quiescent so stale phenotypes from the previous
    # iteration do not carry over. Later marking functions overwrite this.
    for cell in env.cells:
        if not cell.is_quiescent:
            cell.mark_quiescent()

    marked_count = 0
    for cell in env.cells:
        if cell.gene_states.get(Phenotype.APOPTOSIS.value, False):
            cell.mark_apoptotic()
            marked_count += 1

    if marked_count > 0:
        print(f"[APOPTOSIS] Marked {marked_count} cells as apoptotic")

    env.results.record_change('apoptosis', {
        'marked': marked_count,
        'total_cells': len(env.cells),
    })
