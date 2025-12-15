"""
Update cell division based on ATP threshold and cell cycle time.

This function checks which cells should divide based on:
- ATP production rate above threshold
- Cell age exceeds cell cycle time
- Phenotype is 'Proliferation'

Users can customize this to implement different division criteria.
"""

from typing import Dict, Any
import random
from src.workflow.decorators import register_function


@register_function(
    display_name="Update Cell Division",
    description="Handle cell division based on ATP and cell cycle",
    category="INTERCELLULAR",
    outputs=[],
    cloneable=False
)
def update_cell_division(
    population,
    simulator,
    gene_network,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Update cell division based on ATP threshold and cell cycle time.

    For each cell:
    1. Check if cell should divide (ATP rate, age, phenotype)
    2. If yes, create a daughter cell
    3. Reset parent cell age
    4. Place daughter cell near parent

    Division criteria:
    - Cell age >= cell_cycle_time
    - ATP rate / max_atp_rate > atp_threshold
    - Phenotype is 'Proliferation'

    Args:
        population: Population object containing all cells
        simulator: Diffusion simulator for substance concentrations
        gene_network: Gene network object for gene regulation
        config: Configuration object with simulation parameters
        helpers: Dictionary of helper functions from the engine
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # Get division parameters from config
    atp_threshold = _get_config_param(config, 'atp_threshold', 0.8)
    max_atp_rate = _get_config_param(config, 'max_atp_rate', 30.0)
    cell_cycle_time = _get_config_param(config, 'cell_cycle_time', 240.0)
    cell_radius = _get_config_param(config, 'cell_radius', 10.0)

    # Collect cells that should divide
    cells_to_divide = []

    for cell_id, cell in population.state.cells.items():
        # Check division criteria
        if _should_divide(cell, atp_threshold, max_atp_rate, cell_cycle_time):
            cells_to_divide.append((cell_id, cell))

    # Perform divisions
    if cells_to_divide:
        _perform_divisions(population, cells_to_divide, cell_radius, config)


def _should_divide(cell, atp_threshold: float, max_atp_rate: float, cell_cycle_time: float) -> bool:
    """
    Determine if a cell should divide.

    Args:
        cell: Cell object
        atp_threshold: Minimum ATP rate ratio for division
        max_atp_rate: Maximum ATP rate for normalization
        cell_cycle_time: Minimum age for division

    Returns:
        True if cell should divide, False otherwise
    """
    # Check age
    if cell.state.age < cell_cycle_time:
        return False

    # Check phenotype
    if cell.state.phenotype != 'Proliferation':
        return False

    # Check ATP rate
    metabolic_state = cell.state.metabolic_state
    if not metabolic_state:
        return False

    atp_rate = metabolic_state.get('atp_rate', 0.0)
    atp_rate_normalized = atp_rate / max_atp_rate if max_atp_rate > 0 else 0.0

    if atp_rate_normalized <= atp_threshold:
        return False

    return True


def _perform_divisions(population, cells_to_divide, cell_radius: float, config):
    """
    Perform cell divisions by creating daughter cells.

    Args:
        population: Population object
        cells_to_divide: List of (cell_id, cell) tuples
        cell_radius: Cell radius for placement
        config: Configuration object
    """
    new_cells = {}
    updated_cells = {}

    for cell_id, parent_cell in cells_to_divide:
        # Reset parent age
        parent_cell.state = parent_cell.state.with_updates(age=0.0)
        updated_cells[cell_id] = parent_cell

        # Create daughter cell
        daughter_position = _find_daughter_position(parent_cell.state.position, cell_radius)

        # Clone parent cell
        daughter_cell = parent_cell.clone()
        daughter_cell.state = daughter_cell.state.with_updates(
            position=daughter_position,
            age=0.0
        )

        # Generate new cell ID
        new_cell_id = _generate_cell_id(population)
        new_cells[new_cell_id] = daughter_cell

    # Update population with new and updated cells
    all_cells = {**population.state.cells, **updated_cells, **new_cells}
    population.state = population.state.with_updates(cells=all_cells)


def _find_daughter_position(parent_position, cell_radius: float):
    """
    Find a position for the daughter cell near the parent.

    Args:
        parent_position: Parent cell position (x, y) or (x, y, z)
        cell_radius: Cell radius

    Returns:
        Daughter cell position
    """
    # Random angle for 2D placement
    angle = random.uniform(0, 2 * 3.14159)
    distance = cell_radius * 2.0  # Place at 2x radius distance

    if len(parent_position) == 2:
        # 2D case
        x, y = parent_position
        dx = distance * random.choice([-1, 1])
        dy = distance * random.choice([-1, 1])
        return (x + dx, y + dy)
    else:
        # 3D case
        x, y, z = parent_position
        dx = distance * random.choice([-1, 1])
        dy = distance * random.choice([-1, 1])
        dz = distance * random.choice([-1, 1])
        return (x + dx, y + dy, z + dz)


def _generate_cell_id(population):
    """Generate a unique cell ID."""
    existing_ids = set(population.state.cells.keys())
    new_id = max(existing_ids) + 1 if existing_ids else 1
    return new_id


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

