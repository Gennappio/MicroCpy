"""
Custom Functions Template for MicroC 2.0

Copy this file and modify the functions you want to customize.
Only define the functions you want to override - the system will
automatically fall back to defaults for any functions not defined.

To use:
1. Copy this file to your project directory
2. Rename it to 'custom_functions.py' 
3. Modify the functions you want to customize
4. In your simulation script:
   
   from pathlib import Path
   from interfaces.hooks import set_custom_functions_path
   set_custom_functions_path(Path("custom_functions.py"))

Available functions to override:
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np

# =============================================================================
# CELL BEHAVIOR FUNCTIONS
# =============================================================================

def custom_calculate_cell_metabolism(local_environment: Dict[str, Any], cell_state: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate metabolic rates for a cell
    
    Parameters:
    - local_environment: Dict with 'oxygen_concentration', 'glucose_concentration', etc.
    - cell_state: Dict with 'age', 'phenotype', etc.
    
    Returns:
    - Dict with metabolic rates (mol/s/cell)
    """
    # Example: Simple oxygen-dependent metabolism
    oxygen = local_environment.get('oxygen_concentration', 0.07)
    
    if oxygen > 0.05:
        return {'oxygen_consumption_rate': 1.0e-18}
    else:
        return {'oxygen_consumption_rate': 0.5e-18}

def custom_update_cell_phenotype(local_environment: Dict[str, Any], gene_states: Dict[str, bool], current_phenotype: str) -> str:
    """
    Update cell phenotype based on environment and genes
    
    Parameters:
    - local_environment: Environmental conditions
    - gene_states: Current gene expression states
    - current_phenotype: Current phenotype string
    
    Returns:
    - New phenotype string
    """
    # Example: Simple oxygen-based phenotype
    oxygen = local_environment.get('oxygen_concentration', 0.07)
    
    if oxygen < 0.02:
        return "hypoxic"
    else:
        return "normal"

def custom_check_cell_death(cell_state: Dict[str, Any], local_environment: Dict[str, Any]) -> bool:
    """
    Determine if cell should die
    
    Parameters:
    - cell_state: Cell properties  
    - local_environment: Environmental conditions
    
    Returns:
    - True if cell should die
    """
    # Example: Age and oxygen-based death
    age = cell_state.get('age', 0.0)
    oxygen = local_environment.get('oxygen_concentration', 0.07)
    
    return age > 120.0 or oxygen < 0.005

# =============================================================================
# GENE NETWORK FUNCTIONS
# =============================================================================

def custom_update_gene_network(current_states: Dict[str, bool], inputs: Dict[str, float], network_params: Dict[str, Any]) -> Dict[str, bool]:
    """
    Custom gene network update logic

    This completely overrides the gene network logic from config.py!
    Use this to implement custom gene regulatory logic.

    Parameters:
    - current_states: Current gene expression states
    - inputs: Environmental inputs (from substance concentrations)
    - network_params: Network parameters

    Returns:
    - Updated gene expression states (must include phenotype outputs)
    """
    # Example: Custom gene network logic
    new_states = current_states.copy()

    # Get environmental inputs
    oxygen = inputs.get('Oxygen_supply', True)
    glucose = inputs.get('Glucose_supply', True)
    growth_inhibitor = inputs.get('Growth_Inhibitor', False)

    # Custom regulatory logic
    new_states['p53'] = not oxygen or not glucose or growth_inhibitor
    new_states['p21'] = new_states['p53']

    # Custom phenotype determination
    if not oxygen and not glucose:
        # Severe stress -> Necrosis
        new_states['Necrosis'] = True
        new_states['Apoptosis'] = False
        new_states['Growth_Arrest'] = False
        new_states['Proliferation'] = False
    elif not oxygen:
        # Hypoxia -> Apoptosis
        new_states['Necrosis'] = False
        new_states['Apoptosis'] = True
        new_states['Growth_Arrest'] = False
        new_states['Proliferation'] = False
    elif new_states['p21']:
        # p21 activation -> Growth arrest
        new_states['Necrosis'] = False
        new_states['Apoptosis'] = False
        new_states['Growth_Arrest'] = True
        new_states['Proliferation'] = False
    elif oxygen and glucose:
        # Good conditions -> Proliferation
        new_states['Necrosis'] = False
        new_states['Apoptosis'] = False
        new_states['Growth_Arrest'] = False
        new_states['Proliferation'] = True
    else:
        # Default -> Growth arrest
        new_states['Necrosis'] = False
        new_states['Apoptosis'] = False
        new_states['Growth_Arrest'] = True
        new_states['Proliferation'] = False

    return new_states

# =============================================================================
# SUBSTANCE SIMULATION FUNCTIONS
# =============================================================================

def custom_calculate_boundary_conditions(substance_name: str, position: Tuple[float, float], time: float) -> float:
    """
    Calculate custom boundary conditions
    
    Parameters:
    - substance_name: Name of the substance
    - position: (x, y) position in meters
    - time: Current time in hours
    
    Returns:
    - Boundary concentration value
    """
    # Example: Time-varying oxygen
    if substance_name == "oxygen":
        base = 0.07  # mM
        variation = 0.01 * np.sin(2 * np.pi * time / 24.0)  # Daily cycle
        return base + variation
    
    return 0.0

# =============================================================================
# POPULATION DYNAMICS FUNCTIONS
# =============================================================================

def custom_initialize_cell_placement(grid_size: Tuple[int, int], simulation_params: Dict[str, Any]) -> List[Any]:
    """
    Define initial cell placement pattern

    Parameters:
    - grid_size: (width, height) of the simulation grid
    - simulation_params: Additional simulation parameters

    Returns:
    - List of cell placements. Each placement can be:
      * Dict: {'position': (x, y), 'phenotype': 'normal'}
      * Tuple: ((x, y), 'phenotype') or (x, y, 'phenotype')
    """
    # Example: Single cell at center
    center_x = grid_size[0] // 2
    center_y = grid_size[1] // 2

    return [
        {'position': (center_x, center_y), 'phenotype': 'normal'}
    ]

def custom_select_division_direction(parent_position: Tuple[int, int], available_positions: List[Tuple[int, int]]) -> Tuple[int, int]:
    """
    Select direction for cell division
    
    Parameters:
    - parent_position: (x, y) grid position of parent
    - available_positions: List of available (x, y) positions
    
    Returns:
    - Selected (x, y) position for daughter cell
    """
    # Example: Random selection
    if available_positions:
        return available_positions[np.random.randint(len(available_positions))]
    return parent_position

def custom_calculate_migration_probability(cell_state: Dict[str, Any], local_environment: Dict[str, Any], target_position: Tuple[int, int]) -> float:
    """
    Calculate probability of cell migration
    
    Parameters:
    - cell_state: Cell properties
    - local_environment: Current and target environment
    - target_position: Target (x, y) position
    
    Returns:
    - Migration probability (0.0 to 1.0)
    """
    # Example: Migrate towards better oxygen
    current_oxygen = local_environment.get('oxygen_concentration', 0.07)
    target_oxygen = local_environment.get('target_oxygen_concentration', 0.07)
    
    if target_oxygen > current_oxygen:
        return 0.8
    else:
        return 0.2

# =============================================================================
# TIMING ORCHESTRATION FUNCTIONS
# =============================================================================

def custom_should_update_diffusion(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool:
    """
    Determine if diffusion should be updated this step
    
    Parameters:
    - current_step: Current simulation step
    - last_update: Step of last update
    - interval: Default update interval
    - state: Current simulation state
    
    Returns:
    - True if should update
    """
    # Example: Fixed interval
    return (current_step - last_update) >= interval

def custom_should_update_intracellular(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool:
    """
    Determine if intracellular processes should be updated this step
    """
    # Example: Update every step
    return True

def custom_should_update_intercellular(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool:
    """
    Determine if intercellular processes should be updated this step
    """
    # Example: Fixed interval
    return (current_step - last_update) >= interval

# =============================================================================
# PERFORMANCE MONITORING FUNCTIONS
# =============================================================================

def custom_capture_custom_metrics(monitor: Any, timestamp: float) -> Dict[str, float]:
    """
    Capture custom performance metrics
    
    Parameters:
    - monitor: Performance monitor object
    - timestamp: Current timestamp
    
    Returns:
    - Dict of custom metrics
    """
    # Example: Custom metrics
    return {
        'custom_efficiency': 0.95,
        'custom_throughput': 1000.0
    }

def custom_handle_performance_alert(alert: Dict[str, Any]) -> None:
    """
    Handle performance alerts
    
    Parameters:
    - alert: Alert information dict
    """
    # Example: Log alert
    print(f"Performance alert: {alert.get('message', 'Unknown')}")

# =============================================================================
# USAGE INSTRUCTIONS
# =============================================================================

"""
USAGE INSTRUCTIONS:

1. Copy this template to the config folder as 'config/custom_functions.py'

2. Modify only the functions you want to customize

3. Delete functions you don't want to override (system will use defaults)

4. In your simulation script:

   from pathlib import Path
   from interfaces.hooks import set_custom_functions_path

   # Load your custom functions from config folder
   set_custom_functions_path(Path("config/custom_functions.py"))

   # Run simulation - custom functions will be used automatically!

5. Available hooks (all use custom_ prefix):
   - custom_calculate_cell_metabolism
   - custom_update_cell_phenotype
   - custom_check_cell_death
   - custom_update_gene_network
   - custom_calculate_boundary_conditions
   - custom_initialize_cell_placement
   - custom_select_division_direction
   - custom_calculate_migration_probability
   - custom_should_update_diffusion
   - custom_should_update_intracellular
   - custom_should_update_intercellular
   - custom_capture_custom_metrics
   - custom_handle_performance_alert

6. The system automatically falls back to defaults for undefined functions

7. No modification of core MicroC 2.0 code required!
"""
