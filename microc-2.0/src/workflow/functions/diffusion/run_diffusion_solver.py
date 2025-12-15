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
from src.workflow.decorators import register_function


@register_function(
    display_name="Run Diffusion Solver",
    description="Solve diffusion PDE with cell reactions",
    category="DIFFUSION",
    parameters=[
        {
            "name": "max_iterations",
            "type": "INT",
            "description": "Maximum solver iterations",
            "default": 1000,
            "min_value": 1
        },
        {
            "name": "tolerance",
            "type": "FLOAT",
            "description": "Convergence tolerance",
            "default": 1e-6,
            "min_value": 0.0
        },
        {
            "name": "solver_type",
            "type": "STRING",
            "description": "Solver type",
            "default": "steady_state",
            "options": ["steady_state", "transient"]
        }
    ],
    outputs=[],
    cloneable=False
)
def run_diffusion_solver(
    population,
    simulator,
    gene_network,
    config,
    dt: float,
    helpers: Dict[str, Any],
    max_iterations: int = 1000,
    tolerance: float = 1e-6,
    solver_type: str = "steady_state",
    **kwargs
) -> None:
    """
    Run the diffusion solver to update substance concentrations.

    This function:
    1. Configures substances if not already configured (first run)
    2. Collects reaction terms (consumption/production) from all cells
    3. Applies reaction terms to the diffusion equation
    4. Solves the PDE using FiPy for one time step
    5. Updates substance concentrations in the simulator

    Args:
        population: Population object containing all cells
        simulator: Diffusion simulator for substance concentrations
        gene_network: Gene network object for gene regulation
        config: Configuration object with simulation parameters
        dt: Time step for diffusion (hours)
        helpers: Dictionary of helper functions from the engine
        max_iterations: Maximum iterations for solver
        tolerance: Convergence tolerance for solver
        solver_type: Type of solver ("steady_state" or "transient")
        **kwargs: Additional parameters including individual substance definitions
                 (name, diffusion_coeff, production_rate, uptake_rate, initial_value,
                  boundary_value, boundary_type, unit, gene_network_input)

    Returns:
        None (modifies simulator state in-place)
    """
    # Collect substance definitions from kwargs
    # Each substance is passed as individual parameters with keys like:
    # name, diffusion_coeff, production_rate, etc.
    substances = _collect_substance_definitions(kwargs)

    # Configure substances if provided and not already configured
    if substances and (not hasattr(config, 'substances') or not config.substances):
        _configure_substances(config, simulator, substances)

    # Configure solver parameters if provided
    if hasattr(simulator, 'set_solver_params'):
        simulator.set_solver_params(
            max_iterations=max_iterations,
            tolerance=tolerance,
            solver_type=solver_type
        )

    # Get current substance concentrations
    substance_concentrations = simulator.get_substance_concentrations()

    # Collect reaction terms from all cells
    # Prefer the same implementation used by the non-workflow engine so that
    # workflow and classic YAML runs produce identical diffusion inputs where possible.
    position_reactions = None

    # Only call CellPopulation.get_substance_reactions if the configuration
    # has a valid environment attached. In MinimalConfig (pure-workflow runs),
    # environment may be absent, and CellPopulation._get_local_environment
    # would raise; in that case we gracefully fall back to the local
    # implementation based on cell.metabolic_state.
    can_use_population_reactions = (
        hasattr(population, "get_substance_reactions")
        and hasattr(config, "environment")
        and getattr(config, "environment") is not None
    )

    if can_use_population_reactions:
        try:
            # population.get_substance_reactions already returns {position: {substance: rate}}
            position_reactions = population.get_substance_reactions(substance_concentrations)
        except Exception as e:
            print(
                "[WORKFLOW] Warning: get_substance_reactions failed in run_diffusion_solver, "
                f"falling back to local reaction-term computation: {e}"
            )

    if position_reactions is None:
        # Fallback to local implementation for non-CellPopulation objects
        # or when get_substance_reactions is not available / failed
        reaction_terms = _collect_reaction_terms(population, substance_concentrations)
        # MultiSubstanceSimulator.update() expects a dict of {position: {substance: rate}}
        # Convert from {substance: {position: rate}} to {position: {substance: rate}}
        position_reactions = _convert_to_position_reactions(reaction_terms)

    # Update diffusion with reactions (steady state solver)
    simulator.update(position_reactions)


def _collect_substance_definitions(kwargs):
    """
    Collect substance definitions from kwargs.

    The workflow executor merges parameters from multiple parameter nodes,
    so we receive individual substance parameters with keys like:
    - name, diffusion_coeff, production_rate, uptake_rate, etc.

    We need to group these into substance definitions.

    Args:
        kwargs: Dictionary of all parameters

    Returns:
        List of substance definitions
    """
    substances = []

    # Check if we have substance parameters
    # Each parameter node contributes its parameters to kwargs
    # We look for 'name' keys to identify substance definitions

    # Collect all substance names from kwargs
    # Parameters from different nodes are merged, so we need to identify
    # which parameters belong to which substance

    # Since each substance comes from a separate parameter node,
    # we can collect them by looking for the 'name' parameter
    # But kwargs is flat, so we need a different approach

    # Actually, the workflow executor should pass each parameter node's
    # parameters separately. Let me check how parameters are merged...

    # For now, let's assume substances are passed as a list
    # (we'll need to update this based on how the executor merges params)

    if 'substances' in kwargs:
        return kwargs['substances']

    # Alternative: collect individual substance definitions
    # If we have 'name' in kwargs, it's a single substance
    if 'name' in kwargs:
        substances.append({
            'name': kwargs.get('name'),
            'diffusion_coeff': kwargs.get('diffusion_coeff', 1e-10),
            'production_rate': kwargs.get('production_rate', 0.0),
            'uptake_rate': kwargs.get('uptake_rate', 0.0),
            'initial_value': kwargs.get('initial_value', 0.0),
            'boundary_value': kwargs.get('boundary_value', 0.0),
            'boundary_type': kwargs.get('boundary_type', 'fixed'),
            'unit': kwargs.get('unit', 'mM'),
            'gene_network_input': kwargs.get('gene_network_input', None)
        })

    return substances


def _configure_substances(config, simulator, substances):
    """
    Configure substances in the simulator (called once on first run).

    Args:
        config: Configuration object
        simulator: Diffusion simulator
        substances: List of substance definitions (each with name, diffusion_coeff, etc.)
    """
    from src.config.config import SubstanceConfig

    print(f"[WORKFLOW] Configuring substances in diffusion solver")

    # Initialize substances dict if not exists
    if not hasattr(config, 'substances'):
        config.substances = {}

    # Initialize associations dict
    if not hasattr(config, 'associations'):
        config.associations = {}

    # Add each substance
    from src.core.units import Concentration

    for sub_def in substances:
        name = sub_def['name']

        # Create SubstanceConfig with all required parameters
        sub_config = SubstanceConfig(
            name=name,
            diffusion_coeff=sub_def.get('diffusion_coeff', 1e-10),
            production_rate=sub_def.get('production_rate', 0.0),
            uptake_rate=sub_def.get('uptake_rate', 0.0),
            initial_value=Concentration(sub_def.get('initial_value', 0.0), sub_def.get('unit', 'mM')),
            boundary_value=Concentration(sub_def.get('boundary_value', 0.0), sub_def.get('unit', 'mM')),
            boundary_type=sub_def.get('boundary_type', 'fixed')
        )

        config.substances[name] = sub_config

        # Set gene network association if provided
        gene_network_input = sub_def.get('gene_network_input')
        if gene_network_input:
            config.associations[name] = gene_network_input

        print(f"   [+] Configured substance: {name} (D={sub_config.diffusion_coeff:.2e}, init={sub_config.initial_value})")

    # Reinitialize simulator with new substances
    if hasattr(simulator, 'initialize_substances'):
        simulator.initialize_substances(config.substances)

    print(f"   [+] Configured {len(config.substances)} substances in diffusion solver")


def _convert_to_position_reactions(reaction_terms):
    """
    Convert reaction terms from {substance: {position: rate}} to {position: {substance: rate}}.

    The MultiSubstanceSimulator.update() expects reactions organized by position.

    Args:
        reaction_terms: Dict of {substance_name: {position: rate}}

    Returns:
        Dict of {position: {substance_name: rate}}
    """
    position_reactions = {}

    for substance_name, position_rates in reaction_terms.items():
        for position, rate in position_rates.items():
            if position not in position_reactions:
                position_reactions[position] = {}
            position_reactions[position][substance_name] = rate

    return position_reactions


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
    for cell_id, cell in population.state.cells.items():
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

