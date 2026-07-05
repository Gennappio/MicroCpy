"""Report dendritic-cell migration progress and T0 contact each step.

Diagnostic world behaviour: for every dendritic cell, the Chebyshev distance to
the nearest T0 cell; reports the mean/min across DCs and how many DCs are in
contact (distance <= 1). Over a run the mean distance should fall and contacts
rise as DCs climb the CCL21 gradient into the T0 cluster — the observable proof
of ``chemotax_ccl21``.
"""
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


def _cheb(a, b) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


@register_function(
    display_name="Report DC Progress",
    description="Mean/min dendritic-cell distance to the nearest T0 and the number of "
                "DCs in contact, recorded each step.",
    category="FINALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["abm_population"],
)
def report_dc_progress(env: BiologicalContext, **kwargs) -> bool:
    pop = env.raw_context.get("abm_population")
    if pop is None:
        return True
    dcs = pop.agents_of_kind("dendritic_cell")
    tcells = pop.agents_of_kind("tcell")
    if not dcs or not tcells:
        return True

    tpos = [t.position for t in tcells]
    dists = [min(_cheb(d.position, tp) for tp in tpos) for d in dcs]
    in_contact = sum(1 for x in dists if x <= 1)
    mean_d = sum(dists) / len(dists)
    env.record("dc_mean_dist", mean_d)
    env.record("dc_contacts", float(in_contact))
    print(f"[DC] {len(dcs)} DCs | dist-to-nearest-T0 mean={mean_d:.1f} min={min(dists)} "
          f"| in contact: {in_contact}/{len(dcs)}")
    return True
