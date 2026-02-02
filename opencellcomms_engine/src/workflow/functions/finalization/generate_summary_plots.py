"""
Generate summary plots workflow function.

This function generates all automatic plots (substance heatmaps, cell distributions, etc.)
at the end of the simulation. Supports both custom directory output and GUI-compatible output.
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function


def _generate_plots_to_directory(
    context: Dict[str, Any],
    output_dir: Path,
    marker: str = "",
    substances_to_plot: str = "",
    clean_directory: bool = True,
    add_timestamp: bool = False,
) -> int:
    """
    Internal helper to generate plots to a specific directory.

    Args:
        context: Workflow context containing population, simulator, config, etc.
        output_dir: Directory to write plots to
        marker: String to append to filenames (e.g., "INITIAL", "FINAL")
        substances_to_plot: Comma-separated list of substances to plot (empty = all)
        clean_directory: If True, clean image files before writing new plots
        add_timestamp: If True, append timestamp to filenames for debugging

    Returns:
        Number of plots generated
    """
    import sys
    from datetime import datetime
    visualization_dir = Path(__file__).parent.parent.parent.parent / "visualization"
    if str(visualization_dir) not in sys.path:
        sys.path.insert(0, str(visualization_dir.parent))

    from visualization.auto_plotter import AutoPlotter

    population = context['population']
    simulator = context['simulator']
    config = context['config']
    results = context.get('results', {})

    # Create output directory if it doesn't exist
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
    description="Generate summary plots. Uses context['plots_dir'] automatically (set by executor based on GUI/CLI mode).",
    category="FINALIZATION",
    parameters=[
        {"name": "marker", "type": "STRING", "description": "String to append to filenames (e.g., 'INITIAL', 'FINAL'). Leave empty for no marker.", "default": ""},
        {"name": "substances_to_plot", "type": "STRING", "description": "Comma-separated list of substances to plot (e.g., 'Oxygen,Glucose,Lactate'). Leave empty for all substances.", "default": ""},
        {"name": "clean_directory", "type": "BOOL", "description": "If true, remove existing plots before writing new ones", "default": False},
        {"name": "add_timestamp", "type": "BOOL", "description": "If true, append timestamp (HHMMSS) to filenames for debugging", "default": False},
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
    Generate summary plots in finalization stage.

    This function generates all automatic plots (substance heatmaps, etc.)
    Uses context['plots_dir'] which is automatically set by the executor
    based on whether running from GUI or CLI.

    Args:
        context: Workflow context containing population, simulator, config, etc.
        marker: String to append to filenames (e.g., "INITIAL", "FINAL")
        substances_to_plot: Comma-separated list of substances to plot (empty = all)
        clean_directory: If True, remove existing plots before writing new ones
        add_timestamp: If True, append timestamp (HHMMSS) to filenames for debugging
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    # If marker not provided as parameter, check context (passed from subworkflow call)
    if not marker and 'marker' in context:
        marker = context['marker']

    # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
    # The executor sets plots_dir based on GUI/CLI mode automatically
    if 'plots_dir' in context:
        output_path = Path(context['plots_dir'])
    else:
        # Fallback for legacy contexts without plots_dir
        config = context.get('config')
        if config and hasattr(config, 'plots_dir'):
            output_path = Path(config.plots_dir)
        else:
            output_path = Path('results/plots')

    running_from_gui = context.get('running_from_gui', False)
    mode = "GUI" if running_from_gui else "CLI"
    print(f"[WORKFLOW] Generating plots ({mode} mode) to: {output_path}")

    marker_info = f" with marker '{marker}'" if marker else ""
    timestamp_info = " with timestamp" if add_timestamp else ""
    substances_info = f" for substances: {substances_to_plot}" if substances_to_plot else " for all substances"
    print(f"[WORKFLOW] Generating plots{marker_info}{timestamp_info}{substances_info}...")

    try:
        count = _generate_plots_to_directory(
            context, output_path,
            marker=marker,
            substances_to_plot=substances_to_plot,
            clean_directory=clean_directory,
            add_timestamp=add_timestamp
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

