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
    description="Initialize simulation infrastructure (name, timestep, output directory)",
    category="INITIALIZATION",
    parameters=[
        {"name": "name", "type": "STRING", "description": "Simulation name", "default": "MicroCpy Simulation"},
        {"name": "dt", "type": "FLOAT", "description": "Timestep size (hours)", "default": 0.1},
        {"name": "output_dir", "type": "STRING", "description": "Base output directory", "default": "results"},
    ],
    outputs=["config"],
    cloneable=False
)
def setup_simulation(
    context: Dict[str, Any],
    name: str = "MicroCpy Simulation",
    dt: float = 0.1,
    output_dir: str = "results",
    **kwargs
) -> bool:
    """
    Setup simulation infrastructure.

    This function creates the minimal config object and output directories.

    Note: The following parameters are intentionally NOT included here because
    they are controlled elsewhere in the granular workflow:
    - total_steps: Controlled by macrostep.steps in the workflow JSON
    - save_interval: Not needed - finalization functions are called explicitly
    - diffusion_step/intracellular_step/intercellular_step: Controlled by
      step_count on individual nodes in the macrostep canvas

    Args:
        context: Workflow context
        name: Simulation name
        dt: Timestep size (hours)
        output_dir: Base output directory
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

        # Set dt in context so the engine uses it
        context['dt'] = float(dt)

        # Store simulation parameters in context (for later use)
        context['simulation_params'] = {
            'name': name,
            'dt': dt,
            'output_dir': timestamped_dir,
            'plots_dir': plots_dir,
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
                # Note: end_time is not set here - it's controlled by macrostep.steps
                # Multi-timescale is controlled by step_count on nodes in macrostep canvas
                self.time = TimeConfig(
                    dt=dt,
                    end_time=100.0,  # Placeholder - actual steps controlled by macrostep.steps
                    diffusion_step=1,  # Controlled by step_count on microenvironment_step node
                    intracellular_step=1,  # Controlled by step_count on intracellular_step node
                    intercellular_step=1  # Controlled by step_count on intercellular_step node
                )
                # Set default diffusion config (can be overridden by parameters)
                self.diffusion = DiffusionConfig(
                    max_iterations=1000,
                    tolerance=1e-6,
                    solver_type="steady_state",
                    twodimensional_adjustment_coefficient=1.0
                )
                # Set default output config
                # Note: save intervals are not used in granular workflow -
                # finalization functions are called explicitly
                self.output = OutputConfig(
                    save_data_interval=1,
                    save_plots_interval=1,
                    save_final_plots=True,
                    save_initial_plots=True,
                    status_print_interval=1,
                    save_cellstate_interval=1
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
        print(f"   [+] Timestep: {dt}")
        print(f"   [+] Output directory: {timestamped_dir}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to setup simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

