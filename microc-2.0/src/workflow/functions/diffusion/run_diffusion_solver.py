"""
Run the diffusion solver to update substance concentrations.

This function solves the diffusion PDE with source/sink terms from cells
for all substances (Oxygen, Glucose, Lactate, H+, pH).

The diffusion equation is:
    ∂C/∂t = D∇²C + R(x,y,z)

Where:
- C is the concentration field
- D is the diffusion coefficient
- R(x,y,z) is the reaction term (cell consumption/production)

Users can customize this to implement different diffusion solvers or boundary conditions.
"""

from typing import Dict, Any


def run_diffusion_solver(
    population,
    simulator,
    gene_network,
    config,
    dt: float,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Run the diffusion solver to update substance concentrations.

    This function:
    1. Collects reaction terms (consumption/production) from all cells
    2. Applies reaction terms to the diffusion equation
    3. Solves the PDE using FiPy for one time step
    4. Updates substance concentrations in the simulator

    Args:
        population: Population object containing all cells
        simulator: Diffusion simulator for substance concentrations
        gene_network: Gene network object for gene regulation
        config: Configuration object with simulation parameters
        dt: Time step for diffusion (hours)
        helpers: Dictionary of helper functions from the engine
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies simulator state in-place)
    """
    # Get current substance concentrations
    substance_concentrations = simulator.get_substance_concentrations()

    # Collect reaction terms from all cells
    reaction_terms = _collect_reaction_terms(population, substance_concentrations)

    # Apply reaction terms to simulator
    for substance_name, reactions in reaction_terms.items():
        if hasattr(simulator, 'set_reaction_term'):
            simulator.set_reaction_term(substance_name, reactions)

    # Solve diffusion PDE for one time step
    if hasattr(simulator, 'step'):
        simulator.step(dt)
    else:
        # Fallback: call the helper function
        helpers['run_diffusion']()


def _collect_reaction_terms(population, substance_concentrations):
    """
    Collect reaction terms (consumption/production rates) from all cells.

    For each substance, creates a grid of reaction rates based on cell
    metabolism at each position.

    Args:
        population: Population object with cells
        substance_concentrations: Dict of substance -> concentration grid

    Returns:
        Dict of substance_name -> reaction_grid
        Reaction rates are in mol/s/volume
    """
    reaction_terms = {}

    # Initialize reaction grids for each substance
    for substance_name in substance_concentrations.keys():
        reaction_terms[substance_name] = {}

    # Collect reactions from each cell
    for cell_id, cell in population.cells.items():
        position = cell.state.position

        # Get cell's metabolic state (calculated in update_metabolism)
        metabolic_state = cell.state.metabolic_state

        if not metabolic_state:
            continue

        # Get local environment
        local_env = {}
        for substance_name, conc_grid in substance_concentrations.items():
            local_env[substance_name] = conc_grid.get(position, 0.0)

        # Calculate cell's reaction rates
        if hasattr(cell.custom_functions, 'calculate_cell_metabolism'):
            reactions = cell.custom_functions.calculate_cell_metabolism(
                local_env,
                cell.state.__dict__,
                None  # config passed separately
            )
        else:
            # Use metabolic state if available
            reactions = {
                'Oxygen': -metabolic_state.get('oxygen_consumption', 0.0),
                'Glucose': -metabolic_state.get('glucose_consumption', 0.0),
                'Lactate': metabolic_state.get('lactate_production', 0.0) - metabolic_state.get('lactate_consumption', 0.0),
            }

        # Add cell's reactions to the grid
        for substance_name, rate in reactions.items():
            if substance_name in reaction_terms:
                if position not in reaction_terms[substance_name]:
                    reaction_terms[substance_name][position] = 0.0
                reaction_terms[substance_name][position] += rate

    return reaction_terms

