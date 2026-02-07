"""
Setup environment configuration.

This function configures environment parameters like pH.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig
from src.workflow.logging import log, log_always


@register_function(
    display_name="Setup Environment",
    description="Configure environment parameters (pH, etc.)",
    category="INITIALIZATION",
    parameters=[
        {"name": "ph", "type": "FLOAT", "description": "Environment pH value", "default": 7.4},
        {"name": "verbose", "type": "BOOL", "description": "Enable detailed logging", "default": None},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def setup_environment(
    context: Dict[str, Any],
    ph: float = 7.4,
    verbose: Optional[bool] = None,
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
    log(context, f"Setting up environment configuration", prefix="[WORKFLOW]", node_verbose=verbose)

    try:
        config: Optional[IConfig] = context.get('config')

        if not config:
            log_always("[ERROR] Config must be set up before environment")
            return False

        # Create environment config
        class EnvironmentConfig:
            def __init__(self, ph_value):
                self.ph = ph_value

        config.environment = EnvironmentConfig(ph)

        log(context, f"Environment pH: {ph}", prefix="[+]", node_verbose=verbose)

        return True

    except Exception as e:
        log_always(f"[ERROR] Failed to setup environment: {e}")
        import traceback
        traceback.print_exc()
        return False

