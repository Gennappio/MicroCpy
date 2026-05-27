"""
Mark cells in Growth_Arrest state based on gene network output.

Marks cells as 'Growth_Arrest' when the Growth_Arrest gene is ON, and tracks
how long each cell has been in that state via a per-cell counter. Cells in
Growth_Arrest are effectively idle (no metabolism, no gene updates). When
the counter exceeds max_growth_arrest_steps the cell stays arrested
(permanent arrest); the counter resets when the gene goes OFF.

The counters dict is kept in `env.raw_context['growth_arrest_counters']`
because it is per-cell scratch state, not a biology operation.
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext, Phenotype


@register_function(
    display_name="Mark Growth Arrest Cells",
    description="Track and manage cells in Growth_Arrest state with time limit",
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "max_growth_arrest_steps",
            "type": "INT",
            "description": "Maximum number of steps a cell can remain in Growth_Arrest",
            "default": 100,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_growth_arrest_cells(
    env: BiologicalContext,
    max_growth_arrest_steps: int = 100,
    **kwargs
) -> None:
    counters = env.raw_context.setdefault('growth_arrest_counters', {})

    cells_in_arrest = 0
    cells_expired = 0
    cells_exited = 0
    cells_newly_marked = 0

    for cell in env.cells:
        if cell.gene_states.get(Phenotype.GROWTH_ARREST.value, False):
            if not cell.is_growth_arrested:
                cell.mark_growth_arrested()
                cells_newly_marked += 1

            counters[cell.id] = counters.get(cell.id, 0) + 1
            cells_in_arrest += 1

            if counters[cell.id] >= max_growth_arrest_steps:
                cells_expired += 1
                # Cell remains arrested (permanent). Could transition here.
        else:
            if cell.id in counters:
                del counters[cell.id]
                cells_exited += 1

    iteration_counter = env.raw_context.get('iteration_counter', 0) + 1
    env.raw_context['iteration_counter'] = iteration_counter

    if iteration_counter % 100 == 0:
        print(f"[PROGRESS] Iteration {iteration_counter}: "
              f"{len(env.cells)} cells, {cells_in_arrest} in arrest")
    if cells_exited > 0:
        print(f"[GROWTH_ARREST] Exited: {cells_exited}, In arrest: {cells_in_arrest}")

    env.results.record_change('growth_arrest', {
        'cells_in_arrest': cells_in_arrest,
        'newly_marked': cells_newly_marked,
        'cells_expired': cells_expired,
        'cells_exited': cells_exited,
        'max_steps': max_growth_arrest_steps,
        'total_tracked': len(counters),
    })
