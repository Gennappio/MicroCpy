"""
Custom Functions for MicroC 2.0 - Single Cell Test

This file respects the initial_cell_count parameter from the config.
"""

from typing import Dict, Any, List, Tuple
import numpy as np

def custom_initialize_cell_placement(grid_size: Tuple[int, int], simulation_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Custom initial cell placement that respects initial_cell_count
    """
    width, height = grid_size
    center_x, center_y = width // 2, height // 2
    
    # Get initial_cell_count from simulation_params
    initial_cell_count = simulation_params.get('initial_cell_count', 1)
    
    placements = []
    
    if initial_cell_count == 1:
        # Single cell at center
        placements.append({
            'position': (center_x, center_y),
            'phenotype': "Proliferation"  # Start with proliferation to test gene network
        })
    else:
        # Multiple cells - create a compact arrangement
        positions_added = 0
        for radius in range(max(width, height)):
            if positions_added >= initial_cell_count:
                break
                
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if positions_added >= initial_cell_count:
                        break
                        
                    x = center_x + dx
                    y = center_y + dy
                    
                    if (0 <= x < width and 0 <= y < height and 
                        abs(dx) + abs(dy) <= radius):  # Manhattan distance
                        
                        # Center cell is proliferative, others are growth arrest
                        if dx == 0 and dy == 0:
                            phenotype = "Proliferation"
                        else:
                            phenotype = "Growth_Arrest"
                        
                        placements.append({
                            'position': (x, y),
                            'phenotype': phenotype
                        })
                        positions_added += 1
    
    print(f"🧬 Created {len(placements)} cell placements (requested: {initial_cell_count})")
    return placements


def custom_get_cell_color(cell, gene_states: Dict[str, bool], config: Any) -> str:
    """
    Get cell color based on metabolic state from gene network outputs.

    Color scheme:
    - Black: Necrosis
    - Red: Apoptosis
    - Blue: OXPHOS only (mitoATP active, glycoATP inactive)
    - Green: Glycolysis only (glycoATP active, mitoATP inactive)
    - Violet: Mixed metabolism (both active)
    - Gray: Quiescent (neither active)
    """
    # Death states (highest priority)
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
        return "gray"       # Quiescent (no active metabolism)
