"""PhysiCell-style snapshot: cells over the CCL21 field, colored by kind / fate.

Renders each frame like the reference PhysiBoSS output -- the CCL21 concentration as
a background heatmap (micrometre coordinates, centered on the origin) with every cell
drawn as a circle colored by kind and fate: naive T0 grey, Treg red, Th1 gold, Th17
green, dendritic blue, endothelial magenta. Runs every ``plot_interval`` steps so the
frames form a trackable sequence (``plots/cells/cells_0000.png``, ``_0005.png``, ...),
ready to flip through or assemble into a movie.
"""
import numpy as np

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext

_FATE_COLORS = {"Treg": "red", "Th1": "gold", "Th17": "green"}
_KIND_COLORS = {"dendritic_cell": "blue", "endothelial_cell": "magenta"}


@register_function(
    requires=["abm_population", "simulator"],
    display_name="Plot Cells over CCL21 Field",
    description="PhysiCell-style snapshot: cells colored by kind/fate over the CCL21 heatmap, "
                "one frame every plot_interval steps.",
    category="FINALIZATION",
    parameters=[
        {"name": "plot_interval", "type": "INT",
         "description": "Render a frame every N steps (1 = every step).",
         "default": 5, "min_value": 1},
        {"name": "minutes_per_step", "type": "FLOAT",
         "description": "Minutes of model time per step, for the frame time label (PhysiCell dt=6).",
         "default": 6.0, "min_value": 0.0},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def plot_ccl21_cells(env: BiologicalContext, plot_interval: int = 5,
                     minutes_per_step: float = 6.0, **kwargs) -> bool:
    ctx = env.raw_context
    step = int(ctx.get("loop_iteration", env.step) or 0)
    if plot_interval > 1 and step % plot_interval != 0:
        return True

    simulator = ctx.get("simulator")
    pop = ctx.get("abm_population")
    config = ctx.get("config")
    if simulator is None or pop is None or config is None:
        return True
    if "CCL21" not in simulator.state.substances:
        return True

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    dom = config.domain
    cell_um = dom.cell_height.micrometers
    half_x = dom.size_x.micrometers / 2.0
    half_y = dom.size_y.micrometers / 2.0

    # CCL21 field as the background heatmap. The internal scale is arbitrary, so
    # normalize to [0, 1] for a stable, readable gradient across frames.
    field = np.asarray(simulator.state.substances["CCL21"].concentrations, dtype=float)  # [ny, nx]
    disp = field / (field.max() or 1.0)

    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    im = ax.imshow(disp, origin="lower", extent=[-half_x, half_x, -half_y, half_y],
                   cmap="YlOrRd", vmin=0.0, vmax=1.0, aspect="equal")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label("CCL21 (relative)")

    # Cells as circles in centered-micrometre coordinates (tile centre).
    r = cell_um * 0.45
    n = 0
    for agent in pop.agents():
        gx, gy = agent.position[0], agent.position[1]
        x_um = gx * cell_um - half_x + cell_um / 2.0
        y_um = gy * cell_um - half_y + cell_um / 2.0
        kind = agent.kind
        if kind in _KIND_COLORS:
            color = _KIND_COLORS[kind]
        elif kind == "tcell":
            color = _FATE_COLORS.get(agent.get("fate", "naive"), "grey")
        else:
            color = "grey"
        ax.add_patch(Circle((x_um, y_um), r, facecolor=color, edgecolor="black",
                            linewidth=0.3, zorder=3))
        n += 1

    total_min = step * minutes_per_step
    d, h, m = int(total_min // 1440), int((total_min % 1440) // 60), int(total_min % 60)
    ax.set_title(f"{d} days, {h} hrs, {m} mins ({n} agents)")
    ax.set_xlim(-half_x, half_x)
    ax.set_ylim(-half_y, half_y)
    ax.set_xlabel("x (um)")
    ax.set_ylabel("y (um)")

    out_dir = env.plots_dir / "cells"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"cells_{step:04d}.png"
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return True
