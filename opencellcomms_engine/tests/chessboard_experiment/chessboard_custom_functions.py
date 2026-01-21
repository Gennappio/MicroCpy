"""
Chessboard Experiment Custom Functions
Creates an artificial domain with fixed substance concentrations in different zones.
Each zone has one cell with specific high/low substance combinations.
"""

from typing import Dict, List, Tuple, Any
import numpy as np


def custom_initialize_cell_placement(grid_size: Tuple[int, int], simulation_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Place one cell in each grid zone (4x4 = 16 cells total).
    Each cell will be in a zone with a unique combination of substance concentrations.
    """
    nx, ny = grid_size  # Should be 4x4

    print(f"[SEARCH] SYSTEMATIC COMBINATION PLACEMENT:")
    print(f"   Grid size: {nx}x{ny}")
    print(f"   Total combinations: {nx * ny} (2^4)")

    placements = []

    # Place one cell in each grid position
    for x in range(nx):
        for y in range(ny):
            # Calculate combination ID (0-15)
            combination_id = y * nx + x

            placements.append({
                'position': (x, y),
                'phenotype': "Proliferation",  # All start as proliferative
                'combination_id': combination_id
            })

    print(f"   [CHART] Placed {len(placements)} cells (one per combination)")
    return placements


def custom_setup_chessboard_concentrations(simulator, config):
    """
    Set up systematic combination patterns for all 2^4 = 16 combinations.
    Each grid position represents a unique combination of 4 substances (high/low).
    """
    print(f" Setting up systematic combination patterns...")

    # Get grid size (should be 4x4)
    nx, ny = config.domain.nx, config.domain.ny
    params = config.custom_parameters

    # Define the 4 key substances for systematic combination testing
    # These are the substances that will have systematic high/low combinations
    # All other substances will remain at default values
    key_substances = {
        "Oxygen": {
            'high': params.get('oxygen_high', 0.06),
            'low': params.get('oxygen_low', 0.01),
            'bit_position': 0  # Bit 0 (rightmost)
        },
        "Lactate": {
            'high': params.get('lactate_high', 3.0),
            'low': params.get('lactate_low', 0.5),
            'bit_position': 1  # Bit 1
        },
        "Glucose": {
            'high': params.get('glucose_high', 6.0),
            'low': params.get('glucose_low', 2.0),
            'bit_position': 2  # Bit 2
        },
        "TGFA": {
            'high': params.get('tgfa_high', 2.0e-6),
            'low': params.get('tgfa_low', 5.0e-7),
            'bit_position': 3  # Bit 3 (leftmost)
        }
    }

    print(f"   [CHART] Creating {2**len(key_substances)} combinations for {len(key_substances)} key substances")
    print(f"    Key substances: {list(key_substances.keys())}")

    # Apply systematic combinations to key substances only
    for substance_name, substance_info in key_substances.items():
        if substance_name in simulator.state.substances:
            concentrations = simulator.state.substances[substance_name].concentrations
            high_val = substance_info['high']
            low_val = substance_info['low']
            bit_pos = substance_info['bit_position']

            # For each grid position, determine if this substance should be high or low
            for i in range(ny):
                for j in range(nx):
                    # Calculate combination ID (0-15)
                    combination_id = i * nx + j

                    # Check if the bit at bit_position is set (1 = high, 0 = low)
                    is_high = (combination_id >> bit_pos) & 1

                    if is_high:
                        concentrations[i, j] = high_val
                    else:
                        concentrations[i, j] = low_val

            print(f"    {substance_name}: min={concentrations.min():.2e}, max={concentrations.max():.2e}")

    # Set all other substances to their default values (uniform across all zones)
    for substance_name in simulator.state.substances.keys():
        if substance_name not in key_substances:
            concentrations = simulator.state.substances[substance_name].concentrations
            # Use the initial value from config as uniform concentration
            default_val = getattr(config.substances[substance_name], 'initial_value', 0.0)
            if hasattr(default_val, 'value'):
                default_val = default_val.value
            concentrations.fill(default_val)
            print(f"   [TOOL] {substance_name}: uniform={default_val:.2e}")

    # Print the combination table for reference
    print(f"\n    SYSTEMATIC COMBINATION TABLE:")
    print(f"   {'ID':<3} {'Pos':<7} {'Oxygen':<8} {'Lactate':<8} {'Glucose':<8} {'TGFA':<8}")
    print(f"   {'-'*3} {'-'*7} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

    for i in range(ny):
        for j in range(nx):
            combination_id = i * nx + j
            oxygen_state = "HIGH" if (combination_id >> 0) & 1 else "LOW"
            lactate_state = "HIGH" if (combination_id >> 1) & 1 else "LOW"
            glucose_state = "HIGH" if (combination_id >> 2) & 1 else "LOW"
            tgfa_state = "HIGH" if (combination_id >> 3) & 1 else "LOW"

            print(f"   {combination_id:<3} ({j},{i})<3 {oxygen_state:<8} {lactate_state:<8} {glucose_state:<8} {tgfa_state:<8}")

    print(f"   [+] All 16 systematic combinations applied to key substances!")
    print(f"   [+] All other substances set to uniform default values!")


def custom_calculate_cell_metabolism(local_environment: Dict[str, float],
                                   cell_state: Dict[str, Any],
                                   config: Any = None) -> Dict[str, float]:
    """
    No metabolism - keep concentrations fixed in artificial environment.
    Return zero consumption/production for all substances.
    """
    return {
        'Oxygen': 0.0,
        'Glucose': 0.0,
        'Lactate': 0.0,
        'H': 0.0,
        'FGF': 0.0,
        'EGF': 0.0,
        'TGFA': 0.0,
        'VEGF': 0.0,
        'HGF': 0.0,
        'EGFRD': 0.0,
        'FGFRD': 0.0,
        'GI': 0.0,
        'cMETD': 0.0,
        'pH': 0.0,
        'MCT1D': 0.0,
        'GLUT1D': 0.0
    }


def custom_post_initialization_setup(simulator, config):
    """
    Called after simulation initialization to set up chessboard patterns.
    This is a hook that can be called from the main simulation.
    """
    print(" Post-initialization: Setting up chessboard patterns...")
    custom_setup_chessboard_concentrations(simulator, config)


def custom_get_cell_color(cell_state: Dict[str, Any], local_environment: Dict[str, Any]) -> str:
    """
    Color cells based on their phenotype for easy visualization.
    """
    phenotype = cell_state.get('phenotype', 'Unknown')
    
    color_map = {
        'Proliferation': '#00FF00',    # Green
        'Growth_Arrest': '#FFA500',    # Orange  
        'Quiescent': '#0000FF',        # Blue
        'Apoptosis': '#FF0000',        # Red
        'Necrosis': '#800080',         # Purple
        'Glycolysis': '#FFFF00',       # Yellow
        'OXPHOS': '#00FFFF',           # Cyan
        'Mixed_Metabolism': '#FF69B4'  # Pink
    }
    
    return color_map.get(phenotype, '#808080')  # Gray for unknown
