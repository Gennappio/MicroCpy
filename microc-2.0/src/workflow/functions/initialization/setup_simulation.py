"""
Setup simulation infrastructure.

This function initializes the basic simulation parameters like name, duration, timestep, etc.
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Setup Simulation",
    description="Initialize simulation parameters (name, duration, timestep)",
    category="INITIALIZATION",
    parameters=[
        {"name": "name", "type": "STRING", "description": "Simulation name", "default": "MicroCpy Simulation"},
        {"name": "duration", "type": "FLOAT", "description": "Total simulation time", "default": 10.0},
        {"name": "dt", "type": "FLOAT", "description": "Timestep size", "default": 0.1},
        {"name": "output_dir", "type": "STRING", "description": "Base output directory", "default": "results"},
        {"name": "save_interval", "type": "INT", "description": "How often to save data", "default": 10},
        {"name": "diffusion_step", "type": "INT", "description": "Run diffusion every N steps", "default": 1},
        {"name": "intracellular_step", "type": "INT", "description": "Run intracellular every N steps", "default": 1},
        {"name": "intercellular_step", "type": "INT", "description": "Run intercellular every N steps", "default": 1},
    ],
    outputs=["config"],
    cloneable=False
)
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

        # Store simulation parameters in context (for later use)
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

        # Create a minimal config object that will be populated by other setup functions
        # This is a placeholder that will be filled in by setup_domain, setup_substances, etc.
        from src.config.config import TimeConfig, DiffusionConfig, OutputConfig, InitialStateConfig

        class MinimalConfig:
            """Minimal config object that can be built up by granular setup functions"""
            def __init__(self):
                self.output_dir = timestamped_dir
                self.plots_dir = plots_dir
                self.data_dir = timestamped_dir / "data"
                self.custom_parameters = {}
                self.debug_phenotype_detailed = False
                self.log_simulation_status = False
                self._workflow_mode = True  # Mark as workflow mode
                # Set time config from parameters
                self.time = TimeConfig(
                    dt=dt,
                    end_time=duration,
                    diffusion_step=diffusion_step,
                    intracellular_step=intracellular_step,
                    intercellular_step=intercellular_step
                )
                # Set default diffusion config (can be overridden by parameters)
                self.diffusion = DiffusionConfig(
                    max_iterations=1000,
                    tolerance=1e-6,
                    solver_type="steady_state",
                    twodimensional_adjustment_coefficient=1.0
                )
                # Set default output config
                self.output = OutputConfig(
                    save_data_interval=save_interval,
                    save_plots_interval=save_interval,
                    save_final_plots=True,
                    save_initial_plots=True,
                    status_print_interval=save_interval,
                    save_cellstate_interval=save_interval
                )
                # Set default initial state config
                self.initial_state = InitialStateConfig()
                # These will be set by other setup functions:
                self.domain = None
                self.substances = {}
                self.associations = {}
                self.thresholds = {}
                self.gene_network = None
                self.custom_functions_path = None

        context['config'] = MinimalConfig()

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

