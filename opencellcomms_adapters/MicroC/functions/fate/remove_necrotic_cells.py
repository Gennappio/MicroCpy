"""
Remove cells that have been necrotic for a configurable number of steps.

mark_necrotic_cells marks a cell as Necrosis when its local oxygen/glucose
drop below the necrosis thresholds; the cell then sits inert (no metabolism,
no fate changes -- Necrosis is a terminal fate). This node makes it
disappear: each scheduler step it advances a per-cell counter of steps spent
necrotic, and once the counter reaches ``necrosis_removal_delay`` the cell
is removed from the population (its gene network is cleaned up too).

Run it collectively (no for_each), after remove_apoptotic_cells in the
division subworkflow: removal rebuilds the population state, so it must see
the whole population at once.

The counters dict is kept in ``env.raw_context['necrosis_step_counters']``
because it is per-cell scratch state, not a biology operation.
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    requires=['gene_networks', 'population'],
    display_name="Remove Necrotic Cells",
    description="Remove cells that have stayed in Necrosis for necrosis_removal_delay scheduler steps",
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "necrosis_removal_delay",
            "type": "INT",
            "description": "Scheduler steps a cell remains visible as Necrosis before it is removed",
            "default": 10,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def remove_necrotic_cells(
    env: BiologicalContext,
    necrosis_removal_delay: int = 10,
    **kwargs
) -> None:
    # Population object needed for the low-level state rebuild below.
    population = env.cells.raw
    if population is None:
        print("[remove_necrotic_cells] No population in context - skipping")
        return

    delay = int(necrosis_removal_delay)
    counters = env.raw_context.setdefault('necrosis_step_counters', {})

    initial_count = len(env.cells)
    updated_cells = {}
    removed_count = 0
    still_necrotic = 0

    for cell in env.cells:
        if cell.is_necrotic:
            counters[cell.id] = counters.get(cell.id, 0) + 1
            if counters[cell.id] >= delay:
                # Remove the cell (don't add to updated_cells) and clean up
                # its counter and orphaned gene network.
                removed_count += 1
                del counters[cell.id]
                env.remove_gene_network(cell.id)
                continue
            still_necrotic += 1
        elif cell.id in counters:
            # Defensive: a cell that somehow left Necrosis restarts its clock.
            del counters[cell.id]

        updated_cells[cell.id] = cell.raw

    population.state = population.state.with_updates(cells=updated_cells, total_cells=len(updated_cells))

    if removed_count > 0:
        print(f"[REMOVE-NECROSIS] Removed {removed_count} cells necrotic for >= {delay} steps. "
              f"Population: {initial_count} -> {len(updated_cells)}")

    env.results.record_change('remove_necrosis', {
        'removed': removed_count,
        'still_necrotic': still_necrotic,
        'delay_steps': delay,
        'remaining': len(updated_cells),
    })
