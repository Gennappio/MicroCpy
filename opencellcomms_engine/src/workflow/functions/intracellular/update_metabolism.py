"""
Update intracellular metabolism for all cells.

This granular function updates ATP, metabolite concentrations, and other
intracellular state variables for each cell using Michaelis-Menten kinetics.

Users can customize this function to implement their own metabolic models.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
================================================================================

All workflow functions follow this pattern:

    def function_name(context: Dict[str, Any], user_param1=default1, ...):
        '''
        Args:
            context: The workflow execution context
            user_param1, ...: User-configurable parameters (shown in GUI)
        '''

CORE CONTEXT (read-mostly):
    population, simulator, config, dt, step, time, helpers, substances

USER CONTEXT (mutable):
    results, simulation_params, custom keys

Functions pull what they need from context and handle None gracefully.
================================================================================
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Update Metabolism",
    description="Update intracellular metabolism (ATP, metabolites)",
    category="INTRACELLULAR",
    # Only user-configurable parameters are listed
    parameters=[],
    # Explicitly specify inputs - only 'context'
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def update_metabolism(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Update intracellular metabolism for all cells.

    This function iterates through all cells and updates their metabolic state
    by calculating ATP production rates, oxygen/glucose consumption, and
    lactate production based on gene network states and local environment.

    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
            - simulator: Diffusion simulator (OPTIONAL - uses empty env if None)
            - config: Configuration object
            - dt: Time step
        **kwargs: Additional user parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # =========================================================================
    # EXTRACT CORE CONTEXT ITEMS
    # =========================================================================
    population = context.get('population')
    simulator = context.get('simulator')
    config = context.get('config')
    dt = context.get('dt', 0.1)

    # =========================================================================
    # VALIDATE REQUIRED CORE ITEMS
    # =========================================================================
    if population is None:
        print("[update_metabolism] No population in context - skipping")
        return

    # =========================================================================
    # GET SUBSTANCE CONCENTRATIONS (optional)
    # If no simulator, use empty environment
    # =========================================================================
    if simulator is not None:
        try:
            substance_concentrations = simulator.get_substance_concentrations()
        except Exception as e:
            print(f"[update_metabolism] Failed to get substance concentrations: {e}")
            substance_concentrations = {}
    else:
        print("[update_metabolism] No simulator - using empty environment")
        substance_concentrations = {}

    # =========================================================================
    # UPDATE EACH CELL'S METABOLIC STATE
    # =========================================================================
    updated_cells = {}
    skipped_inactive = 0

    # Phenotypes that should not have metabolism updates
    # Note: Apoptotic cells are removed, so we only skip Necrosis and Growth_Arrest
    inactive_phenotypes = {'Necrosis', 'Growth_Arrest'}

    for cell_id, cell in population.state.cells.items():
        # Skip cells in inactive states (Necrosis, Growth_Arrest)
        if cell.state.phenotype in inactive_phenotypes:
            skipped_inactive += 1
            updated_cells[cell_id] = cell
            continue

        # Age the cell
        cell.age(dt)

        # Get local environment for this cell
        local_env = _get_local_environment(cell.state.position, substance_concentrations, config)

        # Calculate and update metabolic state
        if hasattr(cell.custom_functions, 'update_cell_metabolic_state'):
            cell.custom_functions.update_cell_metabolic_state(cell, local_env, config)
        else:
            # Default implementation: calculate metabolism using Michaelis-Menten kinetics
            _update_cell_metabolic_state_default(cell, local_env, config)

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    # Log if cells were skipped
    if skipped_inactive > 0:
        print(f"[METABOLISM] Skipped {skipped_inactive} inactive cells (Necrosis/Growth_Arrest)")


def _get_local_environment(position, substance_concentrations, config=None):
    """
    Get local substance concentrations at a cell's position.

    Handles coordinate conversion from cell logical positions to grid indices.
    Cell positions are in logical coordinates (cell_index * cell_size_um).
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
        if cell_x > nx or cell_y > ny:
            # Scale to fit the concentration grid
            scale_factor = max(cell_x, cell_y) / max(nx, ny) if max(cell_x, cell_y) > 0 else 1.0
            scale_factor = max(1.0, scale_factor)
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
            # Try with original position as fallback
            if position[:2] in conc_grid:
                local_env[substance_name] = conc_grid[position[:2]]
            else:
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

    # FALLBACK: If no ATP pathway is active, use SubstanceConfig rates as defaults
    # This allows basic diffusion to work even without gene network initialization
    if not mito_atp and not glyco_atp:
        # Use uptake_rate from SubstanceConfig as fallback for each substance
        if config and hasattr(config, 'substances'):
            substances = config.substances
            if isinstance(substances, dict):
                for substance_name, substance_cfg in substances.items():
                    if hasattr(substance_cfg, 'uptake_rate') and substance_cfg.uptake_rate:
                        # Negative because uptake is consumption
                        reactions[substance_name] = -float(substance_cfg.uptake_rate)
                    if hasattr(substance_cfg, 'production_rate') and substance_cfg.production_rate:
                        # Positive because production adds to concentration
                        if substance_name not in reactions:
                            reactions[substance_name] = 0.0
                        reactions[substance_name] += float(substance_cfg.production_rate)

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

