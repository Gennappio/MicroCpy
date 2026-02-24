"""
Apply Associations to Inputs - Set gene inputs based on substance concentrations.

For each association (substance -> gene_input):
- Read substance concentration (cell-local from simulator, or flat from context)
- Compare to threshold
- Set gene_input = ON if concentration > threshold, else OFF
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation, IConfig


@register_function(
    display_name="Apply Associations to Inputs",
    description="Set gene input states based on substance concentrations and association thresholds",
    category="INITIALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def apply_associations_to_inputs(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Apply substance-to-gene associations.

    When a simulator is available (spatial model), reads cell-local concentrations
    from the simulator's spatial grid. Each cell gets its own input states based on
    the concentrations at its grid position.

    When no simulator is available (standalone gene network), falls back to flat
    context['substances'] values applied uniformly to all cells.
    """
    try:
        population: Optional[ICellPopulation] = context.get('population')
        config: Optional[IConfig] = context.get('config')
        simulator = context.get('simulator')

        # Get associations and thresholds from either context or config
        associations = context.get('associations', {})
        thresholds = context.get('thresholds', {})

        # If not in context directly, try config object
        if not associations and config:
            associations = getattr(config, 'associations', {}) or {}
            thresholds_config = getattr(config, 'thresholds', {}) or {}
            for gene_input, threshold_obj in thresholds_config.items():
                if hasattr(threshold_obj, 'threshold'):
                    thresholds[gene_input] = threshold_obj.threshold
                else:
                    thresholds[gene_input] = threshold_obj

        if not associations:
            print("[WARNING] No associations defined")
            return True

        # Get spatial concentrations from simulator (if available)
        substance_concentrations = {}
        if simulator and hasattr(simulator, 'get_substance_concentrations'):
            substance_concentrations = simulator.get_substance_concentrations()

        # Grid geometry (same pattern as _recalculate_metabolism)
        cell_size_um = 20.0
        if config and hasattr(config, 'domain'):
            domain = config.domain
            grid_spacing_x = domain.size_x.micrometers / domain.nx
            grid_spacing_y = domain.size_y.micrometers / domain.ny
        else:
            grid_spacing_x = grid_spacing_y = 30.0

        gene_networks = context.get('gene_networks', {})

        # --- Spatial model: per-cell local concentrations from simulator ---
        if population and substance_concentrations:
            print(f"[ASSOCIATIONS] Applying {len(associations)} associations (spatial, per-cell)")
            cells_on_count = {gene_input: 0 for gene_input in associations.values()}
            first_cell_logged = False

            for cell_id, cell in population.state.cells.items():
                # Get cell grid position
                pos = cell.state.position
                if len(pos) == 2:
                    cell_x, cell_y = pos
                else:
                    cell_x, cell_y = pos[0], pos[1]
                phys_x = cell_x * cell_size_um
                phys_y = cell_y * cell_size_um
                grid_x = int(phys_x / grid_spacing_x)
                grid_y = int(phys_y / grid_spacing_y)

                # Clamp to valid grid bounds
                if config and hasattr(config, 'domain'):
                    grid_x = max(0, min(config.domain.nx - 1, grid_x))
                    grid_y = max(0, min(config.domain.ny - 1, grid_y))

                # Per-cell input states based on LOCAL concentrations
                cell_input_states = {}
                for substance_name, gene_input in associations.items():
                    local_conc = substance_concentrations.get(
                        substance_name, {}).get((grid_x, grid_y), 0.0)
                    threshold = thresholds.get(gene_input, 0.0)
                    is_on = local_conc > threshold
                    cell_input_states[gene_input] = is_on
                    if is_on:
                        cells_on_count[gene_input] += 1

                # Log first cell for diagnostics
                if not first_cell_logged:
                    print(f"   [SAMPLE] cell={cell_id}, grid=({grid_x},{grid_y}):")
                    for substance_name, gene_input in associations.items():
                        local_conc = substance_concentrations.get(
                            substance_name, {}).get((grid_x, grid_y), 0.0)
                        threshold = thresholds.get(gene_input, 0.0)
                        status = "ON" if cell_input_states[gene_input] else "OFF"
                        print(f"     {substance_name} ({local_conc:.4g}) > {threshold} -> {gene_input} = {status}")
                    first_cell_logged = True

                # Write to context['gene_networks'] (new pattern)
                if cell_id in gene_networks:
                    cell_gn = gene_networks[cell_id]
                    for node_name, state in cell_input_states.items():
                        if node_name in cell_gn.nodes:
                            cell_gn.nodes[node_name].current_state = state

                # Write to cell.state.gene_network (old pattern, if present)
                if hasattr(cell.state, 'gene_network') and cell.state.gene_network:
                    for node_name, state in cell_input_states.items():
                        if node_name in cell.state.gene_network.nodes:
                            cell.state.gene_network.nodes[node_name].current_state = state

            total_cells = len(population.state.cells)
            print(f"   [SUMMARY] {total_cells} cells processed. Inputs ON counts:")
            for gene_input, count in cells_on_count.items():
                print(f"     {gene_input}: {count}/{total_cells} ON")

        # --- Fallback: no simulator (standalone gene network / initialization) ---
        elif population:
            substances = context.get('substances', {})
            input_states = {}

            print(f"[ASSOCIATIONS] Applying {len(associations)} associations (flat, uniform):")
            for substance_name, gene_input in associations.items():
                concentration = substances.get(substance_name, 0.0)
                threshold = thresholds.get(gene_input, 0.0)
                is_on = concentration > threshold
                input_states[gene_input] = is_on
                status = "ON" if is_on else "OFF"
                print(f"   {substance_name} ({concentration}) > {threshold} -> {gene_input} = {status}")

            # Apply uniformly to all cells
            for cell_id, cell_gn in gene_networks.items():
                for node_name, state in input_states.items():
                    if node_name in cell_gn.nodes:
                        cell_gn.nodes[node_name].current_state = state

            # Old-pattern backward compatibility
            for cell_id, cell in population.state.cells.items():
                if hasattr(cell.state, 'gene_network') and cell.state.gene_network:
                    for node_name, state in input_states.items():
                        if node_name in cell.state.gene_network.nodes:
                            cell.state.gene_network.nodes[node_name].current_state = state

            context['gene_network_inputs'] = input_states
        else:
            print("[WARNING] No population available")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to apply associations: {e}")
        import traceback
        traceback.print_exc()
        return False
