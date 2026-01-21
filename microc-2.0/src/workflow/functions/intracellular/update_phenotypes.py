"""
Update cell phenotypes based on gene network states.

This function determines each cell's phenotype (Proliferation, Quiescence, Apoptosis,
Necrosis) based on gene network states and environmental conditions.

Users can customize this to implement different phenotype determination logic.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Update Phenotypes",
    description="Update cell phenotypes based on gene network states",
    category="INTRACELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def update_phenotypes(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Update cell phenotypes based on gene network states.

    For each cell:
    1. Read gene states (Proliferation, Apoptosis, Necrosis genes)
    2. Check environmental conditions (oxygen, glucose)
    3. Determine phenotype based on gene states and thresholds
    4. Update cell's phenotype state

    Phenotype priority (highest to lowest):
    - Necrosis: If Necrosis gene is ON
    - Apoptosis: If Apoptosis gene is ON
    - Proliferation: If Proliferation gene is ON
    - Quiescence: Default state

    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
            - simulator: Diffusion simulator (OPTIONAL)
            - config: Configuration object
        **kwargs: Additional user parameters (ignored)

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
        print("[update_phenotypes] No population in context - skipping")
        return

    # =========================================================================
    # GET SUBSTANCE CONCENTRATIONS (optional)
    # =========================================================================
    if simulator is not None:
        try:
            substance_concentrations = simulator.get_substance_concentrations()
        except Exception as e:
            print(f"[update_phenotypes] Failed to get substance concentrations: {e}")
            substance_concentrations = {}
    else:
        substance_concentrations = {}

    # =========================================================================
    # UPDATE EACH CELL'S PHENOTYPE
    # =========================================================================
    updated_cells = {}

    for cell_id, cell in population.state.cells.items():
        # Get cached gene states from gene network update
        gene_states = getattr(cell, '_cached_gene_states', cell.state.gene_states)
        local_env = getattr(cell, '_cached_local_env', {})

        # If no cached environment, get it now
        if not local_env:
            local_env = _get_local_environment(cell.state.position, substance_concentrations)

        # Determine phenotype based on gene states
        phenotype = _determine_phenotype(gene_states, local_env, config)

        # Update cell's phenotype
        cell.state = cell.state.with_updates(phenotype=phenotype)

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)


def _get_local_environment(position, substance_concentrations):
    """
    Get local substance concentrations at a cell's position.

    Args:
        position: Cell position (x, y) or (x, y, z)
        substance_concentrations: Dict of substance name -> concentration grid

    Returns:
        Dict of substance name -> local concentration
    """
    local_env = {}

    for substance_name, conc_grid in substance_concentrations.items():
        if position in conc_grid:
            local_env[substance_name] = conc_grid[position]
        else:
            local_env[substance_name] = 0.0

    return local_env


def _determine_phenotype(gene_states: Dict[str, bool], local_env: Dict[str, float], config) -> str:
    """
    Determine cell phenotype based on gene network states and environment.

    Phenotype determination logic:
    1. Necrosis: If Necrosis gene is ON (highest priority)
    2. Apoptosis: If Apoptosis gene is ON
    3. Proliferation: If Proliferation gene is ON
    4. Quiescence: Default state (no active phenotype genes)

    Args:
        gene_states: Dict of gene name -> boolean state
        local_env: Dict of substance concentrations
        config: Configuration object

    Returns:
        Phenotype string: 'Necrosis', 'Apoptosis', 'Proliferation', or 'Quiescence'
    """
    # Check for death phenotypes first (highest priority)
    if gene_states.get('Necrosis', False):
        return 'Necrosis'

    if gene_states.get('Apoptosis', False):
        return 'Apoptosis'

    # Check for proliferation
    if gene_states.get('Proliferation', False):
        return 'Proliferation'

    # Default to quiescence
    return 'Quiescence'

