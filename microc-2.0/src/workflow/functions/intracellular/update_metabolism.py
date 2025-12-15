"""
Update intracellular metabolism for all cells.

This granular function updates ATP, metabolite concentrations, and other
intracellular state variables for each cell using Michaelis-Menten kinetics.

Users can customize this function to implement their own metabolic models.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Update Metabolism",
    description="Update intracellular metabolism (ATP, metabolites)",
    category="INTRACELLULAR",
    outputs=[],
    cloneable=False
)
def update_metabolism(
    population,
    simulator,
    gene_network,
    config,
    dt: float,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Update intracellular metabolism for all cells.

    This function iterates through all cells and updates their metabolic state
    by calculating ATP production rates, oxygen/glucose consumption, and
    lactate production based on gene network states and local environment.

    Args:
        population: Population object containing all cells
        simulator: Diffusion simulator for substance concentrations
        gene_network: Gene network object for gene regulation
        config: Configuration object with simulation parameters
        dt: Time step (hours)
        helpers: Dictionary of helper functions from the engine
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # Get current substance concentrations from the simulator
    substance_concentrations = simulator.get_substance_concentrations()

    # Update each cell's metabolic state
    updated_cells = {}

    for cell_id, cell in population.state.cells.items():
        # Age the cell
        cell.age(dt)

        # Get local environment for this cell
        local_env = _get_local_environment(cell.state.position, substance_concentrations)

        # Calculate and update metabolic state
        if hasattr(cell.custom_functions, 'update_cell_metabolic_state'):
            cell.custom_functions.update_cell_metabolic_state(cell, local_env, config)
        else:
            # Default implementation: calculate metabolism using Michaelis-Menten kinetics
            _update_cell_metabolic_state_default(cell, local_env, config)

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


def _update_cell_metabolic_state_default(cell, local_environment: Dict[str, float], config):
    """
    Default implementation: Update cell's metabolic state using Michaelis-Menten kinetics.

    This calculates ATP production rate, oxygen/glucose consumption, and lactate
    production based on gene network states (glycoATP, mitoATP) and local
    substance concentrations.

    Users can customize this function or provide their own via custom_functions module.
    """
    # Calculate metabolism using Michaelis-Menten kinetics
    reactions = _calculate_cell_metabolism(local_environment, cell.state.__dict__, config)

    # Extract key metabolic values
    atp_rate = reactions.get('atp_rate', 0.0)
    oxygen_rate = reactions.get('Oxygen', 0.0)
    glucose_rate = reactions.get('Glucose', 0.0)
    lactate_rate = reactions.get('Lactate', 0.0)

    # Update cell's metabolic state
    metabolic_state = {
        'atp_rate': atp_rate,
        'oxygen_consumption': abs(oxygen_rate) if oxygen_rate < 0 else 0.0,
        'glucose_consumption': abs(glucose_rate) if glucose_rate < 0 else 0.0,
        'lactate_production': lactate_rate if lactate_rate > 0 else 0.0,
        'lactate_consumption': abs(lactate_rate) if lactate_rate < 0 else 0.0
    }

    # Update cell state
    cell.state = cell.state.with_updates(metabolic_state=metabolic_state)


def _calculate_cell_metabolism(local_environment: Dict[str, float], cell_state: Dict[str, Any], config) -> Dict[str, float]:
    """
    Calculate substance consumption/production rates using Michaelis-Menten kinetics.

    This implements the core metabolic model:
    - OXPHOS cells (mitoATP active): consume oxygen and glucose/lactate, produce ATP efficiently
    - Glycolytic cells (glycoATP active): consume glucose, produce lactate and protons
    - Mixed metabolism: both pathways active

    Args:
        local_environment: Dict of substance concentrations at cell location
        cell_state: Dict of cell state variables (gene_states, phenotype, etc.)
        config: Configuration object with metabolic parameters

    Returns:
        Dict of substance name -> reaction rate (mol/s/cell)
        Negative = consumption, Positive = production
    """
    # Get gene states from cell
    gene_states = cell_state.get('gene_states', {})
    mito_atp = gene_states.get('mitoATP', False)
    glyco_atp = gene_states.get('glycoATP', False)

    # Get local concentrations (with safe defaults)
    local_oxygen = local_environment.get('Oxygen', local_environment.get('oxygen', 0.0))
    local_glucose = local_environment.get('Glucose', local_environment.get('glucose', 0.0))
    local_lactate = local_environment.get('Lactate', local_environment.get('lactate', 0.0))

    # Get metabolic parameters from config (with defaults)
    km_oxygen = _get_config_param(config, 'KO2', 0.01)  # Michaelis constant for oxygen (mM)
    km_glucose = _get_config_param(config, 'KG', 0.5)   # Michaelis constant for glucose (mM)
    km_lactate = _get_config_param(config, 'KL', 1.0)   # Michaelis constant for lactate (mM)
    vmax_oxygen = _get_config_param(config, 'oxygen_vmax', 1.0e-16)   # Max oxygen uptake (mol/s/cell)
    vmax_glucose = _get_config_param(config, 'glucose_vmax', 3.0e-15) # Max glucose uptake (mol/s/cell)
    max_atp = _get_config_param(config, 'max_atp', 30.0)  # ATP per glucose molecule
    proton_coeff = _get_config_param(config, 'proton_coefficient', 0.01)  # Proton production coefficient

    # Initialize reaction rates
    reactions = {
        'Oxygen': 0.0,
        'Glucose': 0.0,
        'Lactate': 0.0,
        'H': 0.0,
        'pH': 0.0,
        'atp_rate': 0.0
    }

    atp_rate = 0.0

    # OXPHOS pathway (mitoATP active) - consumes oxygen and glucose/lactate
    if mito_atp:
        # Oxygen consumption with Michaelis-Menten kinetics
        oxygen_mm = local_oxygen / (km_oxygen + local_oxygen) if (km_oxygen + local_oxygen) > 0 else 0
        reactions['Oxygen'] = -vmax_oxygen * oxygen_mm

        # Glucose consumption for OXPHOS
        glucose_mm = local_glucose / (km_glucose + local_glucose) if (km_glucose + local_glucose) > 0 else 0
        glucose_consumption = (vmax_oxygen / 6.0) * glucose_mm * oxygen_mm
        reactions['Glucose'] = -glucose_consumption

        # Lactate consumption for OXPHOS
        lactate_mm = local_lactate / (km_lactate + local_lactate) if (km_lactate + local_lactate) > 0 else 0
        lactate_consumption = (vmax_oxygen * 2.0 / 6.0) * lactate_mm * oxygen_mm
        reactions['Lactate'] = -lactate_consumption

        # ATP production from OXPHOS (efficient)
        atp_rate += glucose_consumption * max_atp + lactate_consumption * (max_atp / 2.0)

        # Proton consumption during OXPHOS
        reactions['H'] = -glucose_consumption * proton_coeff

    # Glycolysis pathway (glycoATP active) - consumes glucose, produces lactate
    if glyco_atp:
        # Glucose consumption for glycolysis
        glucose_mm = local_glucose / (km_glucose + local_glucose) if (km_glucose + local_glucose) > 0 else 0
        oxygen_mm = local_oxygen / (km_oxygen + local_oxygen) if (km_oxygen + local_oxygen) > 0 else 0
        oxygen_factor = max(0.1, oxygen_mm)  # Glycolysis still needs some oxygen

        glucose_consumption_glyco = (vmax_glucose / 6.0) * glucose_mm * oxygen_factor
        reactions['Glucose'] += -glucose_consumption_glyco

        # Lactate production from glycolysis
        lactate_production = glucose_consumption_glyco * 3.0  # 3 lactate per glucose
        reactions['Lactate'] += lactate_production

        # Proton production from glycolysis
        reactions['H'] += lactate_production * proton_coeff

        # ATP production from glycolysis (inefficient - only 2 ATP per glucose)
        atp_rate += glucose_consumption_glyco * 2.0

        # Small oxygen consumption even in glycolysis
        reactions['Oxygen'] += -vmax_glucose * 0.5 * oxygen_factor

    # Store ATP rate
    reactions['atp_rate'] = atp_rate

    return reactions


def _get_config_param(config, param_name: str, default_value):
    """
    Safely get a parameter from config with fallback to default.

    Looks in: config.custom_parameters, config top-level, or returns default.
    """
    if not config:
        return default_value

    # Try custom_parameters section first
    if hasattr(config, 'custom_parameters'):
        custom_params = config.custom_parameters
        if isinstance(custom_params, dict) and param_name in custom_params:
            return custom_params[param_name]

    # Try top-level config
    if hasattr(config, param_name):
        return getattr(config, param_name)
    elif isinstance(config, dict) and param_name in config:
        return config[param_name]

    # Return default
    return default_value

