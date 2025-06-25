"""
Test 1 Custom Functions
Tests basic cell placement and behavior
"""

def initialize_cell_placement(grid_size, simulation_params):
    """
    Test 1: Basic cell placement
    Places a single cell in the center for testing basic functionality
    """
    width, height = grid_size
    center_x, center_y = width // 2, height // 2
    
    placements = [
        {'position': (center_x, center_y), 'phenotype': 'Proliferation'}
    ]
    
    return placements

def get_cell_substance_rates(cell_position, cell_phenotype, local_environment, substance_name):
    """
    Test 1: Basic substance rates
    Simple rates for testing consumption/production
    """
    if substance_name == "Oxygen":
        # Basic oxygen consumption
        return {'uptake_rate': 1.0e-17, 'production_rate': 0.0}
    elif substance_name == "Glucose":
        # Basic glucose consumption
        return {'uptake_rate': 1.0e-15, 'production_rate': 0.0}
    elif substance_name == "Lactate":
        # Basic lactate production
        return {'uptake_rate': 0.0, 'production_rate': 1.0e-15}
    else:
        return {'uptake_rate': 0.0, 'production_rate': 0.0}

def update_cell_phenotype(cell, local_environment, dt):
    """
    Test 1: Basic phenotype update
    Simple phenotype logic for testing
    """
    # Check oxygen levels
    oxygen_conc = local_environment.get('oxygen_concentration', 0.05)
    glucose_conc = local_environment.get('glucose_concentration', 3.0)
    
    if oxygen_conc < 0.02 or glucose_conc < 1.0:
        # Low resources - switch to quiescent
        return 'Quiescent'
    else:
        # Good resources - stay proliferative
        return 'Proliferation'

def apply_boundary_conditions(mesh, substance_config):
    """
    Test 1: Basic boundary conditions
    Simple fixed boundary conditions for testing
    """
    # Use default fixed boundary conditions
    return None  # Let system use defaults
