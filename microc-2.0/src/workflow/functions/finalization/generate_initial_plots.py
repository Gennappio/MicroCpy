"""
Generate initial state plots workflow function.
"""

from typing import Dict, Any
from pathlib import Path


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
        # Import AutoPlotter
        import sys
        visualization_dir = Path(__file__).parent.parent.parent / "visualization"
        if str(visualization_dir) not in sys.path:
            sys.path.insert(0, str(visualization_dir.parent))
        
        from visualization.auto_plotter import AutoPlotter
        
        population = context['population']
        simulator = context['simulator']
        config = context['config']

        # Create plotter
        plotter = AutoPlotter(config, config.plots_dir)
        
        # Generate initial state summary (includes heatmaps for all substances)
        initial_plot = plotter.plot_initial_state_summary(population, simulator)
        
        print(f"[WORKFLOW] Generated initial state plots")
        print(f"   [+] Initial state summary: {initial_plot.name}")
        print(f"   [+] Individual heatmaps for {len(config.substances)} substances")
        
        return True
        
    except ImportError:
        print("[WORKFLOW] AutoPlotter not available, skipping initial plots")
        return False
    except Exception as e:
        print(f"[WORKFLOW] Error generating initial plots: {e}")
        import traceback
        traceback.print_exc()
        return False

