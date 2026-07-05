"""Wrap the Corral cells in an abm_population so the model runs on the ABM motor.

``place_cells_from_csv`` fills the legacy CellPopulation (``context['population']``)
and tags each cell with its ``_kind``. This node builds an ``abm.Population`` that
shares that SAME CellPopulation, so the per-kind asks (``for_each {kind: ...}``)
bind ``env.agent``/``env.cell`` per cell while the gene-network nodes keep reading
``context['population']`` unchanged.

Unlike MicroC (see ``build_tumor_cell_abm_population``), this model has no
metabolism step that overwrites ``metabolic_state`` every tick, so the ``_kind`` /
``fate`` tags survive the whole run — which is exactly what a multi-kind model
needs for ``agents_of_kind`` to work.
"""
from src.abm import Domain, LatticeWorld, Population
from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    requires=["population"],
    display_name="Build T-cell ABM Population",
    description="Wrap the Corral cells in an abm_population (sharing the same cells) so "
                "per-kind asks and gene-network steps run on the ABM motor.",
    category="INITIALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=["domain", "abm_population"],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def build_tcell_abm_population(env: BiologicalContext, **kwargs) -> bool:
    ctx = env.raw_context
    config = ctx["config"]
    legacy = ctx["population"]

    # Cells live on the bio-grid: nx = size_um / cell_height_um, tile_size =
    # cell_height, so agent.position == cell.state.position (no re-scaling).
    size_um = config.domain.size_x.micrometers
    cell_um = config.domain.cell_height.micrometers
    world = LatticeWorld(size_um, size_um, cell_um, "bounded", "bounded")
    domain = Domain(world)

    pop = Population(world, config=config, context=ctx,
                     seed=int(ctx.get("seed", 0) or 0))
    pop.cellpop = legacy          # share the SAME cells (identity => same order)
    pop._rebind()                 # re-point world occupancy at the live grid
    pop.domain = domain

    ctx["domain"] = domain
    ctx["abm_population"] = pop
    print(f"[TCELL_CORRAL] Wrapped {len(legacy.state.cells)} cells on a "
          f"{world.nx}x{world.ny} bio-grid; kinds={pop.count_by_kind()}")
    return True
