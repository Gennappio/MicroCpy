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
        local_env = _get_local_environment(cell.state.position, substance_concentrations)

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


def _get_local_environment(position, substance_concentrations):
    """Get local substance concentrations at a cell's position."""
    local_env = {}
    for substance_name, conc_grid in substance_concentrations.items():
        if position in conc_grid:
            local_env[substance_name] = conc_grid[position]
        else:
            local_env[substance_name] = 0.0
    return local_env

