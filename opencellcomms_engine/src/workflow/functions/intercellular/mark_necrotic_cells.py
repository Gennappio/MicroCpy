"""
Mark cells as necrotic based on user-defined conditions.

This function checks each cell's local environment and marks cells as Necrotic
based on conditions specified in a generic parameters dictionary.

Necrotic cells remain in the population but do nothing (no metabolism,
no gene network updates, no phenotype changes).

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.

USAGE:
The 'necrosis_params' dictionary can contain any parameters the user needs.
Example configurations:

1. Threshold-based (default):
   {
       "mode": "threshold",
       "oxygen_threshold": 0.022,
       "glucose_threshold": 0.23,
       "require_both": true
   }

2. Custom logic (user can extend):
   {
       "mode": "custom",
       "substance": "Oxygen",
       "threshold": 0.01,
       "comparison": "less_than"
   }
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Mark Necrotic Cells",
    description="Mark cells as necrotic based on user-defined conditions in necrosis_params",
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "necrosis_params",
            "type": "DICT",
            "description": "Dictionary of necrosis parameters (e.g., thresholds, mode, conditions)",
            "default": {
                "oxygen_threshold": 0.022,
                "glucose_threshold": 0.23,
                "require_both": True
            }
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_necrotic_cells(
    context: Dict[str, Any],
    necrosis_params: Dict[str, Any] = None,
    **kwargs
) -> None:
    """
    Mark cells as necrotic based on user-defined conditions.

    For each cell:
    1. Get local environment concentrations
    2. Evaluate conditions from necrosis_params
    3. If conditions are met, mark cell as Necrotic
    4. Necrotic cells stay in population but are inactive

    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
            - simulator: Diffusion simulator (REQUIRED for concentrations)
            - config: Configuration object
        necrosis_params: Dictionary of parameters for necrosis marking.
            Default keys:
            - oxygen_threshold (float): Oxygen threshold (default 0.022)
            - glucose_threshold (float): Glucose threshold (default 0.23)
            - require_both (bool): If True, both must be below threshold (default True)
            User can add any custom keys for their own logic.
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # Set defaults if necrosis_params is None
    if necrosis_params is None:
        necrosis_params = {}

    # Extract parameters with defaults
    oxygen_threshold = necrosis_params.get('oxygen_threshold', 0.022)
    glucose_threshold = necrosis_params.get('glucose_threshold', 0.23)
    require_both = necrosis_params.get('require_both', True)
    # =========================================================================
    # EXTRACT CORE CONTEXT ITEMS
    # =========================================================================
    population = context.get('population')
    simulator = context.get('simulator')
    config = context.get('config')

    # =========================================================================
    # VALIDATE REQUIRED CORE ITEMS
    # =========================================================================
    if population is None:
        print("[mark_necrotic_cells] No population in context - skipping")
        return

    # =========================================================================
    # GET SUBSTANCE CONCENTRATIONS
    # =========================================================================
    if simulator is not None:
        try:
            substance_concentrations = simulator.get_substance_concentrations()
        except Exception as e:
            print(f"[mark_necrotic_cells] Failed to get substance concentrations: {e}")
            substance_concentrations = {}
    else:
        print("[mark_necrotic_cells] No simulator - cannot check thresholds")
        return

    # =========================================================================
    # MARK NECROTIC CELLS
    # =========================================================================
    initial_count = len(population.state.cells)
    updated_cells = {}
    newly_necrotic = 0
    already_necrotic = 0

    for cell_id, cell in population.state.cells.items():
        # Skip cells already marked as Necrotic
        if cell.state.phenotype == 'Necrosis':
            already_necrotic += 1
            updated_cells[cell_id] = cell
            continue

        # Get local environment
        local_env = _get_local_environment(cell.state.position, substance_concentrations, config)

        # Get oxygen and glucose concentrations
        local_oxygen = local_env.get('Oxygen', local_env.get('oxygen', 0.0))
        local_glucose = local_env.get('Glucose', local_env.get('glucose', 0.0))

        # Check thresholds based on require_both setting
        oxygen_below = local_oxygen < oxygen_threshold
        glucose_below = local_glucose < glucose_threshold

        if require_both:
            # Both must be below thresholds
            should_mark = oxygen_below and glucose_below
        else:
            # Either one below threshold triggers necrosis
            should_mark = oxygen_below or glucose_below

        if should_mark:
            # Mark as necrotic
            cell.state = cell.state.with_updates(phenotype='Necrosis')
            newly_necrotic += 1

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log summary
    final_count = len(updated_cells)
    condition_str = "AND" if require_both else "OR"
    print(f"[NECROSIS] Cell count: {initial_count} -> {final_count} (marked {newly_necrotic}, already {already_necrotic})")
    if newly_necrotic > 0:
        print(f"[NECROSIS] Marked {newly_necrotic} cells as necrotic "
              f"(O2 < {oxygen_threshold} {condition_str} Glc < {glucose_threshold})")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['necrosis'] = {
        'newly_marked': newly_necrotic,
        'already_necrotic': already_necrotic,
        'params': necrosis_params
    }


def _get_local_environment(position, substance_concentrations, config=None):
    """
    Get local substance concentrations at a cell's position.

    Handles coordinate conversion from cell logical positions to grid indices.
    Cell positions are in logical coordinates (cell_index * cell_size_um).
    Grid indices are 0 to nx-1, 0 to ny-1.

    Args:
        position: Cell position in logical coordinates (x, y) or (x, y, z)
        substance_concentrations: Dict of substance name -> {(grid_x, grid_y): concentration}
        config: Configuration object with domain info (optional, for coordinate conversion)

    Returns:
        Dict of substance name -> local concentration
    """
    local_env = {}

    # Get grid dimensions from the first substance's concentration grid
    if not substance_concentrations:
        return local_env

    first_substance = next(iter(substance_concentrations.values()))
    if not first_substance:
        return local_env

    # Get grid dimensions (max x and y indices)
    max_grid_x = max(pos[0] for pos in first_substance.keys()) if first_substance else 0
    max_grid_y = max(pos[1] for pos in first_substance.keys()) if first_substance else 0
    nx = max_grid_x + 1
    ny = max_grid_y + 1

    # Convert cell logical position to grid index
    # Cell positions are in logical coordinates (cell_index)
    # Grid indices are 0 to nx-1, 0 to ny-1
    cell_x, cell_y = position[0], position[1]

    # If config is available, use proper conversion
    if config and hasattr(config, 'domain'):
        # Get domain and cell size info
        domain_size_um = config.domain.size_x.micrometers if hasattr(config.domain.size_x, 'micrometers') else config.domain.size_x
        cell_size_um = config.domain.cell_height.micrometers if hasattr(config.domain, 'cell_height') and hasattr(config.domain.cell_height, 'micrometers') else 20.0

        # Convert logical position to physical position (um)
        phys_x = cell_x * cell_size_um
        phys_y = cell_y * cell_size_um

        # Convert physical position to grid index
        grid_spacing = domain_size_um / nx
        grid_x = int(phys_x / grid_spacing)
        grid_y = int(phys_y / grid_spacing)
    else:
        # Fallback: assume cell positions need scaling to grid
        # Estimate the scaling factor from the position range
        # If cell positions are larger than grid size, scale them down
        if cell_x > nx or cell_y > ny:
            # Assume cell positions are in a larger logical grid
            # Scale to fit the concentration grid
            # This is a heuristic - proper config should be used
            scale_factor = max(cell_x, cell_y) / max(nx, ny) if max(cell_x, cell_y) > 0 else 1.0
            scale_factor = max(1.0, scale_factor)  # At least 1.0
            grid_x = int(cell_x / scale_factor)
            grid_y = int(cell_y / scale_factor)
        else:
            # Positions are already in grid coordinates
            grid_x = int(cell_x)
            grid_y = int(cell_y)

    # Clamp to valid grid bounds
    grid_x = max(0, min(nx - 1, grid_x))
    grid_y = max(0, min(ny - 1, grid_y))

    grid_pos = (grid_x, grid_y)

    for substance_name, conc_grid in substance_concentrations.items():
        if grid_pos in conc_grid:
            local_env[substance_name] = conc_grid[grid_pos]
        else:
            # Try with original position as fallback
            if position[:2] in conc_grid:
                local_env[substance_name] = conc_grid[position[:2]]
            else:
                local_env[substance_name] = 0.0

    return local_env

