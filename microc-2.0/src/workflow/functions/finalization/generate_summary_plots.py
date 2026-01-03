"""
Generate summary plots workflow function.

This function generates all automatic plots (substance heatmaps, cell distributions, etc.)
at the end of the simulation.
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Generate Summary Plots",
    description="Generate summary plots (substance heatmaps, cell distributions)",
    category="FINALIZATION",
    outputs=[],
    cloneable=False
)
def generate_summary_plots(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Generate summary plots in finalization stage.

    This function generates all automatic plots (substance heatmaps, etc.)
    that would normally be generated automatically in non-workflow mode.

    Args:
        context: Workflow context containing population, simulator, config, etc.
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    print("[WORKFLOW] Generating summary plots...")

    try:
        # Import AutoPlotter
        import sys
        visualization_dir = Path(__file__).parent.parent.parent.parent / "visualization"
        if str(visualization_dir) not in sys.path:
            sys.path.insert(0, str(visualization_dir.parent))

        from visualization.auto_plotter import AutoPlotter

        population = context['population']
        simulator = context['simulator']
        config = context['config']
        results = context.get('results', {})

        # Create plotter
        plotter = AutoPlotter(config, config.plots_dir)

        # Generate all plots
        generated_plots = plotter.generate_all_plots(results, simulator, population)

        print(f"[WORKFLOW] Generated {len(generated_plots)} plots")
        return True

    except ImportError as e:
        print(f"[WORKFLOW] AutoPlotter not available, skipping summary plots: {e}")
        return False
    except Exception as e:
        print(f"[WORKFLOW] Error generating summary plots: {e}")
        import traceback
        traceback.print_exc()
        return False

