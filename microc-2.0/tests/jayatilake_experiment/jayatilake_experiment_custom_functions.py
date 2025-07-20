import numpy as np
import math
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

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
    print(f"⚠️  Could not import custom metabolism functions: {e}")
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
    print(f"⚠️  Parameter '{param_name}' not found in config, using default: {default_value}")
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


def initialize_cell_placement(grid_size: Tuple[int, int], simulation_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Initialize cells in a spheroid configuration for metabolic symbiosis experiment.
    Places cells in center with some initial heterogeneity.

    IMPORTANT: This function receives the FiPy grid size, but should calculate
    biological cell positions based on cell_height parameter!
    """
    fipy_nx, fipy_ny = grid_size  # This is the FiPy grid (e.g., 40x40)

    # Calculate biological cell grid based on cell_height
    # Get domain size and cell_height from simulation_params
    domain_size_um = simulation_params['domain_size_um'] if 'domain_size_um' in simulation_params else simulation_params['size_x']
    cell_height_um = simulation_params['cell_height_um'] if 'cell_height_um' in simulation_params else simulation_params['cell_height']
    # Calculate biological cell grid size
    bio_nx = int(domain_size_um / cell_height_um)  # e.g., 600/80 = 7.5 → 7
    bio_ny = int(domain_size_um / cell_height_um)

    print(f"🔍 BIOLOGICAL CELL GRID DEBUG:")
    print(f"   FiPy grid: {fipy_nx}×{fipy_ny}")
    print(f"   Domain size: {domain_size_um} μm")
    print(f"   Cell height: {cell_height_um} μm")
    print(f"   Biological cell grid: {bio_nx}×{bio_ny}")
    print(f"   Biological cell size: {cell_height_um} μm")
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

    # Get initial cell count from simulation parameters
    initial_count = simulation_params['initial_cell_count']
    
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

    print(f"🕰️ INITIALIZING CELL AGES (RANDOM DISTRIBUTION):")
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

        # Debug first few cells
        if cells_updated <= 3:
            can_proliferate = "✅" if random_age >= cell_cycle_time else "❌"
            print(f"   Cell {cell_id[:8]}: age {old_age:.1f} → {random_age:.1f} {can_proliferate}")

    # Print statistics
    ages_array = np.array(ages_set)
    print(f"   📊 Age Statistics:")
    print(f"      Mean: {np.mean(ages_array):.1f}")
    print(f"      Std Dev: {np.std(ages_array):.1f}")
    print(f"      Min: {np.min(ages_array):.1f}")
    print(f"      Max: {np.max(ages_array):.1f}")
    print(f"   ✅ Updated {cells_updated} cells with random ages")
    print(f"   🔬 {cells_can_proliferate}/{cells_updated} cells can proliferate immediately")


def custom_initialize_cell_ages(population, config: Any = None):
    """
    Hook-compatible version of initialize_cell_ages.
    Called via hook system to set initial cell ages.
    """
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
    # Check if metabolism functions are available
    if not METABOLISM_FUNCTIONS_AVAILABLE:
        # Fail gently - return empty reactions if metabolism functions not available
        print("Warning: Metabolism functions not available, skipping metabolism calculations")
        return {substance: 0.0 for substance in [
            'Oxygen', 'Glucose', 'Lactate', 'H', 'pH', 'FGF', 'TGFA', 'HGF', 'GI',
            'EGFRD', 'FGFRD', 'cMETD', 'MCT1D', 'GLUT1D'
        ]}

    # Debug metabolism for random cells at random times
    import random
    cell_id = cell_state.get('id', 'unknown')

    # Random debugging: 1% chance to debug any cell
    debug_this_cell = random.random() < 0.01

    # Get gene states from cell state (they should be stored there after gene network update)
    gene_states = cell_state['gene_states']

    # Get local concentrations
    local_oxygen = local_environment['Oxygen']
    local_glucose = local_environment['Glucose']
    local_lactate = local_environment['Lactate']
    local_h = local_environment['H']

    # Get NetLogo-compatible Michaelis constants and metabolic parameters from config
    km_oxygen = get_parameter_from_config(config, 'the_optimal_oxygen')      # NetLogo Km for oxygen
    km_glucose = get_parameter_from_config(config, 'the_optimal_glucose')     # NetLogo Km for glucose
    km_lactate = get_parameter_from_config(config, 'the_optimal_lactate')     # NetLogo Km for lactate
    vmax_oxygen = get_parameter_from_config(config, 'oxygen_vmax')         # NetLogo Vmax for oxygen
    vmax_glucose = get_parameter_from_config(config, 'glucose_vmax')       # NetLogo Vmax for glucose
    max_atp = get_parameter_from_config(config, 'max_atp')                      # Maximum ATP per glucose
    proton_coefficient = get_parameter_from_config(config, 'proton_coefficient')  # Proton production coefficient

    # Growth factor rate constants (Jayatilake et al. 2024 - Table values)
    tgfa_consumption = get_parameter_from_config(config, 'tgfa_consumption_rate')  # TGFA consumption rate
    tgfa_production = get_parameter_from_config(config, 'tgfa_production_rate')    # TGFA production rate
    hgf_consumption = get_parameter_from_config(config, 'hgf_consumption_rate')    # HGF consumption rate
    hgf_production = get_parameter_from_config(config, 'hgf_production_rate')          # HGF production rate
    fgf_consumption = get_parameter_from_config(config, 'fgf_consumption_rate')    # FGF consumption rate
    fgf_production = get_parameter_from_config(config, 'fgf_production_rate')          # FGF production rate

    # Initialize reactions for all substances (from diffusion-parameters.txt)
    reactions = {
        # Metabolic substances (Michaelis-Menten kinetics)
        'Oxygen': 0.0,
        'Glucose': 0.0,
        'Lactate': 0.0,
        'H': 0.0,
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

    # Only consume/produce if cell is alive (not necrotic)
    is_necrotic = gene_states['Necrosis']
    if is_necrotic:
        if debug_this_cell:
            print(f"\n🔬 NECROTIC CELL {cell_id[:8]}: No metabolism")
        return reactions

    # Get gene states
    mito_atp = 1.0 if gene_states['mitoATP'] else 0.0
    glyco_atp = 1.0 if gene_states['glycoATP'] else 0.0

    # Determine cell type for debugging
    cell_type = "UNKNOWN"
    if mito_atp and not glyco_atp:
        cell_type = "mitoATP"
    elif glyco_atp and not mito_atp:
        cell_type = "glycoATP"
    elif mito_atp and glyco_atp:
        cell_type = "BOTH_ATP"
    else:
        cell_type = "NO_ATP"

    # NetLogo-style reaction term calculations using Michaelis-Menten kinetics
    # Based on NetLogo MicroC implementation (lines 2788, 2998, 3054, 3161)

    # Calculate ATP rate using NetLogo-style kinetics
    atp_rate = 0.0

    # OXPHOS pathway (mitoATP active) - consumes oxygen and glucose/lactate
    if mito_atp > 0:
        # Oxygen consumption with Michaelis-Menten kinetics (NetLogo style)
        oxygen_mm_factor = local_oxygen / (km_oxygen + local_oxygen)
        reactions['Oxygen'] = -vmax_oxygen * oxygen_mm_factor

        # Glucose consumption for OXPHOS (NetLogo line 2998) - REDUCED for mitoATP
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

        # Lactate production from glycolysis using proper Michaelis-Menten kinetics
        # Formula: R_L,p = (2*μ_O2*A_0/6) * (C_G/(2*K_G + C_G)) * (glycoATP)
        # Where μ_O2*A_0 = vmax_oxygen, K_G = km_glucose, C_G = local_glucose
                # Lactate production from glycolysis (NetLogo line 3660)
        lactate_production = 0.01*(vmax_oxygen * 2.0 / 6) * (max_atp / 2) * glucose_mm_factor

        reactions['Lactate'] += lactate_production

        # Proton production from glycolysis (NetLogo line 3429)
        # Proton production should be proportional to lactate production
        proton_production = (vmax_oxygen * 2.0 / 6) * proton_coefficient * (max_atp / 2) * glucose_mm_factor
        reactions['H'] += proton_production

        # ATP production from glycolysis
        atp_rate += glucose_consumption_glyco * 2  # 2 ATP per glucose in glycolysis

        # Small oxygen consumption even in glycolysis (NetLogo style)
        reactions['Oxygen'] += -vmax_oxygen * 0.5 * oxygen_mm_factor  # K=0.5 according to paper

    # Store ATP rate in cell state for division decisions
    cell_state['atp_rate'] = atp_rate

    # Growth factor kinetics (Jayatilake et al. 2024: RS = γS,C × CS for consumption, RS = γS,P for production)

    # TGFA - specific table values
    tgfa_conc = local_environment['TGFA']
    reactions['TGFA'] = -tgfa_consumption * tgfa_conc + tgfa_production

    # HGF - specific table values (no production)
    hgf_conc = local_environment['HGF']
    reactions['HGF'] = -hgf_consumption * hgf_conc + hgf_production

    # FGF - from diffusion-parameters.txt
    fgf_conc = local_environment['FGF']
    reactions['FGF'] = -fgf_consumption * fgf_conc + fgf_production

    # Growth inhibitor kinetics (from diffusion-parameters.txt: GI consumption=2.0e-17, production=0.0e-20)
    gi_conc = local_environment['GI']
    reactions['GI'] = -2.0e-17 * gi_conc  # Only consumption, no production

    # Drug inhibitor kinetics (from diffusion-parameters.txt: all have consumption=4.0e-17, production=0.0)
    drug_inhibitors = ['EGFRD', 'FGFRD', 'cMETD', 'MCT1D', 'GLUT1D']
    for drug in drug_inhibitors:
        local_conc = local_environment[drug]
        reactions[drug] = -4.0e-17 * local_conc  # From diffusion-parameters.txt

    # pH calculation (Jayatilake et al. 2024: pH = -log10([H+]))
    h_conc = local_environment['H']
    if h_conc > 0:
        import math
        ph_value = -math.log10(h_conc)
        # pH doesn't have a "reaction rate" - it's a derived quantity
        reactions['pH'] = 0.0  # pH is calculated from H+, not produced/consumed directly

    # ATP PRODUCTION RATE CALCULATION
    # Calculate ATP production based on metabolic pathways (glycolysis vs OXPHOS)
    atp_rate = 0.0

    # Glycolytic ATP production (from glucose consumption)
    if glyco_atp and reactions['Glucose'] < 0:  # If consuming glucose
        glucose_consumption_rate = abs(reactions['Glucose'])  # mol/s/cell
        # Glycolysis: 1 glucose → 2 ATP (net)
        glycolytic_atp = glucose_consumption_rate * 2.0  # 2 ATP per glucose
        atp_rate += glycolytic_atp

    # Mitochondrial ATP production (from oxygen consumption)
    if mito_atp and reactions['Oxygen'] < 0:  # If consuming oxygen
        oxygen_consumption_rate = abs(reactions['Oxygen'])  # mol/s/cell
        # OXPHOS: 1 O2 → ~30 ATP (approximate)
        mitochondrial_atp = oxygen_consumption_rate * 30.0  # 30 ATP per O2
        atp_rate += mitochondrial_atp

    # Store ATP rate in reactions for access by division function
    reactions['atp_rate'] = atp_rate

    # Apply environmental constraints - don't consume more than available
    for substance in ['Oxygen', 'Glucose', 'Lactate', 'FGF', 'TGFA', 'HGF', 'GI'] + drug_inhibitors:
        local_conc = local_environment[substance]
        if reactions[substance] < 0:  # Consumption
            max_consumption = abs(reactions[substance])
            available = local_conc
            if available < max_consumption:
                reactions[substance] = -available * 0.9  # Leave some residual

    # Optional debug output for metabolism results (uncomment for debugging)
    # if debug_this_cell:
    #     print(f"   METABOLISM RESULTS:")
    # Comprehensive debugging output
    if debug_this_cell:
        print(f"\n🔬 CELL {cell_id[:8]} ({cell_type}) METABOLISM:")
        print(f"  Environment: O2={local_environment.get('Oxygen', 0):.3f}, Glc={local_environment.get('Glucose', 0):.3f}, Lac={local_environment.get('Lactate', 0):.3f}")
        print(f"  Gene states: mitoATP={mito_atp}, glycoATP={glyco_atp}")
        print(f"  OXYGEN:  {reactions['Oxygen']:.2e} mol/s/cell")
        print(f"  GLUCOSE: {reactions['Glucose']:.2e} mol/s/cell")
        print(f"  LACTATE: {reactions['Lactate']:.2e} mol/s/cell")
        print(f"  H+:      {reactions['H']:.2e} mol/s/cell")
        print(f"  TGFA:    {reactions['TGFA']:.2e} mol/s/cell")

    return reactions


def update_cell_metabolic_state(cell, local_environment: Dict[str, float], config: Any = None):
    """
    Update cell's metabolic state with calculated ATP rate and other metabolic values.
    This function should be called during intracellular processes to populate metabolic_state.
    """
    # Calculate metabolism using the existing function
    reactions = calculate_cell_metabolism(local_environment, cell.state.__dict__, config)

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

    # Check if cell has sufficient age (basic cell cycle time)
    if cell.state.age < cell_cycle_time:
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
        print(f"   ATP: rate={atp_rate:.2e}, max={max_atp_rate:.2e}, normalized={atp_rate_normalized:.4f}, threshold={atp_threshold}")
    except Exception as e:
        print(f"   ❌ ATP ERROR: {e}")
        print(f"   Cell state: {cell.state}")
        return False

    # METABOLIC OVERRIDE: If ATP conditions are met, FORCE proliferation phenotype
    # This ensures metabolic decisions override gene network phenotype decisions
    if atp_rate_normalized > atp_threshold:
        print(f"   ATP check PASSED: {atp_rate_normalized:.4f} > {atp_threshold} - FORCING Proliferation")
        # Update cell phenotype to proliferation (override gene network decision)
        cell.state = cell.state.with_updates(phenotype="Proliferation")
        print(f"   DIVISION DECISION: TRUE (ATP override)")
        return True

    # If ATP is insufficient, check if we're already in proliferation state
    # (Allow continued proliferation if already started)
    if cell.state.phenotype == "Proliferation":
        print(f"   ATP check FAILED but already Proliferation - allowing division")
        print(f"   DIVISION DECISION: TRUE (already proliferating)")
        return True

    print(f"   ATP check FAILED: {atp_rate_normalized:.4f} <= {atp_threshold}, phenotype: {cell.state.phenotype}")
    print(f"   DIVISION DECISION: FALSE")
    return False


def get_cell_color(cell, gene_states: Dict[str, bool], config: Any) -> str:
    """
    Get cell color based on gene network outputs (matching NetLogo visualization).
    """
    # Phenotype-based colors (highest priority)
    if gene_states['Necrosis']:
        return "black"
    elif gene_states['Apoptosis']:
        return "red"

    # Metabolic state colors based on gene network outputs
    glyco_active = gene_states['glycoATP']
    mito_active = gene_states['mitoATP']

    if glyco_active and not mito_active:
        return "green"      # Glycolysis only
    elif not glyco_active and mito_active:
        return "blue"       # OXPHOS only
    elif glyco_active and mito_active:
        return "violet"     # Mixed metabolism
    else:
        return "gray"       # Quiescent


def final_report(population, local_environments, config: Any = None) -> None:
    """
    Print comprehensive final report of all cells with their metabolic rates and states.
    Called at the end of simulation to provide detailed cell-by-cell analysis.
    """
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
        print(f"🕐 INTRACELLULAR CHECK: step={current_step}, last={last_update}, interval={interval}")

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
        print(f"🔄 INTERCELLULAR UPDATE: step={current_step}, last={last_update}, interval={interval}")

    # Use standard interval-based updates
    return should_update




def update_cell_phenotype(cell_state: Dict[str, Any], local_environment: Dict[str, float], gene_states: Dict[str, bool], current_phenotype: str = None) -> str:
    """
    Determine cell phenotype based on gene network states for Jayatilake experiment.
    Uses the standard NetLogo-style phenotype determination logic.
    """
    # Check fate genes in NetLogo order (sequential, not if-elif)
    # Later fate genes can overwrite earlier ones when multiple are active

    # Start with default phenotype
    phenotype = "Growth_Arrest"

    # Check each fate gene in NetLogo order
    if gene_states['Apoptosis']:
        phenotype = "Apoptosis"

    if gene_states['Proliferation']:
        phenotype = "Proliferation"

    if gene_states['Growth_Arrest']:
        phenotype = "Growth_Arrest"

    if gene_states['Necrosis']:
        phenotype = "Necrosis"

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
    # Get current phenotype
    phenotype = cell_state['phenotype']

    # Cell dies if it has death phenotypes
    return phenotype in ['Apoptosis', 'Necrosis']

