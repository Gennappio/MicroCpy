"""
Setup environment configuration.

This function configures environment parameters like pH.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Setup Environment",
    description="Configure environment parameters (pH, etc.)",
    category="INITIALIZATION",
    parameters=[
        {"name": "ph", "type": "FLOAT", "description": "Environment pH value", "default": 7.4},
    ],
    outputs=[],
    cloneable=False
)
def setup_environment(
    context: Dict[str, Any],
    ph: float = 7.4,
    **kwargs
) -> bool:
    """
    Setup environment configuration.
    
    Args:
        context: Workflow context
        ph: Environment pH value
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Setting up environment configuration")
    
    try:
        config = context.get('config')
        
        if not config:
            print("[ERROR] Config must be set up before environment")
            return False
        
        # Create environment config
        class EnvironmentConfig:
            def __init__(self, ph_value):
                self.ph = ph_value
        
        config.environment = EnvironmentConfig(ph)
        
        print(f"   [+] Environment pH: {ph}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup environment: {e}")
        import traceback
        traceback.print_exc()
        return False

