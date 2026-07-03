"""Advance each T0 cell's MaBoSS network by one intracellular time step.

Uses the engine's continuous-time stochastic mode
(``BooleanNetwork.step_maboss``), so per-node transition rates -- including any
FOXP3_2 override applied at build time -- govern the dynamics. This is the piece
the discrete Boolean modes cannot do: a rate perturbation is meaningful here.

Runs per-agent when the executor's per-cell ask binds ``env.cell``; otherwise it
advances every cell's network. Each cell's trajectory is independent, so the two
forms produce equivalent statistics.
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Step T-cell Networks (MaBoSS)",
    description="Advance each T0 cell's MaBoSS network by intracellular_dt of continuous "
                "time using the stochastic CTMC mode.",
    category="INTRACELLULAR",
    parameters=[
        {"name": "intracellular_dt", "type": "FLOAT",
         "description": "MaBoSS time advanced per tick (the PhysiCell config uses 6)",
         "default": 6.0, "min_value": 0.0},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["gene_networks", "population"],
)
def step_tcell_network(
    env: BiologicalContext,
    intracellular_dt: float = 6.0,
    **kwargs,
) -> bool:
    cell_source = [env.cell] if env.cell is not None else env.cells

    stepped = 0
    for cell in cell_source:
        gn = env.gene_network(cell)
        if gn is None:
            continue
        # Global RNG: the executor seeds it once per run for reproducibility.
        gn.step_maboss(intracellular_dt)
        cell.set_gene_state_snapshot(gn.get_all_states())
        stepped += 1

    return True
