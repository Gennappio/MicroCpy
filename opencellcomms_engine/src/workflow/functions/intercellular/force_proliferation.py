"""
Force cell proliferation based on dynamic probability.

This function forces cells to divide based on a population-dependent probability:
- When cells < 100: 10% chance per cell (rapid growth)
- When cells > 1000: 1% chance per cell (slow growth)
- Between 100-1000: smoothly interpolates between 10% and 1%

This creates natural population regulation without explicit carrying capacity.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any, Optional
import random
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation, IConfig

@register_function(
    display_name="Force Proliferating Cells",
    description="Force cells as proliferating",
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "activation_probability",
            "type": "FLOAT",
            "description": "Probability of cell division per cell (e.g., 0.01 = 1% chance)",
            "default": 0.01
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def force_proliferation(
    context: Dict[str, Any],
    activation_probability: float = 0.01,
    **kwargs
) -> None:

    """
    Force cell proliferation based on dynamic population-dependent probability.

    For each cell:
    1. Calculate dynamic probability based on current population size
       - < 100 cells: 10% chance per cell
       - > 1000 cells: 1% chance per cell
       - Between: smooth linear interpolation
    2. Check if cell should divide (random probability)
    3. If yes, create a daughter cell
    4. Reset parent cell age
    5. Place daughter cell near parent

    This creates natural population regulation where growth slows as
    population increases, without hard carrying capacity limits.

    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
            - config: Configuration object
        activation_probability: Base probability (currently unused - dynamic calc overrides)
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # =========================================================================
    # EXTRACT CORE CONTEXT ITEMS
    # =========================================================================
    population: Optional[ICellPopulation] = context.get('population')
    config: Optional[IConfig] = context.get('config')

    # =========================================================================
    # VALIDATE REQUIRED CORE ITEMS
    # =========================================================================
    if population is None:
        print("[update_cell_division] No population in context - skipping")
        return

    # Get division parameters from config
    atp_threshold = _get_config_param(config, 'atp_threshold', 0.8)
    max_atp_rate = _get_config_param(config, 'max_atp_rate', 30.0)
    cell_cycle_time = _get_config_param(config, 'cell_cycle_time', 240.0)
    cell_radius = _get_config_param(config, 'cell_radius', 10.0)

    # Calculate dynamic activation probability based on current cell count
    current_cell_count = len(population.state.cells)
    dynamic_probability = _calculate_activation_probability(
        current_cell_count,
        min_cells=100,
        max_cells=1000,
        max_probability=0.10,  # 10% when few cells
        min_probability=0.01   # 1% when many cells
    )
    
    print(f"[FORCE_PROLIFERATION] Cells: {current_cell_count}, Activation probability: {dynamic_probability:.3%}")
    
    # First, normalize all cell positions to int tuples (grid positions must be int)
    for cell_id, cell in population.state.cells.items():
        pos = cell.state.position
        int_pos = tuple(int(round(c)) for c in pos)
        if int_pos != pos:
            cell.state = cell.state.with_updates(position=int_pos)
    
    # Build spatial map of occupied positions for collision detection
    occupied_positions = {cell.state.position for cell in population.state.cells.values()}
    
    # Get domain bounds from config
    domain_bounds = _get_domain_bounds(config)
    
    # Debug: show a few cell positions
    sample_cells = list(population.state.cells.values())[:3]
    sample_positions = [c.state.position for c in sample_cells]
    print(f"[FORCE_PROLIFERATION] Domain: {domain_bounds['xmax']+1}x{domain_bounds['ymax']+1}, "
          f"Occupied: {len(occupied_positions)}, "
          f"Sample pos: {sample_positions}")
    
    # 1. Roll dice for each cell
    cells_to_divide = []
    for cell_id, cell in population.state.cells.items():
        # Roll the dice: if random < probability, cell divides
        if random.random() < dynamic_probability:
            cells_to_divide.append((cell_id, cell))
    
    print(f"[FORCE_PROLIFERATION] {len(cells_to_divide)}/{current_cell_count} cells rolled successfully for division")
    
    # Perform divisions
    if cells_to_divide:
        _perform_divisions(population, cells_to_divide, cell_radius, config, context, 
                          occupied_positions, domain_bounds)
    else:
        print(f"[FORCE_PROLIFERATION] No cells selected for division (bad luck on dice rolls)")


def _calculate_activation_probability(
    current_cell_count: int,
    min_cells: int = 100,
    max_cells: int = 1000,
    max_probability: float = 0.10,
    min_probability: float = 0.01
) -> float:
    """
    Calculate activation probability based on current cell count.
    
    Uses smooth linear interpolation:
    - When cell_count <= min_cells: returns max_probability (10%)
    - When cell_count >= max_cells: returns min_probability (1%)
    - In between: smoothly interpolates between the two
    
    Args:
        current_cell_count: Current number of cells in population
        min_cells: Cell count below which max_probability is used
        max_cells: Cell count above which min_probability is used
        max_probability: Probability when few cells (default: 0.10 = 10%)
        min_probability: Probability when many cells (default: 0.01 = 1%)
    
    Returns:
        Activation probability between min_probability and max_probability
    """
    if current_cell_count <= min_cells:
        return max_probability
    elif current_cell_count >= max_cells:
        return min_probability
    else:
        # Linear interpolation between min_cells and max_cells
        # Formula: prob = max_prob - (max_prob - min_prob) * (count - min) / (max - min)
        range_cells = max_cells - min_cells
        range_prob = max_probability - min_probability
        position = (current_cell_count - min_cells) / range_cells
        return max_probability - (range_prob * position)


def _should_divide(cell, activation_probability: float) -> bool:
    """
    Determine if a cell should divide based on probability.

    Args:
        cell: Cell object
        activation_probability: Probability of division (e.g., 0.01 = 1% chance)

    Returns:
        True if cell should divide (based on random chance), False otherwise
    """
    # Simple probability-based activation
    # If activation_probability = 0.01, there's a 1% chance of proliferating
    return random.random() < activation_probability


def _perform_divisions(population, cells_to_divide, cell_radius: float, config, context, 
                      occupied_positions, domain_bounds):
    """
    Perform cell divisions by creating daughter cells.

    Args:
        population: Population object
        cells_to_divide: List of (cell_id, cell) tuples
        cell_radius: Cell radius for placement
        config: Configuration object
        context: Workflow context (for gene networks)
        occupied_positions: Set of currently occupied positions
        domain_bounds: Dict with 'xmin', 'xmax', 'ymin', 'ymax', etc.
    """
    from src.biology.cell import Cell
    
    new_cells = {}
    gene_networks = context.get('gene_networks', {})
    failed_divisions = 0
    successful_divisions = 0

    for cell_id, parent_cell in cells_to_divide:
        parent_pos = parent_cell.state.position
        
        # Try to find a valid position for daughter cell
        daughter_position = _find_daughter_position(
            parent_pos, 
            cell_radius, 
            occupied_positions,
            domain_bounds
        )
        
        # If no valid position found, skip this division
        if daughter_position is None:
            failed_divisions += 1
            continue
        
        successful_divisions += 1
        
        # Create new daughter cell with same properties as parent
        daughter_cell = Cell(
            position=daughter_position,
            phenotype=parent_cell.state.phenotype,
            custom_functions_module=parent_cell.custom_functions
        )
        
        # Copy gene states from parent to daughter
        daughter_cell.state = daughter_cell.state.with_updates(
            gene_states=parent_cell.state.gene_states.copy(),
            metabolic_state=parent_cell.state.metabolic_state.copy(),
            age=0.0
        )
        
        # Reset parent age and increment division count
        parent_cell.state = parent_cell.state.with_updates(
            age=0.0,
            division_count=parent_cell.state.division_count + 1
        )

        # Generate new cell ID
        new_cell_id = _generate_cell_id(population)
        new_cells[new_cell_id] = daughter_cell
        
        # Mark position as occupied
        occupied_positions.add(daughter_position)
        
        # Clone parent's gene network for daughter cell (if gene networks are enabled)
        if gene_networks and cell_id in gene_networks:
            parent_gn = gene_networks[cell_id]
            daughter_gn = parent_gn.copy()  # BooleanNetwork has a copy() method
            gene_networks[new_cell_id] = daughter_gn

    # Update population with new cells AND spatial grid AND total_cells count
    initial_count = len(population.state.cells)
    all_cells = {**population.state.cells, **new_cells}
    new_spatial_grid = population.state.spatial_grid.copy()
    for cell_id, cell in new_cells.items():
        new_spatial_grid[cell.state.position] = cell_id
    population.state = population.state.with_updates(
        cells=all_cells,
        spatial_grid=new_spatial_grid,
        total_cells=population.state.total_cells + len(new_cells)
    )
    final_count = len(all_cells)

    # Log summary
    print(f"[FORCE_PROLIFERATION] Division: {successful_divisions} ok, "
          f"{failed_divisions} failed (no space), "
          f"cells {initial_count} → {final_count}")


def _find_daughter_position(parent_position, cell_radius: float, occupied_positions, domain_bounds):
    """
    Find first available position in the 8 spaces around the parent (2D) or 26 (3D).
    All positions are integer grid coordinates.

    Args:
        parent_position: Parent cell position (i, j) or (i, j, k) - ints
        cell_radius: Cell radius (not used, kept for compatibility)
        occupied_positions: Set of occupied grid positions (tuples of ints)
        domain_bounds: Dict with domain boundaries

    Returns:
        First available (int tuple) position, or None if all spaces are taken
    """
    if len(parent_position) == 2:
        i, j = parent_position
        offsets = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
    else:
        offsets = []
        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                for dk in [-1, 0, 1]:
                    if di == 0 and dj == 0 and dk == 0:
                        continue
                    offsets.append((di, dj, dk))
    
    for offset in offsets:
        # All arithmetic stays int
        candidate = tuple(int(p) + int(o) for p, o in zip(parent_position, offset))
        
        if candidate in occupied_positions:
            continue
        if not _is_within_bounds(candidate, domain_bounds):
            continue
        
        return candidate   # First free neighbour
    
    return None  # Completely surrounded


def _is_within_bounds(position, domain_bounds) -> bool:
    """
    Check if a position is within domain bounds.
    
    Args:
        position: Position (x, y) or (x, y, z)
        domain_bounds: Dict with domain boundaries
        
    Returns:
        True if within bounds
    """
    if len(position) == 2:
        x, y = position
        return (domain_bounds['xmin'] <= x <= domain_bounds['xmax'] and
                domain_bounds['ymin'] <= y <= domain_bounds['ymax'])
    else:
        x, y, z = position
        return (domain_bounds['xmin'] <= x <= domain_bounds['xmax'] and
                domain_bounds['ymin'] <= y <= domain_bounds['ymax'] and
                domain_bounds['zmin'] <= z <= domain_bounds['zmax'])


def _is_valid_position(position, occupied_positions, domain_bounds) -> bool:
    """
    Check if a position is valid for placing a cell.
    
    Args:
        position: Candidate position (x, y) or (x, y, z)
        occupied_positions: Set of occupied positions
        domain_bounds: Dict with domain boundaries
        
    Returns:
        True if position is valid (unoccupied and within bounds)
    """
    # Check if occupied
    if position in occupied_positions:
        return False
    
    # Check bounds
    return _is_within_bounds(position, domain_bounds)


def _get_domain_bounds(config):
    """
    Get domain boundaries from config.
    
    Returns:
        Dict with xmin, xmax, ymin, ymax, zmin, zmax
    """
    if config and hasattr(config, 'domain'):
        domain = config.domain
        
        # Check if this is a 3D domain (nz exists and is not None)
        is_3d = hasattr(domain, 'nz') and domain.nz is not None
        
        return {
            'xmin': 0,
            'xmax': domain.nx - 1,
            'ymin': 0,
            'ymax': domain.ny - 1,
            'zmin': 0,
            'zmax': (domain.nz - 1) if is_3d else 0
        }
    else:
        # Default large bounds if config not available
        return {
            'xmin': 0, 'xmax': 100,
            'ymin': 0, 'ymax': 100,
            'zmin': 0, 'zmax': 100
        }


def _generate_cell_id(population):
    """Generate a unique cell ID (UUID string)."""
    import uuid
    return str(uuid.uuid4())


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

