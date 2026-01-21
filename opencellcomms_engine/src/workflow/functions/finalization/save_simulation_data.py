"""
Save simulation data workflow function.

This function saves simulation results (time series, substance data, config)
to files for later analysis.
"""

from typing import Dict, Any
from pathlib import Path
import json
from src.workflow.decorators import register_function


@register_function(
    display_name="Save Simulation Data",
    description="Save simulation data to files (time series, substance stats, config)",
    category="FINALIZATION",
    parameters=[
        {
            "name": "save_config",
            "type": "BOOL",
            "description": "Save simulation configuration",
            "default": True
        },
        {
            "name": "save_timeseries",
            "type": "BOOL",
            "description": "Save time series data",
            "default": True
        },
        {
            "name": "save_substances",
            "type": "BOOL",
            "description": "Save substance statistics",
            "default": True
        }
    ],
    outputs=[],
    cloneable=False
)
def save_simulation_data(
    context: Dict[str, Any],
    save_config: bool = True,
    save_timeseries: bool = True,
    save_substances: bool = True,
    **kwargs
) -> bool:
    """
    Save simulation data to files in finalization stage.

    This function saves simulation results (time series, substance data, config)
    that would normally be saved automatically in non-workflow mode.

    Args:
        context: Workflow context containing results, config, etc.
        save_config: Whether to save simulation configuration
        save_timeseries: Whether to save time series data
        save_substances: Whether to save substance statistics
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    print("[WORKFLOW] Saving simulation data...")

    try:
        import numpy as np

        config = context['config']
        results = context.get('results', {})

        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save configuration
        if save_config:
            config_data = {
                'simulation_name': getattr(config, 'name', 'Unknown'),
                'total_steps': getattr(config, 'total_steps', 0),
                'dt': getattr(config, 'dt', 0.1),
                'substances': list(config.substances.keys()) if hasattr(config, 'substances') else [],
            }
            with open(output_dir / "config_summary.json", 'w') as f:
                json.dump(config_data, f, indent=2)
            print(f"   [OK] Saved configuration summary")

        # Save time series data
        if save_timeseries and 'time' in results:
            np.save(output_dir / "time.npy", results['time'])
            print(f"   [OK] Saved time series data")

        # Save substance statistics
        if save_substances and 'substance_stats' in results:
            substance_data = {}
            for substance_name, stats in results['substance_stats'].items():
                substance_data[substance_name] = {
                    'mean': list(stats['mean']) if hasattr(stats['mean'], '__iter__') else [stats['mean']],
                    'min': list(stats['min']) if hasattr(stats['min'], '__iter__') else [stats['min']],
                    'max': list(stats['max']) if hasattr(stats['max'], '__iter__') else [stats['max']]
                }

            with open(output_dir / "substance_stats.json", 'w') as f:
                json.dump(substance_data, f, indent=2)
            print(f"   [OK] Saved substance statistics")

        print(f"[WORKFLOW] Data saved to {output_dir}")
        return True

    except Exception as e:
        print(f"[WORKFLOW] Error saving data: {e}")
        import traceback
        traceback.print_exc()
        return False

