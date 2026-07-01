"""Wrap MicroC's cells in an abm_population so the model runs on the new ABM motor.

MicroC builds a legacy CellPopulation (``context['population']``) filled from the
CSV. This node — the last step of ``tumor_cell_init``, after the cells exist —
builds an ``abm.Population`` that shares the SAME CellPopulation object, so:

  * ``gene_update`` / ``fate_update`` route through the per-agent ask
    (``executor._run_for_each_entity``) and act per cell (``env.cell`` is bound to
    the agent's underlying cell);
  * the diffusion / division code keeps reading ``context['population']``
    unchanged, because ``abm_population.cellpop`` IS that object;
  * cells stay in the same order, so the seeded shuffle produces the identical
    processing order — results are preserved byte-for-byte (validated against the
    golden reference, ``tools/migration/microc_golden.py``).

See docs/MICROC_MIGRATION_NEXT_STEPS.md (Stage 4).
"""
from src.abm import Domain, LatticeWorld, Population
from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    requires=["population"],
    display_name="Build Tumor Cell ABM Population",
    description="Wrap MicroC's cells in an abm_population (sharing the same cells) so it runs on the ABM motor",
    category="INITIALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=["domain", "abm_population"],
    cloneable=False,
    compatible_kernels=["*"],
)
def build_tumor_cell_abm_population(env: BiologicalContext, **kwargs) -> bool:
    ctx = env.raw_context
    config = ctx["config"]
    legacy = ctx["population"]            # MicroC's filled CellPopulation

    # Cells live on the bio-grid: nx = size_um / cell_height_um (= 75 for MicroC),
    # tile_size = cell_height, so agent.position == cell.state.position.
    size_um = config.domain.size_x.micrometers
    cell_um = config.domain.cell_height.micrometers
    world = LatticeWorld(size_um, size_um, cell_um, "bounded", "bounded")
    domain = Domain(world)

    pop = Population(world, config=config, context=ctx,
                    seed=int(ctx.get("seed", 0) or 0))
    pop.cellpop = legacy                  # share the SAME cells (identity => same order)
    pop._rebind()                         # re-point world occupancy at the live grid
    pop.domain = domain

    # NOTE: we do NOT tag cells with metabolic_state['_kind']. MicroC's metabolism
    # step REPLACES metabolic_state every diffusion tick (run_diffusion_solver_coupled
    # ~L433), which would wipe the tag and make agents_of_kind('tumor_cell') empty.
    # MicroC is single-kind, so its gene_update/fate_update ask iterate ALL agents
    # (for_each has no `kind`) — see microc.json. Multi-kind models would need _kind
    # to survive metabolism (merge instead of replace, or a dedicated cell field).

    ctx["domain"] = domain
    ctx["abm_population"] = pop
    print(f"[build_tumor_cell_abm_population] wrapped {len(legacy.state.cells)} "
          f"cells on a {world.nx}x{world.ny} bio-grid world")
    return True
