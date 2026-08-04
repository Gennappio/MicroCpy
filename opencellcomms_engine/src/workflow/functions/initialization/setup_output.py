"""
Setup output configuration.

This function configures output settings for plots, data saving, etc.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig


@register_function(
    display_name="Setup Output",
    description="Configure output settings (plots, data saving)",
    category="INITIALIZATION",
    parameters=[
        {"name": "save_data_interval", "type": "INT", "description": "Save data every N steps", "default": 10},
        {"name": "save_plots_interval", "type": "INT", "description": "Generate plots every N steps", "default": 10},
        {"name": "save_final_plots", "type": "BOOL", "description": "Generate plots at the end", "default": True},
        {"name": "save_initial_plots", "type": "BOOL", "description": "Generate plots at the beginning", "default": True},
        {"name": "status_print_interval", "type": "INT", "description": "Print status every N steps", "default": 10},
        {"name": "save_cellstate_interval", "type": "INT", "description": "Save cell states every N steps (0=disabled)", "default": 0},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def setup_output(
    context: Dict[str, Any],
    save_data_interval: int = 10,
    save_plots_interval: int = 10,
    save_final_plots: bool = True,
    save_initial_plots: bool = True,
    status_print_interval: int = 10,
    save_cellstate_interval: int = 0,
    **kwargs
) -> bool:
    """
    Setup output configuration.
    
    Args:
        context: Workflow context
        save_data_interval: Save data every N steps
        save_plots_interval: Generate plots every N steps
        save_final_plots: Generate plots at the end
        save_initial_plots: Generate plots at the beginning
        status_print_interval: Print status every N steps
        save_cellstate_interval: Save cell states every N steps (0 = disabled)
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    print("[WORKFLOW] Setting up output configuration")

    config: Optional[IConfig] = context.get('config')
    if config is None:
        raise RuntimeError("Config must be set up before output")
    if not hasattr(config, 'output') or config.output is None:
        raise RuntimeError("Config has no output configuration")

    positive_intervals = {
        'save_data_interval': save_data_interval,
        'save_plots_interval': save_plots_interval,
        'status_print_interval': status_print_interval,
    }
    for name, value in positive_intervals.items():
        if int(value) <= 0:
            raise ValueError(f"{name} must be greater than zero")
    if int(save_cellstate_interval) < 0:
        raise ValueError("save_cellstate_interval must be zero or greater")

    output = config.output
    output.save_data_interval = int(save_data_interval)
    output.save_plots_interval = int(save_plots_interval)
    output.save_final_plots = bool(save_final_plots)
    output.save_initial_plots = bool(save_initial_plots)
    output.status_print_interval = int(status_print_interval)
    output.save_cellstate_interval = int(save_cellstate_interval)

    print(f"   [+] Save data interval: {output.save_data_interval}")
    print(f"   [+] Save plots interval: {output.save_plots_interval}")
    print(f"   [+] Save final plots: {output.save_final_plots}")
    print(f"   [+] Save initial plots: {output.save_initial_plots}")
    return True
