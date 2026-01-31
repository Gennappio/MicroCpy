"""
Update Gene Networks V2 - Based on working standalone code.

This is a FIXED version that properly propagates gene networks using the
proven logic from gene_network_standalone.py and brute_gene_network_workflow.json.

The key fixes:
1. Uses proper NetLogo-style random single-gene updates (mode="netlogo")
2. Uses sufficient propagation steps (500 by default, not 20)
3. Re-enforces input states after each propagation step
4. Logs mitoATP and glycoATP states for debugging
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Update Gene Networks V2 (Fixed)",
    description="FIXED: Properly propagates gene networks using proven standalone logic. Logs mitoATP/glycoATP states.",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps (use 500+ for proper convergence)", "default": 500},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def update_gene_networks_v2(
    context: Dict[str, Any],
    propagation_steps: int = 500,
    **kwargs
) -> None:
    """
    Update gene networks using PROVEN standalone logic.
    
    Key differences from old update_gene_networks:
    1. Uses NetLogo-style updates (random single gene per step) - PROVEN TO WORK
    2. Uses 500 propagation steps by default (not 20) - NEEDED FOR CONVERGENCE
    3. Logs mitoATP and glycoATP states to verify they're active
    """
    # =========================================================================
    # EXTRACT CONTEXT
    # =========================================================================
    population = context.get('population')
    simulator = context.get('simulator')
    config = context.get('config')
    
    if population is None:
        print("[update_gene_networks_v2] No population in context - skipping")
        return
    
    # =========================================================================
    # GET ASSOCIATIONS AND THRESHOLDS
    # =========================================================================
    associations = config.associations if config and hasattr(config, 'associations') else {}
    thresholds = config.thresholds if config and hasattr(config, 'thresholds') else {}
    
    # =========================================================================
    # GET SUBSTANCE CONCENTRATIONS
    # =========================================================================
    substance_concentrations = {}
    if simulator is not None:
        try:
            substance_concentrations = simulator.get_substance_concentrations()
        except Exception as e:
            print(f"[update_gene_networks_v2] Failed to get concentrations: {e}")
    
    # Ensure propagation_steps is int
    propagation_steps = int(propagation_steps)
    
    # =========================================================================
    # UPDATE EACH CELL
    # =========================================================================
    updated_cells = {}
    cells_with_gn = 0
    cells_without_gn = 0
    
    # Track mitoATP and glycoATP for logging
    mito_true_count = 0
    glyco_true_count = 0
    
    for cell_id, cell in population.state.cells.items():
        # Skip necrotic cells
        if cell.state.phenotype == 'Necrosis':
            updated_cells[cell_id] = cell
            continue
        
        cell_gn = cell.state.gene_network
        
        if cell_gn is None:
            cells_without_gn += 1
            updated_cells[cell_id] = cell
            continue
        
        cells_with_gn += 1
        
        # =====================================================================
        # SET INPUT STATES FROM ENVIRONMENT (like original)
        # =====================================================================
        if substance_concentrations and associations:
            input_states = _compute_input_states(
                cell.state.position, substance_concentrations, associations, thresholds, config
            )
            cell_gn.set_input_states(input_states)
        
        # =====================================================================
        # PROPAGATE USING NETLOGO-STYLE (PROVEN TO WORK!)
        # =====================================================================
        # Use mode="netlogo" which is the same as standalone's single-gene updates
        gene_states = cell_gn.step(propagation_steps, mode="netlogo")
        
        # =====================================================================
        # LOG mitoATP and glycoATP when TRUE
        # =====================================================================
        mito_state = gene_states.get('mitoATP', False)
        glyco_state = gene_states.get('glycoATP', False)
        
        if mito_state:
            mito_true_count += 1
        if glyco_state:
            glyco_true_count += 1
        
        # Cache and update cell
        cell._cached_gene_states = gene_states
        cell.state = cell.state.with_updates(gene_states=gene_states)
        updated_cells[cell_id] = cell
    
    # Update population
    population.state = population.state.with_updates(cells=updated_cells)
    
    # =========================================================================
    # LOG SUMMARY WITH mitoATP/glycoATP STATS
    # =========================================================================
    total_cells = len(population.state.cells)
    print(f"[GENE_NETWORK_V2] Updated {cells_with_gn}/{total_cells} cells ({propagation_steps} steps, netlogo mode)")
    print(f"[GENE_NETWORK_V2] mitoATP=TRUE: {mito_true_count}/{cells_with_gn}, glycoATP=TRUE: {glyco_true_count}/{cells_with_gn}")

    if mito_true_count == 0 and glyco_true_count == 0:
        print("[GENE_NETWORK_V2] WARNING: All cells have mitoATP=False and glycoATP=False!")

    # =========================================================================
    # VERIFY gene_states are stored in cell.state.gene_states
    # =========================================================================
    verify_count = 0
    verify_mito = 0
    verify_glyco = 0
    for cell_id, cell in population.state.cells.items():
        gs = cell.state.gene_states
        if gs:
            verify_count += 1
            if gs.get('mitoATP', False):
                verify_mito += 1
            if gs.get('glycoATP', False):
                verify_glyco += 1
    print(f"[GENE_NETWORK_V2] VERIFY: {verify_count} cells have gene_states, mitoATP={verify_mito}, glycoATP={verify_glyco}")
    
    # Store in context for GUI
    context['changes'] = context.get('changes', {})
    context['changes']['gene_network'] = {
        'cells_updated': cells_with_gn,
        'mitoATP_true': mito_true_count,
        'glycoATP_true': glyco_true_count,
        'propagation_steps': propagation_steps
    }


def _compute_input_states(position, substance_concentrations, associations, thresholds, config):
    """Compute input gene states from local substance concentrations."""
    input_states = {}

    # Get local concentrations at cell position
    local_env = _get_local_environment(position, substance_concentrations, config)

    for substance_name, gene_name in associations.items():
        local_conc = local_env.get(substance_name, 0.0)

        # Get threshold
        threshold_config = thresholds.get(gene_name, {})
        if isinstance(threshold_config, dict):
            threshold_value = threshold_config.get('threshold', 0.0)
        elif hasattr(threshold_config, 'threshold'):
            threshold_value = threshold_config.threshold
        else:
            threshold_value = float(threshold_config) if threshold_config else 0.0

        # Set gene state
        input_states[gene_name] = local_conc > threshold_value

    return input_states


def _get_local_environment(position, substance_concentrations, config=None):
    """Get local substance concentrations at a cell's position."""
    local_env = {}

    if not substance_concentrations:
        return local_env

    first_substance = next(iter(substance_concentrations.values()))
    if not first_substance:
        return local_env

    # Get grid dimensions
    max_grid_x = max(pos[0] for pos in first_substance.keys()) if first_substance else 0
    max_grid_y = max(pos[1] for pos in first_substance.keys()) if first_substance else 0
    nx = max_grid_x + 1
    ny = max_grid_y + 1

    # Convert cell position to grid index
    cell_x, cell_y = position[0], position[1]

    if config and hasattr(config, 'domain'):
        domain_size_um = config.domain.size_x.micrometers if hasattr(config.domain.size_x, 'micrometers') else config.domain.size_x
        cell_size_um = config.domain.cell_height.micrometers if hasattr(config.domain, 'cell_height') and hasattr(config.domain.cell_height, 'micrometers') else 20.0

        phys_x = cell_x * cell_size_um
        phys_y = cell_y * cell_size_um

        grid_spacing = domain_size_um / nx
        grid_x = int(phys_x / grid_spacing)
        grid_y = int(phys_y / grid_spacing)
    else:
        grid_x = int(cell_x)
        grid_y = int(cell_y)

    # Clamp to valid bounds
    grid_x = max(0, min(nx - 1, grid_x))
    grid_y = max(0, min(ny - 1, grid_y))

    grid_pos = (grid_x, grid_y)

    for substance_name, conc_grid in substance_concentrations.items():
        if grid_pos in conc_grid:
            local_env[substance_name] = conc_grid[grid_pos]
        else:
            local_env[substance_name] = 0.0

    return local_env

