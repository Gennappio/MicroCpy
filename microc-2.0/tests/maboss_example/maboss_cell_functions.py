"""
Simple MaBoSS Example - Custom Cell Functions

Minimal custom functions required for the MaBoSS cell fate example.
Provides timing functions for the orchestrator.
"""


def should_update_diffusion(current_step: int, last_update: int, interval: int, state: dict) -> bool:
    """
    Determine if diffusion should be updated this step.

    For this simple example, update every step.
    """
    return (current_step - last_update) >= interval


def should_update_intracellular(current_step: int, last_update: int, interval: int, state: dict) -> bool:
    """
    Determine if intracellular processes (including MaBoSS) should be updated.

    For this example, update every step so MaBoSS runs at each time_tick.
    """
    return (current_step - last_update) >= interval


def should_update_intercellular(current_step: int, last_update: int, interval: int, state: dict) -> bool:
    """
    Determine if intercellular processes should be updated.

    For this simple example, update every step.
    """
    return (current_step - last_update) >= interval


def update_cell_phenotype(cell, gene_states: dict, local_env: dict, config) -> str:
    """
    Update cell phenotype based on gene network states.
    
    Simple logic for the cell fate model:
    - If Apoptosis is True -> Apoptosis phenotype
    - If Proliferation is True -> Proliferation phenotype
    - Otherwise -> Quiescent
    
    Args:
        cell: Cell object
        gene_states: Dictionary of gene name -> bool state
        local_env: Local environment concentrations
        config: Configuration object
        
    Returns:
        New phenotype name
    """
    # Check apoptosis first (takes priority)
    if gene_states.get('Apoptosis', False):
        return 'Apoptosis'
    
    # Check proliferation
    if gene_states.get('Proliferation', False):
        return 'Proliferation'
    
    # Default to quiescent
    return 'Quiescent'


def get_cell_behavior(cell, phenotype: str, gene_states: dict, config) -> dict:
    """
    Get cell behavior parameters based on phenotype.
    
    Args:
        cell: Cell object
        phenotype: Current phenotype name
        gene_states: Dictionary of gene states
        config: Configuration object
        
    Returns:
        Dictionary of behavior parameters
    """
    behaviors = {
        'Apoptosis': {
            'can_divide': False,
            'can_migrate': False,
            'is_dying': True,
            'death_probability': 1.0,
        },
        'Proliferation': {
            'can_divide': True,
            'can_migrate': True,
            'is_dying': False,
            'division_probability': 0.1,
        },
        'Quiescent': {
            'can_divide': False,
            'can_migrate': False,
            'is_dying': False,
        },
    }
    
    return behaviors.get(phenotype, behaviors['Quiescent'])

