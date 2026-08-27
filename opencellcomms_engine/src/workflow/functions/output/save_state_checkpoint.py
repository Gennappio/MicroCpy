"""Per-iteration full-state checkpoint next to the iteration plots.

Thin node over ``src.io.state_checkpoint.write_state_checkpoint`` (the format
owner). Saves ALL substance fields plus every cell's position, phenotype,
gene states, metabolic state, age and division count, together with the
resolved isoline thresholds, domain geometry, iteration and time — enough to
re-render each retained iteration plot offline with
``opencellcomms_engine/tools/replot_checkpoint.py``, without re-running the
simulation. Works for 2D and 3D domains alike (arrays are saved verbatim in
the renderers' native orientation).
"""

from pathlib import Path
from typing import Any, Dict

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext
from src.io.state_checkpoint import write_state_checkpoint


@register_function(
    requires=['population', 'simulator'],
    display_name="Save State Checkpoint",
    description="Save the full per-iteration state alongside the iteration "
                "plots: all substance fields (compressed npz) + every cell's "
                "position, phenotype/fate, gene network states, metabolic "
                "state, age and division count (json), plus the resolved "
                "isoline thresholds, the proliferation ATP gate if one ran, "
                "domain geometry and time. Keeps a bounded recent history by "
                "default, sufficient to re-render retained iterations offline "
                "via tools/replot_checkpoint.py, in 2D and 3D.",
    category="FINALIZATION",
    parameters=[
        {"name": "interval", "type": "INT",
         "description": "Save every N loop iterations (1 = every iteration, "
                        "0 = disabled).",
         "default": 1},
        {"name": "max_checkpoints", "type": "INT",
         "description": "Keep only the newest N complete checkpoint pairs "
                        "(10 = bounded routine history, 0 = keep all).",
         "default": 10},
        {"name": "subdir", "type": "STRING",
         "description": "Directory under the plots dir for the checkpoint "
                        "files.",
         "default": "checkpoints"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def save_state_checkpoint(
    env: BiologicalContext,
    interval: int = 1,
    max_checkpoints: int = 10,
    subdir: str = "checkpoints",
    **kwargs
) -> bool:
    """Write this iteration's checkpoint and prune history beyond the limit."""
    ctx = env.raw_context
    population = env.cells.raw
    simulator = env.environment.raw_simulator
    config = env.config
    results = ctx.get('results', {})

    # Same iteration clock and gating style as the iteration-plot nodes.
    iteration = ctx.get('loop_iteration', 0) or ctx.get('macrostep', env.step)
    interval = int(interval)
    max_checkpoints = int(max_checkpoints)
    if interval <= 0:
        return True
    if max_checkpoints < 0:
        print("[WARNING] max_checkpoints must be 0 (unlimited) or a positive integer")
        return False
    if interval > 1 and iteration % interval != 0:
        return True

    if not simulator or not population or not config:
        print("[WARNING] Simulator/population/config not available - skipping state checkpoint")
        return False

    fields = {name: state.concentrations
              for name, state in simulator.state.substances.items()}

    # dt: the workflows wire it into config.time; clock/context keys win when
    # a workflow does set them. The chosen source is recorded in the file.
    clock = ctx.get('clock')
    if clock is not None and getattr(clock, 'dt', None) is not None:
        dt, dt_source = float(clock.dt), "clock"
    elif ctx.get('dt') is not None:
        dt, dt_source = float(ctx['dt']), "context.dt"
    elif getattr(getattr(config, 'time', None), 'dt', None) is not None:
        dt, dt_source = float(config.time.dt), "config.time.dt"
    else:
        dt, dt_source = 1.0, "default"

    # render_time = the exact value the plot nodes used this iteration (kept
    # for filename/title parity); time = iteration * dt (the honest clock).
    time_points = results.get('time', [])
    render_time = time_points[-1] if time_points else getattr(simulator, 'current_time', 0.0) or 0.0

    out_dir = Path(ctx.get('plots_dir', 'results/plots')) / str(subdir)

    try:
        json_path, _ = write_state_checkpoint(
            out_dir, iteration,
            fields=fields,
            cells=population.state.cells.values(),
            config=config,
            necrosis_thresholds=results.get('necrosis_thresholds', {}),
            proliferation_gate=results.get('proliferation_gate', {}),
            time=iteration * dt,
            render_time=render_time,
            dt=dt,
            dt_source=dt_source,
            provenance={
                'workflow_file': str(ctx.get('workflow_file', '') or ''),
                'subworkflow_name': str(ctx.get('subworkflow_name', '') or ''),
            },
        )
        removed = _prune_state_checkpoints(out_dir, max_checkpoints)
        print(f"[WORKFLOW] State checkpoint written: {json_path}")
        if removed:
            print(
                f"[WORKFLOW] Checkpoint retention: kept newest "
                f"{max_checkpoints}, removed {removed} old pair(s)"
            )
        return True
    except Exception as e:
        # A checkpoint failure must not kill a long run.
        print(f"[WORKFLOW] Error writing state checkpoint: {e}")
        import traceback
        traceback.print_exc()
        return False


def _prune_state_checkpoints(out_dir: Path, max_checkpoints: int) -> int:
    """Remove oldest complete JSON/NPZ pairs beyond ``max_checkpoints``."""
    if max_checkpoints <= 0:
        return 0

    prefix = "checkpoint_ITER_"
    complete = []
    for json_path in out_dir.glob(f"{prefix}*.json"):
        try:
            iteration = int(json_path.stem[len(prefix):])
        except ValueError:
            continue
        npz_path = out_dir / f"{json_path.stem}_fields.npz"
        if npz_path.exists():
            complete.append((iteration, json_path, npz_path))

    expired = sorted(complete)[:-max_checkpoints]
    removed = 0
    for _, json_path, npz_path in expired:
        try:
            json_path.unlink(missing_ok=True)
            npz_path.unlink(missing_ok=True)
            removed += 1
        except OSError as exc:
            print(f"[WORKFLOW] Warning: could not prune checkpoint pair: {exc}")
    return removed
