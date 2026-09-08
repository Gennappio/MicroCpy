"""
Necrotic disc growing from the centre of the domain, one step at a time.

Stability-search protocol (stabilitysearch.json): instead of letting the
environment decide necrosis, a disc centred on the domain grows every
scheduler step and every living cell inside it is marked Necrosis. Necrotic
cells stay in the population forever (this workflow has no removal node);
the metabolism node gives them an all-zero exchange (fate weight 0) and this
node switches their glycoATP / mitoATP genes OFF so the gene census counts
consuming cells only. Their genes are frozen from then on: the glucose gate
skips necrotic cells.

THE RULE
    radius(iteration) = initial_diameter_um / 2
                        + radius_step_fraction * domain side (size_x) * iteration

    iteration is the 1-based scheduler loop counter. With initial_diameter_um
    = 0 and the default fraction 0.05 the disc has radius 5 % of the side
    after the first step, 10 % after the second, ... With
    radius_step_fraction = 0 the disc is FIXED at initial_diameter_um for the
    whole run (a time series at one necrotic radius). A cell is inside when
    the distance from its centre ((index + 0.5) * Cell Height on every axis)
    to the domain centre is <= radius.

WHY
    Each step removes a ring of consumers, so the per-step seed checkpoints
    form a ladder of populations with a decreasing glucose drawdown. Reloading
    any of them (Read Checkpoint) starts a long run at that fixed necrotic
    radius, which is how the instability threshold is bracketed.

COLLECTIVE
    The disc is one geometry for the whole population, so this node runs once
    per step (collective=True: the executor runs it once even when the owning
    agent kind gives it a per-agent ask).
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    requires=['population'],
    display_name="Necrotic Disc At Centre (fixed or growing)",
    description="A disc centred on the domain, radius = initial_diameter_um/2 "
                "+ radius_step_fraction x domain side x scheduler step (fraction "
                "0 = fixed disc); every living cell inside it is marked "
                "Necrosis, its glycoATP/mitoATP switched OFF, and it is never "
                "removed.",
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "initial_diameter_um",
            "type": "FLOAT",
            "description": "Diameter of the necrotic disc before any growth, in um "
                           "(0 = starts from a point).",
            "default": 0.0,
            "min_value": 0.0,
        },
        {
            "name": "radius_step_fraction",
            "type": "FLOAT",
            "description": "Disc radius growth per scheduler step, as a fraction "
                           "of the domain side (0.05 = 5 % of the side per step; "
                           "0 = the disc stays at initial_diameter_um).",
            "default": 0.05,
            "min_value": 0.0,
            "max_value": 1.0,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    collective=True,
    compatible_kernels=["biophysics"],
)
def mark_necrotic_growing_circle(
    env: BiologicalContext,
    initial_diameter_um: float = 0.0,
    radius_step_fraction: float = 0.05,
    **kwargs
) -> bool:
    initial_diameter_um = float(initial_diameter_um)
    radius_step_fraction = float(radius_step_fraction)
    # Scheduler loop counter (1-based). env.step is the engine clock, which the
    # workflow scheduler does not advance — same convention as the reporters.
    iteration = int(env.raw_context.get('loop_iteration', 0) or 0)

    dom = env.config.domain
    sides = [float(dom.size_x.micrometers), float(dom.size_y.micrometers)]
    if int(getattr(dom, 'dimensions', 2) or 2) == 3:
        sides.append(float(dom.size_z.micrometers))
    cell_um = float(dom.cell_height.micrometers)
    centre = [s / 2.0 for s in sides]
    radius_um = initial_diameter_um / 2.0 + radius_step_fraction * sides[0] * iteration

    newly = 0
    already = 0
    for cell in env.cells:
        if cell.is_necrotic:
            already += 1
            continue
        d2 = 0.0
        for axis, index in enumerate(cell.position[:len(sides)]):
            d2 += ((float(index) + 0.5) * cell_um - centre[axis]) ** 2
        if d2 <= radius_um * radius_um:
            cell.mark_necrotic()
            genes = cell.gene_states
            genes['glycoATP'] = False
            genes['mitoATP'] = False
            cell.set_gene_state_snapshot(genes)
            newly += 1

    total = len(env.cells)
    env.results.store('necrosis_disc', {
        'iteration': iteration,
        'radius_um': radius_um,
        'initial_diameter_um': initial_diameter_um,
        'radius_step_fraction': radius_step_fraction,
        'newly_necrotic': newly,
        'necrotic_total': already + newly,
        'living': total - already - newly,
    })
    print(f"[NECROSIS-DISC] iteration {iteration}: radius = {initial_diameter_um:g}/2 + "
          f"{radius_step_fraction} x {sides[0]:g} um x {iteration} = {radius_um:g} um; "
          f"marked {newly} cells "
          f"(necrotic {already + newly}/{total}, living {total - already - newly})")
    return True
