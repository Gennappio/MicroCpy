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
        _recalculate_metabolism(context, simulator, population, config)

        # Step 3: Collect reaction terms and solve diffusion
        position_reactions = _collect_reactions_from_cells(population, simulator)
        simulator.update(position_reactions)

        # Step 4: Get new concentrations and check convergence
        new_concentrations = _get_concentration_snapshot(simulator)
        max_change = _compute_max_change(old_concentrations, new_concentrations)

        print(f"[COUPLED] Iteration {coupling_iter + 1}: max change = {max_change:.4e}")

        if max_change < coupling_tolerance:
            print(f"[COUPLED] Converged after {coupling_iter + 1} iterations")
            break

        # Step 5: Apply under-relaxation (blend old and new)
        if relaxation_factor < 1.0 and coupling_iter < max_coupling_iterations - 1:
            _apply_relaxation(simulator, old_concentrations, new_concentrations, relaxation_factor)

    else:
        print(f"[COUPLED] WARNING: Did not converge after {max_coupling_iterations} iterations "
              f"(final max_change={max_change:.4e})")

    # Final check for any remaining negative values (safety clamp)
    _clamp_negative_concentrations(simulator)


def _recalculate_metabolism(context: Dict[str, Any], simulator, population, config) -> None:
    """
    Recalculate cell metabolism based on current concentrations.

    This is the key step in iterative coupling - we update the metabolic rates
    using the current (possibly updated) concentration field, so that
    Michaelis-Menten kinetics can naturally reduce consumption as concentrations
    approach zero.
    """
    # Get current concentrations from simulator
    try:
        substance_concentrations = simulator.get_substance_concentrations()
    except Exception as e:
        print(f"[COUPLED] Failed to get concentrations: {e}")
        return

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
    else:
        grid_spacing_x = grid_spacing_y = 30.0  # Default

    # Update metabolism for each cell
    for cell_id, cell in population.state.cells.items():
        # Skip inactive cells
        phenotype = cell.state.phenotype
        # Handle both string phenotypes and Phenotype objects with .name attribute
        phenotype_name = phenotype.name if hasattr(phenotype, 'name') else str(phenotype) if phenotype else None
        if phenotype_name in ['Necrosis', 'Growth_Arrest']:
            continue

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

        # Get local concentrations (clamped to non-negative)
        local_oxygen = max(0.0, substance_concentrations.get('Oxygen', {}).get((grid_x, grid_y), 0.0))
        local_glucose = max(0.0, substance_concentrations.get('Glucose', {}).get((grid_x, grid_y), 0.0))
        local_lactate = max(0.0, substance_concentrations.get('Lactate', {}).get((grid_x, grid_y), 0.0))

        # Get gene states
        gene_states = cell.state.gene_states or {}
        mito_atp = gene_states.get('mitoATP', False)
        glyco_atp = gene_states.get('glycoATP', False)

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
            oxygen_consumption += vmax_oxygen * oxygen_mm
            glucose_consumption += (vmax_oxygen / 6.0) * glucose_mm * oxygen_mm
            lactate_consumption += (vmax_oxygen * 2.0 / 6.0) * lactate_mm * oxygen_mm

        if glyco_atp:
            glucose_consumption_glyco = (vmax_glucose / 6.0) * glucose_mm * max(0.1, oxygen_mm)
            glucose_consumption += glucose_consumption_glyco
            lactate_production += glucose_consumption_glyco * 3.0

        # Update cell's metabolic state
        new_metabolic_state = {
            'oxygen_consumption': oxygen_consumption,
            'glucose_consumption': glucose_consumption,
            'lactate_production': lactate_production,
            'lactate_consumption': lactate_consumption,
            'Oxygen_consumption': oxygen_consumption,
            'Glucose_consumption': glucose_consumption,
            'Lactate_production': lactate_production,
            'Lactate_consumption': lactate_consumption,
        }

        # Update cell state
        cell.state = cell.state.with_updates(metabolic_state=new_metabolic_state)


def _collect_reactions_from_cells(population, simulator) -> Dict[Tuple[float, float], Dict[str, float]]:
    """Collect reaction terms from all cells based on their metabolic state."""
    position_reactions = {}

    for cell_id, cell in population.state.cells.items():
        position = cell.state.position
        metabolic_state = cell.state.metabolic_state

        if not metabolic_state:
            continue

        if position not in position_reactions:
            position_reactions[position] = {}

        # Build reactions from metabolic state
        position_reactions[position]['Oxygen'] = -metabolic_state.get('oxygen_consumption', 0.0)
        position_reactions[position]['Glucose'] = -metabolic_state.get('glucose_consumption', 0.0)
        position_reactions[position]['Lactate'] = (
            metabolic_state.get('lactate_production', 0.0) -
            metabolic_state.get('lactate_consumption', 0.0)
        )

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
    """Apply under-relaxation: c_next = α * c_new + (1-α) * c_old."""
    for name, substance_state in simulator.state.substances.items():
        if name in old and name in new:
            blended = alpha * new[name] + (1 - alpha) * old[name]
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
            print(f"[COUPLED] Safety clamp: {name} had {num_negative} negative values "
                  f"(min={min_val:.4e})")

            if hasattr(simulator, 'fipy_variables') and name in simulator.fipy_variables:
                simulator.fipy_variables[name].setValue(
                    substance_state.concentrations.flatten(order='F')
                )

