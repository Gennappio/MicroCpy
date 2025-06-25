"""
Test 2 Custom Functions
Tests multiple cell interactions and gradient formation
"""

def initialize_cell_placement(grid_size, simulation_params):
    """
    Test 2: Multiple cell placement
    Places multiple cells to test interactions and gradient formation
    """
    width, height = grid_size
    center_x, center_y = width // 2, height // 2
    
    placements = []
    
    # Central cluster of cells
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            x, y = center_x + dx, center_y + dy
            if 0 <= x < width and 0 <= y < height:
                # Vary phenotypes to test interactions
                if dx == 0 and dy == 0:
                    phenotype = "Proliferation"
                elif abs(dx) + abs(dy) == 1:
                    phenotype = "Growth_Arrest"
                else:
                    phenotype = "Quiescent"
                
                placements.append({'position': (x, y), 'phenotype': phenotype})
    
    # Add some scattered cells
    scattered_positions = [
        (center_x - 3, center_y - 3),
        (center_x + 3, center_y + 3),
        (center_x - 3, center_y + 3),
        (center_x + 3, center_y - 3)
    ]
    
    for pos in scattered_positions:
        x, y = pos
        if 0 <= x < width and 0 <= y < height:
            placements.append({'position': (x, y), 'phenotype': 'Proliferation'})
    
    return placements

def get_cell_substance_rates(cell_position, cell_phenotype, local_environment, substance_name):
    """
    Test 2: Phenotype-dependent substance rates
    Different rates based on cell phenotype to test interactions
    """
    # Base rates depend on phenotype
    if cell_phenotype == "Proliferation":
        multiplier = 2.0  # High activity
    elif cell_phenotype == "Growth_Arrest":
        multiplier = 1.0  # Normal activity
    elif cell_phenotype == "Quiescent":
        multiplier = 0.5  # Low activity
    else:
        multiplier = 1.0
    
    if substance_name == "Oxygen":
        return {
            'uptake_rate': 2.0e-17 * multiplier,
            'production_rate': 0.0
        }
    elif substance_name == "Glucose":
        return {
            'uptake_rate': 2.0e-15 * multiplier,
            'production_rate': 0.0
        }
    elif substance_name == "Lactate":
        return {
            'uptake_rate': 0.0,
            'production_rate': 2.0e-15 * multiplier
        }
    elif substance_name == "FGF":
        # Only proliferating cells produce FGF
        production = 1.0e-16 if cell_phenotype == "Proliferation" else 0.0
        return {
            'uptake_rate': 5.0e-17,
            'production_rate': production
        }
    elif substance_name == "TGFA":
        # Growth arrested cells produce TGFA
        production = 5.0e-17 if cell_phenotype == "Growth_Arrest" else 0.0
        return {
            'uptake_rate': 2.0e-17,
            'production_rate': production
        }
    else:
        return {'uptake_rate': 0.0, 'production_rate': 0.0}

def update_cell_phenotype(cell, local_environment, dt):
    """
    Test 2: Complex phenotype update
    Phenotype changes based on multiple environmental factors
    """
    # Get concentrations
    oxygen_conc = local_environment.get('oxygen_concentration', 0.07)
    glucose_conc = local_environment.get('glucose_concentration', 5.0)
    lactate_conc = local_environment.get('lactate_concentration', 1.0)
    fgf_conc = local_environment.get('fgf_concentration', 0.01)
    tgfa_conc = local_environment.get('tgfa_concentration', 0.005)
    
    # Complex decision logic
    if oxygen_conc < 0.022 or glucose_conc < 2.0:
        # Hypoxic or nutrient-starved
        if lactate_conc > 3.0:
            return 'Apoptosis'  # Too much lactate
        else:
            return 'Quiescent'  # Survive but don't grow
    elif fgf_conc > 0.02:
        # High growth factor
        return 'Proliferation'
    elif tgfa_conc > 0.01:
        # Growth inhibition signal
        return 'Growth_Arrest'
    else:
        # Default based on current state
        current_phenotype = getattr(cell, 'phenotype', 'Proliferation')
        if current_phenotype == 'Quiescent' and oxygen_conc > 0.05 and glucose_conc > 4.0:
            return 'Proliferation'  # Recovery
        else:
            return current_phenotype  # Stay the same

def apply_boundary_conditions(mesh, substance_config):
    """
    Test 2: Custom boundary conditions
    Test different boundary condition types
    """
    # For testing, use different boundary conditions for different substances
    if substance_config.name == "FGF":
        # Zero flux boundary for growth factors (they don't cross boundaries easily)
        return "zero_flux"
    elif substance_config.name == "TGFA":
        # Zero flux boundary
        return "zero_flux"
    else:
        # Use default fixed boundaries for metabolites
        return None
