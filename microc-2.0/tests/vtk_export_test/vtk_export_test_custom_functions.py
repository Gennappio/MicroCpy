#!/usr/bin/env python3
"""
Custom functions for VTK Export Test

This module provides simplified custom functions for testing the VTK export functionality.
Focus is on ATP production states that can be visualized in the VTK output.
"""

from typing import Dict, Any, Tuple
import random


def determine_phenotype(gene_states: Dict[str, bool], local_environment: Dict[str, float], 
                       config: Any = None) -> str:
    """
    Determine cell phenotype based on gene network states
    
    Args:
        gene_states: Dictionary of gene name -> boolean state
        local_environment: Local substance concentrations
        config: Configuration object
        
    Returns:
        Phenotype string: "Proliferation", "Apoptosis", "Growth_Arrest", or "Quiescent"
    """
    
    # Get key gene states
    proliferation = gene_states.get('Proliferation', False)
    apoptosis = gene_states.get('Apoptosis', False)
    growth_arrest = gene_states.get('Growth_Arrest', False)
    
    # Determine phenotype based on gene states
    if apoptosis:
        return "Apoptosis"
    elif proliferation:
        return "Proliferation"
    elif growth_arrest:
        return "Growth_Arrest"
    else:
        return "Quiescent"


def custom_should_divide(cell_state: Dict[str, Any], local_environment: Dict[str, float], 
                        config: Any = None) -> Tuple[bool, str]:
    """
    Determine if a cell should divide
    
    Args:
        cell_state: Cell state dictionary
        local_environment: Local substance concentrations
        config: Configuration object
        
    Returns:
        Tuple of (should_divide: bool, reason: str)
    """
    
    # Get cell properties
    phenotype = cell_state.get('phenotype', 'Quiescent')
    age = cell_state.get('age', 0.0)
    
    # Only proliferating cells can divide
    if phenotype != "Proliferation":
        return False, f"Not proliferating (phenotype: {phenotype})"
    
    # Age requirement
    if age < 12.0:  # 12 hours minimum
        return False, f"Too young (age: {age:.1f}h)"
    
    # Environmental requirements
    oxygen = local_environment.get('oxygen_concentration', 0.0)
    glucose = local_environment.get('glucose_concentration', 0.0)
    
    if oxygen < 0.05:  # 0.05 mM minimum oxygen
        return False, f"Low oxygen ({oxygen:.3f} mM)"
    
    if glucose < 1.0:  # 1.0 mM minimum glucose
        return False, f"Low glucose ({glucose:.3f} mM)"
    
    # Random division probability
    if random.random() < 0.3:  # 30% chance
        return True, "Conditions favorable for division"
    else:
        return False, "Random division check failed"


def custom_should_die(cell_state: Dict[str, Any], local_environment: Dict[str, float], 
                     config: Any = None) -> Tuple[bool, str]:
    """
    Determine if a cell should die
    
    Args:
        cell_state: Cell state dictionary
        local_environment: Local substance concentrations
        config: Configuration object
        
    Returns:
        Tuple of (should_die: bool, reason: str)
    """
    
    # Get cell properties
    phenotype = cell_state.get('phenotype', 'Quiescent')
    age = cell_state.get('age', 0.0)
    
    # Apoptotic cells die
    if phenotype == "Apoptosis":
        return True, "Apoptosis phenotype"
    
    # Age-based death
    if age > 48.0:  # 48 hours maximum lifespan
        return True, f"Old age ({age:.1f}h)"
    
    # Environmental stress
    oxygen = local_environment.get('oxygen_concentration', 0.0)
    
    if oxygen < 0.01:  # 0.01 mM critical oxygen level
        return True, f"Severe hypoxia ({oxygen:.3f} mM)"
    
    return False, "Survival conditions met"


def calculate_cell_metabolism(local_environment: Dict[str, float], cell_state: Dict[str, Any], 
                             config: Any = None) -> Dict[str, float]:
    """
    Calculate metabolic production/consumption rates
    
    Args:
        local_environment: Local substance concentrations
        cell_state: Cell state dictionary
        config: Configuration object
        
    Returns:
        Dictionary of substance -> rate (mol/s/cell)
    """
    
    # Initialize all reactions to zero
    reactions = {
        'Oxygen': 0.0,
        'Glucose': 0.0, 
        'Lactate': 0.0
    }
    
    # Get cell properties
    phenotype = cell_state.get('phenotype', 'Quiescent')
    
    # Dead cells don't metabolize
    if phenotype == "Apoptosis":
        return reactions
    
    # Get environmental concentrations
    oxygen = local_environment.get('oxygen_concentration', 0.0)
    glucose = local_environment.get('glucose_concentration', 0.0)
    
    # Base metabolic rates (simplified)
    if phenotype == "Proliferation":
        # High metabolism for proliferating cells
        reactions['Oxygen'] = -1.0e-18    # Consumption (negative)
        reactions['Glucose'] = -2.0e-18   # Consumption (negative)
        reactions['Lactate'] = +3.0e-18   # Production (positive)
    elif phenotype == "Growth_Arrest":
        # Medium metabolism for arrested cells
        reactions['Oxygen'] = -0.5e-18    # Consumption (negative)
        reactions['Glucose'] = -1.0e-18   # Consumption (negative)
        reactions['Lactate'] = +1.5e-18   # Production (positive)
    else:  # Quiescent
        # Low metabolism for quiescent cells
        reactions['Oxygen'] = -0.2e-18    # Consumption (negative)
        reactions['Glucose'] = -0.5e-18   # Consumption (negative)
        reactions['Lactate'] = +0.7e-18   # Production (positive)
    
    # Scale by availability (simple Michaelis-Menten-like)
    oxygen_factor = oxygen / (oxygen + 0.01)  # Half-saturation at 0.01 mM
    glucose_factor = glucose / (glucose + 0.5)  # Half-saturation at 0.5 mM
    
    reactions['Oxygen'] *= oxygen_factor
    reactions['Glucose'] *= glucose_factor
    reactions['Lactate'] *= glucose_factor  # Lactate production depends on glucose
    
    return reactions


def update_cell_metabolic_state(cell, local_environment: Dict[str, float], config: Any = None):
    """
    Update cell metabolic state based on current environment
    
    Args:
        cell: Cell object
        local_environment: Local substance concentrations
        config: Configuration object
    """
    
    # Calculate metabolic reactions
    reactions = calculate_cell_metabolism(local_environment, cell.state.__dict__, config)
    
    # Update metabolic state
    metabolic_state = {
        'oxygen_consumption': abs(reactions.get('Oxygen', 0.0)) if reactions.get('Oxygen', 0.0) < 0 else 0.0,
        'glucose_consumption': abs(reactions.get('Glucose', 0.0)) if reactions.get('Glucose', 0.0) < 0 else 0.0,
        'lactate_production': reactions.get('Lactate', 0.0) if reactions.get('Lactate', 0.0) > 0 else 0.0,
        'lactate_consumption': abs(reactions.get('Lactate', 0.0)) if reactions.get('Lactate', 0.0) < 0 else 0.0
    }
    
    # Update cell state
    cell.state = cell.state.with_updates(metabolic_state=metabolic_state)


def custom_migration_direction(cell_state: Dict[str, Any], local_environment: Dict[str, float],
                              neighbor_environments: Dict[Tuple[int, int], Dict[str, float]],
                              config: Any = None) -> Tuple[int, int]:
    """
    Determine migration direction for a cell

    Args:
        cell_state: Cell state dictionary
        local_environment: Current local environment
        neighbor_environments: Dictionary of position -> environment for neighbors
        config: Configuration object

    Returns:
        Tuple of (dx, dy) for migration direction
    """

    # Simple random migration
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]
    return random.choice(directions)


def update_cell_phenotype(cell_state: Dict[str, Any], local_environment: Dict[str, float],
                         gene_states: Dict[str, bool], current_phenotype: str,
                         config: Any = None) -> str:
    """
    Update cell phenotype based on gene network states

    Args:
        cell_state: Cell state dictionary
        local_environment: Local substance concentrations
        gene_states: Dictionary of gene name -> boolean state
        current_phenotype: Current phenotype string
        config: Configuration object

    Returns:
        New phenotype string
    """
    return determine_phenotype(gene_states, local_environment, config)


def should_update_diffusion(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool:
    """Determine if diffusion should be updated this step"""
    return (current_step - last_update) >= interval


def should_update_intracellular(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool:
    """Determine if intracellular processes should be updated this step"""
    return (current_step - last_update) >= interval


def should_update_intercellular(current_step: int, last_update: int, interval: int, state: Dict[str, Any]) -> bool:
    """Determine if intercellular processes should be updated this step"""
    return (current_step - last_update) >= interval


def check_cell_death(cell_state: Dict[str, Any], local_environment: Dict[str, float],
                    config: Any = None) -> Tuple[bool, str]:
    """
    Check if a cell should die (wrapper for custom_should_die)

    Args:
        cell_state: Cell state dictionary
        local_environment: Local substance concentrations
        config: Configuration object

    Returns:
        Tuple of (should_die: bool, reason: str)
    """
    return custom_should_die(cell_state, local_environment, config)


# Required function list for MicroC
REQUIRED_FUNCTIONS = [
    'determine_phenotype',
    'custom_should_divide',
    'custom_should_die',
    'calculate_cell_metabolism',
    'update_cell_metabolic_state',
    'custom_migration_direction',
    'update_cell_phenotype',
    'check_cell_death',
    'should_update_diffusion',
    'should_update_intracellular',
    'should_update_intercellular'
]
