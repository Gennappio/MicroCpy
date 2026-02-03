"""
Generate iteration-specific plots workflow function.

This function generates plots for a specific iteration with the iteration number
in both the filename and plot title. Supports filtering to specific substances.
"""

from typing import Dict, Any, List
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Generate Iteration Plots",
    description="Generate plots for current iteration with iteration number in filename and title. Supports substance filtering.",
    category="FINALIZATION",
    parameters=[
        {"name": "substances_to_plot", "type": "STRING", "description": "Comma-separated list of substances to plot (e.g., 'Oxygen,Glucose,Lactate'). Leave empty for all substances.", "default": ""},
        {"name": "clean_directory", "type": "BOOL", "description": "If true, remove existing plots before writing new ones", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def generate_iteration_plots(
    context: Dict[str, Any],
    substances_to_plot: str = "",
    clean_directory: bool = False,
    **kwargs
) -> bool:
    """
    Generate plots for current iteration with iteration number in filename and title.

    This function generates heatmaps for specified substances (or all if not specified)
    with the iteration number included in both the filename and plot title.

    Args:
        context: Workflow context containing population, simulator, config, step, etc.
        substances_to_plot: Comma-separated list of substances to plot (e.g., "Oxygen,Glucose,Lactate")
        clean_directory: If True, remove existing plots before writing new ones
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    import sys
    from pathlib import Path
    
    # Add visualization module to path
    visualization_dir = Path(__file__).parent.parent.parent.parent / "visualization"
    if str(visualization_dir) not in sys.path:
        sys.path.insert(0, str(visualization_dir.parent))

    from visualization.iteration_plotter import IterationPlotter

    population = context.get('population')
    simulator = context.get('simulator')
    config = context.get('config')
    step = context.get('step', 0)
    macrostep = context.get('macrostep', 0)
    
    # Use macrostep if available (for loop iterations), otherwise use step
    iteration = macrostep if macrostep > 0 else step

    # Parse substances to plot
    substance_list = None
    if substances_to_plot:
        substance_list = [s.strip() for s in substances_to_plot.split(',') if s.strip()]

    # Get output directory from context
    if 'plots_dir' in context:
        output_path = Path(context['plots_dir'])
    else:
        # Fallback for legacy contexts without plots_dir
        if config and hasattr(config, 'plots_dir'):
            output_path = Path(config.plots_dir)
        else:
            output_path = Path('results/plots')

    running_from_gui = context.get('running_from_gui', False)
    mode = "GUI" if running_from_gui else "CLI"

    substance_info = f" ({', '.join(substance_list)})" if substance_list else " (all substances)"
    print(f"[WORKFLOW] Generating iteration {iteration} plots{substance_info} ({mode} mode)")
    print(f"[WORKFLOW]   Output path: {output_path}")
    print(f"[WORKFLOW]   plots_dir in context: {'plots_dir' in context}")

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Optionally clean the directory before writing new plots
    if clean_directory:
        for file in output_path.iterdir():
            if file.is_file() and file.suffix in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf']:
                file.unlink()

    try:
        # Create plotter with the specified output directory
        plotter = IterationPlotter(config, output_path)

        # Generate plots for this iteration
        generated_plots = plotter.generate_iteration_plots(
            simulator=simulator,
            population=population,
            iteration=iteration,
            substance_filter=substance_list
        )

        print(f"[WORKFLOW] Generated {len(generated_plots)} plots for iteration {iteration}")
        return True

    except Exception as e:
        print(f"[WORKFLOW] Error generating iteration plots: {e}")
        import traceback
        traceback.print_exc()
        return False

