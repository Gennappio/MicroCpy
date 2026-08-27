"""
Setup simulation infrastructure.

This function initializes the basic simulation parameters like name, duration, timestep, etc.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always


@register_function(
    display_name="Setup Simulation",
    description="Initialize simulation infrastructure. Workflow outputs use the executor-managed runs/<run name> folder; output_dir is only the standalone-call fallback.",
    category="INITIALIZATION",
    parameters=[
        {"name": "name", "type": "STRING", "description": "Simulation name", "default": "OpenCellComms Simulation"},
        {"name": "dt", "type": "FLOAT", "description": "Timestep size (hours)", "default": 0.1},
        {"name": "dimensions", "type": "INT", "description": "Domain dimensions (2 or 3)", "default": 2},
        {"name": "output_dir", "type": "STRING", "description": "Fallback output directory only when this function is called outside the workflow executor", "default": "results"},
        {"name": "verbose", "type": "BOOL", "description": "Enable detailed logging", "default": None},
    ],
    inputs=["context"],
    outputs=["config"],
    cloneable=False
)
def setup_simulation(
    context: Dict[str, Any],
    name: str = "OpenCellComms Simulation",
    dt: float = 0.1,
    # Default 2, matching setup_domain: workflows usually wire Dimensions only
    # to setup_domain, and a stale default 3 here once put a 3D value in
    # context['dimensions'] for a 2D world (cell division then stacked
    # daughters in a phantom z-layer). 3D runs must opt in explicitly.
    dimensions: int = 2,
    output_dir: str = "results",
    verbose: Optional[bool] = None,
    **kwargs
) -> bool:
    """
    Setup simulation infrastructure.

    This function creates the minimal config object. In a workflow, output
    paths are owned by the executor and writers create directories lazily.

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
        dimensions: Domain dimensions (2 or 3)
        output_dir: Base output directory
        **kwargs: Additional parameters

    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Setting up simulation: {name}")

    try:
        # The executor is the single owner of workflow output paths. It places
        # real artifacts under runs/<run name>/<subworkflow> before this node
        # executes. The parameter remains a supported fallback for direct
        # standalone calls, where no executor-managed path exists.
        managed_output_dir = context.get('output_dir')
        if managed_output_dir is not None:
            resolved_output_dir = Path(managed_output_dir)
            plots_dir = Path(context.get('plots_dir') or resolved_output_dir)
            output_source = "workflow run folder"
        else:
            resolved_output_dir = Path(output_dir)
            plots_dir = resolved_output_dir / "plots"
            output_source = "standalone output_dir parameter"

        # Store dimensions in context so other functions can use them.
        # Note: dt is intentionally NOT written as a flat key here — it lives on
        # context['clock'] (set by configure_time_and_steps or the engine).
        context['dimensions'] = int(dimensions)

        # Store simulation parameters in context (for later use)
        context['simulation_params'] = {
            'name': name,
            'dt': dt,
            'dimensions': dimensions,
            'output_dir': resolved_output_dir,
            'plots_dir': plots_dir,
        }

        # Initialize results tracking
        context['results'] = {
            'time': [],
            'cell_count': [],
            'substance_stats': {}
        }

        # Initialize helpers dict (for workflow-only mode)
        # In full simulation mode, this is populated by SimulationEngine._build_context()
        # In workflow-only mode, we need an empty dict to satisfy function signatures
        if 'helpers' not in context:
            context['helpers'] = {}

        # Create a minimal config object that will be populated by other setup functions
        # This is a placeholder that will be filled in by setup_domain, setup_substances, etc.
        from src.config.config import TimeConfig, DiffusionConfig, OutputConfig, InitialStateConfig

        class MinimalConfig:
            """Minimal config object that can be built up by granular setup functions"""
            def __init__(self):
                self.output_dir = resolved_output_dir
                self.plots_dir = plots_dir
                self.data_dir = resolved_output_dir / "data"
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
                # Create minimal domain object to store dimensions
                # (will be fully populated by setup_domain)
                class MinimalDomain:
                    def __init__(self):
                        self.dimensions = dimensions
                self.domain = MinimalDomain()
                # These will be set by other setup functions:
                self.substances = {}
                self.associations = {}
                self.thresholds = {}
                self.gene_network = None
                self.custom_functions_path = None

        context['config'] = MinimalConfig()

        log(context, f"Simulation name: {name}", prefix="[+]", node_verbose=verbose)
        log(context, f"Timestep: {dt}", prefix="[+]", node_verbose=verbose)
        log(
            context,
            f"Output directory ({output_source}): {resolved_output_dir}",
            prefix="[+]",
            node_verbose=verbose,
        )

        return True

    except Exception as e:
        log_always(f"[ERROR] Failed to setup simulation: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_simulation_dt_hours(context: Dict[str, Any]) -> float:
    """dt (hours) as owned by the Setup Simulation node (R2.2: one value, one owner).

    setup_simulation stores its GUI ``dt`` parameter in ``config.time.dt``;
    every per-step consumer (the transient diffusion solves, the MaBoSS window)
    resolves it here at run time instead of declaring a second dt parameter.

    Deliberately NOT ``env.dt``: in the v2.0 executor path no clock is seeded
    and no flat ``context['dt']`` exists, so ``env.dt`` silently returns its
    1.0 fallback and would discard the configured value. And deliberately no
    fallback here (R2.3): ``setup_simulation`` always runs first in
    ``__world__``, so a missing owner is a wiring bug — fail loudly.
    """
    config = context.get('config')
    dt = getattr(getattr(config, 'time', None), 'dt', None)
    if dt is None:
        raise ValueError(
            "dt is owned by the Setup Simulation node (config.time.dt) and is "
            "not set — ensure setup_simulation runs in __world__ before any "
            "transient-diffusion or MaBoSS node")
    return float(dt)  # GUI may deliver "0.01" as a string
