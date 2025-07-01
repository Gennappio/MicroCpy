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

    # Track coordinate collisions
    used_positions = set()
    collision_count = 0

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

                    # Check for coordinate collisions
                    fipy_pos = (fipy_x, fipy_y)
                    if fipy_pos in used_positions:
                        collision_count += 1
                        if collision_count <= 5:
                            print(f"   ⚠️  COLLISION: Cell {cells_placed} at bio({x},{y}) → fipy({fipy_x},{fipy_y}) already used!")
                        continue  # Skip this cell to avoid overwriting

                    used_positions.add(fipy_pos)

                    # Debug coordinate mapping for first few cells
                    if cells_placed < 5:
                        print(f"   Cell {cells_placed}: bio({x},{y}) → fipy({fipy_x},{fipy_y})")

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

    # Summary
    print(f"   📊 Placement summary: {len(placements)} cells placed, {collision_count} collisions avoided")

    return placements


def custom_calculate_cell_metabolism(local_environment: Dict[str, float], cell_state: Dict[str, Any], config: Any = None) -> Dict[str, float]:
    """
    Calculate substance consumption/production rates using NetLogo-style Michaelis-Menten kinetics.
    Uses gene states (glycoATP, mitoATP, GLUT1, MCT1, MCT4) and NetLogo-compatible parameters.

    Implements NetLogo MicroC reaction term calculations with Michaelis-Menten kinetics:
    - OXPHOS cells consume lactate and oxygen, produce minimal lactate
    - Glycolytic cells consume glucose, produce lactate and protons
    - Metabolic switching based on gene network states
    """
    # Check if metabolism functions are available
    if not METABOLISM_FUNCTIONS_AVAILABLE: # TODO: remove. just fail gently
        # Fallback to simple metabolism if functions not available
        return {
            'Oxygen': -1e-16,
            'Glucose': -1e-16,
            'Lactate': 0.0,
            'H': 0.0,
            'FGF': 0.0,
            'TGFA': 0.0,
            'HGF': 0.0
        }

    # Get gene states from cell state (they should be stored there after gene network update)
    gene_states = cell_state.get('gene_states', {})

    # Get local concentrations
    local_oxygen = local_environment.get('Oxygen', 0.0)
    local_glucose = local_environment.get('Glucose', 0.0)
    local_lactate = local_environment.get('Lactate', 0.0)
    local_h = local_environment.get('H', 0.0)

    # Get NetLogo-compatible Michaelis constants and metabolic parameters from config
    km_oxygen = get_parameter_from_config(config, 'the_optimal_oxygen', 0.005)      # NetLogo Km for oxygen
    km_glucose = get_parameter_from_config(config, 'the_optimal_glucose', 0.04)     # NetLogo Km for glucose
    km_lactate = get_parameter_from_config(config, 'the_optimal_lactate', 0.04)     # NetLogo Km for lactate
    vmax_oxygen = get_parameter_from_config(config, 'oxygen_vmax', 3.0e-17)         # NetLogo Vmax for oxygen
    vmax_glucose = get_parameter_from_config(config, 'glucose_vmax', 3.0e-15)       # NetLogo Vmax for glucose
    max_atp = get_parameter_from_config(config, 'max_atp', 30)                      # Maximum ATP per glucose
    proton_coefficient = get_parameter_from_config(config, 'proton_coefficient', 0.01)  # Proton production coefficient

    # Growth factor rate constants (Jayatilake et al. 2024)
    gamma_sc = get_parameter_from_config(config, 'gamma_sc', 1.0e-18)               # Growth factor consumption rate constant
    gamma_sp = get_parameter_from_config(config, 'gamma_sp', 1.0e-19)               # Growth factor production rate constant

    # Initialize reactions
    reactions = {
        'Oxygen': 0.0,
        'Glucose': 0.0,
        'Lactate': 0.0,
        'H': 0.0,
        'FGF': 0.0,
        'TGFA': 0.0,
        'HGF': 0.0
    }

    # Only consume/produce if cell is alive (not necrotic)
    if gene_states.get('Necrosis', False):
        return reactions

    # Get gene states
    mito_atp = 1.0 if gene_states.get('mitoATP', False) else 0.0
    glyco_atp = 1.0 if gene_states.get('glycoATP', False) else 0.0

    # NetLogo-style reaction term calculations using Michaelis-Menten kinetics
    # Based on NetLogo MicroC implementation (lines 2788, 2998, 3054, 3161)

    # Calculate ATP rate using NetLogo-style kinetics
    atp_rate = 0.0

    # OXPHOS pathway (mitoATP active) - consumes oxygen and glucose/lactate
    if mito_atp > 0:
        # Oxygen consumption with Michaelis-Menten kinetics (NetLogo style)
        oxygen_mm_factor = local_oxygen / (km_oxygen + local_oxygen)
        reactions['Oxygen'] = -vmax_oxygen * oxygen_mm_factor

        # Glucose consumption for OXPHOS (NetLogo line 2998)
        glucose_mm_factor = local_glucose / (km_glucose + local_glucose)
        glucose_consumption = (vmax_oxygen * 1.0 / 6) * glucose_mm_factor * oxygen_mm_factor
        reactions['Glucose'] = -glucose_consumption

        # Lactate consumption for OXPHOS (NetLogo line 3054)
        lactate_mm_factor = local_lactate / (km_lactate + local_lactate)
        lactate_consumption = (vmax_oxygen * 2.0 / 6) * lactate_mm_factor * oxygen_mm_factor
        reactions['Lactate'] = -lactate_consumption

        # ATP production from OXPHOS
        atp_rate += glucose_consumption * max_atp + lactate_consumption * (max_atp / 2)

        # Proton consumption during OXPHOS (negative H production)
        reactions['H'] = -glucose_consumption * proton_coefficient

    # Glycolysis pathway (glycoATP active) - consumes glucose, produces lactate
    if glyco_atp > 0:
        # Glucose consumption for glycolysis (NetLogo line 3161)
        glucose_mm_factor = local_glucose / (km_glucose + local_glucose)
        oxygen_mm_factor = local_oxygen / (km_oxygen + local_oxygen)
        glucose_consumption_glyco = (vmax_oxygen * 1.0 / 6) * glucose_mm_factor * oxygen_mm_factor
        reactions['Glucose'] += -glucose_consumption_glyco

        # Lactate production from glycolysis (NetLogo line 3660)
        lactate_production = (vmax_oxygen * 2.0 / 6) * (max_atp / 2) * glucose_mm_factor
        reactions['Lactate'] += lactate_production

        # Proton production from glycolysis (NetLogo line 3429)
        proton_production = (vmax_oxygen * 2.0 / 6) * proton_coefficient * (max_atp / 2) * glucose_mm_factor
        reactions['H'] += proton_production

        # ATP production from glycolysis
        atp_rate += glucose_consumption_glyco * 2  # 2 ATP per glucose in glycolysis

        # Small oxygen consumption even in glycolysis (NetLogo style)
        reactions['Oxygen'] += -vmax_oxygen * 0.1 * oxygen_mm_factor  # 10% of normal oxygen consumption TODO: according to paper K=0.5, not 0.1

    # Store ATP rate in cell state for division decisions
    cell_state['atp_rate'] = atp_rate

    # Apply environmental constraints - don't consume more than available
    for substance in ['Oxygen', 'Glucose', 'Lactate']:
        local_conc = local_environment.get(substance, 0.0)
        if reactions[substance] < 0:  # Consumption
            max_consumption = abs(reactions[substance])
            available = local_conc
            if available < max_consumption:
                reactions[substance] = -available * 0.9  # Leave some residual

    return reactions


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


# def custom_check_cell_death(cell_state: Dict[str, Any], local_environment: Dict[str, float]) -> bool:
#     """
#     Determine if cell should die based on gene network state and environmental conditions.
#     """
#     # Get gene states from cell state
#     gene_states = cell_state.get('gene_states', {})

#     # Cell dies if Necrosis or Apoptosis genes are active
#     necrosis = gene_states.get('Necrosis', False)
#     apoptosis = gene_states.get('Apoptosis', False)

#     if necrosis or apoptosis:
#         return True

#     # Additional death conditions could be added here
#     # For example, extreme hypoxia, nutrient starvation, etc.
#     # Use lowercase 'oxygen' key (FIXED)
#     oxygen = local_environment.get('oxygen', 0.0)
#     if oxygen < 0.001:  # Severe hypoxia
#         return True

#     return False


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
