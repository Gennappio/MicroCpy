"""
Mark cells as Proliferation based on gene network Proliferation output.

This is the LAST marking function in the fate cycle and acts as the final arbiter.
Cells whose Proliferation gene is ON become Proliferation (overwriting any
previous phenotype). Cells already marked Apoptosis or Growth_Arrest by an
earlier marker in this cycle keep that phenotype. Everything else resets to
Quiescent.

The Quiescent reset is critical: without it, stale phenotypes from previous
iterations persist and cause cells to keep dividing/dying after the gene
network no longer supports that fate.
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext, Phenotype


_PROTECTED_FATES = {Phenotype.APOPTOSIS.value, Phenotype.GROWTH_ARREST.value}


@register_function(
    requires=['population'],
    display_name="Mark Proliferating Cells",
    description="Mark cells as proliferating based on gene network Proliferation output",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_proliferating_cells(env: BiologicalContext, **kwargs) -> None:
    # Per-cell when the executor's per-cell ask bound a cell (env.cell); else
    # fall back to the whole-population loop. The aggregate summary/record_change
    # only make sense for the whole-population call.
    targets = [env.cell] if env.cell is not None else list(env.cells)

    proliferating = 0
    overwritten = 0
    unchanged = 0
    quiescent = 0

    for cell in targets:
        old_phenotype = cell.phenotype
        if cell.gene_states.get(Phenotype.PROLIFERATION.value, False):
            if not cell.is_proliferating:
                cell.mark_proliferating()
                if old_phenotype in _PROTECTED_FATES:
                    overwritten += 1
            proliferating += 1
        else:
            if cell.phenotype not in _PROTECTED_FATES:
                if not cell.is_quiescent:
                    cell.mark_quiescent()
                quiescent += 1
            else:
                unchanged += 1

    if env.cell is None:
        if proliferating > 0:
            print(f"[PROLIFERATION] Proliferating: {proliferating}, "
                  f"Quiescent: {quiescent}, Overwritten: {overwritten}")
        env.results.record_change('proliferation', {
            'proliferating': proliferating,
            'quiescent': quiescent,
            'unchanged': unchanged,
            'overwritten': overwritten,
        })
