"""
Custom Functions for MicroC 2.0

This file is automatically loaded from the config folder.
Define any functions you want to customize here.

Only define the functions you want to override - the system will
automatically fall back to defaults for any functions not defined.
"""

from typing import Dict, Any, List, Tuple
import numpy as np

def initialize_cell_placement(grid_size: Tuple[int, int], simulation_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Custom initial cell placement

    Example: Create a small tumor spheroid in the center
    """
    width, height = grid_size
    center_x, center_y = width // 2, height // 2

    placements = []

    # Create a small spheroid (3x3 cells)
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            x = center_x + dx
            y = center_y + dy

            if 0 <= x < width and 0 <= y < height:
                # Center cell is proliferative, others are growth arrest
                if dx == 0 and dy == 0:
                    phenotype = "Proliferation"
                else:
                    phenotype = "Growth_Arrest"

                placements.append({
                    'position': (x, y),
                    'phenotype': phenotype
                })

    return placements

def calculate_cell_metabolism(local_environment: Dict[str, Any], cell_state: Dict[str, Any]) -> Dict[str, float]:
    """
    Custom metabolism calculation
    
    Example: Slightly reduced consumption rates
    """
    phenotype = cell_state['phenotype']
    
    # Custom metabolism rates (slightly lower than defaults)
    if phenotype == "Proliferation":
        return {
            'oxygen_consumption_rate': 2.0e-17,  # Reduced from 3.0e-17
            'glucose_consumption_rate': 1.5e-17,
            'lactate_production_rate': 0.8e-17
        }
    elif phenotype == "Growth_Arrest":
        return {
            'oxygen_consumption_rate': 0.8e-17,  # Reduced from 1.0e-17
            'glucose_consumption_rate': 0.4e-17,
            'lactate_production_rate': 0.2e-17
        }
    elif phenotype == "Apoptosis":
        return {
            'oxygen_consumption_rate': 0.05e-17,
            'glucose_consumption_rate': 0.05e-17,
            'lactate_production_rate': 0.0
        }
    else:  # Necrosis
        return {
            'oxygen_consumption_rate': 0.0,
            'glucose_consumption_rate': 0.0,
            'lactate_production_rate': 0.0
        }

def calculate_boundary_conditions(substance_name: str, position: Tuple[float, float], time: float) -> float:
    """
    Custom boundary conditions
    
    Example: Slightly varying oxygen levels
    """
    if substance_name == "oxygen":
        # Base oxygen with small time variation
        base = 0.07  # mM
        variation = 0.005 * np.sin(2 * np.pi * time / 24.0)  # Daily cycle
        return base + variation
    elif substance_name == "glucose":
        return 5.0  # mM
    else:
        return 0.0

# Note: You can define any of the 14 available hook functions here:
# - calculate_cell_metabolism
# - update_cell_phenotype
# - check_cell_division
# - check_cell_death
# - update_gene_network
# - calculate_boundary_conditions
# - initialize_cell_placement
# - select_division_direction
# - calculate_migration_probability
# - should_update_diffusion
# - should_update_intracellular
# - should_update_intercellular
# - capture_custom_metrics
# - handle_performance_alert
