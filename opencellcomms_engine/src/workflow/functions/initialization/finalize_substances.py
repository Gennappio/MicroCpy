"""
Finalize substances after all have been added.

This function initializes the simulator with all configured substances.
Call this AFTER all add_substance calls to ensure all substances are properly initialized.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from interfaces.base import ISubstanceSimulator


@register_function(
    display_name="Finalize Substances",
    description="Initialize simulator with all configured substances (call after all add_substance)",
    category="INITIALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def finalize_substances(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Finalize substances by initializing the simulator with all configured substances.
    
    This should be called AFTER all add_substance calls to ensure the simulator
    has all substances properly initialized.
    
    Args:
        context: Workflow context containing config and simulator
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    try:
        config = context.get('config')
        simulator: Optional[ISubstanceSimulator] = context.get('simulator')
        
        if not config or not simulator:
            print("[WARNING] No config or simulator in context")
            return True
        
        if not hasattr(config, 'substances') or not config.substances:
            print("[WARNING] No substances configured")
            return True
        
        # Initialize simulator with all substances
        if hasattr(simulator, 'initialize_substances'):
            simulator.initialize_substances(config.substances)
            print(f"[WORKFLOW] Initialized {len(config.substances)} substances in diffusion solver:")
            for name in config.substances.keys():
                print(f"   [+] {name}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to finalize substances: {e}")
        import traceback
        traceback.print_exc()
        return False

