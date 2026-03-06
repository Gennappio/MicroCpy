"""
Run the diffusion solver with iterative coupling (Picard iteration).

This solver uses iterative coupling between metabolism calculation and diffusion
solving to prevent negative concentrations. The key insight is that Michaelis-Menten
kinetics naturally reduce consumption as concentration approaches zero, but this
only works if metabolism is recalculated during the solve.

Algorithm (Picard iteration with reaction-term under-relaxation):
1. Calculate metabolism based on current concentrations
2. Collect reaction terms from cells
3. Blend reaction terms: r_next = α * r_new + (1-α) * r_old
4. Solve steady-state diffusion with blended reaction rates
5. Check convergence: if max(|new - old|) < tolerance, done
6. Repeat from step 1

Under-relaxation (0 < α < 1) is applied to source/reaction terms rather than
concentrations. This is the standard Picard fix for oscillatory instability
in coupled PDE-ODE systems.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig
from src.workflow.logging import log, log_always

# Global debug switch - DEPRECATED: Use verbose parameter instead
DEBUG_COUPLED_SOLVER = False


@register_function(
    display_name="Run Diffusion Solver (Coupled)",
    description="Solve diffusion PDE with iterative coupling to prevent negative concentrations",
    category="DIFFUSION",
    parameters=[
        {
            "name": "max_iterations",
            "type": "INT",
            "description": "Maximum FiPy solver iterations per coupling step",
            "default": 1000,
            "min_value": 1
        },
        {
            "name": "tolerance",
            "type": "FLOAT",
            "description": "FiPy solver convergence tolerance",
            "default": 1e-6,
            "min_value": 0.0
        },
        {
            "name": "solver_type",
            "type": "STRING",
            "description": "Solver type",
            "default": "steady_state",
            "options": ["steady_state", "transient"]
        },
        {
            "name": "max_coupling_iterations",
            "type": "INT",
            "description": "Maximum Picard coupling iterations",
            "default": 10,
            "min_value": 1
        },
        {
            "name": "coupling_tolerance",
            "type": "FLOAT",
            "description": "Convergence tolerance for coupling (max concentration change)",
            "default": 1e-4,
            "min_value": 0.0
        },
        {
            "name": "relaxation_factor",
            "type": "FLOAT",
            "description": "Under-relaxation factor (0 < α ≤ 1). Lower = more stable, slower",
            "default": 0.7,
            "min_value": 0.1,
            "max_value": 1.0
        },
        {
            "name": "oxygen_conversion_factor",
            "type": "FLOAT",
            "description": "Oxygen consumption conversion factor (multiplier)",
            "default": 1.0,
            "min_value": 0.0
        },
        {
            "name": "glucose_conversion_factor",
            "type": "FLOAT",
            "description": "Glucose consumption conversion factor (multiplier)",
            "default": 1.0,
            "min_value": 0.0
        },
        {
            "name": "lactate_conversion_factor",
            "type": "FLOAT",
            "description": "Lactate production conversion factor (multiplier)",
            "default": 1.0,
            "min_value": 0.0
        },
        {
            "name": "oxygen_consumption_multiplier",
            "type": "FLOAT",
            "description": "Multiplier for mitoATP oxygen consumption (replaces hardcoded 50x)",
            "default": 1.0,
            "min_value": 0.0
        },
        {
            "name": "verbose",
            "type": "BOOL",
            "description": "Enable detailed logging (None = use global setting)",
            "default": None
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def run_diffusion_solver_coupled(
    context: Dict[str, Any],
    max_iterations: int = 1000,
    tolerance: float = 1e-6,
    solver_type: str = "steady_state",
    max_coupling_iterations: int = 10,
    coupling_tolerance: float = 1e-4,
    relaxation_factor: float = 0.7,
    oxygen_conversion_factor: float = 1.0,
    glucose_conversion_factor: float = 1.0,
    lactate_conversion_factor: float = 1.0,
    oxygen_consumption_multiplier: float = 1.0,
    verbose: Optional[bool] = None,
    **kwargs
) -> None:
    """
    Run the diffusion solver with iterative coupling (Picard iteration).

    This function iterates between:
    1. Recalculating cell metabolism based on current concentrations
    2. Solving the diffusion-reaction PDE

    This prevents negative concentrations because Michaelis-Menten kinetics
    naturally reduce consumption as concentration approaches zero.

    Args:
        context: Workflow execution context
        max_iterations: Maximum FiPy solver iterations per coupling step
        tolerance: FiPy solver convergence tolerance
        solver_type: Type of solver - "steady_state" or "transient"
        max_coupling_iterations: Maximum Picard coupling iterations
        coupling_tolerance: Convergence tolerance for coupling
        relaxation_factor: Under-relaxation factor (0 < α ≤ 1)
        oxygen_conversion_factor: Multiplier for oxygen consumption rates
        glucose_conversion_factor: Multiplier for glucose consumption rates
        lactate_conversion_factor: Multiplier for lactate production rates
        oxygen_consumption_multiplier: Multiplier for mitoATP oxygen consumption rate
        verbose: Enable detailed logging (None = use global setting)
        **kwargs: Additional parameters

    Returns:
        None (modifies simulator state in-place)
    """
    simulator = context.get('simulator')
    population = context.get('population')
    config: Optional[IConfig] = context.get('config')

    if simulator is None:
        log_always("[run_diffusion_solver_coupled] No simulator in context - cannot run diffusion.")
        return

    if population is None:
        log_always("[run_diffusion_solver_coupled] No population - falling back to standard solver.")
        from src.workflow.functions.diffusion.run_diffusion_solver import run_diffusion_solver
        run_diffusion_solver(context, max_iterations, tolerance, solver_type, **kwargs)
        return

    log_always(f"Starting iterative coupling (max {max_coupling_iterations} iterations, "
               f"α={relaxation_factor}, tol={coupling_tolerance})",
        prefix="[COUPLED]")

    # Configure solver parameters
    if hasattr(simulator, 'set_solver_params'):
        simulator.set_solver_params(
            max_iterations=max_iterations,
            tolerance=tolerance,
            solver_type=solver_type
        )

    # Main coupling loop with reaction-term under-relaxation
    old_reactions = None

    for coupling_iter in range(max_coupling_iterations):
        # Step 1: Store old concentrations for convergence check
        old_concentrations = _get_concentration_snapshot(simulator)

        # Step 2: Recalculate metabolism based on current concentrations
        _recalculate_metabolism(context, simulator, population, config,
                                oxygen_conversion_factor, glucose_conversion_factor, lactate_conversion_factor,
                                oxygen_consumption_multiplier=oxygen_consumption_multiplier,
                                verbose=verbose)

        # Step 3: Collect reaction terms from cells
        new_reactions = _collect_reactions_from_cells(population, simulator, context, verbose=verbose)

        # Step 4: Blend reaction terms (under-relaxation on source terms)
        if old_reactions is not None and relaxation_factor < 1.0:
            position_reactions = _blend_reactions(old_reactions, new_reactions, relaxation_factor)
            log_always(f"Blended reaction terms with α={relaxation_factor}",
                prefix="[COUPLED]")
        else:
            position_reactions = new_reactions
        old_reactions = new_reactions  # store unblended for next iteration

        # Step 5: Solve diffusion with (blended) reaction terms
        simulator.update(position_reactions)

        # Step 5b: Clamp negatives before convergence check (prevents unphysical state propagation)
        _clamp_negative_concentrations(simulator, context, verbose=verbose)

        # Step 6: Get new concentrations and check convergence
        new_concentrations = _get_concentration_snapshot(simulator)
        max_change = _compute_max_change(old_concentrations, new_concentrations)

        log_always(f"Iteration {coupling_iter + 1}: max change = {max_change:.4e}",
            prefix="[COUPLED]")
        if 'Oxygen' in simulator.state.substances:
            oxygen_conc = simulator.state.substances['Oxygen'].concentrations
            log_always(f"Oxygen after iteration {coupling_iter + 1}: min={oxygen_conc.min():.6f}, max={oxygen_conc.max():.6f} mM",
                prefix="[COUPLED]")

        if max_change < coupling_tolerance:
            log_always(f"Converged after {coupling_iter + 1} iterations",
                prefix="[COUPLED]")
            break

        # Step 7: Apply concentration relaxation if not converged (belt and suspenders)
        if relaxation_factor < 1.0 and coupling_iter < max_coupling_iterations - 1:
            _apply_relaxation(simulator, old_concentrations, new_concentrations, relaxation_factor)
            log_always(f"Applied concentration relaxation (α={relaxation_factor})",
                prefix="[COUPLED]")

    else:
        log_always(f"WARNING: Did not converge after {max_coupling_iterations} iterations "
                   f"(final max_change={max_change:.4e})",
            prefix="[COUPLED]")

    # Final check for any remaining negative values (safety clamp)
    _clamp_negative_concentrations(simulator, context, verbose=verbose)

    # Log population count at end
    if population is not None:
        final_count = len(population.state.cells)
        log_always(f"Population count: {final_count} cells", prefix="[COUPLED-END]")


def _recalculate_metabolism(context: Dict[str, Any], simulator, population, config,
                           oxygen_conversion_factor: float = 1.0,
                           glucose_conversion_factor: float = 1.0,
                           lactate_conversion_factor: float = 1.0,
                           oxygen_consumption_multiplier: float = 1.0,
                           verbose: Optional[bool] = None) -> None:
    """
    Recalculate cell metabolism based on current concentrations.

    This is the key step in iterative coupling - we update the metabolic rates
    using the current (possibly updated) concentration field, so that
    Michaelis-Menten kinetics can naturally reduce consumption as concentrations
    approach zero.

    Args:
        context: Workflow execution context
        simulator: Diffusion simulator
        population: Cell population
        config: Configuration object
        oxygen_conversion_factor: Multiplier for oxygen consumption
        glucose_conversion_factor: Multiplier for glucose consumption
        lactate_conversion_factor: Multiplier for lactate production
    """
    # Get current concentrations from simulator
    try:
        substance_concentrations = simulator.get_substance_concentrations()
    except Exception as e:
        log_always(f"Failed to get concentrations: {e}", prefix="[COUPLED]")
        return

    # DEBUG: Check what we got from get_substance_concentrations
    oxygen_dict = substance_concentrations.get('Oxygen', {})
    log(context, f"substance_concentrations keys: {list(substance_concentrations.keys())}",
        prefix="[METABOLISM DEBUG]", node_verbose=verbose)
    log(context, f"Oxygen dict has {len(oxygen_dict)} entries",
        prefix="[METABOLISM DEBUG]", node_verbose=verbose)
    if oxygen_dict:
        sample_keys = list(oxygen_dict.keys())[:5]
        sample_values = [oxygen_dict[k] for k in sample_keys]
        log(context, f"Sample Oxygen keys: {sample_keys}",
            prefix="[METABOLISM DEBUG]", node_verbose=verbose)
        log(context, f"Sample Oxygen values: {sample_values}",
            prefix="[METABOLISM DEBUG]", node_verbose=verbose)

    # Get metabolism parameters from context
    custom_params = context.get('custom_parameters', {})
    vmax_oxygen = custom_params.get('oxygen_vmax', 3.0e-17)   # NetLogo: 3.0e-17 mol/s/cell
    vmax_glucose = custom_params.get('glucose_vmax', 3.0e-15)
    km_oxygen = custom_params.get('KO2', 0.005)              # NetLogo: the-optimal-oxygen = 0.005 mM
    km_glucose = custom_params.get('KG', 0.5)
    km_lactate = custom_params.get('KL', 1.0)
    max_atp = custom_params.get('max_atp', 30.0)
    proton_coeff = custom_params.get('proton_coefficient', 0.01)
    glyco_oxygen_ratio = custom_params.get('glyco_oxygen_ratio', 0.5)

    # Get grid parameters for coordinate conversion
    cell_size_um = 20.0  # Default cell size
    if config and hasattr(config, 'domain'):
        domain = config.domain
        grid_spacing_x = domain.size_x.micrometers / domain.nx
        grid_spacing_y = domain.size_y.micrometers / domain.ny
        log(context, f"Domain: {domain.size_x.micrometers}x{domain.size_y.micrometers} μm, grid: {domain.nx}x{domain.ny}",
            prefix="[METABOLISM DEBUG]", node_verbose=verbose)
        log(context, f"Grid spacing: {grid_spacing_x}x{grid_spacing_y} μm, cell_size: {cell_size_um} μm",
            prefix="[METABOLISM DEBUG]", node_verbose=verbose)
    else:
        grid_spacing_x = grid_spacing_y = 30.0  # Default

    # DEBUG: Track metabolism statistics
    debug_cells_processed = 0
    debug_cells_with_mito = 0
    debug_cells_with_glyco = 0
    debug_total_oxygen_consumption = 0.0
    debug_max_oxygen_consumption = 0.0
    debug_total_local_oxygen = 0.0
    debug_cells_with_zero_oxygen = 0
    debug_first_cell_logged = False

    # CRITICAL: Collect updated cells to write back to population
    updated_cells = {}

    # Update metabolism for each cell
    for cell_id, cell in population.state.cells.items():
        # Skip inactive cells
        phenotype = cell.state.phenotype
        # Handle both string phenotypes and Phenotype objects with .name attribute
        phenotype_name = phenotype.name if hasattr(phenotype, 'name') else str(phenotype) if phenotype else None
        if phenotype_name in ['Necrosis', 'Growth_Arrest']:
            updated_cells[cell_id] = cell
            continue

        debug_cells_processed += 1

        # Get cell position and convert to grid coordinates (support both 2D and 3D)
        if len(cell.state.position) == 2:
            cell_x, cell_y = cell.state.position
        else:
            cell_x, cell_y, _ = cell.state.position  # 3D: extract x, y, ignore z
        phys_x = cell_x * cell_size_um
        phys_y = cell_y * cell_size_um
        grid_x = int(phys_x / grid_spacing_x)
        grid_y = int(phys_y / grid_spacing_y)

        # Clamp to valid grid bounds
        if config and hasattr(config, 'domain'):
            grid_x = max(0, min(config.domain.nx - 1, grid_x))
            grid_y = max(0, min(config.domain.ny - 1, grid_y))

        # DEBUG: Log first cell's coordinate conversion
        if not debug_first_cell_logged:
            oxygen_dict = substance_concentrations.get('Oxygen', {})
            lookup_result = oxygen_dict.get((grid_x, grid_y), "NOT_FOUND")
            log(context, f"First cell: pos=({cell_x}, {cell_y}), phys=({phys_x}, {phys_y}) μm, grid=({grid_x}, {grid_y})",
                prefix="[METABOLISM DEBUG]", node_verbose=verbose)
            log(context, f"Lookup (grid_x, grid_y)=({grid_x}, {grid_y}) -> {lookup_result}",
                prefix="[METABOLISM DEBUG]", node_verbose=verbose)
            debug_first_cell_logged = True

        # Get local concentrations (clamped to non-negative)
        local_oxygen = max(0.0, substance_concentrations.get('Oxygen', {}).get((grid_x, grid_y), 0.0))
        local_glucose = max(0.0, substance_concentrations.get('Glucose', {}).get((grid_x, grid_y), 0.0))
        local_lactate = max(0.0, substance_concentrations.get('Lactate', {}).get((grid_x, grid_y), 0.0))

        debug_total_local_oxygen += local_oxygen
        if local_oxygen == 0.0:
            debug_cells_with_zero_oxygen += 1

        # Get gene states
        gene_states = cell.state.gene_states or {}
        mito_atp = gene_states.get('mitoATP', False)
        glyco_atp = gene_states.get('glycoATP', False)

        if mito_atp:
            debug_cells_with_mito += 1
        if glyco_atp:
            debug_cells_with_glyco += 1

        # Calculate Michaelis-Menten terms
        oxygen_mm = local_oxygen / (km_oxygen + local_oxygen) if (km_oxygen + local_oxygen) > 0 else 0
        glucose_mm = local_glucose / (km_glucose + local_glucose) if (km_glucose + local_glucose) > 0 else 0
        lactate_mm = local_lactate / (km_lactate + local_lactate) if (km_lactate + local_lactate) > 0 else 0

        # Calculate consumption/production rates
        oxygen_consumption = 0.0
        glucose_consumption = 0.0
        lactate_production = 0.0
        lactate_consumption = 0.0

        if mito_atp:
            oxygen_consumption += vmax_oxygen * oxygen_consumption_multiplier * oxygen_mm
            glucose_consumption += (vmax_oxygen / 6.0) * glucose_mm * oxygen_mm
            lactate_consumption += (vmax_oxygen * 2.0 / 6.0) * lactate_mm * oxygen_mm

        if glyco_atp:
            oxygen_consumption += vmax_oxygen * glyco_oxygen_ratio * oxygen_mm
            glucose_consumption_glyco = (vmax_oxygen / 6.0) * (max_atp / 2.0) * glucose_mm
            glucose_consumption += glucose_consumption_glyco
            lactate_production += glucose_consumption_glyco * 3.0

        debug_total_oxygen_consumption += oxygen_consumption
        debug_max_oxygen_consumption = max(debug_max_oxygen_consumption, oxygen_consumption)

        # DEBUG: Track glucose consumption for first few cells
        if debug_cells_processed < 5:
            log(context, f"Cell {debug_cells_processed}: glucose_consumption={glucose_consumption:.2e}, glucose_mm={glucose_mm:.4f}, local_glucose={local_glucose:.4f}",
                prefix="[GLUCOSE DEBUG]", node_verbose=verbose)

        # Update cell's metabolic state
        new_metabolic_state = {
            'oxygen_consumption': oxygen_consumption*oxygen_conversion_factor,
            'glucose_consumption': glucose_consumption*glucose_conversion_factor,
            'lactate_production': lactate_production*lactate_conversion_factor,
            'lactate_consumption': lactate_consumption,
        }

        # Update cell state
        cell.state = cell.state.with_updates(metabolic_state=new_metabolic_state)

        # CRITICAL: Store updated cell to write back to population
        updated_cells[cell_id] = cell

    # CRITICAL: Update population state with modified cells
    population.state = population.state.with_updates(cells=updated_cells)

    # Print metabolism debug summary
    avg_local_oxygen = debug_total_local_oxygen / debug_cells_processed if debug_cells_processed > 0 else 0
    total_glucose_consumption = sum([c.state.metabolic_state.get('glucose_consumption', 0.0) for c in population.state.cells.values()])
    log(context, f"Cells processed: {debug_cells_processed}", prefix="[METABOLISM]", node_verbose=verbose)
    log(context, f"Cells with mitoATP=True: {debug_cells_with_mito}", prefix="[METABOLISM]", node_verbose=verbose)
    log(context, f"Cells with glycoATP=True: {debug_cells_with_glyco}", prefix="[METABOLISM]", node_verbose=verbose)
    log(context, f"Cells with zero local oxygen: {debug_cells_with_zero_oxygen}", prefix="[METABOLISM]", node_verbose=verbose)
    log(context, f"Avg local oxygen: {avg_local_oxygen:.6f} mM", prefix="[METABOLISM]", node_verbose=verbose)
    log(context, f"vmax_oxygen: {vmax_oxygen:.2e}, km_oxygen: {km_oxygen:.4f}", prefix="[METABOLISM]", node_verbose=verbose)
    log(context, f"vmax_glucose: {vmax_glucose:.2e}, km_glucose: {km_glucose:.4f}", prefix="[METABOLISM]", node_verbose=verbose)
    log(context, f"Total oxygen consumption: {debug_total_oxygen_consumption:.2e} mol/s", prefix="[METABOLISM]", node_verbose=verbose)
    log(context, f"Max oxygen consumption (single cell): {debug_max_oxygen_consumption:.2e} mol/s", prefix="[METABOLISM]", node_verbose=verbose)
    log(context, f"Total glucose consumption: {total_glucose_consumption:.2e} mol/s", prefix="[METABOLISM]", node_verbose=verbose)


def _collect_reactions_from_cells(population, simulator, context: Dict[str, Any], verbose: Optional[bool] = None) -> Dict[Tuple[float, float], Dict[str, float]]:
    """Collect reaction terms from all cells based on their metabolic state."""
    position_reactions = {}

    # DEBUG counters
    total_cells = 0
    cells_with_metabolic_state = 0
    cells_with_oxygen_consumption = 0
    max_oxygen_consumption = 0.0
    total_oxygen_consumption = 0.0

    for _, cell in population.state.cells.items():
        total_cells += 1
        position = cell.state.position
        metabolic_state = cell.state.metabolic_state

        if not metabolic_state:
            continue

        cells_with_metabolic_state += 1

        if position not in position_reactions:
            position_reactions[position] = {}

        # Build reactions from metabolic state
        oxygen_consumption = metabolic_state.get('oxygen_consumption', 0.0)
        position_reactions[position]['Oxygen'] = -oxygen_consumption
        position_reactions[position]['Glucose'] = -metabolic_state.get('glucose_consumption', 0.0)
        position_reactions[position]['Lactate'] = (
            metabolic_state.get('lactate_production', 0.0) -
            metabolic_state.get('lactate_consumption', 0.0)
        )

        if oxygen_consumption > 0:
            cells_with_oxygen_consumption += 1
            max_oxygen_consumption = max(max_oxygen_consumption, oxygen_consumption)
            total_oxygen_consumption += oxygen_consumption

    # DEBUG output
    log(context, f"Total cells: {total_cells}", prefix="[REACTIONS]", node_verbose=verbose)
    log(context, f"Cells with metabolic_state: {cells_with_metabolic_state}", prefix="[REACTIONS]", node_verbose=verbose)
    log(context, f"Cells with oxygen_consumption > 0: {cells_with_oxygen_consumption}", prefix="[REACTIONS]", node_verbose=verbose)
    log(context, f"Total oxygen consumption: {total_oxygen_consumption:.2e} mol/s", prefix="[REACTIONS]", node_verbose=verbose)
    log(context, f"Max oxygen consumption (single cell): {max_oxygen_consumption:.2e} mol/s", prefix="[REACTIONS]", node_verbose=verbose)
    log(context, f"Unique positions with reactions: {len(position_reactions)}", prefix="[REACTIONS]", node_verbose=verbose)

    return position_reactions


def _blend_reactions(
    old_reactions: Dict[Tuple, Dict[str, float]],
    new_reactions: Dict[Tuple, Dict[str, float]],
    alpha: float
) -> Dict[Tuple, Dict[str, float]]:
    """Blend reaction terms: blended = α * new + (1-α) * old.

    Positions only in new (new cells) use new values directly.
    Positions only in old (removed cells) are dropped.
    """
    blended = {}

    for pos, new_subs in new_reactions.items():
        if pos in old_reactions:
            old_subs = old_reactions[pos]
            blended[pos] = {}
            # Blend substances present in both
            all_substances = set(new_subs.keys()) | set(old_subs.keys())
            for sub in all_substances:
                new_val = new_subs.get(sub, 0.0)
                old_val = old_subs.get(sub, 0.0)
                blended[pos][sub] = alpha * new_val + (1 - alpha) * old_val
        else:
            # New position (new cell) — use new values directly
            blended[pos] = dict(new_subs)

    return blended


def _get_concentration_snapshot(simulator) -> Dict[str, np.ndarray]:
    """Get a snapshot of all concentration fields."""
    snapshot = {}
    for name, substance_state in simulator.state.substances.items():
        snapshot[name] = substance_state.concentrations.copy()
    return snapshot


def _compute_max_change(old: Dict[str, np.ndarray], new: Dict[str, np.ndarray]) -> float:
    """Compute maximum absolute change between two concentration snapshots."""
    max_change = 0.0
    for name in old:
        if name in new:
            change = np.max(np.abs(new[name] - old[name]))
            max_change = max(max_change, change)
    return max_change


def _apply_relaxation(simulator, old: Dict[str, np.ndarray], new: Dict[str, np.ndarray],
                      alpha: float) -> None:
    """Apply under-relaxation: c_next = α * c_new + (1-α) * c_old.

    CRITICAL: Clamp negative values to zero before blending to prevent
    numerical instability from propagating across iterations.
    """
    for name, substance_state in simulator.state.substances.items():
        if name in old and name in new:
            # CRITICAL FIX: Clamp both old and new to non-negative before blending
            # This prevents garbage negative values from propagating
            old_clamped = np.maximum(old[name], 0.0)
            new_clamped = np.maximum(new[name], 0.0)

            blended = alpha * new_clamped + (1 - alpha) * old_clamped

            # Extra safety: clamp the result too
            blended = np.maximum(blended, 0.0)

            substance_state.concentrations = blended

            # Update FiPy variable if it exists
            if hasattr(simulator, 'fipy_variables') and name in simulator.fipy_variables:
                simulator.fipy_variables[name].setValue(blended.flatten(order='F'))


def _clamp_negative_concentrations(simulator, context: Dict[str, Any], verbose: Optional[bool] = None) -> None:
    """Clamp any remaining negative concentrations to zero (safety net)."""
    for name, substance_state in simulator.state.substances.items():
        concentrations = substance_state.concentrations
        negative_mask = concentrations < 0
        num_negative = np.sum(negative_mask)

        if num_negative > 0:
            min_val = np.min(concentrations[negative_mask])
            substance_state.concentrations = np.maximum(concentrations, 0.0)
            log(context, f"Safety clamp: {name} had {num_negative} negative values (min={min_val:.4e})",
                prefix="[COUPLED]", node_verbose=verbose)

            if hasattr(simulator, 'fipy_variables') and name in simulator.fipy_variables:
                simulator.fipy_variables[name].setValue(
                    substance_state.concentrations.flatten(order='F')
                )

