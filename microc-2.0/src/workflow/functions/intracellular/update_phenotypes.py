"""
Update cell phenotypes based on gene network states.

This function determines each cell's phenotype (Proliferation, Quiescence, Apoptosis,
Necrosis) based on gene network states and environmental conditions.

Users can customize this to implement different phenotype determination logic.
"""

from typing import Dict, Any


def update_phenotypes(
    population,
    simulator,
    gene_network,
    config,
    helpers: Dict[str, Any],
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
        population: Population object containing all cells
        simulator: Diffusion simulator for substance concentrations
        gene_network: Gene network object for gene regulation
        config: Configuration object with simulation parameters
        helpers: Dictionary of helper functions from the engine
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # Get current substance concentrations
    substance_concentrations = simulator.get_substance_concentrations()

    updated_cells = {}

    for cell_id, cell in population.cells.items():
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

