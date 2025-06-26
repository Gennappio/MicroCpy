import numpy as np
import math
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

# Import custom metabolism functions from separate file
try:
    import os
    import sys
    # Add the current directory to path to import the metabolism file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    import jayatilake_experiment_custom_metabolism as metabolism
    METABOLISM_FUNCTIONS_AVAILABLE = True
    print("✅ Imported custom metabolism functions from jayatilake_experiment_custom_metabolism.py")
except ImportError as e:
    print(f"⚠️  Could not import custom metabolism functions: {e}")
    METABOLISM_FUNCTIONS_AVAILABLE = False
    metabolism = None



# ============================================================================
# END OF INTEGRATED CUSTOM METABOLISM FUNCTIONS
# ============================================================================


def get_parameter_from_config(config, param_name: str, default_value=None, section=None):
    """
    Config-agnostic parameter lookup - works with any configuration structure.
    Looks for parameters in multiple possible locations.

    Args:
        config: Configuration object (can be None for global config access)
        param_name: Name of the parameter to look for
        default_value: Default value if parameter not found
        section: Optional section name (e.g., 'metabolism', 'custom_parameters')
    """
    # If no config provided, return default
    if not config:
        return default_value

    # If section specified, look in that section first
    if section:
        section_data = getattr(config, section, {})
        if isinstance(section_data, dict) and param_name in section_data:
            return section_data[param_name]

    # Look in custom_parameters section first (for custom function parameters)
    custom_params = getattr(config, 'custom_parameters', {})
    if isinstance(custom_params, dict) and param_name in custom_params:
        return custom_params[param_name]

    # Look at top level of config (for general parameters like cell_cycle_time)
    if hasattr(config, param_name):
        return getattr(config, param_name)
    elif isinstance(config, dict) and param_name in config:
        return config[param_name]

    # If still not found, return default value
    return default_value


@dataclass
class MetabolicState:
    """Represents the metabolic state of a cell"""
    metabolism_type: int  # 1=glycolysis, 2=OXPHOS, 3=quiescent, 4=mixed
    atp_rate: float
    oxygen_consumption: float
    glucose_consumption: float
    lactate_production: float
    lactate_consumption: float
    proton_production: float


def custom_initialize_cell_placement(grid_size: Tuple[int, int], simulation_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Initialize cells in a spheroid configuration for metabolic symbiosis experiment.
    Places cells in center with some initial heterogeneity.

    IMPORTANT: This function receives the FiPy grid size, but should calculate
    biological cell positions based on cell_height parameter!
    """
    fipy_nx, fipy_ny = grid_size  # This is the FiPy grid (e.g., 40x40)

    # Calculate biological cell grid based on cell_height
    # Get domain size and cell_height from simulation_params
    domain_size_um = simulation_params.get('domain_size_um', 600.0)  # Default 600 μm
    cell_height_um = simulation_params.get('cell_height_um', 20.0)   # Default 20 μm

    # Calculate biological cell grid size
    bio_nx = int(domain_size_um / cell_height_um)  # e.g., 600/80 = 7.5 → 7
    bio_ny = int(domain_size_um / cell_height_um)

    print(f"🔍 BIOLOGICAL CELL GRID DEBUG:")
    print(f"   FiPy grid: {fipy_nx}×{fipy_ny}")
    print(f"   Domain size: {domain_size_um} μm")
    print(f"   Cell height: {cell_height_um} μm")
    print(f"   Biological cell grid: {bio_nx}×{bio_ny}")
    print(f"   Biological cell size: {cell_height_um} μm")

    # Use biological cell grid for placement
    center_x, center_y = bio_nx // 2, bio_ny // 2

    # Get initial cell count from simulation parameters
    initial_count = simulation_params.get('initial_cell_count', 100)
    
    placements = []

    # Place cells in expanding spherical pattern on biological cell grid
    radius = 1
    cells_placed = 0

    while cells_placed < initial_count and radius < min(bio_nx, bio_ny) // 2:
        for x in range(max(0, center_x - radius), min(bio_nx, center_x + radius + 1)):
            for y in range(max(0, center_y - radius), min(bio_ny, center_y + radius + 1)):
                if cells_placed >= initial_count:
                    break
                
                # Check if position is within radius
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                if distance <= radius:
                    # Convert biological cell coordinates to FiPy coordinates
                    # Scale from biological grid to FiPy grid
                    fipy_x = int(x * fipy_nx / bio_nx)
                    fipy_y = int(y * fipy_ny / bio_ny)

                    # Ensure coordinates are within FiPy grid bounds
                    fipy_x = max(0, min(fipy_nx - 1, fipy_x))
                    fipy_y = max(0, min(fipy_ny - 1, fipy_y))

                    # No randomness - all cells start as Proliferation
                    phenotype = "Proliferation"

                    placements.append({
                        'position': (fipy_x, fipy_y),  # Use FiPy coordinates
                        'phenotype': phenotype,
                        'bio_position': (x, y),  # Store biological position for debugging
                        'bio_grid_size': (bio_nx, bio_ny)
                    })
                    cells_placed += 1
            
            if cells_placed >= initial_count:
                break
        
        radius += 1
    
    return placements


# def custom_calculate_cell_metabolism(local_environment: Dict[str, float], cell_state: Dict[str, Any], config: Any = None) -> Dict[str, float]:
#     """
#     Calculate substance consumption/production rates using Jayathilake metabolism functions.
#     Uses gene states (glycoATP, mitoATP, GLUT1, MCT1, MCT4) and Michaelis kinetics.

#     Implements metabolic symbiosis model from Jayathilake et al. 2024 with metabolism exceptions:
#     - OXPHOS cells consume lactate and oxygen, produce minimal lactate
#     - Glycolytic cells consume glucose, produce lactate
#     - Metabolic switching based on oxygen and nutrient availability
#     """
#     # Check if metabolism functions are available
#     if not METABOLISM_FUNCTIONS_AVAILABLE:
#         # Fallback to simple metabolism if functions not available
#         return {
#             'Oxygen': -1e-16,
#             'Glucose': -1e-16,
#             'Lactate': 0.0,
#             'H': 0.0,
#             'FGF': 0.0,
#             'TGFA': 0.0,
#             'HGF': 0.0
#         }
#         # No custom metabolism functions available - fail hard
#         raise ImportError("Custom metabolism functions not available and no fallback implemented")

#     # Get gene states from cell state (they should be stored there after gene network update)
#     gene_states = cell_state.get('gene_states', {})

#     # Get local concentrations
#     local_oxygen = local_environment.get('Oxygen', 0.0)
#     local_glucose = local_environment.get('Glucose', 0.0)
#     local_lactate = local_environment.get('Lactate', 0.0)
#     local_h = local_environment.get('H', 0.0)

#     # Get Michaelis constants and metabolic parameters from config
#     KG = get_parameter_from_config(config, 'KG')           # Michaelis constant for glucose
#     KO2 = get_parameter_from_config(config, 'KO2')         # Michaelis constant for oxygen
#     KL = get_parameter_from_config(config, 'KL')           # Michaelis constant for lactate
#     mu_o2 = get_parameter_from_config(config, 'mu_o2')     # Oxygen utilization rate
#     A0 = get_parameter_from_config(config, 'A0')           # Reference ATP yield factor
#     beta = get_parameter_from_config(config, 'beta')       # Proton production coefficient
#     K_glyco = get_parameter_from_config(config, 'K_glyco') # Glycolysis oxygen factor

#     # Metabolic thresholds (from article pages 5-7) - removed as per TODO
#     # Metabolism is now purely defined by Michaelis-Menten kinetics, no arbitrary thresholds

#     # Initialize reactions
#     reactions = {
#         'Oxygen': 0.0,
#         'Glucose': 0.0,
#         'Lactate': 0.0,
#         'H': 0.0,
#         'FGF': 0.0,
#         'TGFA': 0.0,
#         'HGF': 0.0
#     }

#     # Only consume/produce if cell is alive (not necrotic)
#     if gene_states.get('Necrosis', False):
#         return reactions

#     # Get gene states
#     mito_atp = 1.0 if gene_states.get('mitoATP', False) else 0.0
#     glyco_atp = 1.0 if gene_states.get('glycoATP', False) else 0.0

#     atp_rate = metabolism.atp_production(mu_o2, A0, local_oxygen, KO2, local_glucose, KG, mito_atp, glyco_atp)

#     # Store ATP rate in cell state for division decisions
#     cell_state['atp_rate'] = atp_rate

#     # Metabolic pathway selection based purely on gene states and Michaelis-Menten kinetics
#     if mito_atp > 0:
#         # OXPHOS pathway active
#         reactions['Lactate'] = -metabolism.lactate_consumption(mu_o2, local_oxygen, KO2, local_lactate, KL, mito_atp)
#         reactions['Oxygen'] = -metabolism.oxygen_consumption(mu_o2, local_oxygen, KO2, mito_atp, 0.0, K_glyco)
#         # Proton consumption during OXPHOS
#         reactions['H'] = -metabolism.proton_production(beta, A0, mu_o2, local_glucose, KG, 0.0)

#     if glyco_atp > 0:
#         # Glycolysis pathway active (when glycoATP gene active and GLUT1 transporter present)
#         reactions['Glucose'] = -metabolism.glucose_consumption(mu_o2, A0, local_oxygen, KO2, local_glucose, KG, 0.0, glyco_atp)
#         reactions['Lactate'] = metabolism.lactate_production(mu_o2, A0, local_glucose, KG, glyco_atp)
#         reactions['H'] = metabolism.proton_production(beta, A0, mu_o2, local_glucose, KG, glyco_atp)
#         reactions['Oxygen'] = -metabolism.oxygen_consumption(mu_o2, local_oxygen, KO2, 0.0, glyco_atp, K_glyco)


#     # Apply environmental constraints - don't consume more than available
#     for substance in ['Oxygen', 'Glucose', 'Lactate']:
#         local_conc = local_environment.get(substance, 0.0)
#         if reactions[substance] < 0:  # Consumption
#             max_consumption = abs(reactions[substance])
#             available = local_conc
#             if available < max_consumption:
#                 reactions[substance] = -available * 0.9  # Leave some residual

#     return reactions


def custom_check_cell_division(cell_state: Dict[str, Any], local_environment: Dict[str, float], config: Any = None) -> bool:
    """
    Determine if cell should attempt division based on ATP rate and cell cycle time.
    Config-agnostic function that works with any configuration structure.
    """
    # Get parameters using config-agnostic lookup
    atp_threshold = get_parameter_from_config(config, 'atp_threshold', 0.8)
    max_atp = get_parameter_from_config(config, 'max_atp', 30)
    cell_cycle_time = get_parameter_from_config(config, 'cell_cycle_time', 240)

    # Check ATP rate from cell state
    atp_rate = cell_state.get('atp_rate', 0.0)
    atp_rate_normalized = atp_rate / max_atp if max_atp > 0 else 0

    # Check cell age from cell state
    cell_age = cell_state.get('age', 0)

    # Check phenotype from cell state
    phenotype = cell_state.get('phenotype', 'Growth_Arrest')

    return (atp_rate_normalized > atp_threshold and
            cell_age > cell_cycle_time and
            phenotype == "Proliferation")


def custom_check_cell_death(cell_state: Dict[str, Any], local_environment: Dict[str, float]) -> bool:
    """
    Determine if cell should die based on gene network state and environmental conditions.
    """
    # Get gene states from cell state
    gene_states = cell_state.get('gene_states', {})

    # Cell dies if Necrosis or Apoptosis genes are active
    if gene_states.get('Necrosis', False) or gene_states.get('Apoptosis', False):
        return True

    # Additional death conditions could be added here
    # For example, extreme hypoxia, nutrient starvation, etc.
    oxygen = local_environment.get('Oxygen', 0.0)
    if oxygen < 0.001:  # Severe hypoxia
        return True

    return False


# NOTE: custom_get_substance_reactions was removed because it was redundant
# with custom_calculate_cell_metabolism. Both functions did the same thing.
# The system now uses custom_calculate_cell_metabolism via cell.calculate_metabolism().


def custom_should_divide(cell, config: Any) -> bool:
    """
    Determine if cell should attempt division based on gene network state and cell conditions.
    """
    # Only proliferative cells can divide
    if not hasattr(cell, 'state') or cell.state.phenotype != "Proliferation":
        return False

    # Check if cell has sufficient age (basic cell cycle time)
    # Get cell cycle time using config-agnostic lookup
    cell_cycle_time = get_parameter_from_config(config, 'cell_cycle_time', 240)  # iterations
    if cell.state.age < cell_cycle_time:
        return False

    # Additional checks could be added here based on gene states
    # For now, use simple age-based division for proliferative cells
    return True


def custom_get_cell_color(cell, gene_states: Dict[str, bool], config: Any) -> str:
    """
    Get cell color based on gene network outputs (matching NetLogo visualization).
    """
    # Phenotype-based colors (highest priority)
    if gene_states.get('Necrosis', False):
        return "black"
    elif gene_states.get('Apoptosis', False):
        return "red"

    # Metabolic state colors based on gene network outputs
    glyco_active = gene_states.get('glycoATP', False)
    mito_active = gene_states.get('mitoATP', False)

    if glyco_active and not mito_active:
        return "green"      # Glycolysis only
    elif not glyco_active and mito_active:
        return "blue"       # OXPHOS only
    elif glyco_active and mito_active:
        return "violet"     # Mixed metabolism
    else:
        return "gray"       # Quiescent
