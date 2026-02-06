"""
Generate initial state plots workflow function.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from src.workflow.decorators import register_function
from interfaces.base import ICellPopulation, ISubstanceSimulator, IConfig


@register_function(
    display_name="Generate Initial Plots",
    description="Generate initial state plots before simulation",
    category="FINALIZATION",
    outputs=[],
    cloneable=False
)
def generate_initial_plots(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Generate initial state plots (before simulation starts).
    
    This function creates:
    - Initial state summary plot (4-panel overview)
    - Individual heatmaps for ALL substances showing true initial state
    
    Args:
        context: Workflow context containing population, simulator, config, etc.
        **kwargs: Additional parameters (ignored)
        
    Returns:
        True if successful, False otherwise
    """
    print("[WORKFLOW] Generating initial state plots...")

    try:
        # Import AutoPlotter (uses context['engine_root'] if available)
        from visualization.auto_plotter import AutoPlotter

        population: ICellPopulation = context['population']
        simulator: ISubstanceSimulator = context['simulator']
        config: IConfig = context['config']

        # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
        if 'plots_dir' in context:
            plots_dir = Path(context['plots_dir'])
        else:
            # Fallback for legacy contexts
            plots_dir = Path(config.plots_dir) if hasattr(config, 'plots_dir') else Path('results/plots')

        plots_dir.mkdir(parents=True, exist_ok=True)

        # Create plotter with context-provided path
        plotter = AutoPlotter(config, plots_dir)

        # Generate initial state summary (includes heatmaps for all substances)
        initial_plot = plotter.plot_initial_state_summary(population, simulator)

        running_from_gui = context.get('running_from_gui', False)
        mode = "GUI" if running_from_gui else "CLI"
        print(f"[WORKFLOW] Generated initial state plots ({mode} mode)")
        print(f"   [+] Initial state summary: {initial_plot.name}")
        print(f"   [+] Individual heatmaps for {len(config.substances)} substances")
        print(f"   [+] Output directory: {plots_dir}")

        return True

    except ImportError as e:
        print(f"[WORKFLOW] AutoPlotter not available, skipping initial plots: {e}")
        return False
    except Exception as e:
        print(f"[WORKFLOW] Error generating initial plots: {e}")
        import traceback
        traceback.print_exc()
        return False

