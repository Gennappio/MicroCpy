"""
Store simulation dimensions (2D/3D) in context.

This function reads the dimensions from config.domain.dimensions and stores it
in the context for easy access by other workflow functions.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Store Simulation Dimensions",
    description="Store simulation dimensions (2D/3D) in context",
    category="INITIALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=["dimensions"],
    cloneable=False
)
def store_simulation_dimensions(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Store simulation dimensions in context.
    
    Reads config.domain.dimensions (2 or 3) and stores it in context['dimensions']
    for easy access by other workflow functions.
    
    Args:
        context: Workflow context (must contain config with domain.dimensions)
        **kwargs: Additional parameters (ignored)
        
    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Storing simulation dimensions in context")
    
    try:
        config = context.get('config')
        
        if not config:
            print("[ERROR] Config must be set up before storing dimensions")
            return False
        
        if not hasattr(config, 'domain') or not hasattr(config.domain, 'dimensions'):
            print("[ERROR] Config must have domain.dimensions attribute")
            return False
        
        dimensions = config.domain.dimensions
        
        if dimensions not in [2, 3]:
            print(f"[ERROR] Invalid dimensions: {dimensions} (must be 2 or 3)")
            return False
        
        # Store in context
        context['dimensions'] = dimensions
        
        print(f"   [+] Stored dimensions: {dimensions}D")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to store simulation dimensions: {e}")
        import traceback
        traceback.print_exc()
        return False

