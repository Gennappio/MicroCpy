"""
Mark cells as necrotic based on oxygen and glucose thresholds.

This function checks each cell's local oxygen and glucose concentrations
and marks cells as Necrotic if BOTH are below the specified thresholds.

Necrotic cells remain in the population but do nothing (no metabolism,
no gene network updates, no phenotype changes).

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Mark Necrotic Cells",
    description="Mark cells as necrotic based on oxygen and glucose thresholds",
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "oxygen_threshold",
            "type": "FLOAT",
            "description": "Oxygen threshold for necrosis (cells below this are marked)",
            "default": 0.022
        },
        {
            "name": "glucose_threshold",
            "type": "FLOAT",
            "description": "Glucose threshold for necrosis (cells below this are marked)",
            "default": 0.23
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def mark_necrotic_cells(
    context: Dict[str, Any],
    oxygen_threshold: float = 0.022,
    glucose_threshold: float = 0.23,
    **kwargs
) -> None:
    """
    Mark cells as necrotic based on oxygen and glucose thresholds.

    For each cell:
    1. Get local oxygen and glucose concentrations
    2. If BOTH are below thresholds, mark cell as Necrotic
    3. Necrotic cells stay in population but are inactive

    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
            - simulator: Diffusion simulator (REQUIRED for concentrations)
            - config: Configuration object
        oxygen_threshold: Oxygen threshold for necrosis marking
        glucose_threshold: Glucose threshold for necrosis marking
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
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

        # Check if BOTH are below thresholds
        if local_oxygen < oxygen_threshold and local_glucose < glucose_threshold:
            # Mark as necrotic
            cell.state = cell.state.with_updates(phenotype='Necrosis')
            newly_necrotic += 1

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log summary
    if newly_necrotic > 0:
        print(f"[NECROSIS] Marked {newly_necrotic} cells as necrotic "
              f"(O2 < {oxygen_threshold}, Glc < {glucose_threshold}). "
              f"Already necrotic: {already_necrotic}")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['necrosis'] = {
        'newly_marked': newly_necrotic,
        'already_necrotic': already_necrotic,
        'oxygen_threshold': oxygen_threshold,
        'glucose_threshold': glucose_threshold
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

