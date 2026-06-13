"""
Plot World — a generic snapshot of the ABM world (grid + resources + agents).

A deliberately simple, model-agnostic plotter: it draws each resource field as a
heatmap and overlays agent positions colored by kind. It works for any tile-grid
ABM (not just biology). Drop it wherever you want a picture:
- on the Space/Initialization canvas → an initial-conditions snapshot,
- in the Scheduler loop → one frame per step (an animation series),
- in Processing/finalization → a final snapshot.

It is an ordinary node: removable, replaceable, and enable/disable like any other.
Output PNGs go to ``context['plots_dir']``, which the Results tab reads.
"""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function
from src.workflow.logging import log_always

_KIND_COLORS = ["#f59e0b", "#22d3ee", "#a78bfa", "#f472b6", "#34d399", "#ef4444"]


@register_function(
    display_name="Plot World",
    description="Simple generic snapshot: resource fields as heatmaps + agent positions by kind",
    category="FINALIZATION",
    parameters=[
        {"name": "resource", "type": "STRING", "description": "Resource field to show as the heatmap (blank = first available)", "default": ""},
        {"name": "prefix", "type": "STRING", "description": "Output filename prefix", "default": "world"},
        {"name": "show_resources", "type": "BOOL", "description": "Draw resource fields as a heatmap", "default": True},
        {"name": "show_agents", "type": "BOOL", "description": "Draw agent positions", "default": True},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    compatible_kernels=["*"],
    requires=[],
)
def plot_world(
    env: BiologicalContext,
    resource: str = "",
    prefix: str = "world",
    show_resources: bool = True,
    show_agents: bool = True,
    **kwargs,
) -> bool:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pathlib import Path

    space = env.space
    domain = env.domain
    population = env.population
    if space is None:
        log_always("[plot_world] No space in context — nothing to plot (run setup_space first)")
        return True  # non-fatal: a plotting node should never break a run

    fig, ax = plt.subplots(figsize=(5, 5))

    # Resource heatmap (optional)
    resources = domain.resources() if show_resources and domain is not None else []
    chosen = None
    if resources:
        names = [r.name for r in resources]
        pick = resource if resource in names else names[0]
        chosen = domain.resource(pick)
        ax.imshow(chosen.values(), origin="lower", cmap="YlOrBr",
                  extent=[0, space.nx, 0, space.ny], aspect="equal")

    # Agents as dots, colored by kind
    if show_agents and population is not None:
        agents = population.agents()
        kinds = sorted({(a.kind or "agent") for a in agents})
        for a in agents:
            ci = kinds.index(a.kind or "agent") % len(_KIND_COLORS)
            ax.plot(a.position[0] + 0.5, a.position[1] + 0.5, "o",
                    color=_KIND_COLORS[ci], markersize=3)
        for i, k in enumerate(kinds):
            ax.plot([], [], "o", color=_KIND_COLORS[i % len(_KIND_COLORS)], label=k)
        if kinds:
            ax.legend(loc="upper right", fontsize=7, framealpha=0.7)

    ax.set_xlim(0, space.nx)
    ax.set_ylim(0, space.ny)
    step = env.step
    ax.set_title(f"{prefix} — step {step}" + (f" · {chosen.name}" if chosen else ""))

    out_dir = Path(env.raw_context.get("plots_dir", "results/plots"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{prefix}_step{step:04d}.png" if isinstance(step, int) else out_dir / f"{prefix}.png"
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"[plot_world] wrote {out_path}")
    return True


@register_function(
    display_name="Plot Space",
    description="Snapshot the grid bounds without resource heatmaps or agent markers",
    category="FINALIZATION",
    parameters=[
        {"name": "prefix", "type": "STRING", "description": "Output filename prefix", "default": "space"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    compatible_kernels=["*"],
    requires=[],
)
def plot_space(env: BiologicalContext, prefix: str = "space", **kwargs) -> bool:
    return plot_world(env, resource="", prefix=prefix, show_resources=False, show_agents=False, **kwargs)


@register_function(
    display_name="Plot Agents",
    description="Snapshot agent positions by kind without a resource heatmap",
    category="FINALIZATION",
    parameters=[
        {"name": "prefix", "type": "STRING", "description": "Output filename prefix", "default": "agents"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    compatible_kernels=["*"],
    requires=[],
)
def plot_agents(env: BiologicalContext, prefix: str = "agents", **kwargs) -> bool:
    return plot_world(env, resource="", prefix=prefix, show_resources=False, show_agents=True, **kwargs)


@register_function(
    display_name="Plot Resources",
    description="Snapshot one resource field without agent markers",
    category="FINALIZATION",
    parameters=[
        {"name": "resource", "type": "STRING", "description": "Resource field to show (blank = first available)", "default": ""},
        {"name": "prefix", "type": "STRING", "description": "Output filename prefix", "default": "resources"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    compatible_kernels=["*"],
    requires=[],
)
def plot_resources(env: BiologicalContext, resource: str = "", prefix: str = "resources", **kwargs) -> bool:
    return plot_world(env, resource=resource, prefix=prefix, show_resources=True, show_agents=False, **kwargs)
