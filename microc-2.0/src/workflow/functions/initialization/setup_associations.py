"""
Setup substance-to-gene associations and thresholds.

This function configures how substances map to gene network inputs.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Add Association",
    description="Add a substance-to-gene association (use one node per association)",
    category="INITIALIZATION",
    parameters=[
        {"name": "substance_name", "type": "STRING", "description": "Name of the substance", "default": "Oxygen"},
        {"name": "gene_input", "type": "STRING", "description": "Gene network input node name", "default": "Oxygen_supply"},
        {"name": "threshold", "type": "FLOAT", "description": "Activation threshold for this association", "default": 0.022},
    ],
    outputs=[],
    cloneable=True
)
def add_association(
    context: Dict[str, Any],
    substance_name: str = "Oxygen",
    gene_input: str = "Oxygen_supply",
    threshold: float = 0.022,
    **kwargs
) -> bool:
    """
    Add a substance-to-gene association.
    
    Args:
        context: Workflow context
        substance_name: Name of the substance
        gene_input: Gene network input node name
        threshold: Activation threshold
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Adding association: {substance_name} -> {gene_input}")
    
    try:
        config = context.get('config')
        
        if not config:
            print("[ERROR] Config must be set up before associations")
            return False
        
        # Ensure associations dict exists
        if not hasattr(config, 'associations') or config.associations is None:
            config.associations = {}
        
        # Ensure thresholds dict exists
        if not hasattr(config, 'thresholds') or config.thresholds is None:
            config.thresholds = {}

        # Add association
        config.associations[substance_name] = gene_input

        # Add threshold as an object with .threshold attribute (expected by population.py)
        class ThresholdConfig:
            def __init__(self, threshold_value):
                self.threshold = threshold_value

        config.thresholds[gene_input] = ThresholdConfig(threshold)
        
        print(f"   [+] {substance_name} -> {gene_input} (threshold: {threshold})")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to add association: {e}")
        import traceback
        traceback.print_exc()
        return False

