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


@register_function(
    display_name="Generate Iteration Plots",
    description="Generate plots for current iteration using the same AutoPlotter as FINAL plots. "
                "Iteration number appears in filename and title. "
                "Output goes to config.plots_dir (timestamped results folder).",
    category="FINALIZATION",
    parameters=[
        {"name": "substances_to_plot", "type": "STRING",
         "description": "Comma-separated substances to plot (e.g. 'Oxygen,Glucose,Lactate'). "
                        "Leave empty for all substances.", "default": ""},
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
        {"name": "use_config_plots_dir", "type": "BOOL",
         "description": "If true, always use config.plots_dir (shared timestamped folder) instead of "
                        "the subworkflow-specific plots_dir. Useful when multiple plot sub-workflows "
                        "should write to the same directory.",
         "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def generate_iteration_plots(
    context: Dict[str, Any],
    substances_to_plot: str = "",
    clean_directory: bool = False,
    plot_interval: int = 1,
    plot_name_suffix: str = "",
    use_config_plots_dir: bool = False,
    **kwargs
) -> bool:
    """
    Generate plots for the current loop iteration.

    Uses exactly the same AutoPlotter code path as generate_summary_plots,
    producing identical formatting (threshold isolines, dual cell legends,
    metabolic-state colours, etc.).

    The iteration number is embedded in:
      - filename  → e.g. Oxygen_heatmap_t5.000_ITER_003.png
      - title     → e.g. "Oxygen Distribution at t = 5.000 [Iteration 3] ..."

    Output directory: context['plots_dir'] (GUI-viewable subworkflow folder).

    Args:
        context:            Workflow context.
        substances_to_plot: Comma-separated list (empty = all).
        clean_directory:    Wipe image files from the target dir first.
        plot_interval:      Plot every N iterations (1=all, 5=every 5th, etc.).
        plot_name_suffix:   Suffix appended to marker and title (e.g. '_pre_micro').
        **kwargs:           Ignored.

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
    population       = context.get('population')
    simulator        = context.get('simulator')
    config: Optional[IConfig] = context.get('config')
    results          = context.get('results', {})

    # The executor sets loop_iteration (1-based) for every sub-workflow
    # iteration.  Fall back to macrostep / step for legacy callers.
    iteration = context.get('loop_iteration', 0)
    if iteration == 0:
        iteration = context.get('macrostep', context.get('step', 0))

    # --- coerce string parameters from JSON --------------------------------
    plot_interval = int(plot_interval)
    if isinstance(use_config_plots_dir, str):
        use_config_plots_dir = use_config_plots_dir.lower() in ('true', '1', 'yes')
    
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
    # When use_config_plots_dir is set, skip the subworkflow-specific path
    # and use the shared timestamped config.plots_dir instead.
    if use_config_plots_dir and config and hasattr(config, 'plots_dir') and config.plots_dir:
        output_path = Path(config.plots_dir)
    elif 'plots_dir' in context:
        output_path = Path(context['plots_dir'])
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
    print(f"[WORKFLOW] Generating iteration {iteration} plots{substance_info}")
    print(f"[WORKFLOW]   Output path: {output_path}")

    # --- generate plots using the *same* AutoPlotter as FINAL plots -------
    try:
        plotter = AutoPlotter(config, output_path)

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
