"""
Setup substance-to-gene associations and thresholds.

This function configures how substances map to gene network inputs.
"""

import json
from typing import Dict, Any, List, Union
from src.workflow.decorators import register_function


def _parse_associations(associations: Union[Dict, List[str], str]) -> Dict[str, Dict[str, Any]]:
    """
    Parse associations from various input formats.

    Supports:
    - Dict[str, Dict]: {"Oxygen": {"gene_input": "Oxygen_supply", "threshold": 0.022}}
    - List of JSON strings: ['{"substance": "Oxygen", "gene_input": "...", "threshold": 0.022}']
    - Single JSON string (for the whole dict)

    Returns:
        Dict mapping substance names to {gene_input, threshold}
    """
    if associations is None:
        return {}

    # If it's already a dict with the right structure
    if isinstance(associations, dict):
        return associations

    # If it's a JSON string, parse it
    if isinstance(associations, str):
        try:
            parsed = json.loads(associations)
            if isinstance(parsed, dict):
                return parsed
            elif isinstance(parsed, list):
                associations = parsed  # Continue to list processing
        except json.JSONDecodeError:
            print(f"[ERROR] Failed to parse associations JSON string")
            return {}

    # If it's a list of JSON strings (from list parameter node)
    if isinstance(associations, list):
        result = {}
        for item in associations:
            if isinstance(item, str):
                try:
                    entry = json.loads(item)
                    substance = entry.get('substance') or entry.get('substance_name')
                    if substance:
                        result[substance] = {
                            'gene_input': entry.get('gene_input'),
                            'threshold': entry.get('threshold', 0.0)
                        }
                except json.JSONDecodeError:
                    print(f"[ERROR] Failed to parse association entry: {item}")
            elif isinstance(item, dict):
                substance = item.get('substance') or item.get('substance_name')
                if substance:
                    result[substance] = {
                        'gene_input': item.get('gene_input'),
                        'threshold': item.get('threshold', 0.0)
                    }
        return result

    return {}


@register_function(
    display_name="Setup Associations",
    description="Configure all substance-to-gene associations with thresholds (use one dict node)",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "associations",
            "type": "DICT",
            "description": "Dict mapping substance names to {gene_input, threshold}",
            "default": {}
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def setup_associations(
    context: Dict[str, Any],
    associations: Union[Dict, List, str] = None,
    **kwargs
) -> bool:
    """
    Setup all substance-to-gene associations from a dictionary.

    This is more efficient than multiple add_association calls.
    Uses a single dictionary node in the GUI.

    Args:
        context: Workflow context
        associations: Dictionary mapping substance names to {gene_input, threshold}.
            Example: {
                "Oxygen": {"gene_input": "Oxygen_supply", "threshold": 0.022},
                "Glucose": {"gene_input": "Glucose_supply", "threshold": 4.0}
            }
        **kwargs: Additional parameters

    Returns:
        True if successful
    """
    try:
        # Parse associations from various formats
        parsed = _parse_associations(associations)

        if not parsed:
            print("[WARNING] No associations provided to setup_associations")
            return True

        config = context.get('config')

        # Process each association
        count = 0
        for substance_name, assoc_data in parsed.items():
            gene_input = assoc_data.get('gene_input')
            threshold = assoc_data.get('threshold', 0.0)

            if not gene_input:
                print(f"[WARNING] Skipping {substance_name}: no gene_input specified")
                continue

            if config:
                # Full simulation mode: store in config
                if not hasattr(config, 'associations') or config.associations is None:
                    config.associations = {}
                if not hasattr(config, 'thresholds') or config.thresholds is None:
                    config.thresholds = {}

                config.associations[substance_name] = gene_input

                # Add threshold as object with .threshold attribute
                class ThresholdConfig:
                    def __init__(self, threshold_value):
                        self.threshold = threshold_value

                config.thresholds[gene_input] = ThresholdConfig(threshold)
            else:
                # Simple mode: store directly in context
                if 'associations' not in context:
                    context['associations'] = {}
                if 'thresholds' not in context:
                    context['thresholds'] = {}

                context['associations'][substance_name] = gene_input
                context['thresholds'][gene_input] = threshold

            print(f"[ASSOCIATION] {substance_name} -> {gene_input} (threshold: {threshold})")
            count += 1

        print(f"[WORKFLOW] Configured {count} substance-to-gene associations")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to setup associations: {e}")
        import traceback
        traceback.print_exc()
        return False


@register_function(
    display_name="Add Association",
    description="Add a substance-to-gene association (use one node per association)",
    category="INITIALIZATION",
    parameters=[
        {"name": "substance_name", "type": "STRING", "description": "Name of the substance", "default": "Oxygen"},
        {"name": "gene_input", "type": "STRING", "description": "Gene network input node name", "default": "Oxygen_supply"},
        {"name": "threshold", "type": "FLOAT", "description": "Activation threshold for this association", "default": 0.022},
    ],
    inputs=["context"],
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

    Works in two modes:
    1. Full simulation mode (config present): stores in config object
    2. Simple mode (no config): stores directly in context

    Args:
        context: Workflow context
        substance_name: Name of the substance
        gene_input: Gene network input node name
        threshold: Activation threshold
        **kwargs: Additional parameters

    Returns:
        True if successful
    """
    try:
        config = context.get('config')

        if config:
            # Full simulation mode: store in config
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
        else:
            # Simple mode: store directly in context
            if 'associations' not in context:
                context['associations'] = {}
            if 'thresholds' not in context:
                context['thresholds'] = {}

            context['associations'][substance_name] = gene_input
            context['thresholds'][gene_input] = threshold

        print(f"[ASSOCIATION] {substance_name} -> {gene_input} (threshold: {threshold})")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to add association: {e}")
        import traceback
        traceback.print_exc()
        return False

