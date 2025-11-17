"""
Setup output configuration.

This function configures output settings for plots, data saving, etc.
"""

from typing import Dict, Any


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
    print(f"[WORKFLOW] Setting up output configuration")
    
    try:
        config = context.get('config')
        
        if not config:
            print("[ERROR] Config must be set up before output")
            return False
        
        # Store output configuration
        config.output_save_data_interval = save_data_interval
        config.output_save_plots_interval = save_plots_interval
        config.output_save_final_plots = save_final_plots
        config.output_save_initial_plots = save_initial_plots
        config.output_status_print_interval = status_print_interval
        config.output_save_cellstate_interval = save_cellstate_interval
        
        print(f"   [+] Save data interval: {save_data_interval}")
        print(f"   [+] Save plots interval: {save_plots_interval}")
        print(f"   [+] Save final plots: {save_final_plots}")
        print(f"   [+] Save initial plots: {save_initial_plots}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup output: {e}")
        import traceback
        traceback.print_exc()
        return False

