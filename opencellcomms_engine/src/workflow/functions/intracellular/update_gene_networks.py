"""
Update gene networks based on current environmental conditions.

This function updates each cell's gene network based on local environmental
conditions (oxygen, glucose, lactate, etc.) and propagates the Boolean network
to determine gene states (mitoATP, glycoATP, Proliferation, Apoptosis, etc.).

Users can customize this to implement different gene regulatory models.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Update Gene Networks",
    description="Update gene network states and propagate signals",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of gene network propagation steps", "default": 500},
    ],
    # Only context needed - user params are defined above
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def update_gene_networks(
    context: Dict[str, Any],
    propagation_steps: int = None,
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
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
            - simulator: Diffusion simulator (OPTIONAL)
            - config: Configuration with associations/thresholds
        propagation_steps: Number of gene network propagation steps (user parameter)
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
        print("[update_gene_networks] No population in context - skipping")
        return

    # =========================================================================
    # GET SUBSTANCE CONCENTRATIONS (optional)
    # =========================================================================
    if simulator is not None:
        try:
            substance_concentrations = simulator.get_substance_concentrations()
        except Exception as e:
            print(f"[update_gene_networks] Failed to get substance concentrations: {e}")
            substance_concentrations = {}
    else:
        substance_concentrations = {}

    # Get gene network configuration
    associations = config.associations if config and hasattr(config, 'associations') else {}
    thresholds = config.thresholds if config and hasattr(config, 'thresholds') else {}

    # Use explicit parameter if provided, otherwise fallback to config
    if propagation_steps is None:
        propagation_steps = 500
        if config and hasattr(config, 'gene_network') and config.gene_network is not None:
            propagation_steps = getattr(config.gene_network, 'propagation_steps', 500)

    # =========================================================================
    # UPDATE EACH CELL'S GENE NETWORK
    # =========================================================================
    updated_cells = {}
    cells_with_gn = 0
    cells_without_gn = 0
    skipped_inactive = 0

    # Phenotypes that should not have gene network updates
    # Note: Apoptotic cells are removed, so we only skip Necrosis and Growth_Arrest
    inactive_phenotypes = {'Necrosis', 'Growth_Arrest'}

    for cell_id, cell in population.state.cells.items():
        # Skip cells in inactive states (Necrosis, Growth_Arrest)
        if cell.state.phenotype in inactive_phenotypes:
            skipped_inactive += 1
            updated_cells[cell_id] = cell
            continue

        # Get local environment
        local_env = _get_local_environment(cell.state.position, substance_concentrations)

        # Get cell's gene network
        cell_gene_network = cell.state.gene_network

        # Skip if this cell has no gene network attached
        if cell_gene_network is None:
            cells_without_gn += 1
            updated_cells[cell_id] = cell
            continue

        cells_with_gn += 1

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

    # Log summary
    total_cells = len(population.state.cells)
    print(f"[GENE_NETWORK] Updated {cells_with_gn}/{total_cells} cells "
          f"(skipped {cells_without_gn} without gene network, "
          f"{skipped_inactive} inactive - Necrosis/Growth_Arrest)")

    # Collect output state statistics for context changes
    output_stats = {}
    sample_outputs = {}

    if cells_with_gn > 0:
        print(f"[GENE_NETWORK] Propagation steps: {propagation_steps}, associations: {len(associations)}")

        # Collect statistics on output node states across all cells
        for cell_id, cell in updated_cells.items():
            cell_gn = cell.state.gene_network
            if cell_gn:
                output_states = cell_gn.get_output_states()
                for node_name, state in output_states.items():
                    if node_name not in output_stats:
                        output_stats[node_name] = {'True': 0, 'False': 0}
                    output_stats[node_name]['True' if state else 'False'] += 1

        # Sample output: show fate gene states for first cell
        if updated_cells:
            sample_cell = next(iter(updated_cells.values()))
            sample_gn = sample_cell.state.gene_network
            if sample_gn:
                sample_outputs = sample_gn.get_output_states()
                print(f"[GENE_NETWORK] Sample cell outputs: {sample_outputs}")

    # Store changes in context for GUI display
    context['changes'] = context.get('changes', {})
    context['changes']['gene_network'] = {
        'cells_updated': cells_with_gn,
        'cells_skipped': cells_without_gn,
        'propagation_steps': propagation_steps,
        'associations_count': len(associations),
        'output_stats': output_stats,
        'sample_outputs': sample_outputs
    }


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

