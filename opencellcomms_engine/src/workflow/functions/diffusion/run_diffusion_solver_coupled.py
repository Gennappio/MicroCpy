"""
Run the diffusion solver with iterative coupling (Picard iteration).

This solver uses iterative coupling between metabolism calculation and diffusion
solving to prevent negative concentrations. The key insight is that Michaelis-Menten
kinetics naturally reduce consumption as concentration approaches zero, but this
only works if metabolism is recalculated during the solve.

Algorithm (Picard iteration):
1. Calculate metabolism based on current concentrations
2. Solve steady-state diffusion with these reaction rates
3. Check convergence: if max(|new - old|) < tolerance, done
4. Apply under-relaxation: c_next = α * c_new + (1-α) * c_old
5. Repeat from step 1

Under-relaxation (0 < α < 1) improves stability by damping oscillations.
"""

from typing import Dict, Any, Tuple
import numpy as np
from src.workflow.decorators import register_function

# Global debug switch - set to True to enable detailed logging
DEBUG_COUPLED_SOLVER = True


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
            "default": 0.5,
            "min_value": 0.0
        },
        {
            "name": "glucose_conversion_factor",
            "type": "FLOAT",
            "description": "Glucose consumption conversion factor (multiplier)",
            "default": 100000.0,
            "min_value": 0.0
        },
        {
            "name": "lactate_conversion_factor",
            "type": "FLOAT",
            "description": "Lactate production conversion factor (multiplier)",
            "default": 5.0,
            "min_value": 0.0
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
    oxygen_conversion_factor: float = 0.5,
    glucose_conversion_factor: float = 1.0,
    lactate_conversion_factor: float = 5.0,
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
        **kwargs: Additional parameters

    Returns:
        None (modifies simulator state in-place)
    """
    simulator = context.get('simulator')
    population = context.get('population')
    config = context.get('config')

    if simulator is None:
        print("[run_diffusion_solver_coupled] No simulator in context - cannot run diffusion.")
        return

    if population is None:
        print("[run_diffusion_solver_coupled] No population - falling back to standard solver.")
        from src.workflow.functions.diffusion.run_diffusion_solver import run_diffusion_solver
        run_diffusion_solver(context, max_iterations, tolerance, solver_type, **kwargs)
        return

    if DEBUG_COUPLED_SOLVER:
        print(f"[COUPLED] Starting iterative coupling (max {max_coupling_iterations} iterations, "
              f"α={relaxation_factor}, tol={coupling_tolerance})")

    # Configure solver parameters
    if hasattr(simulator, 'set_solver_params'):
        simulator.set_solver_params(
            max_iterations=max_iterations,
            tolerance=tolerance,
            solver_type=solver_type
        )

    # Main coupling loop
    for coupling_iter in range(max_coupling_iterations):
        # Step 1: Store old concentrations for convergence check
        old_concentrations = _get_concentration_snapshot(simulator)

        # Step 2: Recalculate metabolism based on current concentrations
        _recalculate_metabolism(context, simulator, population, config,
                                oxygen_conversion_factor, glucose_conversion_factor, lactate_conversion_factor)

        # Step 3: Collect reaction terms and solve diffusion
        position_reactions = _collect_reactions_from_cells(population, simulator)
        simulator.update(position_reactions)

        # Step 4: Get new concentrations and check convergence
        new_concentrations = _get_concentration_snapshot(simulator)
        max_change = _compute_max_change(old_concentrations, new_concentrations)

        if DEBUG_COUPLED_SOLVER:
            print(f"[COUPLED] Iteration {coupling_iter + 1}: max change = {max_change:.4e}")
            if 'Oxygen' in simulator.state.substances:
                oxygen_conc = simulator.state.substances['Oxygen'].concentrations
                print(f"[COUPLED] Oxygen after iteration {coupling_iter + 1}: min={oxygen_conc.min():.6f}, max={oxygen_conc.max():.6f} mM")

        if max_change < coupling_tolerance:
            if DEBUG_COUPLED_SOLVER:
                print(f"[COUPLED] Converged after {coupling_iter + 1} iterations")
            break

        # Step 5: Apply under-relaxation (blend old and new)
        if relaxation_factor < 1.0 and coupling_iter < max_coupling_iterations - 1:
            _apply_relaxation(simulator, old_concentrations, new_concentrations, relaxation_factor)

    else:
        if DEBUG_COUPLED_SOLVER:
            print(f"[COUPLED] WARNING: Did not converge after {max_coupling_iterations} iterations "
                  f"(final max_change={max_change:.4e})")

    # Final check for any remaining negative values (safety clamp)
    _clamp_negative_concentrations(simulator)

    # Log population count at end
    if population is not None:
        final_count = len(population.state.cells)
        print(f"[COUPLED-END] Population count: {final_count} cells")


def _recalculate_metabolism(context: Dict[str, Any], simulator, population, config,
                           oxygen_conversion_factor: float = 0.5,
                           glucose_conversion_factor: float = 100000.0,
                           lactate_conversion_factor: float = 5.0) -> None:
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
        print(f"[COUPLED] Failed to get concentrations: {e}")
        return

    # DEBUG: Check what we got from get_substance_concentrations
    if DEBUG_COUPLED_SOLVER:
        oxygen_dict = substance_concentrations.get('Oxygen', {})
        print(f"[METABOLISM DEBUG] substance_concentrations keys: {list(substance_concentrations.keys())}")
        print(f"[METABOLISM DEBUG] Oxygen dict has {len(oxygen_dict)} entries")
        if oxygen_dict:
            sample_keys = list(oxygen_dict.keys())[:5]
            sample_values = [oxygen_dict[k] for k in sample_keys]
            print(f"[METABOLISM DEBUG] Sample Oxygen keys: {sample_keys}")
            print(f"[METABOLISM DEBUG] Sample Oxygen values: {sample_values}")

    # Get metabolism parameters from context
    custom_params = context.get('custom_parameters', {})
    vmax_oxygen = custom_params.get('oxygen_vmax', 1.0e-16)
    vmax_glucose = custom_params.get('glucose_vmax', 3.0e-15)
    km_oxygen = custom_params.get('KO2', 0.01)
    km_glucose = custom_params.get('KG', 0.5)
    km_lactate = custom_params.get('KL', 1.0)
    max_atp = custom_params.get('max_atp', 30.0)
    proton_coeff = custom_params.get('proton_coefficient', 0.01)

    # Get grid parameters for coordinate conversion
    cell_size_um = 20.0  # Default cell size
    if config and hasattr(config, 'domain'):
        domain = config.domain
        grid_spacing_x = domain.size_x.micrometers / domain.nx
        grid_spacing_y = domain.size_y.micrometers / domain.ny
        if DEBUG_COUPLED_SOLVER:
            print(f"[METABOLISM DEBUG] Domain: {domain.size_x.micrometers}x{domain.size_y.micrometers} μm, grid: {domain.nx}x{domain.ny}")
            print(f"[METABOLISM DEBUG] Grid spacing: {grid_spacing_x}x{grid_spacing_y} μm, cell_size: {cell_size_um} μm")
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

        # Get cell position and convert to grid coordinates
        cell_x, cell_y = cell.state.position
        phys_x = cell_x * cell_size_um
        phys_y = cell_y * cell_size_um
        grid_x = int(phys_x / grid_spacing_x)
        grid_y = int(phys_y / grid_spacing_y)

        # Clamp to valid grid bounds
        if config and hasattr(config, 'domain'):
            grid_x = max(0, min(config.domain.nx - 1, grid_x))
            grid_y = max(0, min(config.domain.ny - 1, grid_y))

        # DEBUG: Log first cell's coordinate conversion
        if DEBUG_COUPLED_SOLVER and not debug_first_cell_logged:
            oxygen_dict = substance_concentrations.get('Oxygen', {})
            lookup_result = oxygen_dict.get((grid_x, grid_y), "NOT_FOUND")
            print(f"[METABOLISM DEBUG] First cell: pos=({cell_x}, {cell_y}), phys=({phys_x}, {phys_y}) μm, grid=({grid_x}, {grid_y})")
            print(f"[METABOLISM DEBUG] Lookup (grid_x, grid_y)=({grid_x}, {grid_y}) -> {lookup_result}")
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
            oxygen_consumption += 50*vmax_oxygen * oxygen_mm
            glucose_consumption += (vmax_oxygen / 6.0) * glucose_mm * oxygen_mm
            lactate_consumption += (vmax_oxygen * 2.0 / 6.0) * lactate_mm * oxygen_mm

        if glyco_atp:
            glucose_consumption_glyco = (vmax_glucose / 6.0) * glucose_mm * max(0.1, oxygen_mm)
            glucose_consumption += glucose_consumption_glyco
            lactate_production += glucose_consumption_glyco * 3.0

        debug_total_oxygen_consumption += oxygen_consumption
        debug_max_oxygen_consumption = max(debug_max_oxygen_consumption, oxygen_consumption)

        # DEBUG: Track glucose consumption for first few cells
        if DEBUG_COUPLED_SOLVER and debug_cells_processed < 5:
            print(f"[GLUCOSE DEBUG] Cell {debug_cells_processed}: glucose_consumption={glucose_consumption:.2e}, glucose_mm={glucose_mm:.4f}, local_glucose={local_glucose:.4f}")

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
    if DEBUG_COUPLED_SOLVER:
        avg_local_oxygen = debug_total_local_oxygen / debug_cells_processed if debug_cells_processed > 0 else 0
        total_glucose_consumption = sum([c.state.metabolic_state.get('glucose_consumption', 0.0) for c in population.state.cells.values()])
        print(f"[METABOLISM] Cells processed: {debug_cells_processed}")
        print(f"[METABOLISM] Cells with mitoATP=True: {debug_cells_with_mito}")
        print(f"[METABOLISM] Cells with glycoATP=True: {debug_cells_with_glyco}")
        print(f"[METABOLISM] Cells with zero local oxygen: {debug_cells_with_zero_oxygen}")
        print(f"[METABOLISM] Avg local oxygen: {avg_local_oxygen:.6f} mM")
        print(f"[METABOLISM] vmax_oxygen: {vmax_oxygen:.2e}, km_oxygen: {km_oxygen:.4f}")
        print(f"[METABOLISM] vmax_glucose: {vmax_glucose:.2e}, km_glucose: {km_glucose:.4f}")
        print(f"[METABOLISM] Total oxygen consumption: {debug_total_oxygen_consumption:.2e} mol/s")
        print(f"[METABOLISM] Max oxygen consumption (single cell): {debug_max_oxygen_consumption:.2e} mol/s")
        print(f"[METABOLISM] Total glucose consumption: {total_glucose_consumption:.2e} mol/s")


def _collect_reactions_from_cells(population, simulator) -> Dict[Tuple[float, float], Dict[str, float]]:
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
    if DEBUG_COUPLED_SOLVER:
        print(f"[REACTIONS] Total cells: {total_cells}")
        print(f"[REACTIONS] Cells with metabolic_state: {cells_with_metabolic_state}")
        print(f"[REACTIONS] Cells with oxygen_consumption > 0: {cells_with_oxygen_consumption}")
        print(f"[REACTIONS] Total oxygen consumption: {total_oxygen_consumption:.2e} mol/s")
        print(f"[REACTIONS] Max oxygen consumption (single cell): {max_oxygen_consumption:.2e} mol/s")
        print(f"[REACTIONS] Unique positions with reactions: {len(position_reactions)}")

    return position_reactions


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


def _clamp_negative_concentrations(simulator) -> None:
    """Clamp any remaining negative concentrations to zero (safety net)."""
    for name, substance_state in simulator.state.substances.items():
        concentrations = substance_state.concentrations
        negative_mask = concentrations < 0
        num_negative = np.sum(negative_mask)

        if num_negative > 0:
            min_val = np.min(concentrations[negative_mask])
            substance_state.concentrations = np.maximum(concentrations, 0.0)
            if DEBUG_COUPLED_SOLVER:
                print(f"[COUPLED] Safety clamp: {name} had {num_negative} negative values "
                      f"(min={min_val:.4e})")

            if hasattr(simulator, 'fipy_variables') and name in simulator.fipy_variables:
                simulator.fipy_variables[name].setValue(
                    substance_state.concentrations.flatten(order='F')
                )

