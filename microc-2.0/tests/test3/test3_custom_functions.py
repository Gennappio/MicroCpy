"""
Test 3 Custom Functions
Stress tests and edge cases
"""

def initialize_cell_placement(grid_size, simulation_params):
    """
    Test 3: Stress test cell placement
    Many cells in different patterns to stress test the system
    """
    width, height = grid_size
    placements = []
    
    # Dense central cluster
    center_x, center_y = width // 2, height // 2
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            x, y = center_x + dx, center_y + dy
            if 0 <= x < width and 0 <= y < height:
                # Alternate phenotypes in checkerboard pattern
                if (dx + dy) % 2 == 0:
                    phenotype = "Proliferation"
                else:
                    phenotype = "Growth_Arrest"
                placements.append({'position': (x, y), 'phenotype': phenotype})
    
    # Border cells to test boundary interactions
    border_positions = [
        (1, 1), (1, height-2), (width-2, 1), (width-2, height-2),  # Corners
        (width//4, 1), (3*width//4, 1),  # Top edge
        (width//4, height-2), (3*width//4, height-2),  # Bottom edge
        (1, height//4), (1, 3*height//4),  # Left edge
        (width-2, height//4), (width-2, 3*height//4)  # Right edge
    ]
    
    for pos in border_positions:
        x, y = pos
        if 0 <= x < width and 0 <= y < height:
            placements.append({'position': (x, y), 'phenotype': 'Quiescent'})
    
    # Random scattered cells
    import random
    random.seed(42)  # Reproducible
    for _ in range(10):
        x = random.randint(0, width-1)
        y = random.randint(0, height-1)
        # Avoid placing on existing cells
        if not any(p['position'] == (x, y) for p in placements):
            placements.append({'position': (x, y), 'phenotype': 'Proliferation'})
    
    return placements

def get_cell_substance_rates(cell_position, cell_phenotype, local_environment, substance_name):
    """
    Test 3: Extreme substance rates
    High rates to test numerical stability
    """
    # Extreme multipliers based on phenotype
    if cell_phenotype == "Proliferation":
        multiplier = 3.0  # Very high activity
    elif cell_phenotype == "Growth_Arrest":
        multiplier = 0.1  # Very low activity
    elif cell_phenotype == "Quiescent":
        multiplier = 0.01  # Extremely low activity
    elif cell_phenotype == "Apoptosis":
        multiplier = 0.0  # No activity
    else:
        multiplier = 1.0
    
    # Position-dependent rates (edge effects)
    x, y = cell_position
    edge_factor = 1.0
    if x < 3 or y < 3 or x > 26 or y > 26:  # Near edges
        edge_factor = 2.0  # Higher activity near edges
    
    total_multiplier = multiplier * edge_factor
    
    if substance_name == "Oxygen":
        return {
            'uptake_rate': 5.0e-17 * total_multiplier,
            'production_rate': 0.0
        }
    elif substance_name == "Glucose":
        return {
            'uptake_rate': 5.0e-15 * total_multiplier,
            'production_rate': 0.0
        }
    elif substance_name == "Lactate":
        return {
            'uptake_rate': 0.0,
            'production_rate': 5.0e-15 * total_multiplier
        }
    elif substance_name == "FGF":
        # Only proliferating cells produce FGF
        production = 2.0e-16 * total_multiplier if cell_phenotype == "Proliferation" else 0.0
        return {
            'uptake_rate': 1.0e-16 * total_multiplier,
            'production_rate': production
        }
    elif substance_name == "TGFA":
        # Growth arrested cells produce TGFA
        production = 1.0e-16 * total_multiplier if cell_phenotype == "Growth_Arrest" else 0.0
        return {
            'uptake_rate': 5.0e-17 * total_multiplier,
            'production_rate': production
        }
    elif substance_name == "HGF":
        # Quiescent cells produce HGF
        production = 1.5e-16 * total_multiplier if cell_phenotype == "Quiescent" else 0.0
        return {
            'uptake_rate': 3.0e-17 * total_multiplier,
            'production_rate': production
        }
    elif substance_name == "GI":
        # All cells produce growth inhibitor when stressed
        oxygen_conc = local_environment['oxygen_concentration']
        glucose_conc = local_environment['glucose_concentration']
        
        if oxygen_conc < 0.05 or glucose_conc < 2.0:
            production = 3.0e-16 * total_multiplier  # Stress response
        else:
            production = 0.0
        
        return {
            'uptake_rate': 1.0e-16 * total_multiplier,
            'production_rate': production
        }
    else:
        return {'uptake_rate': 0.0, 'production_rate': 0.0}

def update_cell_phenotype(cell, local_environment, dt):
    """
    Test 3: Complex phenotype transitions
    Multiple factors and potential oscillations
    """
    # Get all concentrations
    oxygen_conc = local_environment['oxygen_concentration']
    glucose_conc = local_environment['glucose_concentration']
    lactate_conc = local_environment['lactate_concentration']
    fgf_conc = local_environment['fgf_concentration']
    tgfa_conc = local_environment['tgfa_concentration']
    hgf_conc = local_environment['hgf_concentration']
    gi_conc = local_environment['gi_concentration']
    
    # Complex decision tree with multiple conditions
    if gi_conc > 0.001:
        # Growth inhibitor present
        if oxygen_conc < 0.01:
            return 'Apoptosis'  # Death
        else:
            return 'Quiescent'  # Survival mode
    elif oxygen_conc < 0.01 or glucose_conc < 0.5:
        # Severe hypoxia/starvation
        if lactate_conc > 5.0:
            return 'Apoptosis'  # Lactate toxicity
        else:
            return 'Quiescent'  # Try to survive
    elif lactate_conc > 3.0:
        # Lactate stress
        return 'Growth_Arrest'
    elif fgf_conc > 0.005 and hgf_conc > 0.01:
        # Strong growth signals
        return 'Proliferation'
    elif tgfa_conc > 0.003:
        # Growth arrest signal
        return 'Growth_Arrest'
    elif oxygen_conc > 0.05 and glucose_conc > 5.0:
        # Good conditions
        return 'Proliferation'
    else:
        # Marginal conditions
        return 'Quiescent'

def apply_boundary_conditions(mesh, substance_config):
    """
    Test 3: Mixed boundary conditions
    Different types to test robustness
    """
    if substance_config.name in ["FGF", "TGFA", "HGF", "GI"]:
        # Growth factors and inhibitors don't cross boundaries
        return "zero_flux"
    else:
        # Metabolites have fixed boundaries
        return None
