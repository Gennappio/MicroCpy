"""
Generate iteration-specific plots workflow function.

Uses the same AutoPlotter code path as generate_summary_plots (INITIAL / FINAL),
ensuring identical formatting, legends, threshold isolines, etc.  The only
difference is the marker (ITER_001, ITER_002, ...) and a title suffix that
includes the iteration number.

Pseudocode:
  1. Read iteration number from context (macrostep or step).
  2. Resolve output directory: prefer config.plots_dir (timestamped folder)
     so that all plots land in  results/$timestamp/plots/heatmaps/.
  3. Instantiate AutoPlotter with the resolved directory.
  4. Call generate_all_plots() with marker="ITER_NNN" and
     title_suffix="[Iteration N]" so both filename and title carry
     the iteration number.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig
from src.biology.context import BiologicalContext
from opencellcomms_adapters.MicroC.functions.reporting.cell_colors import (
    jayatilake_cell_color, fate_fill_cell_color, FATE_FILL_LEGEND)


def _to_bool(val) -> bool:
    """Coerce a value to bool, tolerating GUI strings ("true"/"false")."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'on', 'yes')
    return bool(val)


# One shared definition of the heatmap display flags: both AutoPlotter-based
# plot nodes (iteration and summary) expose exactly these switches, and each
# maps 1:1 onto the AutoPlotter constructor option of the same name.
HEATMAP_DISPLAY_FLAGS = [
    {"name": "show_cells", "type": "BOOL",
     "description": "Draw the cells over each substance heatmap. Off = fields "
                    "only; the cell legends disappear with them.",
     "default": True},
    {"name": "show_metabolism_colors", "type": "BOOL",
     "description": "Colour each cell's interior by metabolic mode (green "
                    "glycoATP / blue mitoATP / violet mixed / lightgray none). "
                    "Off = neutral lightgray interiors and no metabolism legend.",
     "default": True},
    {"name": "show_fate_colors", "type": "BOOL",
     "description": "Colour each cell's border by marked phenotype (black "
                    "Necrosis / red Apoptosis / lightgreen Proliferation / "
                    "orange Growth_Arrest / gray Quiescent). Off = neutral gray "
                    "borders and no phenotype legend.",
     "default": True},
    {"name": "show_isolines", "type": "BOOL",
     "description": "Draw the threshold lines on each heatmap (gene-association "
                    "threshold, solid red; necrosis thresholds, dashed). "
                    "Off = clean fields only.",
     "default": True},
    {"name": "show_legends", "type": "BOOL",
     "description": "Draw the metabolic-state and phenotype cell legends on the "
                    "heatmaps. Off = no cell-colour key.",
     "default": True},
    {"name": "show_info_box", "type": "BOOL",
     "description": "Draw the 'Simulation Details' text box (grid, domain, "
                    "min/max/mean, cell count) on each heatmap. Off = no box.",
     "default": True},
    {"name": "cell_size_percent", "type": "FLOAT",
     "description": "Drawn size of each cell marker as a percentage of the "
                    "biological cell diameter (Cell Height). 100 = true size. "
                    "Display only.",
     "default": 100.0, "min_value": 1.0, "max_value": 100.0},
    {"name": "cell_color_mode", "type": "STRING",
     "description": "How each cell is coloured. interior_border: interior = "
                    "metabolic mode, border = phenotype, two legends (classic). "
                    "fill: one solid disc, no border: black Necrosis, green "
                    "glycoATP, blue mitoATP, violet both, gray no pathway; the "
                    "show_metabolism_colors / show_fate_colors switches do not "
                    "apply.",
     "default": "interior_border", "options": ["interior_border", "fill"]},
    {"name": "cell_border_width", "type": "FLOAT",
     "description": "Width of each cell marker's phenotype-coloured border, in "
                    "points. 2 = the classic look. Display only.",
     "default": 2.0, "min_value": 0.0, "max_value": 10.0},
    {"name": "show_grid_lines", "type": "BOOL",
     "description": "Draw the white solver-mesh lines (one per FiPy cell "
                    "boundary) over each heatmap. Off = field and cells only; "
                    "useful on fine grids where the mesh hides everything.",
     "default": True},
]


def select_cell_colorer(cell_color_mode: str):
    """(colour function, fill legend) for a cell_color_mode value. Shared by
    the iteration and summary plot nodes so both apply the same two laws."""
    if cell_color_mode == "fill":
        return fate_fill_cell_color, FATE_FILL_LEGEND
    if cell_color_mode == "interior_border":
        return jayatilake_cell_color, None
    raise ValueError(f"cell_color_mode must be 'interior_border' or 'fill', got {cell_color_mode!r}")


@register_function(
    requires=['population', 'simulator'],
    display_name="Generate Iteration Plots",
    description="Generate plots for current iteration using the same AutoPlotter as FINAL plots. "
                "Iteration number appears in filename and title. "
                "Output goes to config.plots_dir (timestamped results folder). "
                "Every heatmap overlay (cells, metabolism colours, fate colours, "
                "isolines, legends, info box) has its own show_* switch.",
    category="FINALIZATION",
    parameters=[
        {"name": "substances_to_plot", "type": "STRING",
         "description": "Comma-separated substances to plot (e.g. 'Oxygen,Glucose,Lactate'). "
                        "Leave empty for all substances.", "default": ""},
        *HEATMAP_DISPLAY_FLAGS,
        {"name": "clean_directory", "type": "BOOL",
         "description": "If true, remove existing plots before writing new ones",
         "default": False},
        {"name": "plot_interval", "type": "INT",
         "description": "Plot every N iterations (e.g., 1=every iteration, 5=every 5th iteration, 10=every 10th). "
                        "Set to 1 to plot every iteration.",
         "default": 1},
        {"name": "plot_name_suffix", "type": "STRING",
         "description": "Suffix appended to plot filenames and titles (e.g. '_pre_micro', '_post_micro'). "
                        "Leave empty for no suffix.",
         "default": ""},
        {"name": "redirect_to_subworkflow", "type": "STRING",
         "description": "Write plots into a different subworkflow's output directory. "
                        "Set to the target subworkflow name (e.g. 'Generate_loop_plots') so that "
                        "multiple plot nodes share one folder. Leave empty to use this node's own folder.",
         "default": ""},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def generate_iteration_plots(
    env: BiologicalContext,
    substances_to_plot: str = "",
    show_cells: bool = True,
    show_metabolism_colors: bool = True,
    show_fate_colors: bool = True,
    show_isolines: bool = True,
    show_legends: bool = True,
    show_info_box: bool = True,
    cell_size_percent: float = 100.0,
    cell_color_mode: str = "interior_border",
    cell_border_width: float = 2.0,
    show_grid_lines: bool = True,
    clean_directory: bool = False,
    plot_interval: int = 1,
    plot_name_suffix: str = "",
    redirect_to_subworkflow: str = "",
    **kwargs
) -> bool:
    """
    Generate plots for the current loop iteration.

    Uses exactly the same AutoPlotter code path as generate_summary_plots,
    producing identical formatting (threshold isolines, dual cell legends,
    metabolic-state colours, etc.). The show_* display flags (see
    HEATMAP_DISPLAY_FLAGS) each remove one heatmap overlay.

    The iteration number is embedded in:
      - filename  → e.g. Oxygen_heatmap_t5.000_ITER_003.png
      - title     → e.g. "Oxygen Distribution at t = 5.000 [Iteration 3] ..."

    Output directory: ctx['plots_dir'] (GUI-viewable subworkflow folder).

    Args:
        context:            Workflow context.
        substances_to_plot: Comma-separated list (empty = all).
        clean_directory:    Wipe image files from the target dir first.
        plot_interval:      Plot every N iterations (1=all, 5=every 5th, etc.).
        plot_name_suffix:         Suffix appended to marker and title (e.g. '_pre_micro').
        redirect_to_subworkflow:  Write into a different subworkflow's plots dir.
        **kwargs:                 Ignored.

    Returns:
        True on success, False on error (or skipped if not a plot iteration).
    """
    import sys

    # --- make visualisation package importable ---------------------------
    visualization_dir = Path(__file__).parent.parent.parent.parent / "visualization"
    if str(visualization_dir) not in sys.path:
        sys.path.insert(0, str(visualization_dir.parent))

    from visualization.auto_plotter import AutoPlotter

    # --- pull objects from context ----------------------------------------
    ctx = env.raw_context
    population       = env.cells.raw
    simulator        = env.environment.raw_simulator
    config: Optional[IConfig] = env.config
    results          = ctx.get('results', {})

    # The executor sets loop_iteration (1-based) for every sub-workflow
    # iteration.  Fall back to clock.step for legacy callers.
    iteration = ctx.get('loop_iteration', 0)
    if iteration == 0:
        iteration = ctx.get('macrostep', env.step)

    # --- coerce string parameters from JSON --------------------------------
    plot_interval = int(plot_interval)
    show_cells = _to_bool(show_cells)
    show_metabolism_colors = _to_bool(show_metabolism_colors)
    show_fate_colors = _to_bool(show_fate_colors)
    show_isolines = _to_bool(show_isolines)
    show_legends = _to_bool(show_legends)
    show_info_box = _to_bool(show_info_box)
    
    # Skip plotting if this iteration doesn't match the interval
    if plot_interval > 1 and iteration % plot_interval != 0:
        print(f"[WORKFLOW] Skipping plots for iteration {iteration} (plot_interval={plot_interval})")
        return True  # Return success, just skipped
    
    # --- sanity checks ----------------------------------------------------
    if not simulator:
        print("[WARNING] Simulator not available in context - skipping iteration plots")
        return False
    if not population:
        print("[WARNING] Population not available in context - skipping iteration plots")
        return False
    if not config:
        print("[WARNING] Config not available in context - skipping iteration plots")
        return False

    # --- resolve output directory -----------------------------------------
    # When redirect_to_subworkflow is set, write into a sibling subworkflow's
    # folder under the same run. GUI and CLI now share one path shape
    # (runs/<label>/<subworkflow>), so the redirect is just a sibling swap.
    if redirect_to_subworkflow and 'plots_dir' in ctx:
        current_plots = Path(ctx['plots_dir'])
        output_path = current_plots.parent / redirect_to_subworkflow
    elif 'plots_dir' in ctx:
        output_path = Path(ctx['plots_dir'])
    else:
        # Fallback to config.plots_dir or default
        if config and hasattr(config, 'plots_dir') and config.plots_dir:
            output_path = Path(config.plots_dir)
        else:
            output_path = Path('results/plots')

    output_path.mkdir(parents=True, exist_ok=True)

    # Optionally clean the directory before writing new plots
    if clean_directory:
        heatmaps_dir = output_path / "heatmaps"
        if heatmaps_dir.exists():
            for f in heatmaps_dir.iterdir():
                if f.is_file() and f.suffix in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf']:
                    f.unlink()

    # --- parse substance filter -------------------------------------------
    substance_list = None
    if substances_to_plot:
        substance_list = [s.strip() for s in substances_to_plot.split(',') if s.strip()]

    # --- build marker & title suffix --------------------------------------
    marker       = f"ITER_{iteration:03d}{plot_name_suffix}"
    title_suffix = f"[Iteration {iteration}{' ' + plot_name_suffix.strip('_') if plot_name_suffix else ''}]"

    substance_info = f" ({', '.join(substance_list)})" if substance_list else " (all substances)"
    hidden = [label for label, shown in [('cells', show_cells),
                                         ('metabolism colours', show_metabolism_colors),
                                         ('fate colours', show_fate_colors),
                                         ('isolines', show_isolines),
                                         ('legends', show_legends),
                                         ('info box', show_info_box)] if not shown]
    hidden_info = f" — hidden: {', '.join(hidden)}" if hidden else ""
    print(f"[WORKFLOW] Generating iteration {iteration} plots{substance_info}{hidden_info}")
    print(f"[WORKFLOW]   Output path: {output_path}")

    # --- generate plots using the *same* AutoPlotter as FINAL plots -------
    try:
        # Necrosis thresholds published by mark_necrotic_cells → dashed isolines
        # on the Oxygen/Glucose heatmaps.
        extra_isolines = {substance: [(value, 'Necrosis')]
                          for substance, value in results.get('necrosis_thresholds', {}).items()}
        color_fn, fill_legend = select_cell_colorer(cell_color_mode)
        plotter = AutoPlotter(config, output_path, cell_color_fn=color_fn,
                              cell_color_mode=cell_color_mode, fill_legend=fill_legend,
                              extra_isolines=extra_isolines,
                              show_cells=show_cells,
                              show_metabolism_colors=show_metabolism_colors,
                              show_fate_colors=show_fate_colors,
                              show_legends=show_legends,
                              show_isolines=show_isolines,
                              show_info_box=show_info_box,
                              cell_size_percent=float(cell_size_percent),
                              cell_border_width=float(cell_border_width),
                              show_grid_lines=_to_bool(show_grid_lines))

        generated_plots = plotter.generate_all_plots(
            results, simulator, population,
            marker=marker,
            substance_filter=substance_list,
            title_suffix=title_suffix,
        )

        print(f"[WORKFLOW] Generated {len(generated_plots)} plots for iteration {iteration}")
        return True

    except Exception as e:
        print(f"[WORKFLOW] Error generating iteration plots: {e}")
        import traceback
        traceback.print_exc()
        return False
