"""
Update cell migration based on chemotaxis and random walk.

This function handles cell movement based on:
- Chemotaxis: Movement along substance gradients (oxygen, glucose)
- Random walk: Stochastic movement
- Collision avoidance: Prevent cells from overlapping

Users can customize this to implement different migration strategies.
"""

from typing import Dict, Any
import random
import math


def update_cell_migration(
    population,
    simulator,
    gene_network,
    config,
    dt: float,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Update cell migration based on chemotaxis and random walk.

    For each cell:
    1. Calculate chemotaxis force (gradient of oxygen/glucose)
    2. Add random walk component
    3. Check for collisions with other cells
    4. Update cell position

    Migration is only active for cells with 'Proliferation' phenotype.

    Args:
        population: Population object containing all cells
        simulator: Diffusion simulator for substance concentrations
        gene_network: Gene network object for gene regulation
        config: Configuration object with simulation parameters
        dt: Time step (hours)
        helpers: Dictionary of helper functions from the engine
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # Get migration parameters from config
    migration_speed = _get_config_param(config, 'migration_speed', 0.0)
    chemotaxis_strength = _get_config_param(config, 'chemotaxis_strength', 0.0)
    random_walk_strength = _get_config_param(config, 'random_walk_strength', 0.0)
    cell_radius = _get_config_param(config, 'cell_radius', 10.0)

    # If migration is disabled, return early
    if migration_speed == 0.0:
        return

    # Get current substance concentrations
    substance_concentrations = simulator.get_substance_concentrations()

    # Update each cell's position
    updated_cells = {}

    for cell_id, cell in population.state.cells.items():
        # Only migrate proliferating cells
        if cell.state.phenotype != 'Proliferation':
            updated_cells[cell_id] = cell
            continue

        # Calculate new position
        current_position = cell.state.position

        # Calculate chemotaxis force
        chemotaxis_force = _calculate_chemotaxis(
            current_position,
            substance_concentrations,
            chemotaxis_strength
        )

        # Add random walk
        random_force = _calculate_random_walk(random_walk_strength)

        # Combine forces
        total_force = (
            chemotaxis_force[0] + random_force[0],
            chemotaxis_force[1] + random_force[1]
        )

        # Calculate displacement
        displacement = (
            total_force[0] * migration_speed * dt,
            total_force[1] * migration_speed * dt
        )

        # Calculate new position
        new_position = (
            current_position[0] + displacement[0],
            current_position[1] + displacement[1]
        )

        # Check for collisions and boundary constraints
        new_position = _check_collisions(new_position, cell_id, population.state.cells, cell_radius)
        new_position = _apply_boundary_constraints(new_position, config)

        # Update cell position
        cell.state = cell.state.with_updates(position=new_position)
        updated_cells[cell_id] = cell

    # Update population
    population.state = population.state.with_updates(cells=updated_cells)


def _calculate_chemotaxis(position, substance_concentrations, strength: float):
    """
    Calculate chemotaxis force based on substance gradients.

    Cells move toward higher oxygen and glucose concentrations.
    """
    if strength == 0.0:
        return (0.0, 0.0)

    # Simple gradient estimation using finite differences
    dx = 1.0  # Grid spacing

    gradient_x = 0.0
    gradient_y = 0.0

    for substance_name in ['Oxygen', 'Glucose']:
        if substance_name not in substance_concentrations:
            continue

        conc_grid = substance_concentrations[substance_name]

        # Get concentrations at neighboring positions
        x, y = position[:2]
        c_center = conc_grid.get((x, y), 0.0)
        c_right = conc_grid.get((x + dx, y), c_center)
        c_left = conc_grid.get((x - dx, y), c_center)
        c_up = conc_grid.get((x, y + dx), c_center)
        c_down = conc_grid.get((x, y - dx), c_center)

        # Calculate gradient
        gradient_x += (c_right - c_left) / (2 * dx)
        gradient_y += (c_up - c_down) / (2 * dx)

    # Normalize and scale by strength
    magnitude = math.sqrt(gradient_x**2 + gradient_y**2)
    if magnitude > 0:
        gradient_x = (gradient_x / magnitude) * strength
        gradient_y = (gradient_y / magnitude) * strength

    return (gradient_x, gradient_y)


def _calculate_random_walk(strength: float):
    """Calculate random walk force."""
    if strength == 0.0:
        return (0.0, 0.0)

    angle = random.uniform(0, 2 * math.pi)
    return (
        strength * math.cos(angle),
        strength * math.sin(angle)
    )


def _check_collisions(new_position, cell_id, all_cells, cell_radius: float):
    """Check for collisions with other cells and adjust position."""
    min_distance = cell_radius * 2.0

    for other_id, other_cell in all_cells.items():
        if other_id == cell_id:
            continue

        other_pos = other_cell.state.position
        distance = math.sqrt(
            (new_position[0] - other_pos[0])**2 +
            (new_position[1] - other_pos[1])**2
        )

        if distance < min_distance:
            # Collision detected - don't move
            return all_cells[cell_id].state.position

    return new_position


def _apply_boundary_constraints(position, config):
    """Apply domain boundary constraints."""
    if not hasattr(config, 'domain'):
        return position

    domain = config.domain
    x_min, x_max = 0, domain.get('x_max', 500.0)
    y_min, y_max = 0, domain.get('y_max', 500.0)

    x = max(x_min, min(x_max, position[0]))
    y = max(y_min, min(y_max, position[1]))

    return (x, y)


def _get_config_param(config, param_name: str, default_value):
    """Safely get a parameter from config with fallback to default."""
    if not config:
        return default_value

    if hasattr(config, 'custom_parameters'):
        custom_params = config.custom_parameters
        if isinstance(custom_params, dict) and param_name in custom_params:
            return custom_params[param_name]

    if hasattr(config, param_name):
        return getattr(config, param_name)
    elif isinstance(config, dict) and param_name in config:
        return config[param_name]

    return default_value

