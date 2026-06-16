"""
Standard workflow functions for OpenCellComms.

These are high-level orchestrator functions that can be used in workflows.
They receive the full simulation context and can call helper functions.

NOTE: Granular functions (update_metabolism, update_gene_networks, etc.) are now
in separate files under src/workflow/functions/ for easy GUI viewing/editing.
They are re-imported here for backward compatibility.
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function

# Import granular engine (kernel / spatial / IO) functions from their individual
# files. Importing them here triggers their @register_function decorators.
# Biology functions (metabolism, gene networks, cell division/migration/death,
# population/gene-network/MaBoSS setup) now live in opencellcomms_adapters/common.
from src.workflow.functions.initialization import (
    setup_simulation,
    setup_domain,
    setup_substances,
    add_substance,
    finalize_substances,
    setup_output,
    setup_environment,
    setup_custom_parameters,
    read_checkpoint,
)
from src.workflow.functions.diffusion import (
    run_diffusion_solver,
    run_diffusion_solver_clamped,
    run_diffusion_solver_coupled,
)
from src.workflow.functions.finalization import (
    collect_statistics,
    export_final_state,
)
from src.workflow.functions.reconciliation import (
    apply_reconciliation,
)

from src.workflow.functions.output.export_csv import (
    export_csv_checkpoint,
    export_csv_checkpoint_conditional,
    export_csv_cells,
    export_csv_substances,
)
from src.workflow.functions.output.export_vtk import (
    export_vtk_checkpoint,
)


# ============================================================================
# INITIALIZATION FUNCTIONS
# ============================================================================





@register_function(
    display_name="Configure Time and Steps",
    description=(
        "Configure dt, macrosteps and steps_per_macrostep from workflow "
        "parameters and compute total_steps = macrosteps × steps_per_macrostep. "
        "These values are stored in the context so that SimulationEngine uses "
        "them instead of YAML time/end_time when available."
    ),
    category="INITIALIZATION",
    parameters=[
        {
            "name": "dt",
            "type": "FLOAT",
            "description": "Time step dt (hours per physical update)",
            "default": 0.1,
            "required": True,
            "min_value": 0.0,
        },
        {
            "name": "macrosteps",
            "type": "INT",
            "description": "Number of macrosteps (high-level loop iterations)",
            "default": 1,
            "required": True,
            "min_value": 1,
        },
        {
            "name": "steps_per_macrostep",
            "type": "INT",
            "description": (
                "Number of physical simulation steps inside each macrostep. "
                "Total physical steps = macrosteps × steps_per_macrostep."
            ),
            "default": 1,
            "required": True,
            "min_value": 1,
        },
        {
            "name": "checkpoint_interval",
            "type": "INT",
            "description": (
                "Checkpoint interval in physical steps (optional, <=0 to disable). "
                "This is stored in context as checkpoint_interval and also applied "
                "to config.output.save_cellstate_interval when a config is present."
            ),
            "default": 0,
            "required": False,
            "min_value": 0,
        },
        {
            "name": "save_data_interval",
            "type": "INT",
            "description": (
                "Results sampling interval in physical steps (optional, <=0 to "
                "leave unchanged). This is stored in context as "
                "save_data_interval and also applied to "
                "config.output.save_data_interval when a config is present."
            ),
            "default": 0,
            "required": False,
            "min_value": 0,
        },
	    ],
	    outputs=[],
	    cloneable=False,
	)
def configure_time_and_steps(
    context: Dict[str, Any],
    dt: float,
    macrosteps: int,
    steps_per_macrostep: int,
    checkpoint_interval: int = 0,
    save_data_interval: int = 0,
    **kwargs,
) -> bool:
    """Configure dt, macrosteps and steps_per_macrostep from workflow parameters.

    This function is intended to be called in the *initialization* stage from the
    workflow editor GUI. It takes dt, macrosteps and steps_per_macrostep from
    parameter nodes, computes::

        total_steps = macrosteps * steps_per_macrostep

    and stores the following in the workflow context:

    - ``context['dt']``
    - ``context['macrosteps']``
    - ``context['steps_per_macrostep']``
    - ``context['total_steps']``
    - optionally ``context['checkpoint_interval']``
    - optionally ``context['save_data_interval']``

    When a ``config`` object is already present in the context (for
    example because ``load_config_file`` was used), this function also keeps the
    YAML/config object in sync by overriding:

    - ``config.time.dt``
    - ``config.time.end_time`` (computed from total_steps × dt)
    - ``config.output.save_cellstate_interval`` (if checkpoint_interval > 0)
    - ``config.output.save_data_interval`` (if save_data_interval > 0)

    The SimulationEngine workflow runner will prefer ``context['total_steps']``
    and ``context['dt']`` over values from the YAML config when they are
    available, so this node makes dt / macrosteps / steps_per_macrostep fully
    controllable from the workflow GUI.
    """

    print("[WORKFLOW] Configuring time and steps from workflow parameters...")

    try:
        # Normalise and validate inputs
        dt_value = float(dt)
        if dt_value <= 0.0:
            raise ValueError("dt must be > 0")

        # ------------------------------------------------------------------
        # Determine macrosteps.
        #
        # Primary source (what you control in the GUI):
        #   - the "steps" field on the *macrostep stage* (outside the canvas).
        #     This comes from workflow.stages["macrostep"].steps and is edited
        #     via the macrostep stage tab in the GUI.
        #
        # The explicit "macrosteps" function parameter is kept for backward
        # compatibility but is treated as a fallback only. In normal GUI use
        # you don't need to touch it; you just set macrostep.stage.steps.
        # ------------------------------------------------------------------
        macrosteps_int = 0
        executor = context.get("_executor")
        if executor is not None:
            try:
                workflow = getattr(executor, "workflow", None)
                if workflow is not None:
                    macro_stage = workflow.get_stage("macrostep")
                    if macro_stage is not None:
                        macrosteps_int = int(getattr(macro_stage, "steps", 0) or 0)
            except Exception:
                # If anything goes wrong here, fall back to function parameter
                macrosteps_int = 0

        # Fallback: use the explicit macrosteps argument if stage.steps
        # was not available or is <= 0.
        if macrosteps_int <= 0:
            macrosteps_int = int(macrosteps)

        steps_per_macro_int = int(steps_per_macrostep)

        if macrosteps_int <= 0 or steps_per_macro_int <= 0:
            raise ValueError("macrosteps and steps_per_macrostep must be > 0")

        total_steps = macrosteps_int * steps_per_macro_int

        # Create or update SimulationClock so all functions have a single
        # authoritative source for dt / step / time in workflow-only mode.
        from src.simulation.clock import SimulationClock
        if 'clock' not in context:
            context['clock'] = SimulationClock(dt=dt_value, num_steps=total_steps)
        else:
            _clock = context['clock']
            _clock.dt = dt_value
            _clock.num_steps = total_steps

        # Also store flat keys so legacy code and run_workflow_mode can find them.
        context["dt"] = dt_value
        context["macrosteps"] = macrosteps_int
        context["steps_per_macrostep"] = steps_per_macro_int
        context["total_steps"] = total_steps

        if checkpoint_interval is not None:
            try:
                checkpoint_int = int(checkpoint_interval)
            except (TypeError, ValueError):
                checkpoint_int = 0
        else:
            checkpoint_int = 0

        if checkpoint_int > 0:
            context["checkpoint_interval"] = checkpoint_int

        if save_data_interval is not None:
            try:
                save_data_int = int(save_data_interval)
            except (TypeError, ValueError):
                save_data_int = 0
        else:
            save_data_int = 0

        if save_data_int > 0:
            context["save_data_interval"] = save_data_int

        # Keep existing config (if any) in sync so legacy code continues to work
        config = context.get("config")
        if config is not None and hasattr(config, "time"):
            try:
                config.time.dt = dt_value
                config.time.end_time = dt_value * float(total_steps)
            except Exception:
                # Be robust against partially initialised configs
                pass

        if config is not None and hasattr(config, "output"):
            try:
                if checkpoint_int > 0:
                    setattr(config.output, "save_cellstate_interval", checkpoint_int)
                if save_data_int > 0:
                    setattr(config.output, "save_data_interval", save_data_int)
            except Exception:
                pass

        print(
            f"   [+] dt={dt_value}, macrosteps={macrosteps_int}, "
            f"steps_per_macrostep={steps_per_macro_int}, total_steps={total_steps}"
        )
        if checkpoint_int > 0:
            print(f"   [+] checkpoint_interval={checkpoint_int} (physical steps)")
        if save_data_int > 0:
            print(f"   [+] save_data_interval={save_data_int} (physical steps)")

        return True

    except Exception as e:
        print(f"[WORKFLOW] Error configuring time / steps: {e}")
        import traceback
        traceback.print_exc()
        return False


# NOTE: load_cells_from_vtk and load_cells_from_csv are now imported from
# src/workflow/functions/initialization/ at the top of this file.
# The old definitions have been removed to avoid conflicts.


# ============================================================================
# INTRACELLULAR FUNCTIONS
# ============================================================================

# NOTE: Granular functions (update_metabolism, update_gene_networks, etc.) are now
# imported from src/workflow/functions/intracellular/ at the top of this file.
# They are in separate files for easy GUI viewing/editing.

# --- Monolithic Intracellular Function (for backward compatibility) ---


    # NOTE: Phenotype marking is now handled by separate marking functions:
    # - mark_necrotic_cells (based on O2/glucose thresholds)
    # - mark_growth_arrest_cells (based on gene network + counter)
    # - mark_apoptotic_cells (based on gene network)
    # - mark_proliferating_cells (based on gene network)
    # These should be called in the intercellular stage, not here.


# ============================================================================
# DIFFUSION FUNCTIONS
# ============================================================================

# NOTE: Granular function (run_diffusion_solver) is now imported from
# src/workflow/functions/diffusion/ at the top of this file.
# It is in a separate file for easy GUI viewing/editing.

# --- Monolithic Diffusion Function (for backward compatibility) ---

@register_function(
    display_name="Standard Diffusion Update",
    description="Standard diffusion update (run diffusion solver)",
    category="DIFFUSION",
    outputs=[],
    cloneable=False
)
def standard_diffusion_update(
    population,
    simulator,
    gene_network,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Standard diffusion update workflow function.

    This is the default behavior when no custom workflow is specified.
    Runs the diffusion solver with substance reactions from cells.

    Args:
        population: Population object
        simulator: Diffusion simulator
        gene_network: Gene network object
        config: Configuration object
        helpers: Dictionary of helper functions
    """
    # Run diffusion solver
    helpers['run_diffusion']()


# ============================================================================
# INTERCELLULAR FUNCTIONS
# ============================================================================

# NOTE: Granular functions (update_cell_division, update_cell_migration) are now
# imported from src/workflow/functions/intercellular/ at the top of this file.
# They are in separate files for easy GUI viewing/editing.

# --- Monolithic Intercellular Function (for backward compatibility) ---





def custom_diffusion_with_validation(
    population,
    simulator,
    gene_network,
    config,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Example custom diffusion function with validation.

    Shows how to add validation around diffusion.
    """
    # Get concentrations before
    conc_before = simulator.get_substance_concentrations()

    # Run diffusion
    helpers['run_diffusion']()

    # Get concentrations after
    conc_after = simulator.get_substance_concentrations()

    # Validate (example: check for negative concentrations)
    for substance_name, conc_field in conc_after.items():
        min_conc = conc_field.min()
        if min_conc < 0:
            print(f"[WARNING] Negative concentration detected for {substance_name}: {min_conc}")


    # NOTE: Phenotype marking now handled by separate functions in intercellular stage


    # NOTE: Cells are no longer removed - they remain in population but become inactive




def diffusion_with_boundary_check(
    simulator,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Diffusion update with boundary condition checking.

    Example showing how to monitor boundary conditions.
    """
    # Run diffusion
    helpers['run_diffusion']()

    # Check boundary conditions
    if step % 50 == 0:  # Every 50 steps
        conc = simulator.get_substance_concentrations()
        for substance_name, conc_field in conc.items():
            mean_conc = conc_field.mean()
            print(f"[BOUNDARY] Step {step} - {substance_name} mean: {mean_conc:.6f}")


# ============================================================================
# FINALIZATION FUNCTIONS
# ============================================================================

@register_function(
    display_name="Standard Data Collection",
    description="Collect final simulation statistics (population, substances, phenotypes)",
    category="FINALIZATION",
    outputs=[],
    cloneable=False
)
def standard_data_collection(
    population,
    simulator,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Standard data collection for finalization stage.

    Collects final statistics about the simulation:
    - Cell population statistics
    - Substance concentration statistics
    - Final state summary

    This should be called in the finalization stage of the workflow.
    """
    print("[STATS] Collecting final simulation data...")

    # Get final population statistics
    pop_stats = population.get_population_statistics()
    print(f"[STATS] Final cell count: {pop_stats.get('total_cells', 0)}")

    # Get final substance statistics
    substance_stats = simulator.get_summary_statistics()
    print(f"[STATS] Final substance statistics:")
    for substance_name, stats in substance_stats.items():
        print(f"  {substance_name}: mean={stats['mean']:.6f}, min={stats['min']:.6f}, max={stats['max']:.6f}")

    # Phenotype distribution
    if hasattr(population, 'cells'):
        phenotype_counts = {}
        for cell in population.cells.values():
            phenotype = cell.phenotype if hasattr(cell, 'phenotype') else 'unknown'
            phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1

        print(f"[STATS] Final phenotype distribution:")
        for phenotype, count in sorted(phenotype_counts.items()):
            print(f"  {phenotype}: {count} cells")


def export_final_state(
    population,
    simulator,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Export final simulation state.

    This can be used in the finalization stage to export the final state
    of the simulation for analysis or visualization.
    """
    print("[EXPORT] Exporting final simulation state...")

    # This would call the appropriate export functions
    # For now, just a placeholder showing the pattern
    # In the future, this could call helpers['export_final_state']()
    pass


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
        import json
        import numpy as np

        config = context['config']
        results = context.get('results', {})

        output_dir = config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save configuration
        if save_config:
            config_file = output_dir / "simulation_config.json"
            with open(config_file, 'w') as f:
                json.dump({
                    'domain': {
                        'nx': config.domain.nx,
                        'ny': config.domain.ny,
                        'size_x': config.domain.size_x.value,
                        'size_y': config.domain.size_y.value
                    },
                    'substances': list(config.substances.keys()),
                    'associations': config.associations,
                    'num_steps': len(results.get('time', [])),
                    'dt': results['time'][1] - results['time'][0] if len(results.get('time', [])) > 1 else 0
                }, f, indent=2)
            print(f"   [OK] Saved config to {config_file}")

        # Save time series data
        if save_timeseries and 'time' in results:
            np.save(output_dir / "time.npy", results['time'])
            print(f"   [OK] Saved time series data")

        # Save substance statistics
        if save_substances and 'substance_stats' in results:
            substance_data = {}
            for substance_name, stats in results['substance_stats'].items():
                substance_data[substance_name] = {
                    'mean': stats['mean'],
                    'min': stats['min'],
                    'max': stats['max']
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


# `print_simulation_summary` now lives in its own module —
# src/workflow/functions/finalization/print_simulation_summary.py (a richer
# version that also reports phenotype distribution). It was duplicated here,
# which collided on the function name; the modular version is canonical.


# =============================================================================
# IMPORT DECORATOR-BASED FUNCTIONS
# =============================================================================
# Import modules that contain decorated functions to trigger decorator execution
# This ensures decorator-based registrations are added to the registry
# Custom experiment functions can be imported here or via workflow configuration
