"""
Run one MaBoSS simulation step.

This function runs pyMaBoSS stochastic Boolean network simulation for one time step.
It updates input node states based on environment, runs MaBoSS, and updates cell gene states.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Run MaBoSS Step",
    description="Run one step of MaBoSS stochastic Boolean network simulation",
    category="INTRACELLULAR",
    inputs=["population", "simulator", "config", "helpers"],
    outputs=[],
    cloneable=False
)
def run_maboss_step(
    population,
    simulator,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Run one MaBoSS simulation step for all cells.

    For each cell:
    1. Get local environment (substance concentrations)
    2. Set MaBoSS input node states based on thresholds
    3. Run MaBoSS stochastic simulation for one time_tick
    4. Update cell gene states based on MaBoSS results

    Args:
        population: Population object containing all cells
        simulator: Diffusion simulator for substance concentrations
        config: Configuration object with simulation parameters
        helpers: Dictionary of helper functions from the engine
        **kwargs: Additional parameters (includes context)

    Returns:
        None (modifies population in-place)
    """
    # Get MaBoSS simulation object from the setup_maboss module
    # This is stored there during initialization for cross-stage access
    try:
        from src.workflow.functions.initialization import setup_maboss as maboss_module
        maboss_sim = getattr(maboss_module, '_MABOSS_SIM', None)
        maboss_config = getattr(maboss_module, '_MABOSS_CONFIG', {})
    except ImportError:
        maboss_sim = None
        maboss_config = {}

    if maboss_sim is None:
        print("[WARNING] MaBoSS not initialized. Call setup_maboss first.")
        return

    # Get current substance concentrations
    substance_concentrations = simulator.get_substance_concentrations()

    # Get associations and thresholds from config
    associations = config.associations if hasattr(config, 'associations') else {}
    thresholds = config.thresholds if hasattr(config, 'thresholds') else {}

    updated_cells = {}
    cells_processed = 0

    for cell_id, cell in population.state.cells.items():
        # Get local environment for this cell
        local_env = _get_local_environment(cell.state.position, substance_concentrations)

        # Build input states based on local environment
        input_states: Dict[str, bool] = {}
        for substance_name, gene_name in associations.items():
            local_conc = local_env.get(substance_name, 0.0)
            threshold_config = thresholds.get(gene_name, {})
            threshold_value = threshold_config.get('threshold', 0.0) if isinstance(threshold_config, dict) else 0.0

            # Set gene state: True if concentration BELOW threshold (stress condition)
            # For DNA_damage: low oxygen triggers damage
            gene_state = local_conc < threshold_value
            input_states[gene_name] = gene_state

        # Set input node states in MaBoSS
        for node_name, state in input_states.items():
            if node_name in maboss_sim.network:
                # Set initial state probability: [prob_OFF, prob_ON]
                if state:
                    maboss_sim.network.set_istate(node_name, [0.0, 1.0])  # ON
                else:
                    maboss_sim.network.set_istate(node_name, [1.0, 0.0])  # OFF

        # Run MaBoSS simulation
        result = maboss_sim.run()

        # Get final state probabilities
        final_states = result.get_last_states_probtraj()

        # Convert MaBoSS results to gene states
        gene_states = _maboss_result_to_gene_states(final_states, maboss_sim.network.keys())

        # Cache gene states for phenotype update
        cell._cached_gene_states = gene_states
        cell._cached_local_env = local_env

        # Update cell's gene states
        cell.state = cell.state.with_updates(gene_states=gene_states)
        updated_cells[cell_id] = cell
        cells_processed += 1

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    if cells_processed > 0:
        print(f"   [MaBoSS] Updated {cells_processed} cells")


def _get_local_environment(position, substance_concentrations: Dict[str, Any]) -> Dict[str, float]:
    """Get local substance concentrations at cell position."""
    local_env = {}

    for substance_name, concentration_field in substance_concentrations.items():
        try:
            # Get concentration at cell position (simplified - uses nearest grid point)
            x, y = int(position[0]), int(position[1])
            if hasattr(concentration_field, 'shape'):
                x = min(max(0, x), concentration_field.shape[0] - 1)
                y = min(max(0, y), concentration_field.shape[1] - 1)
                local_env[substance_name] = float(concentration_field[x, y])
            else:
                local_env[substance_name] = float(concentration_field)
        except (IndexError, TypeError):
            local_env[substance_name] = 0.0

    return local_env


def _maboss_result_to_gene_states(final_states, node_names) -> Dict[str, bool]:
    """Convert MaBoSS probability results to Boolean gene states."""
    gene_states = {}

    # Get the most probable final state
    if hasattr(final_states, 'iloc'):
        # DataFrame - get last row
        last_row = final_states.iloc[-1].to_dict()
        # Find state with highest probability
        max_prob = 0.0
        max_state = ""
        for state, prob in last_row.items():
            if state != 'Time' and prob > max_prob:
                max_prob = prob
                max_state = state
    else:
        # Dict
        max_state = max(final_states.items(), key=lambda x: x[1])[0] if final_states else ""

    # Parse the state string (e.g., "DNA_damage -- p53 -- Apoptosis")
    active_nodes = set(max_state.replace(" ", "").split("--")) if max_state else set()

    # Set gene states based on which nodes are active in the most probable state
    for node_name in node_names:
        gene_states[node_name] = node_name in active_nodes

    return gene_states

