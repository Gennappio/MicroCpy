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

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from interfaces.base import IGeneNetwork, ICellPopulation, ISubstanceSimulator


@register_function(
    display_name="Update Gene Networks",
    description="Update gene network states and propagate signals",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of gene network propagation steps", "default": 20},
        {"name": "update_mode", "type": "STRING", "description": "Update mode: 'synchronous' (all genes update together) or 'netlogo' (random single gene per step)", "default": "synchronous"},
    ],
    # Only context needed - user params are defined above
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def update_gene_networks(
    context: Dict[str, Any],
    propagation_steps: int = None,
    update_mode: str = None,
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
    population: Optional[ICellPopulation] = context.get('population')
    simulator: Optional[ISubstanceSimulator] = context.get('simulator')
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
    substance_concentrations = {}  # Initialize before conditional
    if simulator is not None:
        try:
            substance_concentrations = simulator.get_substance_concentrations()
            # Successfully got substance concentrations
        except Exception as e:
            print(f"[update_gene_networks] Failed to get substance concentrations: {e}")
            import traceback
            traceback.print_exc()
            substance_concentrations = {}
    else:
        print("[GENE_NETWORK WARNING] No simulator in context - substance concentrations will be empty!")
        substance_concentrations = {}

    # Get gene network configuration
    associations = config.associations if config and hasattr(config, 'associations') else {}
    thresholds = config.thresholds if config and hasattr(config, 'thresholds') else {}

    # Use explicit parameter if provided, otherwise fallback to config
    if propagation_steps is None:
        propagation_steps = 20  # Default for synchronous mode (much fewer steps needed)
        if config and hasattr(config, 'gene_network') and config.gene_network is not None:
            propagation_steps = getattr(config.gene_network, 'propagation_steps', 20)

    # Ensure propagation_steps is an integer (may come as string from workflow JSON)
    propagation_steps = int(propagation_steps)

    # Default update mode is synchronous (much faster for long pathways like glycolysis)
    if update_mode is None:
        update_mode = "synchronous"

    # =========================================================================
    # GET GENE NETWORKS FROM CONTEXT
    # =========================================================================
    gene_networks = context.get('gene_networks', {})

    if not gene_networks:
        print("[GENE_NETWORK] No gene networks in context - run 'Initialize Gene Networks' first")
        return

    # =========================================================================
    # UPDATE EACH CELL'S GENE NETWORK
    # =========================================================================
    updated_cells = {}
    cells_with_gn = 0
    cells_without_gn = 0
    skipped_inactive = 0

    # Phenotypes that should not have gene network updates
    # Only Necrosis cells are truly dead - Growth_Arrest cells should still update
    # because they can transition back to Proliferation when conditions improve
    inactive_phenotypes = {'Necrosis'}

    for cell_id, cell in population.state.cells.items():
        # Skip cells in inactive states (Necrosis only - truly dead cells)
        if cell.state.phenotype in inactive_phenotypes:
            skipped_inactive += 1
            updated_cells[cell_id] = cell
            continue

        # Get local environment (with coordinate conversion from biological to solver grid)
        local_env = _get_local_environment(cell.state.position, substance_concentrations, config)

        # Get cell's gene network from context (NOT from cell.state)
        cell_gene_network: Optional[IGeneNetwork] = gene_networks.get(cell_id)

        # Skip if this cell has no gene network
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
            # Handle both dict format and ThresholdConfig object format
            threshold_config = thresholds.get(gene_name, {})
            if isinstance(threshold_config, dict):
                threshold_value = threshold_config.get('threshold', 0.0)
            elif hasattr(threshold_config, 'threshold'):
                # ThresholdConfig object from setup_associations
                threshold_value = threshold_config.threshold
            else:
                # Fallback: assume it's a raw number
                threshold_value = float(threshold_config) if threshold_config else 0.0

            # Set gene state: True if concentration above threshold
            gene_state = local_conc > threshold_value
            input_states[gene_name] = gene_state

        # Apply inputs to the cell's gene network
        cell_gene_network.set_input_states(input_states)

        # Propagate Boolean network using specified mode
        gene_states = cell_gene_network.step(propagation_steps, mode=update_mode)

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
          f"{skipped_inactive} necrotic)")

    # Collect output state statistics for context changes
    output_stats = {}
    sample_outputs = {}

    if cells_with_gn > 0:
        print(f"[GENE_NETWORK] Propagation steps: {propagation_steps}, mode: {update_mode}, associations: {len(associations)}")

        # Collect statistics on output node states across all cells
        for cell_id, cell in updated_cells.items():
            cell_gn: Optional[IGeneNetwork] = gene_networks.get(cell_id)
            if cell_gn:
                output_states = cell_gn.get_output_states()
                for node_name, state in output_states.items():
                    if node_name not in output_stats:
                        output_stats[node_name] = {'True': 0, 'False': 0}
                    output_stats[node_name]['True' if state else 'False'] += 1

        # Sample output: show fate gene states for first cell
        if updated_cells:
            sample_cell_id = next(iter(updated_cells.keys()))
            sample_gn: Optional[IGeneNetwork] = gene_networks.get(sample_cell_id)
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


def _get_local_environment(position, substance_concentrations, config=None):
    """
    Get local substance concentrations at a cell's position.

    Handles coordinate conversion from cell logical positions to grid indices.
    Cell positions are in logical coordinates (cell_index).
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
        # If cell positions are larger than grid size, scale them down
        if cell_x > nx or cell_y > ny:
            # Assume cell positions are in a larger logical grid
            # Scale to fit the concentration grid
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
            # Default to 0 if position not in grid
            local_env[substance_name] = 0.0

    return local_env

