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
    clean_directory: bool = True,
    add_timestamp: bool = False,
) -> int:
    """
    Internal helper to generate plots to a specific directory.

    Args:
        context: Workflow context containing population, simulator, config, etc.
        output_dir: Directory to write plots to
        marker: String to append to filenames (e.g., "INITIAL", "FINAL")
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

    # Create plotter with the specified output directory
    plotter = AutoPlotter(config, output_dir)

    # Generate all plots with marker
    generated_plots = plotter.generate_all_plots(results, simulator, population, marker=marker)

    return len(generated_plots)


@register_function(
    display_name="Generate Summary Plots",
    description="Generate summary plots to custom directory or GUI results directory. Use marker to distinguish plot sets (e.g., INITIAL, FINAL).",
    category="FINALIZATION",
    parameters=[
        {"name": "marker", "type": "STRING", "description": "String to append to filenames (e.g., 'INITIAL', 'FINAL'). Leave empty for no marker.", "default": ""},
        {"name": "clean_directory", "type": "BOOL", "description": "If true, remove existing plots before writing new ones", "default": False},
        {"name": "add_timestamp", "type": "BOOL", "description": "If true, append timestamp (HHMMSS) to filenames for debugging", "default": False},
        {"name": "use_gui_directory", "type": "BOOL", "description": "If true, write to GUI results directory; if false, use custom_directory", "default": False},
        {"name": "custom_directory", "type": "STRING", "description": "Custom directory path (used when use_gui_directory=false)", "default": "results/plots"},
        {"name": "gui_subworkflow_name", "type": "STRING", "description": "GUI subworkflow name (used when use_gui_directory=true)", "default": "main"},
        {"name": "gui_subworkflow_kind", "type": "STRING", "description": "GUI subworkflow kind: 'composer' or 'subworkflow' (used when use_gui_directory=true)", "default": "composer"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def generate_summary_plots(
    context: Dict[str, Any],
    marker: str = "",
    clean_directory: bool = False,
    add_timestamp: bool = False,
    use_gui_directory: bool = False,
    custom_directory: str = "results/plots",
    gui_subworkflow_name: str = "main",
    gui_subworkflow_kind: str = "composer",
    **kwargs
) -> bool:
    """
    Generate summary plots in finalization stage.

    This function generates all automatic plots (substance heatmaps, etc.)
    and can write to either a custom directory or the GUI results directory.
    Use marker to distinguish different plot sets (e.g., INITIAL vs FINAL).

    Args:
        context: Workflow context containing population, simulator, config, etc.
        marker: String to append to filenames (e.g., "INITIAL", "FINAL")
        clean_directory: If True, remove existing plots before writing new ones
        add_timestamp: If True, append timestamp (HHMMSS) to filenames for debugging
        use_gui_directory: If True, write to GUI results directory; if False, use custom_directory
        custom_directory: Custom directory path (relative to project root or absolute)
        gui_subworkflow_name: Subworkflow name for GUI directory (e.g., "main")
        gui_subworkflow_kind: Either "composer" or "subworkflow"
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    # If marker not provided as parameter, check context (passed from subworkflow call)
    if not marker and 'marker' in context:
        marker = context['marker']

    # Determine output directory
    project_root = Path(__file__).parent.parent.parent.parent.parent

    if use_gui_directory:
        # Use GUI results directory structure (in opencellcomms_gui folder, not opencellcomms_engine)
        gui_root = project_root.parent / "opencellcomms_gui"
        kind_plural = "composers" if gui_subworkflow_kind == "composer" else "subworkflows"
        output_path = gui_root / "results" / kind_plural / gui_subworkflow_name
        print(f"[WORKFLOW] Generating plots to GUI directory: {output_path}")
    else:
        # Use custom directory
        output_path = Path(custom_directory)
        if not output_path.is_absolute():
            output_path = project_root / custom_directory
        print(f"[WORKFLOW] Generating plots to custom directory: {output_path}")

    marker_info = f" with marker '{marker}'" if marker else ""
    timestamp_info = " with timestamp" if add_timestamp else ""
    print(f"[WORKFLOW] Generating plots{marker_info}{timestamp_info}...")

    try:
        count = _generate_plots_to_directory(context, output_path, marker=marker, clean_directory=clean_directory, add_timestamp=add_timestamp)
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

