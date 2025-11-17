"""
Setup simulation infrastructure.

This function initializes the basic simulation parameters like name, duration, timestep, etc.
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path


def setup_simulation(
    context: Dict[str, Any],
    name: str = "MicroCpy Simulation",
    duration: float = 10.0,
    dt: float = 0.1,
    output_dir: str = "results",
    save_interval: int = 10,
    diffusion_step: int = 1,
    intracellular_step: int = 1,
    intercellular_step: int = 1,
    **kwargs
) -> bool:
    """
    Setup simulation parameters.
    
    Args:
        context: Workflow context
        name: Simulation name
        duration: Total simulation time
        dt: Timestep size
        output_dir: Base output directory
        save_interval: How often to save data
        diffusion_step: How often to run diffusion (every N steps)
        intracellular_step: How often to run intracellular updates (every N steps)
        intercellular_step: How often to run intercellular updates (every N steps)
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Setting up simulation: {name}")
    
    try:
        # Create timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_dir = Path(output_dir)
        timestamped_dir = base_output_dir / timestamp
        timestamped_dir.mkdir(parents=True, exist_ok=True)
        plots_dir = timestamped_dir / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)
        
        # Store simulation parameters in context
        context['simulation_params'] = {
            'name': name,
            'duration': duration,
            'dt': dt,
            'output_dir': timestamped_dir,
            'plots_dir': plots_dir,
            'save_interval': save_interval,
            'diffusion_step': diffusion_step,
            'intracellular_step': intracellular_step,
            'intercellular_step': intercellular_step,
        }
        
        # Initialize results tracking
        context['results'] = {
            'time': [],
            'cell_count': [],
            'substance_stats': {}
        }
        
        print(f"   [+] Simulation name: {name}")
        print(f"   [+] Duration: {duration} time units")
        print(f"   [+] Timestep: {dt}")
        print(f"   [+] Output directory: {timestamped_dir}")
        print(f"   [+] Multi-timescale: diffusion={diffusion_step}, intracellular={intracellular_step}, intercellular={intercellular_step}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

