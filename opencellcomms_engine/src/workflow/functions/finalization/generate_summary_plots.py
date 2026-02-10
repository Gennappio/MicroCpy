"""
Generate summary plots workflow function.

Generates all automatic plots (substance heatmaps, cell distributions, etc.)
using AutoPlotter.  Used for INITIAL and FINAL markers.

Output directory resolution (CLI mode):
  1. config.plots_dir   (timestamped: results/$timestamp/plots)   ← preferred
  2. context['plots_dir']  (subworkflow-specific, set by executor)
  3. 'results/plots'       (hard fallback)

This ensures INITIAL, ITER_*, and FINAL plots all land in the same
timestamped folder created by setup_simulation.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig


def _generate_plots_to_directory(
    context: Dict[str, Any],
    output_dir: Path,
    marker: str = "",
    substances_to_plot: str = "",
    clean_directory: bool = True,
    add_timestamp: bool = False,
) -> int:
    """
    Internal helper: generate plots to a specific directory.

    Args:
        context:            Workflow context (population, simulator, config, results …)
        output_dir:         Directory to write plots to.
        marker:             Appended to filenames (e.g. "INITIAL", "FINAL").
        substances_to_plot: Comma-separated list (empty = all).
        clean_directory:    Wipe image files before writing new plots.
        add_timestamp:      Append HHMMSS to filenames for debugging.

    Returns:
        Number of plots generated.
    """
    import sys
    from datetime import datetime
    visualization_dir = Path(__file__).parent.parent.parent.parent / "visualization"
    if str(visualization_dir) not in sys.path:
        sys.path.insert(0, str(visualization_dir.parent))

    from visualization.auto_plotter import AutoPlotter

    population = context.get('population')
    simulator  = context.get('simulator')
    config: IConfig = context.get('config')
    results    = context.get('results', {})

    # --- sanity checks ---------------------------------------------------
    if not simulator:
        print("[WARNING] Simulator not available in context - skipping plot generation")
        print(f"[WARNING] Available context keys: {list(context.keys())}")
        return 0
    if not population:
        print("[WARNING] Population not available in context - skipping plot generation")
        return 0
    if not config:
        print("[WARNING] Config not available in context - skipping plot generation")
        return 0

    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    # Optionally clean the directory before writing new plots
    if clean_directory:
        for file in output_dir.iterdir():
            if file.is_file() and file.suffix in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf']:
                file.unlink()

    # Add timestamp to marker if requested
    if add_timestamp:
        timestamp = datetime.now().strftime("%H%M%S")
        marker = f"{marker}_{timestamp}" if marker else timestamp

    # Parse substances to plot
    substance_list = None
    if substances_to_plot:
        substance_list = [s.strip() for s in substances_to_plot.split(',') if s.strip()]

    # Create plotter with the specified output directory
    plotter = AutoPlotter(config, output_dir)

    # Generate all plots with marker and substance filter
    generated_plots = plotter.generate_all_plots(
        results, simulator, population,
        marker=marker,
        substance_filter=substance_list
    )

    return len(generated_plots)


@register_function(
    display_name="Generate Summary Plots",
    description="Generate summary plots (INITIAL / FINAL). "
                "Output goes to config.plots_dir (timestamped results folder).",
    category="FINALIZATION",
    parameters=[
        {"name": "marker", "type": "STRING",
         "description": "Appended to filenames (e.g. 'INITIAL', 'FINAL'). "
                        "Leave empty for no marker.", "default": ""},
        {"name": "substances_to_plot", "type": "STRING",
         "description": "Comma-separated substances to plot. "
                        "Leave empty for all.", "default": ""},
        {"name": "clean_directory", "type": "BOOL",
         "description": "If true, remove existing plots before writing",
         "default": False},
        {"name": "add_timestamp", "type": "BOOL",
         "description": "If true, append HHMMSS to filenames",
         "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def generate_summary_plots(
    context: Dict[str, Any],
    marker: str = "",
    substances_to_plot: str = "",
    clean_directory: bool = False,
    add_timestamp: bool = False,
    **kwargs
) -> bool:
    """
    Generate summary plots (typically INITIAL or FINAL).

    Output directory: config.plots_dir  (the timestamped results folder
    created by setup_simulation), so all plots end up together in
    results/$timestamp/plots/heatmaps/.

    Args:
        context:            Workflow context.
        marker:             Appended to filenames ("INITIAL", "FINAL").
        substances_to_plot: Comma-separated list (empty = all).
        clean_directory:    Wipe image files from target dir first.
        add_timestamp:      Append HHMMSS to filenames.
        **kwargs:           Ignored.

    Returns:
        True on success, False on error.
    """
    # If marker not provided as parameter, check context
    if not marker and 'marker' in context:
        marker = context['marker']

    # --- resolve output directory -----------------------------------------
    # Use context['plots_dir'] set by executor (GUI-viewable subworkflow folder)
    if 'plots_dir' in context:
        output_path = Path(context['plots_dir'])
    else:
        # Fallback to config.plots_dir or default
        config: Optional[IConfig] = context.get('config')
        if config and hasattr(config, 'plots_dir') and config.plots_dir:
            output_path = Path(config.plots_dir)
        else:
            output_path = Path('results/plots')

    running_from_gui = context.get('running_from_gui', False)
    mode = "GUI" if running_from_gui else "CLI"
    print(f"[WORKFLOW] Generating plots ({mode} mode) to: {output_path}")

    marker_info     = f" with marker '{marker}'" if marker else ""
    timestamp_info  = " with timestamp" if add_timestamp else ""
    substances_info = f" for substances: {substances_to_plot}" if substances_to_plot else " for all substances"
    print(f"[WORKFLOW] Generating plots{marker_info}{timestamp_info}{substances_info}...")

    try:
        count = _generate_plots_to_directory(
            context, output_path,
            marker=marker,
            substances_to_plot=substances_to_plot,
            clean_directory=clean_directory,
            add_timestamp=add_timestamp,
        )
        print(f"[WORKFLOW] Generated {count} plots to {output_path}")
        return True

    except ImportError as e:
        print(f"[WORKFLOW] AutoPlotter not available, skipping summary plots: {e}")
        return False
    except Exception as e:
        print(f"[WORKFLOW] Error generating summary plots: {e}")
        import traceback
        traceback.print_exc()
        return False
