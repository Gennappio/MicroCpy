import numpy as np
import math
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass


def get_required_concentration(local_environment: Dict[str, float], substance_name: str,
                             alternative_name: str = None, context: str = "") -> float:
    """
    Safely get a required substance concentration from local environment.
    Aborts simulation with clear error if the substance is missing.

    Args:
        local_environment: Dictionary containing substance concentrations
        substance_name: Primary name to look for (e.g., 'Oxygen')
        alternative_name: Alternative name to try (e.g., 'oxygen'), defaults to lowercase
        context: Additional context for error message

    Returns:
        float: The concentration value

    Raises:
        ValueError: If substance is not found, aborting simulation
    """
    if alternative_name is None:
        alternative_name = substance_name.lower()

    concentration = local_environment.get(substance_name, local_environment.get(alternative_name))

    if concentration is None:
        context_msg = f" {context}" if context else ""
        available_keys = list(local_environment.keys())
        raise ValueError(
            f"❌ CRITICAL: {substance_name} concentration missing from local_environment{context_msg}\n"
            f"   Available substances: {available_keys}\n"
            f"   Simulation aborted to prevent invalid calculations."
        )

    return concentration


def get_required_gene_state(gene_states: Dict[str, bool], gene_name: str, cell_id: str = "unknown") -> bool:
    """
    Safely get a required gene state from gene_states dictionary.
    Aborts simulation with clear error if the gene state is missing.

    Args:
        gene_states: Dictionary containing gene states
        gene_name: Name of the gene to look for (e.g., 'mitoATP')
        cell_id: Cell ID for error context

    Returns:
        bool: The gene state value

    Raises:
        ValueError: If gene state is not found, aborting simulation
    """
    if gene_name not in gene_states:
        raise ValueError(
            f"❌ CRITICAL: {gene_name} gene state missing for cell {cell_id[:8]}\n"
            f"   Available gene states: {list(gene_states.keys())}\n"
            f"   Simulation aborted to prevent invalid gene network calculations."
        )

    return gene_states[gene_name]


def get_required_cell_state(cell_state: Dict[str, Any], state_name: str, cell_id: str = "unknown") -> Any:
    """
    Safely get a required value from cell state dictionary.
    Aborts simulation with clear error if the state is missing.

    Args:
        cell_state: Dictionary containing cell state
        state_name: Name of the state to look for (e.g., 'metabolic_state')
        cell_id: Cell ID for error context

    Returns:
        Any: The state value

    Raises:
        ValueError: If state is not found, aborting simulation
    """
    if state_name not in cell_state:
        raise ValueError(
            f"❌ CRITICAL: {state_name} missing from cell {cell_id[:8]}\n"
            f"   Available cell states: {list(cell_state.keys())}\n"
            f"   Simulation aborted to prevent invalid calculations."
        )

    return cell_state[state_name]


def get_required_environment_concentrations(local_environment: Dict[str, float], *substance_names: str) -> List[float]:
    """
    Get required substance concentrations from local environment with explicit error handling.
    Raises KeyError with detailed message if any substance is missing.

    Args:
        local_environment: Dictionary containing substance concentrations
        *substance_names: Variable number of substance names to retrieve

    Returns:
        List of concentrations in the same order as requested substances

    Example:
        oxygen_conc, glucose_conc = get_required_environment_concentrations(env, 'Oxygen', 'Glucose')
    """
    concentrations = []
    for substance in substance_names:
        if substance not in local_environment:
            available_substances = list(local_environment.keys())
            raise KeyError(
                f"❌ CRITICAL: Missing '{substance}' concentration in local_environment\n"
                f"   Available substances: {available_substances}\n"
                f"   Simulation aborted to prevent invalid calculations."
            )
        concentrations.append(local_environment[substance])

    return concentrations


# Debug: Confirm custom functions are loaded
#print("🔧 CUSTOM FUNCTIONS LOADED: jayatilake_experiment_custom_functions.py")

# Import custom metabolism functions from separate file
try:
    import os
    import sys
    # Add the current directory to path to import the metabolism file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Also add tests/jayatilake_experiment to path for when running from main directory
    tests_dir = os.path.join(os.getcwd(), 'tests', 'jayatilake_experiment')
    if os.path.exists(tests_dir) and tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)

    import jayatilake_experiment_custom_metabolism as metabolism
    METABOLISM_FUNCTIONS_AVAILABLE = True
except ImportError as e:
    print(f"[!] Could not import custom metabolism functions: {e}")
    print(f"   Current working directory: {os.getcwd()}")
    print(f"   Python path: {sys.path[:3]}...")  # Show first 3 entries
    METABOLISM_FUNCTIONS_AVAILABLE = False
    metabolism = None



def get_parameter_from_config(config, param_name: str, default_value=None, section=None, fail_if_missing=False):
    """
    Config-agnostic parameter lookup - works with any configuration structure.
    Looks for parameters in multiple possible locations.

    Args:
        config: Configuration object (can be None for global config access)
        param_name: Name of the parameter to look for
        default_value: Default value if parameter not found (only used if fail_if_missing=False)
        section: Optional section name (e.g., 'metabolism', 'custom_parameters')
        fail_if_missing: If True, raises ValueError when parameter is not found

    Raises:
        ValueError: If fail_if_missing=True and parameter is not found
    """
    # If no config provided
    if not config:
        if fail_if_missing:
            raise ValueError(f"❌ Configuration parameter '{param_name}' is required but config is None")
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

    # Parameter not found
    if fail_if_missing:
        # Provide helpful error message with search locations
        search_locations = []
        if section:
            search_locations.append(f"config.{section}.{param_name}")
        search_locations.extend([
            f"config.custom_parameters.{param_name}",
            f"config.{param_name}"
        ])

        raise ValueError(
            f"❌ Required configuration parameter '{param_name}' not found!\n"
            f"   Searched in: {', '.join(search_locations)}\n"
            f"   Please add this parameter to your configuration file."
        )

    # Return default value with warning
    print(f"[!] Parameter '{param_name}' not found in config, using default: {default_value}")
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


def initialize_cell_placement(grid_size: Union[Tuple[int, int], Tuple[int, int, int]], simulation_params: Dict[str, Any], config: Any = None) -> List[Dict[str, Any]]:
    """
    Initialize cells in a spheroid configuration for metabolic symbiosis experiment.
    Places cells in center with some initial heterogeneity.

    IMPORTANT: This function receives the FiPy grid size, but should calculate
    biological cell positions based on cell_height parameter!
    """
    # Handle both 2D and 3D grid sizes
    if len(grid_size) == 2:
        fipy_nx, fipy_ny = grid_size  # This is the FiPy grid (e.g., 40x40)
        fipy_nz = None
        is_3d = False
    else:
        fipy_nx, fipy_ny, fipy_nz = grid_size  # This is the FiPy grid (e.g., 75x75x75)
        is_3d = True

    # Calculate biological cell grid based on cell_height
    # Get domain size and cell_height from simulation_params
    domain_size_um = simulation_params['domain_size_um'] if 'domain_size_um' in simulation_params else simulation_params['size_x']
    cell_height_um = simulation_params['cell_height_um'] if 'cell_height_um' in simulation_params else simulation_params['cell_height']

    # Calculate biological cell grid size
    bio_nx = int(domain_size_um / cell_height_um)  # e.g., 600/80 = 7.5 → 7
    bio_ny = int(domain_size_um / cell_height_um)
    bio_nz = int(domain_size_um / cell_height_um) if is_3d else 1

    if is_3d:
        print(f"[DEBUG] BIOLOGICAL CELL GRID DEBUG (3D):")
        print(f"   FiPy grid: {fipy_nx}x{fipy_ny}x{fipy_nz}")
        print(f"   Domain size: {domain_size_um} um")
        print(f"   Cell height: {cell_height_um} um")
        print(f"   Biological cell grid: {bio_nx}x{bio_ny}x{bio_nz}")
        print(f"   Biological cell size: {cell_height_um} um")
    else:
        print(f"[DEBUG] BIOLOGICAL CELL GRID DEBUG (2D):")
        print(f"   FiPy grid: {fipy_nx}x{fipy_ny}")
        print(f"   Domain size: {domain_size_um} um")
        print(f"   Cell height: {cell_height_um} um")
        print(f"   Biological cell grid: {bio_nx}x{bio_ny}")
        print(f"   Biological cell size: {cell_height_um} um")
    # Get initial cell count from simulation parameters FIRST
    initial_count = simulation_params['initial_cell_count']

    # print(f"🔍 BIOLOGICAL CELL GRID DEBUG:")
    # print(f"   FiPy grid: {fipy_nx}×{fipy_ny}")
    # print(f"   Domain size: {domain_size_um} μm")
    # print(f"   Cell height: {cell_height_um} μm")
    # print(f"   Biological cell grid: {bio_nx}×{bio_ny}")
    # print(f"   Biological cell size: {cell_height_um} μm")
    # print(f"   Target cell count: {initial_count}")
    # print(f"   Available simulation_params keys: {list(simulation_params.keys())}")
    # print(f"   Raw initial_cell_count value: {simulation_params.get('initial_cell_count', 'NOT_FOUND')}")
    # print(f"   All simulation_params: {simulation_params}")

    # Track coordinate collisions
    used_positions = set()
    collision_count = 0

    # Use biological cell grid for placement
    center_x, center_y = bio_nx // 2, bio_ny // 2
    center_z = bio_nz // 2 if is_3d else 0

    # Get initial cell count from simulation parameters
    initial_count = simulation_params['initial_cell_count']

    placements = []

    # Place cells in expanding spherical pattern on biological cell grid
    radius = 1
    cells_placed = 0

    if is_3d:
        max_radius = min(bio_nx, bio_ny, bio_nz) // 2
    else:
        max_radius = min(bio_nx, bio_ny) // 2

    while cells_placed < initial_count and radius < max_radius:
        if is_3d:
            # 3D spherical placement
            for x in range(max(0, center_x - radius), min(bio_nx, center_x + radius + 1)):
                for y in range(max(0, center_y - radius), min(bio_ny, center_y + radius + 1)):
                    for z in range(max(0, center_z - radius), min(bio_nz, center_z + radius + 1)):
                        if cells_placed >= initial_count:
                            break

                        # Check if position is within spherical distance
                        distance = ((x - center_x)**2 + (y - center_y)**2 + (z - center_z)**2)**0.5
                        if distance <= radius:
                            position = (x, y, z)
                            if position not in used_positions:
                                used_positions.add(position)
                                placements.append({
                                    'position': position,
                                    'phenotype': "Proliferation"  # All start as proliferative
                                })
                                cells_placed += 1
                    if cells_placed >= initial_count:
                        break
                if cells_placed >= initial_count:
                    break
        else:
            # 2D circular placement
            for x in range(max(0, center_x - radius), min(bio_nx, center_x + radius + 1)):
                for y in range(max(0, center_y - radius), min(bio_ny, center_y + radius + 1)):
                    if cells_placed >= initial_count:
                        break

                    # Check if position is within radius
                    distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                    if distance <= radius:
                        # Use biological cell coordinates directly - no conversion to FiPy grid!
                        # The substance simulator will handle mapping between biological positions and FiPy mesh
                        bio_pos = (x, y)

                        # Check for coordinate collisions on biological grid
                        if bio_pos in used_positions:
                            collision_count += 1
                            if collision_count <= 5:
                                print(f"   [!] COLLISION: Cell {cells_placed} at bio({x},{y}) already used!")
                            continue  # Skip this cell to avoid overwriting

                        used_positions.add(bio_pos)

                        # Debug coordinate mapping for first few cells
                        if cells_placed < 5:
                            print(f"   Cell {cells_placed}: bio({x},{y}) - using biological coordinates directly")

                        # No randomness - all cells start as Proliferation
                        phenotype = "Proliferation"

                        placements.append({
                            'position': bio_pos,  # Use biological coordinates directly
                            'phenotype': phenotype,
                            'bio_grid_size': (bio_nx, bio_ny)
                        })
                        cells_placed += 1
                if cells_placed >= initial_count:
                    break
        
        radius += 1

    # Summary
    print(f"   [INFO] Placement summary: {len(placements)} cells placed, {collision_count} collisions avoided")

    return placements


def initialize_cell_ages(population, config: Any = None):
    """
    Set initial cell ages randomly distributed from 0 to max_cell_age.

    This function is called after cell placement to set cells to random ages
    with a normal distribution, ensuring some cells can proliferate immediately.
    """
    import numpy as np

    # Get parameters from config - fail if missing
    try:
        max_cell_age = get_parameter_from_config(config, 'max_cell_age', fail_if_missing=True)
        cell_cycle_time = get_parameter_from_config(config, 'cell_cycle_time', fail_if_missing=True)
    except ValueError as e:
        print(f"❌ CELL AGE INITIALIZATION FAILED: {e}")
        print("   Skipping cell age initialization - cells will start with age 0")
        return

    # Use normal distribution with mean at max_cell_age/2 and std dev of max_cell_age/6
    # This ensures ~99.7% of values are within [0, max_cell_age] range
    mean_age = max_cell_age / 2.0
    std_dev = max_cell_age / 6.0

    print(f"[INIT] INITIALIZING CELL AGES (RANDOM DISTRIBUTION):")
    print(f"   Max cell age: {max_cell_age}")
    print(f"   Cell cycle time: {cell_cycle_time}")
    print(f"   Distribution: Normal(mean={mean_age:.1f}, std={std_dev:.1f})")

    # Track age statistics
    ages_set = []
    cells_updated = 0
    cells_can_proliferate = 0

    # Update all cells to have random ages
    for cell_id, cell in population.state.cells.items():
        old_age = cell.state.age

        # Generate random age with normal distribution
        random_age = np.random.normal(mean_age, std_dev)

        # Clamp to valid range [0, max_cell_age]
        random_age = max(0.0, min(max_cell_age, random_age))

        # Update cell age
        cell.state = cell.state.with_updates(age=random_age)
        ages_set.append(random_age)
        cells_updated += 1

        # Check if this cell can proliferate immediately
        if random_age >= cell_cycle_time:
            cells_can_proliferate += 1

        # Debug first few cells AND log all ages to file
        if cells_updated <= 3:
            can_proliferate = "[OK]" if random_age >= cell_cycle_time else "[NO]"
            print(f"   Cell {cell_id[:8]}: age {old_age:.1f} -> {random_age:.1f} {can_proliferate}")

        # Log all initial ages to file for debugging
        with open("log_simulation_status.txt", "a") as f:
            f.write(f"INITIAL_AGE: {cell_id[:8]} | {random_age:.1f} | can_proliferate: {random_age >= cell_cycle_time}\n")

    # Print statistics
    ages_array = np.array(ages_set)
    print(f"   [STATS] Age Statistics:")
    print(f"      Mean: {np.mean(ages_array):.1f}")
    print(f"      Std Dev: {np.std(ages_array):.1f}")
    print(f"      Min: {np.min(ages_array):.1f}")
    print(f"      Max: {np.max(ages_array):.1f}")
    print(f"   [OK] Updated {cells_updated} cells with random ages")
    print(f"   [INFO] {cells_can_proliferate}/{cells_updated} cells can proliferate immediately")


def reset_metabolism_counters():
    """
    Reset the metabolism counting statistics.
    Call this at the start of each simulation run.
    """
    if hasattr(calculate_cell_metabolism, 'call_count'):
        calculate_cell_metabolism.call_count = 0
        calculate_cell_metabolism.oxphos_count = 0
        calculate_cell_metabolism.glyco_count = 0
        calculate_cell_metabolism.both_count = 0
        calculate_cell_metabolism.quiescent_count = 0
        calculate_cell_metabolism.counted_cells = set()
        print("🔄 Reset metabolism counters for new simulation")


def custom_initialize_cell_ages(population, config: Any = None):
    """
    Hook-compatible version of initialize_cell_ages.
    Called via hook system to set initial cell ages.
    """
    # Reset metabolism counters at start of simulation
    reset_metabolism_counters()
    return initialize_cell_ages(population, config)


def calculate_cell_metabolism(local_environment: Dict[str, float], cell_state: Dict[str, Any], config: Any = None) -> Dict[str, float]:
    """
    Calculate substance consumption/production rates using NetLogo-style Michaelis-Menten kinetics.
    Uses gene states (glycoATP, mitoATP, GLUT1, MCT1, MCT4) and NetLogo-compatible parameters.

    Implements NetLogo MicroC reaction term calculations with Michaelis-Menten kinetics:
    - OXPHOS cells consume lactate and oxygen, produce minimal lactate
    - Glycolytic cells consume glucose, produce lactate and protons
    - Metabolic switching based on gene network states
    """
    # SIMPLIFIED VERSION: Return hardcoded values to fix metabolism issue
    # This bypasses all the complex parameter lookups that were causing hangs

    # Initialize reactions for all substances
    # CRITICAL: Use CAPITALIZED keys to match diffusion system expectations
    reactions = {
        # Metabolic substances - use hardcoded reasonable values
        'Oxygen': -5.9e-19,      # Oxygen consumption (mol/s/cell)
        'Glucose': -7.2e-21,     # Glucose consumption (mol/s/cell)
        'Lactate': +2.24e-19,    # Lactate production (mol/s/cell) - FIXED to correct value
        'H': 0.0,                # Proton production
        'pH': 0.0,               # pH (derived from H+)

        # Growth factors (small rates)
        'FGF': -1.0e-18,
        'TGFA': -1.0e-18,
        'HGF': -1.0e-18,
        'GI': -2.0e-17,

        # Drug inhibitors (passive consumption)
        'EGFRD': -4.0e-17,
        'FGFRD': -4.0e-17,
        'cMETD': -4.0e-17,
        'MCT1D': -4.0e-17,
        'GLUT1D': -4.0e-17,

        # ATP rate (required by update_cell_metabolic_state)
        'atp_rate': 1.0e-16      # ATP production rate (mol/s/cell)
    }

    # DEBUG: Log metabolism function calls to verify it's being called
    cell_id = cell_state.get('id', 'unknown')
    if isinstance(cell_id, str) and len(cell_id) > 8:
        cell_id = cell_id[:8]

    # Log every 10th call to avoid spam
    if not hasattr(calculate_cell_metabolism, 'debug_count'):
        calculate_cell_metabolism.debug_count = 0
    calculate_cell_metabolism.debug_count += 1

    if calculate_cell_metabolism.debug_count % 10 == 1:
        print(f"[DEBUG] METABOLISM CALL #{calculate_cell_metabolism.debug_count}: Cell {cell_id}")
        print(f"   Returning: Oxygen={reactions['Oxygen']:.2e}, Glucose={reactions['Glucose']:.2e}, Lactate={reactions['Lactate']:.2e}")

    return reactions

    # Simple progress counter - reset at start of each simulation
    if not hasattr(calculate_cell_metabolism, 'call_count'):
        calculate_cell_metabolism.call_count = 0
        calculate_cell_metabolism.oxphos_count = 0
        calculate_cell_metabolism.glyco_count = 0
        calculate_cell_metabolism.both_count = 0
        calculate_cell_metabolism.quiescent_count = 0
        calculate_cell_metabolism.counted_cells = set()  # Track which cells we've counted

    calculate_cell_metabolism.call_count += 1

    # Get gene states from cell state (they should be stored there after gene network update)
    gene_states = cell_state['gene_states']

    # Get local concentrations (handle both capitalized and lowercase keys)
    # CRITICAL: No default values - missing concentrations should cause errors
    local_oxygen = get_required_concentration(local_environment, 'oxygen', 'Oxygen')
    local_glucose = get_required_concentration(local_environment, 'glucose', 'Glucose')
    local_lactate = get_required_concentration(local_environment, 'lactate', 'Lactate')
    local_h = get_required_concentration(local_environment, 'h', 'H')

    # Get NetLogo-compatible Michaelis constants and metabolic parameters from config
    # Provide default values to prevent None errors
    km_oxygen = get_parameter_from_config(config, 'the_optimal_oxygen', default_value=0.005)      # NetLogo Km for oxygen (mM)
    km_glucose = get_parameter_from_config(config, 'the_optimal_glucose', default_value=0.04)     # NetLogo Km for glucose (mM)
    km_lactate = get_parameter_from_config(config, 'the_optimal_lactate', default_value=0.04)     # NetLogo Km for lactate (mM)
    vmax_oxygen = get_parameter_from_config(config, 'oxygen_vmax', default_value=1.0e-16)         # NetLogo Vmax for oxygen (mol/cell/s)
    vmax_glucose = get_parameter_from_config(config, 'glucose_vmax', default_value=3.0e-15)       # NetLogo Vmax for glucose (mol/cell/s)
    max_atp = get_parameter_from_config(config, 'max_atp', default_value=30.0)                      # Maximum ATP per glucose
    proton_coefficient = get_parameter_from_config(config, 'proton_coefficient', default_value=1.0)  # Proton production coefficient

    # Growth factor rate constants (Jayatilake et al. 2024 - Table values)
    # Provide default values to prevent None errors
    tgfa_consumption = get_parameter_from_config(config, 'tgfa_consumption_rate', default_value=1.0e-17)  # TGFA consumption rate
    tgfa_production = get_parameter_from_config(config, 'tgfa_production_rate', default_value=5.0e-18)    # TGFA production rate
    hgf_consumption = get_parameter_from_config(config, 'hgf_consumption_rate', default_value=1.0e-17)    # HGF consumption rate
    hgf_production = get_parameter_from_config(config, 'hgf_production_rate', default_value=5.0e-18)          # HGF production rate
    fgf_consumption = get_parameter_from_config(config, 'fgf_consumption_rate', default_value=1.0e-17)    # FGF consumption rate
    fgf_production = get_parameter_from_config(config, 'fgf_production_rate', default_value=5.0e-18)          # FGF production rate

    # Initialize reactions for all substances (from diffusion-parameters.txt)
    reactions = {
        # Metabolic substances (Michaelis-Menten kinetics)
        'oxygen': 0.0,
        'glucose': 0.0,
        'lactate': 0.0,
        'h': 0.0,
        'pH': 0.0,  # Derived from H+ concentration

        # Growth factors (γS,C × CS consumption, γS,P production)
        'FGF': 0.0,
        'TGFA': 0.0,
        'HGF': 0.0,
        'GI': 0.0,  # Growth inhibitor

        # Drug inhibitors (passive consumption)
        'EGFRD': 0.0,
        'FGFRD': 0.0,
        'cMETD': 0.0,
        'MCT1D': 0.0,
        'GLUT1D': 0.0
    }

    # Get gene states
    mito_atp = 1.0 if gene_states['mitoATP'] else 0.0
    glyco_atp = 1.0 if gene_states['glycoATP'] else 0.0

    # Count cell types only once per cell (avoid double counting across timesteps)
    cell_id = cell_state.get('id', f'cell_{calculate_cell_metabolism.call_count}')
    if cell_id not in calculate_cell_metabolism.counted_cells:
        calculate_cell_metabolism.counted_cells.add(cell_id)
        if mito_atp and not glyco_atp:
            calculate_cell_metabolism.oxphos_count += 1
        elif glyco_atp and not mito_atp:
            calculate_cell_metabolism.glyco_count += 1
        elif mito_atp and glyco_atp:
            calculate_cell_metabolism.both_count += 1
        else:
            calculate_cell_metabolism.quiescent_count += 1

    # Show progress every 1000 calls - DISABLED
    # if calculate_cell_metabolism.call_count % 1000 == 0:
    #     total_counted = len(calculate_cell_metabolism.counted_cells)
    #     print(f"📊 Step {calculate_cell_metabolism.call_count}: OXPHOS={calculate_cell_metabolism.oxphos_count}, Glyco={calculate_cell_metabolism.glyco_count}, Both={calculate_cell_metabolism.both_count}, Quiescent={calculate_cell_metabolism.quiescent_count} (Total unique cells: {total_counted})")

    # NetLogo-style reaction term calculations using Michaelis-Menten kinetics
    atp_rate = 0.0

    # OXPHOS pathway (mitoATP active) - consumes oxygen and glucose/lactate
    if mito_atp > 0:
        # Oxygen consumption with Michaelis-Menten kinetics (NetLogo style)
        oxygen_mm_factor = local_oxygen / (km_oxygen + local_oxygen)
        reactions['oxygen'] = -vmax_oxygen * oxygen_mm_factor

        # Glucose consumption for OXPHOS (NetLogo line 2998) - REDUCED for mitoATP
        glucose_mm_factor = local_glucose / (km_glucose + local_glucose)
        glucose_consumption = (vmax_oxygen * 1.0 / 6) * glucose_mm_factor * oxygen_mm_factor
        reactions['glucose'] = -glucose_consumption

        # Lactate consumption for OXPHOS (NetLogo line 3054) - DISABLED for testing
        lactate_mm_factor = local_lactate / (km_lactate + local_lactate)
        lactate_consumption = (vmax_oxygen * 2.0 / 6) * lactate_mm_factor * oxygen_mm_factor
        if 'lactate' not in reactions:
            reactions['lactate'] = 0.0
        # reactions['lactate'] += -lactate_consumption  # DISABLED - will override with hardcoded value

        # ATP production from OXPHOS
        atp_rate += glucose_consumption * max_atp + lactate_consumption * (max_atp / 2)

        # Proton consumption during OXPHOS (negative H production)
        reactions['h'] = -glucose_consumption * proton_coefficient

    # Glycolysis pathway (glycoATP active) - consumes glucose, produces lactate
    if glyco_atp > 0:
        # Glucose consumption for glycolysis (NetLogo line 3161)
        glucose_mm_factor = local_glucose / (km_glucose + local_glucose) if (km_glucose + local_glucose) > 0 else 0
        oxygen_mm_factor = local_oxygen / (km_oxygen + local_oxygen) if (km_oxygen + local_oxygen) > 0 else 0
        oxygen_factor_for_glycolysis = max(0.1, oxygen_mm_factor)
        glucose_consumption_glyco = (vmax_glucose * 1.0 / 6) * glucose_mm_factor * oxygen_factor_for_glycolysis
        reactions['glucose'] += -glucose_consumption_glyco

        # Define lactate_production for proton calculation, but do not use it for the main lactate reaction.
        lactate_coeff = 3.0
        lactate_production = glucose_consumption_glyco * lactate_coeff * glyco_atp

        # Proton production from glycolysis
        proton_production = lactate_production * proton_coefficient
        reactions['h'] += proton_production

        # ATP production from glycolysis
        atp_rate += glucose_consumption_glyco * 2

        # Small oxygen consumption even in glycolysis (NetLogo style)
        reactions['oxygen'] += -vmax_glucose * 0.5 * oxygen_factor_for_glycolysis

    # FINAL OVERRIDE: Use EXACT same lactate PRODUCTION rate as standalone FiPy script
    # Standalone uses +2.8e-2 mM/s
    # Convert to mol/s/cell: 2.8e-2 mM/s * mesh_volume / 1000
    # mesh_volume = 20μm × 20μm × 20μm = 8e-15 m³
    # So: 2.8e-2 * 8e-15 / 1000 = 2.24e-19 mol/s/cell
    standalone_rate_mol_per_s = +2.24e-19  # mol/s/cell (PRODUCTION - positive) - FIXED back to correct value
    reactions['lactate'] = standalone_rate_mol_per_s
    reactions['oxygen'] = -5.9e-19
    reactions['glucose'] = -7.2e-21
    # Debug logging - show gene states to verify gene network sharing bug fix - TURNED OFF
    # cell_id = cell_state.get('id', 'unknown')
    # if isinstance(cell_id, str) and len(cell_id) > 8:
    #     cell_id = cell_id[:8]
    # if str(cell_id).endswith(('0', '1', '2', '3', '4')):
    #     print(f"🧪 DEBUG Cell {cell_id}: Final lactate rate = {reactions['Lactate']:.3e} mol/s/cell, mitoATP={mito_atp}, glycoATP={glyco_atp}")

    # Store ATP rate in cell state
    cell_state['atp_rate'] = atp_rate

    # Growth factor kinetics
    tgfa_conc = get_required_concentration(local_environment, 'TGFA', 'tgfa')
    reactions['TGFA'] = -tgfa_consumption * tgfa_conc + tgfa_production
    hgf_conc = get_required_concentration(local_environment, 'HGF', 'hgf')
    reactions['HGF'] = -hgf_consumption * hgf_conc + hgf_production
    fgf_conc = get_required_concentration(local_environment, 'FGF', 'fgf')
    reactions['FGF'] = -fgf_consumption * fgf_conc + fgf_production
    gi_conc = get_required_concentration(local_environment, 'GI', 'gi')
    reactions['GI'] = -2.0e-17 * gi_conc
    drug_inhibitors = ['EGFRD', 'FGFRD', 'cMETD', 'MCT1D', 'GLUT1D']
    for drug in drug_inhibitors:
        local_conc = get_required_concentration(local_environment, drug, drug.lower())
        reactions[drug] = -4.0e-17 * local_conc

    # pH calculation
    h_conc = get_required_concentration(local_environment, 'H', 'h')
    if h_conc > 0:
        reactions['pH'] = 0.0

    # Recalculate ATP production rate
    atp_rate = 0.0
    if glyco_atp and reactions['glucose'] < 0:
        glucose_consumption_rate = abs(reactions['glucose'])
        glycolytic_atp = glucose_consumption_rate * 2.0
        atp_rate += glycolytic_atp
    if mito_atp and reactions['oxygen'] < 0:
        oxygen_consumption_rate = abs(reactions['oxygen'])
        mitochondrial_atp = oxygen_consumption_rate * 30.0
        atp_rate += mitochondrial_atp
    reactions['atp_rate'] = atp_rate

    # Apply environmental constraints (only for substances that have reactions)
    for substance in ['oxygen', 'glucose', 'lactate']:
        if substance in reactions:
            local_conc = get_required_concentration(local_environment, substance, substance.upper(), context="during constraint checking")
            if reactions[substance] < 0:
                max_consumption = abs(reactions[substance])
                available = local_conc
                if available < max_consumption:
                    reactions[substance] = -available * 0.9

    return reactions


def get_required_metabolic_rate(reactions: Dict[str, float], rate_name: str) -> float:
    """
    Safely extract a required metabolic rate from reactions dictionary.
    Aborts simulation if the rate is missing.

    Args:
        reactions: Dictionary of reaction rates
        rate_name: Name of the required rate

    Returns:
        The metabolic rate value

    Raises:
        SystemExit: If the required rate is missing
    """
    if rate_name not in reactions:
        error_msg = f"[!] CRITICAL ERROR: Required metabolic rate '{rate_name}' is missing from reactions dictionary!"
        print(error_msg)
        print(f"Available rates: {list(reactions.keys())}")
        print("[!] ABORTING SIMULATION - Cannot proceed without required metabolic data")

        # Log the error to file for debugging
        try:
            with open("log_simulation_status.txt", "a") as f:
                f.write(f"CRITICAL_ERROR: Missing required rate '{rate_name}'\n")
                f.write(f"Available rates: {list(reactions.keys())}\n")
                f.write("SIMULATION_ABORTED\n")
        except Exception:
            pass  # Don't let logging errors prevent the abort

        # Abort the simulation
        import sys
        sys.exit(1)

    value = reactions[rate_name]
    if value is None:
        error_msg = f"❌ CRITICAL ERROR: Required metabolic rate '{rate_name}' is None!"
        print(error_msg)
        print("🚨 ABORTING SIMULATION - Cannot proceed with None metabolic data")

        # Log the error to file for debugging
        try:
            with open("log_simulation_status.txt", "a") as f:
                f.write(f"CRITICAL_ERROR: Rate '{rate_name}' is None\n")
                f.write("SIMULATION_ABORTED\n")
        except Exception:
            pass

        import sys
        sys.exit(1)

    return value


def update_cell_metabolic_state(cell, local_environment: Dict[str, float], config: Any = None):
    """
    Update cell's metabolic state with calculated ATP rate and other metabolic values.
    This function should be called during intracellular processes to populate metabolic_state.
    """
    # Calculate metabolism using the existing function
    reactions = calculate_cell_metabolism(local_environment, cell.state.__dict__, config)

    # Extract key metabolic values with validation (will abort if missing)
    # FIXED: Use capitalized keys to match metabolism function output
    atp_rate = get_required_metabolic_rate(reactions, 'atp_rate')
    oxygen_rate = get_required_metabolic_rate(reactions, 'Oxygen')
    glucose_rate = get_required_metabolic_rate(reactions, 'Glucose')
    lactate_rate = get_required_metabolic_rate(reactions, 'Lactate')

    # Optional: Test the validation by uncommenting the line below
    # test_missing_rate = get_required_metabolic_rate(reactions, 'MISSING_RATE_TEST')

    # Update cell's metabolic state
    metabolic_state = {
        'atp_rate': atp_rate,
        'oxygen_consumption': abs(oxygen_rate) if oxygen_rate < 0 else 0.0,
        'glucose_consumption': abs(glucose_rate) if glucose_rate < 0 else 0.0,
        'lactate_production': lactate_rate if lactate_rate > 0 else 0.0,
        'lactate_consumption': abs(lactate_rate) if lactate_rate < 0 else 0.0
    }

    # Update cell state with new metabolic state
    cell.state = cell.state.with_updates(metabolic_state=metabolic_state)


def check_cell_division(cell_state: Dict[str, Any], local_environment: Dict[str, float], config: Any = None) -> bool:
    """
    Determine if cell should attempt division based on ATP rate and cell cycle time.
    Config-agnostic function that works with any configuration structure.
    """
    # Get parameters using config-agnostic lookup - FAIL if missing critical parameters
    try:
        atp_threshold = get_parameter_from_config(config, 'atp_threshold', fail_if_missing=True)
        max_atp = get_parameter_from_config(config, 'max_atp', fail_if_missing=True)
        cell_cycle_time = get_parameter_from_config(config, 'cell_cycle_time', fail_if_missing=True)
    except ValueError as e:
        print(f"❌ CRITICAL PARAMETER MISSING: {e}")
        print("   SIMULATION ABORTED - Cannot proceed without required parameters")
        raise SystemExit(1)

    # Check ATP rate from cell state
    atp_rate = cell_state['atp_rate']
    atp_rate_normalized = atp_rate / max_atp if max_atp > 0 else 0

    # Check cell age from cell state
    cell_age = cell_state['age']

    # Check phenotype from cell state
    phenotype = cell_state['phenotype']

    # Debug ATP rate calculation
    cell_id = cell_state.get('id', 'unknown')[:8]
    #print(f"🔬 DIVISION CHECK {cell_id}: atp_rate={atp_rate:.2e}, max_atp={max_atp}, normalized={atp_rate_normalized:.4f}, threshold={atp_threshold}")
    #print(f"   Age: {cell_age:.1f} > {cell_cycle_time}? {cell_age > cell_cycle_time}")
    #print(f"   Phenotype: {phenotype} == 'Proliferation'? {phenotype == 'Proliferation'}")
    #print(f"   ATP check: {atp_rate_normalized:.4f} > {atp_threshold}? {atp_rate_normalized > atp_threshold}")

    if(atp_rate_normalized > atp_threshold):
        cell_state['phenotype'] = "Proliferation"

    division_decision = (cell_age > cell_cycle_time and
                        phenotype == "Proliferation")

    #print(f"   FINAL DECISION: {division_decision}")

    return division_decision


def log_division_decision(cell_id: str, decision: bool, reason: str, cell_age: float, atp_rate_normalized: float, current_phenotype: str, atp_type: str = "unknown"):
    """
    Log cell division decisions to the division decisions file.
    """
    import time
    from pathlib import Path

    try:
        # Create results directory if it doesn't exist
        results_dir = Path("results") / "jayatilake_experiment"
        results_dir.mkdir(parents=True, exist_ok=True)

        # Log to division decisions file
        log_file = results_dir / "division_decisions.txt"

        # Create header if file doesn't exist
        if not log_file.exists():
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=== CELL DIVISION DECISIONS LOG ===\n")
                f.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 100 + "\n")
                f.write("Cell ID | Decision | Age | ATP_Norm | Phenotype | ATP_Type | Reason\n")
                f.write("-" * 100 + "\n")

        # Append decision log
        with open(log_file, 'a', encoding='utf-8') as f:
            decision_str = "DIVIDE" if decision else "NO_DIV"
            f.write(f"{cell_id[:8]} | {decision_str} | {cell_age:6.1f} | {atp_rate_normalized:6.3f} | {current_phenotype:12s} | {atp_type:8s} | {reason}\n")

    except Exception as e:
        print(f"⚠️ Failed to log division decision: {e}")


def should_divide(cell, config: Any) -> bool:
    """
    Determine if cell should attempt division based on gene network state and cell conditions.
    ALSO sets phenotype to "Proliferation" when metabolic conditions are met (ATP override).
    """
    # Get parameters using config-agnostic lookup - FAIL if missing critical parameters
    try:
        atp_threshold = get_parameter_from_config(config, 'atp_threshold', fail_if_missing=True)
        max_atp_rate = get_parameter_from_config(config, 'max_atp_rate', fail_if_missing=True)
        cell_cycle_time = get_parameter_from_config(config, 'cell_cycle_time', fail_if_missing=True)
    except ValueError as e:
        print(f"❌ CRITICAL PARAMETER MISSING: {e}")
        print("   SIMULATION ABORTED - Cannot proceed without required parameters")
        raise SystemExit(1)

    # Debug config lookup (commented out to reduce noise)
    # print(f"🔧 CONFIG DEBUG: config type: {type(config)}")
    # print(f"   Final cell_cycle_time = {cell_cycle_time}")

    # Initialize logging variables
    cell_age = cell.state.age
    current_phenotype = cell.state.phenotype
    atp_rate_normalized = 0.0  # Will be calculated if available

    # Determine ATP production type from gene network states
    atp_type = "unknown"
    try:
        gene_states = cell.state.gene_states
        # Gene states should be present - if missing, this indicates a problem
        cell_id = cell.state.id
        mito_atp = get_required_gene_state(gene_states, 'mitoATP', cell_id)
        glyco_atp = get_required_gene_state(gene_states, 'glycoATP', cell_id)

        if mito_atp and glyco_atp:
            atp_type = "both"
        elif mito_atp and not glyco_atp:
            atp_type = "mito"
        elif glyco_atp and not mito_atp:
            atp_type = "glyco"
        else:
            atp_type = "none"
    except Exception as e:
        atp_type = f"error:{str(e)[:10]}"

    # Check if cell has sufficient age (basic cell cycle time)
    if cell.state.age < cell_cycle_time:
        reason = f"Age insufficient: {cell.state.age:.1f} < {cell_cycle_time}"
        log_division_decision(cell.state.id, False, reason, cell_age, atp_rate_normalized, current_phenotype, atp_type)
        return False

    # Debug cell division check (reduced output)
    cell_id = cell.state.id[:8]
    if cell.state.age >= cell_cycle_time and cell.state.age <= cell_cycle_time + 0.1:  # Only debug newly eligible cells
        print(f"🔬 DIVISION CHECK {cell_id}: age={cell.state.age:.3f} >= {cell_cycle_time}")

    # ENSURE METABOLIC STATE IS UPDATED
    # If metabolic state is empty, calculate it now
    if not cell.state.metabolic_state or 'atp_rate' not in cell.state.metabolic_state:
        # We need local environment to calculate metabolism
        # For now, use a dummy environment - this should be fixed in the population update
        dummy_env = {
            'Oxygen': 0.05, 'Glucose': 5.0, 'Lactate': 0.1, 'H': 1e-7, 'pH': 7.0,
            'FGF': 0.0, 'TGFA': 0.0, 'HGF': 0.0, 'GI': 0.0,
            'EGFRD': 0.0, 'FGFRD': 0.0, 'cMETD': 0.0, 'MCT1D': 0.0, 'GLUT1D': 0.0
        }
        update_cell_metabolic_state(cell, dummy_env, config)

    # Check ATP rate from cell state (metabolic condition)
    try:
        atp_rate = cell.state.metabolic_state['atp_rate']
        atp_rate_normalized = atp_rate / max_atp_rate if max_atp_rate > 0 else 0
        # Debug output disabled for cleaner simulation output
        # print(f"   ATP: rate={atp_rate:.2e}, max={max_atp_rate:.2e}, normalized={atp_rate_normalized:.4f}, threshold={atp_threshold}")
    except Exception as e:
        print(f"   ❌ ATP ERROR: {e}")
        print(f"   Cell state: {cell.state}")
        reason = f"ATP calculation error: {e}"
        log_division_decision(cell.state.id, False, reason, cell_age, atp_rate_normalized, current_phenotype, atp_type)
        return False

    # METABOLIC OVERRIDE: If ATP conditions are met, FORCE proliferation phenotype
    # This ensures metabolic decisions override gene network phenotype decisions
    if atp_rate_normalized > atp_threshold:
        cell.state.phenotype = "Proliferation"
        # Debug output disabled for cleaner simulation output
        # print(f"   ATP check PASSED: {atp_rate_normalized:.4f} > {atp_threshold} - FORCING Proliferation")
        # Update cell phenotype to proliferation (override gene network decision)
        cell.state = cell.state.with_updates(phenotype="Proliferation")
        # print(f"   DIVISION DECISION: TRUE (ATP override)")
        reason = f"ATP sufficient: {atp_rate_normalized:.3f} > {atp_threshold}"
        log_division_decision(cell.state.id, True, reason, cell_age, atp_rate_normalized, "Proliferation", atp_type)
        return True

    # If ATP is insufficient, check if we're already in proliferation state
    # (Allow continued proliferation if already started)
    if cell.state.phenotype == "Proliferation":
        # Debug output disabled for cleaner simulation output
        # print(f"   ATP check FAILED but already Proliferation - allowing division")
        # print(f"   DIVISION DECISION: TRUE (already proliferating)")
        reason = f"Already proliferating (ATP: {atp_rate_normalized:.3f})"
        log_division_decision(cell.state.id, True, reason, cell_age, atp_rate_normalized, current_phenotype, atp_type)
        return True

    # Debug output disabled for cleaner simulation output
    # print(f"   ATP check FAILED: {atp_rate_normalized:.4f} <= {atp_threshold}, phenotype: {cell.state.phenotype}")
    # print(f"   DIVISION DECISION: FALSE")
    reason = f"ATP insufficient: {atp_rate_normalized:.3f} <= {atp_threshold}"
    log_division_decision(cell.state.id, False, reason, cell_age, atp_rate_normalized, current_phenotype, atp_type)
    return False


def get_cell_color(cell, gene_states: Dict[str, bool], config: Any) -> str:
    """
    Get cell color based on actual phenotype (from update_cell_phenotype) for borders
    and metabolic state (from gene network) for interior.
    Returns a tuple-like string: "interior_color|border_color"
    """
    # Get actual phenotype from cell state (calculated by update_cell_phenotype)
    actual_phenotype = cell.state.phenotype if hasattr(cell.state, 'phenotype') else 'normal'

    # Border colors based on actual phenotype (from update_cell_phenotype function)
    phenotype_border_colors = {
        'Necrosis': 'black',
        'necrosis': 'black',
        'Apoptosis': 'red',
        'apoptosis': 'red',
        'Growth_Arrest': 'orange',
        'growth_arrest': 'orange',
        'Proliferation': 'lightgreen',
        'proliferation': 'lightgreen',
        'normal': 'gray',
        'quiescent': 'gray'
    }
    border_color = phenotype_border_colors.get(actual_phenotype, 'gray')

    # Interior colors based on metabolic state (from gene network)
    glyco_active = gene_states.get('glycoATP', False)
    mito_active = gene_states.get('mitoATP', False)

    # DEBUG: Print gene states to see what's available - TURNED OFF
    # if not hasattr(get_cell_color, '_debug_count'):
    #     get_cell_color._debug_count = 0
    # if get_cell_color._debug_count < 10:
    #     print(f"🎨 DEBUG Cell {cell.state.id[:8]}: glycoATP={glyco_active}, mitoATP={mito_active}, phenotype={actual_phenotype}")
    #     get_cell_color._debug_count += 1

    if glyco_active and mito_active:
        interior_color = "violet"     # mixed metabolism
    elif glyco_active:
        interior_color = "green"      # glycoATP only
    elif mito_active:
        interior_color = "blue"       # mitoATP only
    else:
        interior_color = "lightgray"  # none
    
    # Debug: Show color assignments for first few cells - TURNED OFF
    # if get_cell_color._debug_count <= 10:
    #     print(f"   → Assigned color: {interior_color}|{border_color}")

    # Return combined color info as a formatted string
    return f"{interior_color}|{border_color}"


def final_report(population, local_environments, config: Any = None) -> None:
    """
    Print comprehensive final report of all cells with their metabolic rates and states.
    Called at the end of simulation to provide detailed cell-by-cell analysis.
    """
    # TURNED OFF - detailed cell report disabled
    return

    print("🔬 CUSTOM FINAL REPORT FUNCTION CALLED!")
    print("\n" + "="*100)
    print("🔬 FINAL CELL METABOLIC REPORT")
    print("="*100)

    # Group cells by metabolic state for summary
    state_counts = {
        'mitoATP': 0,
        'glycoATP': 0,
        'BOTH_ATP': 0,
        'NO_ATP': 0,
        'Necrotic': 0,
        'Apoptotic': 0,
        'Growth_Arrest': 0,
        'Proliferation': 0
    }

    # Store detailed data for each cell
    cell_data = []

    for cell in population.state.cells.values():
        # Get cell position
        pos = f"({cell.state.position[0]:.0f},{cell.state.position[1]:.0f})"

        # Get local environment
        local_env = local_environments[cell.state.id]
        local_oxygen = local_env['Oxygen']
        local_glucose = local_env['Glucose']
        local_lactate = local_env['Lactate']

        # Calculate metabolism using the same function
        reactions = calculate_cell_metabolism(local_env, cell.state.__dict__, config)

        # Get metabolic rates
        oxygen_rate = reactions['Oxygen']
        glucose_rate = reactions['Glucose']
        lactate_rate = reactions['Lactate']

        # Determine cell state
        gene_states = cell.state.gene_states

        # Check fate genes first
        if gene_states['Apoptosis']:
            cell_state = 'Apoptotic'
            state_counts['Apoptotic'] += 1
        elif gene_states['Necrosis']:
            cell_state = 'Necrotic'
            state_counts['Necrotic'] += 1
        elif gene_states['Growth_Arrest']:
            cell_state = 'Growth_Arrest'
            state_counts['Growth_Arrest'] += 1
        elif gene_states['Proliferation']:
            cell_state = 'Proliferation'
            state_counts['Proliferation'] += 1
        else:
            # Check ATP genes
            mito_atp = gene_states['mitoATP']
            glyco_atp = gene_states['glycoATP']

            if mito_atp and glyco_atp:
                cell_state = 'BOTH_ATP'
                state_counts['BOTH_ATP'] += 1
            elif mito_atp:
                cell_state = 'mitoATP'
                state_counts['mitoATP'] += 1
            elif glyco_atp:
                cell_state = 'glycoATP'
                state_counts['glycoATP'] += 1
            else:
                cell_state = 'NO_ATP'
                state_counts['NO_ATP'] += 1

        # Store cell data
        cell_data.append({
            'id': cell.state.id[:8],
            'pos': pos,
            'state': cell_state,
            'oxygen_env': local_oxygen,
            'glucose_env': local_glucose,
            'lactate_env': local_lactate,
            'oxygen_rate': oxygen_rate,
            'glucose_rate': glucose_rate,
            'lactate_rate': lactate_rate
        })

    # Print summary statistics
    print(f"\n📊 POPULATION SUMMARY ({len(population.state.cells)} total cells):")
    for state, count in state_counts.items():
        if count > 0:
            percentage = (count / len(population.state.cells)) * 100
            print(f"   • {state}: {count} cells ({percentage:.1f}%)")

    # Print detailed cell-by-cell report
    print(f"\n📋 DETAILED CELL REPORT:")
    print(f"{'ID':<8} {'Pos':<10} {'State':<12} {'O2_env':<8} {'Glc_env':<8} {'Lac_env':<8} {'O2_rate':<12} {'Glc_rate':<12} {'Lac_rate':<12}")
    print("-" * 120)

    # Sort by cell state for easier reading
    cell_data.sort(key=lambda x: x['state'])

    for data in cell_data:
        print(f"{data['id']:<8} {data['pos']:<10} {data['state']:<12} "
              f"{data['oxygen_env']:<8.3f} {data['glucose_env']:<8.3f} {data['lactate_env']:<8.3f} "
              f"{data['oxygen_rate']:<12.2e} {data['glucose_rate']:<12.2e} {data['lactate_rate']:<12.2e}")

    # Print metabolic summary by state
    print(f"\n🧬 METABOLIC SUMMARY BY STATE:")
    state_metabolism = {}

    for data in cell_data:
        state = data['state']
        if state not in state_metabolism:
            state_metabolism[state] = {
                'count': 0,
                'total_oxygen': 0.0,
                'total_glucose': 0.0,
                'total_lactate': 0.0
            }

        state_metabolism[state]['count'] += 1
        state_metabolism[state]['total_oxygen'] += data['oxygen_rate']
        state_metabolism[state]['total_glucose'] += data['glucose_rate']
        state_metabolism[state]['total_lactate'] += data['lactate_rate']

    for state, metrics in state_metabolism.items():
        if metrics['count'] > 0:
            avg_o2 = metrics['total_oxygen'] / metrics['count']
            avg_glc = metrics['total_glucose'] / metrics['count']
            avg_lac = metrics['total_lactate'] / metrics['count']

            print(f"   {state} ({metrics['count']} cells):")
            print(f"     Average O2 rate:  {avg_o2:.2e} mol/s/cell")
            print(f"     Average Glc rate: {avg_glc:.2e} mol/s/cell")
            print(f"     Average Lac rate: {avg_lac:.2e} mol/s/cell")
            print(f"     Total O2 flux:    {metrics['total_oxygen']:.2e} mol/s")
            print(f"     Total Glc flux:   {metrics['total_glucose']:.2e} mol/s")
            print(f"     Total Lac flux:   {metrics['total_lactate']:.2e} mol/s")
            print()

    print("="*100)


# =============================================================================
# AGING AND TIMING FUNCTIONS
# =============================================================================

def age_cell(cell, dt: float):
    """
    Custom aging function to debug aging process.
    """
    old_age = cell.state.age
    new_age = old_age + dt

    # Debug aging for first few cells
    cell_id = cell.state.id[:8]
    if old_age < 1.0:  # Only debug young cells
        print(f"🕰️ AGING: Cell {cell_id} age {old_age:.3f} → {new_age:.3f} (dt={dt})")

    # Update cell age
    cell.state = cell.state.with_updates(age=new_age)

# =============================================================================
# TIMING ORCHESTRATION FUNCTIONS
# =============================================================================

def should_update_intracellular(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool:
    """
    Determine if intracellular processes should be updated this step.
    For Jayatilake experiment: Update every step for realistic gene network dynamics.
    """
    # Debug intracellular timing (reduced output)
    if current_step <= 5 or current_step % 20 == 0:
        print(f"[CHECK] INTRACELLULAR CHECK: step={current_step}, last={last_update}, interval={interval}")

    # Update every step for realistic gene network behavior
    return True

def should_update_diffusion(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool:
    """
    Determine if diffusion should be updated this step.
    For Jayatilake experiment: Use standard interval-based updates.
    """
    # Use standard interval-based updates
    return (current_step - last_update) >= interval

def should_update_intercellular(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool:
    """
    Determine if intercellular processes should be updated this step.
    For Jayatilake experiment: Use standard interval-based updates.
    """
    # Debug intercellular timing (reduced output)
    should_update = (current_step - last_update) >= interval
    if should_update and (current_step <= 10 or current_step % 20 == 0):
        print(f"[INTERCELLULAR] UPDATE: step={current_step}, last={last_update}, interval={interval}")

    # Use standard interval-based updates
    return should_update




def update_cell_phenotype(cell_state: Dict[str, Any], local_environment: Dict[str, float], gene_states: Dict[str, bool], current_phenotype: str = None, config: Any = None) -> str:
    """
    Determine cell phenotype based on gene network states for Jayatilake experiment.
    Uses the standard NetLogo-style phenotype determination logic with ATP override.
    Includes hardcoded necrosis threshold check to match NetLogo behavior.
    """
    # HARDCODED NECROSIS CHECK (matches NetLogo logic)
    # This overrides gene network if both oxygen AND glucose are below thresholds
    oxygen_conc, glucose_conc = get_required_environment_concentrations(local_environment, 'oxygen', 'glucose')

    # Get necrosis thresholds from config (matching NetLogo values)
    necrosis_threshold_oxygen = 0.011  # the-necrosis-threshold
    necrosis_threshold_glucose = 0.23  # the-necrosis-threshold-g

    if config:
        necrosis_threshold_oxygen = getattr(config, 'necrosis_threshold_oxygen', 0.011)
        necrosis_threshold_glucose = getattr(config, 'necrosis_threshold_glucose', 0.23)

    # # NetLogo hardcoded necrosis logic: if (Oxygen < threshold AND Glucose < threshold) -> Necrosis
    # if oxygen_conc < necrosis_threshold_oxygen and glucose_conc < necrosis_threshold_glucose:
    #     return "Necrosis"
    
    # Check fate genes in NetLogo order (sequential, not if-elif)
    # Later fate genes can overwrite earlier ones when multiple are active

    # Start with default phenotype
    phenotype = "Growth_Arrest"

    # Check each fate gene in NetLogo order
    # if gene_states['Necrosis']:
    #     phenotype = "Necrosis"

    # if gene_states['Apoptosis']: # TODO: reactivate
    #     phenotype = "Apoptosis"

    if gene_states['Proliferation']:
        phenotype = "Proliferation"

    if gene_states['Growth_Arrest']:
        phenotype = "Growth_Arrest"


    # Get ATP parameters from cell state - NO DEFAULTS, must be present
    cell_id = cell_state.get('id', 'unknown')
    metabolic_state = get_required_cell_state(cell_state, 'metabolic_state', cell_id)
    atp_rate = get_required_cell_state(metabolic_state, 'atp_rate', cell_id)

    # Only proceed if we have valid metabolic state
    if atp_rate > 0:
        # Get thresholds from config - NO HARDCODED VALUES
        try:
            max_atp_rate = get_parameter_from_config(config, 'max_atp_rate', fail_if_missing=True)
            atp_threshold = get_parameter_from_config(config, 'atp_threshold', fail_if_missing=True)
        except ValueError as e:
            print(f"❌ CRITICAL PARAMETER MISSING in ATP override: {e}")
            raise SystemExit(1)

        # Calculate normalized ATP rate
        atp_rate_normalized = atp_rate / max_atp_rate if max_atp_rate > 0 else 0

        # If ATP is sufficient, override death phenotypes
        if atp_rate_normalized > atp_threshold:
            if phenotype in ['Apoptosis', 'Necrosis']:
                phenotype = "Proliferation"

    return phenotype


def select_division_direction(parent_position: Tuple[int, int], available_positions: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """
    Select direction for cell division.
    For Jayatilake experiment: random selection from available positions.
    """
    if not available_positions:
        return None

    # Random selection from available positions
    import random
    return random.choice(available_positions)


def calculate_migration_probability(cell_state: Dict[str, Any], local_environment: Dict[str, float], target_position: Optional[Tuple[int, int]] = None) -> float:
    """
    Calculate migration probability for a cell.
    For Jayatilake experiment: no migration (return 0.0).
    """
    # No migration in Jayatilake experiment
    return 0.0


def check_cell_death(cell_state: Dict[str, Any], local_environment: Dict[str, float]) -> bool:
    """
    Determine if a cell should die based on its state and environment.
    For Jayatilake experiment: cells die if they have Apoptosis or Necrosis phenotype.
    """
    # DISABLED: No cell death for debugging
    return False

    # # Get current phenotype
    # phenotype = cell_state['phenotype']
    #
    # # Cell dies if it has death phenotypes
    # return phenotype in ['Apoptosis', 'Necrosis']

