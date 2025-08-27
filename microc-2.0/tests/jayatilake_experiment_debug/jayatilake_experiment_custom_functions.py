import numpy as np
import math
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

def get_required_concentration(local_environment: Dict[str, float], substance_name: str, alternative_name: str = None, context: str = "") -> float:
    if alternative_name is None: alternative_name = substance_name.lower()
    concentration = local_environment.get(substance_name, local_environment.get(alternative_name))
    if concentration is None: raise ValueError(f"CRITICAL: {substance_name} concentration missing.")
    return concentration

def get_required_gene_state(gene_states: Dict[str, bool], gene_name: str, cell_id: str = "unknown") -> bool:
    if gene_name not in gene_states: raise ValueError(f"CRITICAL: {gene_name} gene state missing for cell {cell_id}.")
    return gene_states[gene_name]

def get_required_cell_state(cell_state: Dict[str, Any], state_name: str, cell_id: str = "unknown") -> Any:
    if state_name not in cell_state: raise ValueError(f"CRITICAL: {state_name} missing from cell {cell_id}.")
    return cell_state[state_name]

def get_required_environment_concentrations(local_environment: Dict[str, float], *substance_names: str) -> List[float]:
    concentrations = []
    for substance in substance_names:
        if substance not in local_environment: raise KeyError(f"CRITICAL: Missing '{substance}' concentration.")
        concentrations.append(local_environment[substance])
    return concentrations

try:
    import os, sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path: sys.path.insert(0, current_dir)
    tests_dir = os.path.join(os.getcwd(), 'tests', 'jayatilake_experiment')
    if os.path.exists(tests_dir) and tests_dir not in sys.path: sys.path.insert(0, tests_dir)
    import jayatilake_experiment_custom_metabolism as metabolism
    METABOLISM_FUNCTIONS_AVAILABLE = True
except ImportError:
    METABOLISM_FUNCTIONS_AVAILABLE = False

def get_parameter_from_config(config, param_name: str, default_value=None, section=None, fail_if_missing=False):
    if not config:
        if fail_if_missing: raise ValueError(f"Required parameter '{param_name}' missing.")
        return default_value
    if section:
        section_data = getattr(config, section, {})
        if isinstance(section_data, dict) and param_name in section_data: return section_data[param_name]
    custom_params = getattr(config, 'custom_parameters', {})
    if isinstance(custom_params, dict) and param_name in custom_params: return custom_params[param_name]
    if hasattr(config, param_name): return getattr(config, param_name)
    elif isinstance(config, dict) and param_name in config: return config[param_name]
    if fail_if_missing: raise ValueError(f"Required parameter '{param_name}' not found.")
    return default_value

def initialize_cell_placement(grid_size: Tuple[int, int], simulation_params: Dict[str, Any], config: Any) -> List[Dict[str, Any]]:
    fipy_nx, fipy_ny = grid_size
    domain_size_um = config.domain.size_x.micrometers
    cell_height_um = config.domain.cell_height.micrometers
    bio_nx = int(domain_size_um / cell_height_um)
    bio_ny = int(domain_size_um / cell_height_um)
    initial_count = simulation_params['initial_cell_count']
    placements = []
    used_positions = set()
    center_x, center_y = bio_nx // 2, bio_ny // 2
    radius = 1
    cells_placed = 0
    while cells_placed < initial_count and radius < min(bio_nx, bio_ny) // 2:
        for x in range(max(0, center_x - radius), min(bio_nx, center_x + radius + 1)):
            for y in range(max(0, center_y - radius), min(bio_ny, center_y + radius + 1)):
                if cells_placed >= initial_count: break
                if np.sqrt((x - center_x)**2 + (y - center_y)**2) <= radius:
                    fipy_x = max(0, min(fipy_nx - 1, int(x * fipy_nx / bio_nx)))
                    fipy_y = max(0, min(fipy_ny - 1, int(y * fipy_ny / bio_ny)))
                    fipy_pos = (fipy_x, fipy_y)
                    if fipy_pos not in used_positions:
                        used_positions.add(fipy_pos)
                        placements.append({'position': fipy_pos, 'phenotype': "Proliferation"})
                        cells_placed += 1
            if cells_placed >= initial_count: break
        radius += 1
    return placements

def initialize_cell_ages(population, config: Any = None):
    try:
        max_cell_age = get_parameter_from_config(config, 'max_cell_age', fail_if_missing=True)
    except ValueError as e:
        print(f"FAILED: {e}")
        return
    mean_age = max_cell_age / 2.0
    std_dev = max_cell_age / 6.0
    for cell in population.state.cells.values():
        random_age = max(0.0, min(max_cell_age, np.random.normal(mean_age, std_dev)))
        cell.state = cell.state.with_updates(age=random_age)

def custom_initialize_cell_ages(population, config: Any = None):
    initialize_cell_ages(population, config)

def calculate_cell_metabolism(local_environment: Dict[str, float], cell_state: Dict[str, Any], config: Any = None) -> Dict[str, float]:
    reactions = {k: 0.0 for k in ['Oxygen', 'Glucose', 'Lactate', 'H', 'pH', 'FGF', 'TGFA', 'HGF', 'GI', 'EGFRD', 'FGFRD', 'cMETD', 'MCT1D', 'GLUT1D']}

    # FIXED: Lactate PRODUCTION (positive) to match standalone
    # Standalone uses +2.8e-2 mM/s
    # Convert to mol/s/cell: 2.8e-2 mM/s * mesh_volume / 1000
    # mesh_volume = 20um x 20um x 20um = 8e-15 m
    # So: 2.8e-2 * 8e-15 / 1000 = 2.24e-19 mol/s/cell
    reactions['Lactate'] = +2.24e-19  # PRODUCTION (positive) to match standalone
    return reactions

def update_cell_metabolic_state(cell, local_environment: Dict[str, float], config: Any = None):
    reactions = calculate_cell_metabolism(local_environment, cell.state.__dict__, config)
    metabolic_state = {
        'atp_rate': reactions.get('atp_rate', 0.0),
        'oxygen_consumption': abs(reactions.get('Oxygen', 0.0)) if reactions.get('Oxygen', 0.0) < 0 else 0.0,
        'glucose_consumption': abs(reactions.get('Glucose', 0.0)) if reactions.get('Glucose', 0.0) < 0 else 0.0,
        'lactate_production': reactions.get('Lactate', 0.0) if reactions.get('Lactate', 0.0) > 0 else 0.0,
        'lactate_consumption': abs(reactions.get('Lactate', 0.0)) if reactions.get('Lactate', 0.0) < 0 else 0.0
    }
    cell.state = cell.state.with_updates(metabolic_state=metabolic_state)

def should_divide(cell, config: Any) -> bool:
    return False # Disable division for this test

def get_cell_color(cell, gene_states: Dict[str, bool], config: Any) -> str:
    return "lightgray|orange"

def update_cell_phenotype(cell_state: Dict[str, Any], local_environment: Dict[str, float], gene_states: Dict[str, bool], current_phenotype: str = None, config: Any = None) -> str:
    return "Growth_Arrest"

def should_update_intracellular(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool: return True
def should_update_diffusion(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool: return (current_step - last_update) >= interval
def should_update_intercellular(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool: return (current_step - last_update) >= interval
def age_cell(cell, dt: float): cell.state = cell.state.with_updates(age=cell.state.age + dt)
def select_division_direction(parent_position: Tuple[int, int], available_positions: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]: return None
def calculate_migration_probability(cell_state: Dict[str, Any], local_environment: Dict[str, float], target_position: Optional[Tuple[int, int]] = None) -> float: return 0.0
def check_cell_death(cell_state: Dict[str, Any], local_environment: Dict[str, float]) -> bool: return False
