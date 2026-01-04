"""
Update gene networks based on current environmental conditions.

This function updates each cell's gene network based on local environmental
conditions (oxygen, glucose, lactate, etc.) and propagates the Boolean network
to determine gene states (mitoATP, glycoATP, Proliferation, Apoptosis, etc.).

Users can customize this to implement different gene regulatory models.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Update Gene Networks",
    description="Update gene network states and propagate signals",
    category="INTRACELLULAR",
    inputs=["population", "simulator", "gene_network", "config", "helpers"],
    outputs=[],
    cloneable=False
)
def update_gene_networks(
    population,
    simulator,
    gene_network,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Update gene networks based on current environmental conditions.

    For each cell:
    1. Read local substance concentrations (Oxygen, Glucose, Lactate, H+)
    2. Set input gene states based on thresholds
    3. Propagate Boolean network for N steps
    4. Cache gene states for phenotype update

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

    # Get gene network configuration
    associations = config.associations if hasattr(config, 'associations') else {}
    thresholds = config.thresholds if hasattr(config, 'thresholds') else {}
    propagation_steps = 500
    if hasattr(config, 'gene_network') and config.gene_network is not None:
        propagation_steps = getattr(config.gene_network, 'propagation_steps', 500)

    updated_cells = {}

    for cell_id, cell in population.state.cells.items():
        # Get local environment
        local_env = _get_local_environment(cell.state.position, substance_concentrations)

        # Get cell's gene network
        cell_gene_network = cell.state.gene_network

        # Skip if this cell has no gene network attached
        if cell_gene_network is None:
            continue

        # Build input states dict based on local environment
        input_states: Dict[str, bool] = {}
        for substance_name, gene_name in associations.items():
            # Get local concentration
            local_conc = local_env.get(substance_name, 0.0)

            # Get threshold for this gene
            threshold_config = thresholds.get(gene_name, {})
            threshold_value = threshold_config.get('threshold', 0.0) if isinstance(threshold_config, dict) else 0.0

            # Set gene state: True if concentration above threshold
            gene_state = local_conc > threshold_value
            input_states[gene_name] = gene_state

        # Apply inputs to the cell's gene network
        cell_gene_network.set_input_states(input_states)

        # Propagate Boolean network
        gene_states = cell_gene_network.step(propagation_steps)

        # Cache gene states and local environment for phenotype update
        cell._cached_gene_states = gene_states
        cell._cached_local_env = local_env

        # Update cell's gene states
        cell.state = cell.state.with_updates(gene_states=gene_states)

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
            # Default to 0 if position not in grid
            local_env[substance_name] = 0.0

    return local_env

