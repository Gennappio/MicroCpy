"""Commit a contacted T0 cell to a Treg / Th1 / Th17 fate once it settles.

Reads the live MaBoSS output nodes; when a single fate node has been ON — and the
sole fate ON — for ``stable_steps`` consecutive steps, the cell's ``fate`` field is
set to it. From then on the network is no longer consulted (``step_tcell_network``
skips committed cells) and motility follows the fate (``differentiated_motility``).

The stability window matters: a freshly activated network passes transiently
through fates (often Th1) before settling into its attractor, so committing on the
first fate seen would mis-assign. This is the ABM analogue of PhysiCell's
"transform to <fate>" firing only once the boolean output stabilises.
"""
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext

_FATES = ("Treg", "Th1", "Th17")


@register_function(
    display_name="Commit T-cell Fate",
    description="Set a contacted T0 cell's fate once a single Treg/Th1/Th17 output has been "
                "stably ON for stable_steps consecutive steps.",
    category="INTERCELLULAR",
    parameters=[
        {"name": "stable_steps", "type": "INT",
         "description": "Consecutive steps a single fate must stay ON before committing",
         "default": 3, "min_value": 1},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["gene_networks", "abm_population"],
)
def commit_tcell_fate(env: BiologicalContext, stable_steps: int = 3, **kwargs) -> bool:
    agent = env.agent
    if agent is None or agent.get("fate", "naive") != "naive":
        return True                            # already committed

    gn = env.gene_network(env.cell)
    if gn is None:
        return True

    on = [f for f in _FATES if gn.nodes.get(f) is not None and gn.nodes[f].current_state]
    current = on[0] if len(on) == 1 else None   # only an unambiguous single fate counts

    if current is not None and current == agent.get("_pending_fate"):
        count = int(agent.get("_fate_count", 0)) + 1
        agent.set("_fate_count", count)
        if count >= stable_steps:
            agent.set("fate", current)
    else:
        agent.set("_pending_fate", current)
        agent.set("_fate_count", 1 if current is not None else 0)
    return True
