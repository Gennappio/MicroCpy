"""
Remove cells that have died (Apoptosis or Necrosis phenotype).

This function checks each cell's phenotype and removes cells that have
entered Apoptosis or Necrosis states from the population.

Users can customize this to implement different cell death criteria.
"""

from typing import Dict, Any


def remove_dead_cells(
    population,
    simulator,
    gene_network,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Remove cells that have died (Apoptosis or Necrosis phenotype).

    Iterates through all cells and removes those with phenotype:
    - 'Apoptosis': Programmed cell death
    - 'Necrosis': Uncontrolled cell death

    This function modifies the population by removing dead cells from
    the cells dictionary.

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
    # Get death phenotypes from config (with defaults)
    death_phenotypes = _get_death_phenotypes(config)

    # Filter out dead cells
    living_cells = {}
    dead_count = 0

    for cell_id, cell in population.cells.items():
        phenotype = cell.state.phenotype

        # Check if cell is dead
        if phenotype in death_phenotypes:
            dead_count += 1
            # Cell is dead - don't add to living_cells
            continue

        # Cell is alive - keep it
        living_cells[cell_id] = cell

    # Update population with only living cells
    if dead_count > 0:
        population.state = population.state.with_updates(cells=living_cells)

        # Optional: Log removal if verbose mode is enabled
        if hasattr(config, 'verbose') and config.verbose:
            print(f"[REMOVE_DEAD_CELLS] Removed {dead_count} dead cells. "
                  f"Remaining: {len(living_cells)} cells")


def _get_death_phenotypes(config):
    """
    Get the list of phenotypes that indicate cell death.

    Args:
        config: Configuration object

    Returns:
        Set of phenotype strings that indicate death
    """
    # Default death phenotypes
    default_death_phenotypes = {'Apoptosis', 'Necrosis'}

    # Check if config specifies custom death phenotypes
    if hasattr(config, 'death_phenotypes'):
        return set(config.death_phenotypes)
    elif hasattr(config, 'custom_parameters'):
        custom_params = config.custom_parameters
        if isinstance(custom_params, dict) and 'death_phenotypes' in custom_params:
            return set(custom_params['death_phenotypes'])

    return default_death_phenotypes

