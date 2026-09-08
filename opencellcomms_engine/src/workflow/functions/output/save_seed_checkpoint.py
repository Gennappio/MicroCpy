"""Per-iteration seed checkpoint: the population written in the seed CSV
format that ``read_checkpoint`` loads, so any iteration of this run can be
the starting point of another simulation.

Distinct from ``save_state_checkpoint`` (JSON + NPZ: everything needed to
RE-PLOT an iteration offline, not loadable as a population) and from the
legacy ``save_checkpoint`` (CSV keyed on a step counter the executor never
sets, with corner-origin coordinates the seed reader would shift). This node
writes exactly what ``load_initial_state_from_csv`` reads back — centre-
relative coordinates, ``origin=center`` header, phenotype, one ``gene_<name>``
column per gene — via ``src.io.initial_state.write_seed_csv`` (the format
owner, kept next to the reader).

To restart from iteration N: point the ``Checkpoint File`` parameter of the
reloading workflow's Read Checkpoint node at ``<subdir>/seed_ITER_00000N.csv``
and keep the same domain size and Cell Height (both are recorded in the
file's header line).
"""

from pathlib import Path

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext
from src.io.initial_state import write_seed_csv


@register_function(
    requires=['population'],
    display_name="Save Seed Checkpoint",
    description="Write this iteration's population as a seed CSV that Read "
                "Checkpoint reloads as the starting population of another "
                "simulation (centre-relative positions, phenotype, gene states). "
                "One file per iteration, seed_ITER_NNNNNN.csv, never pruned.",
    category="FINALIZATION",
    parameters=[
        {"name": "interval", "type": "INT",
         "description": "Save every N loop iterations (1 = every iteration, "
                        "0 = disabled).",
         "default": 1},
        {"name": "subdir", "type": "STRING",
         "description": "Directory under the plots dir for the seed files.",
         "default": "seeds"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    collective=True,
)
def save_seed_checkpoint(
    env: BiologicalContext,
    interval: int = 1,
    subdir: str = "seeds",
    **kwargs
) -> bool:
    ctx = env.raw_context
    # Same iteration clock as save_state_checkpoint and the plot nodes: the
    # scheduler loop counter (env.step stays 0 under the workflow scheduler).
    iteration = ctx.get('loop_iteration', 0) or ctx.get('macrostep', env.step)
    interval = int(interval)
    if interval <= 0:
        return True
    if interval > 1 and iteration % interval != 0:
        return True

    out_path = env.plots_dir / str(subdir) / f"seed_ITER_{int(iteration):06d}.csv"
    workflow_file = Path(str(ctx.get('workflow_file', '') or '')).name
    description = (f"seed checkpoint iteration {iteration}"
                   + (f" of {workflow_file}" if workflow_file else ""))
    try:
        write_seed_csv(env.cells.raw.state.cells.values(), out_path, env.config,
                       description=description)
    except Exception as e:
        # A checkpoint failure must not kill a long run.
        print(f"[WORKFLOW] Error writing seed checkpoint: {e}")
        import traceback
        traceback.print_exc()
        return False
    dom = env.config.domain
    print(f"[WORKFLOW] Seed checkpoint written: {out_path} "
          f"({len(env.cells)} cells; reload with Read Checkpoint on a "
          f"{dom.size_x.micrometers:g} um domain, Cell Height "
          f"{dom.cell_height.micrometers:g} um)")
    return True
