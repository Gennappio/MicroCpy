"""
Setup custom parameters for cell behavior.

This function configures custom parameters used by cell functions.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Setup Custom Parameters",
    description="Configure custom parameters for cell behavior (ATP, metabolism, etc.)",
    category="INITIALIZATION",
    parameters=[
        {"name": "cell_cycle_time", "type": "FLOAT", "description": "Minimum time for cell division (iterations)", "default": 240.0},
        {"name": "max_cell_age", "type": "FLOAT", "description": "Maximum cell age in hours before death", "default": 500.0},
        {"name": "max_atp", "type": "FLOAT", "description": "Maximum ATP per glucose molecule", "default": 30.0},
        {"name": "max_atp_rate", "type": "FLOAT", "description": "Maximum ATP production rate (mol/s)", "default": 1.0e-14},
        {"name": "atp_threshold", "type": "FLOAT", "description": "ATP threshold for proliferation", "default": 0.8},
        {"name": "glyco_oxygen_ratio", "type": "FLOAT", "description": "Oxygen consumption ratio for glycolysis vs OXPHOS", "default": 0.1},
        {"name": "proton_coefficient", "type": "FLOAT", "description": "Proton production coefficient", "default": 0.01},
        {"name": "glucose_factor", "type": "FLOAT", "description": "Glucose consumption factor", "default": 2.0},
        {"name": "KG", "type": "FLOAT", "description": "Michaelis constant for glucose (mM)", "default": 0.5},
        {"name": "KO2", "type": "FLOAT", "description": "Michaelis constant for oxygen (mM)", "default": 0.01},
        {"name": "KL", "type": "FLOAT", "description": "Michaelis constant for lactate (mM)", "default": 1.0},
        {"name": "oxygen_vmax", "type": "FLOAT", "description": "Maximum oxygen uptake rate", "default": 1.0e-16},
        {"name": "glucose_vmax", "type": "FLOAT", "description": "Maximum glucose uptake rate", "default": 3.0e-15},
        {"name": "necrosis_threshold_oxygen", "type": "FLOAT", "description": "Oxygen threshold for necrosis", "default": 0.011},
        {"name": "necrosis_threshold_glucose", "type": "FLOAT", "description": "Glucose threshold for necrosis", "default": 0.23},
        {"name": "base_migration_rate", "type": "FLOAT", "description": "Base migration probability", "default": 0.0},
    ],
    outputs=[],
    cloneable=False
)
def setup_custom_parameters(
    context: Dict[str, Any],
    cell_cycle_time: float = 240.0,
    max_cell_age: float = 500.0,
    max_atp: float = 30.0,
    max_atp_rate: float = 1.0e-14,
    atp_threshold: float = 0.8,
    glyco_oxygen_ratio: float = 0.1,
    proton_coefficient: float = 0.01,
    glucose_factor: float = 2.0,
    KG: float = 0.5,
    KO2: float = 0.01,
    KL: float = 1.0,
    oxygen_vmax: float = 1.0e-16,
    glucose_vmax: float = 3.0e-15,
    necrosis_threshold_oxygen: float = 0.011,
    necrosis_threshold_glucose: float = 0.23,
    base_migration_rate: float = 0.0,
    **kwargs
) -> bool:
    """
    Setup custom parameters for cell behavior.
    
    Args:
        context: Workflow context
        All other args: Custom parameters for cell functions
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Setting up custom parameters")
    
    try:
        config = context.get('config')
        
        if not config:
            print("[ERROR] Config must be set up before custom parameters")
            return False
        
        # Ensure custom_parameters dict exists
        if not hasattr(config, 'custom_parameters') or config.custom_parameters is None:
            config.custom_parameters = {}
        
        # Set all custom parameters
        config.custom_parameters['cell_cycle_time'] = cell_cycle_time
        config.custom_parameters['max_cell_age'] = max_cell_age
        config.custom_parameters['max_atp'] = max_atp
        config.custom_parameters['max_atp_rate'] = max_atp_rate
        config.custom_parameters['atp_threshold'] = atp_threshold
        config.custom_parameters['glyco_oxygen_ratio'] = glyco_oxygen_ratio
        config.custom_parameters['proton_coefficient'] = proton_coefficient
        config.custom_parameters['glucose_factor'] = glucose_factor
        config.custom_parameters['KG'] = KG
        config.custom_parameters['KO2'] = KO2
        config.custom_parameters['KL'] = KL
        config.custom_parameters['oxygen_vmax'] = oxygen_vmax
        config.custom_parameters['glucose_vmax'] = glucose_vmax
        config.custom_parameters['necrosis_threshold_oxygen'] = necrosis_threshold_oxygen
        config.custom_parameters['necrosis_threshold_glucose'] = necrosis_threshold_glucose
        config.custom_parameters['base_migration_rate'] = base_migration_rate
        
        print(f"   [+] Set {len(config.custom_parameters)} custom parameters")
        print(f"   [+] ATP threshold: {atp_threshold}")
        print(f"   [+] Cell cycle time: {cell_cycle_time}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup custom parameters: {e}")
        import traceback
        traceback.print_exc()
        return False

