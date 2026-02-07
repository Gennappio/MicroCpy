"""
Setup substances and diffusion simulator.

This function initializes substances and creates the diffusion simulator.
"""

import json
from typing import Dict, Any, List, Union, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig
from src.workflow.logging import log, log_always


def _parse_substances(substances: List[Union[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Parse substances list, handling both JSON strings and dict objects.

    Args:
        substances: List of substance definitions, either as:
            - JSON strings: '{"name":"Oxygen","diffusion_coeff":100000.0,...}'
            - Dict objects: {"name": "Oxygen", "diffusion_coeff": 100000.0, ...}

    Returns:
        List of substance dictionaries
    """
    parsed = []
    for i, substance in enumerate(substances):
        if isinstance(substance, str):
            try:
                parsed.append(json.loads(substance))
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse substance {i} as JSON: {e}")
                print(f"        Value: {substance[:100]}...")
                raise
        elif isinstance(substance, dict):
            parsed.append(substance)
        else:
            raise ValueError(f"Substance {i} must be a JSON string or dict, got {type(substance)}")
    return parsed


@register_function(
    display_name="Setup Substances",
    description="Initialize substances and diffusion simulator",
    category="INITIALIZATION",
    parameters=[
        {"name": "verbose", "type": "BOOL", "description": "Enable detailed logging", "default": None},
    ],
    inputs=["context"],
    outputs=["simulator"],
    cloneable=False
)
def setup_substances(
    context: Dict[str, Any],
    substances: List[Union[str, Dict[str, Any]]] = None,
    associations: Dict[str, str] = None,
    verbose: Optional[bool] = None,
    **kwargs
) -> bool:
    """
    Setup substances and diffusion simulator.

    Args:
        context: Workflow context (must contain config and mesh_manager)
        substances: List of substance definitions. Each item can be either:
            - A JSON string: '{"name":"Oxygen","diffusion_coeff":100000.0,...}'
            - A dict object: {"name": "Oxygen", "diffusion_coeff": 100000.0, ...}

            Each substance should have these fields:
            - name: Substance name
            - diffusion_coeff: Diffusion coefficient
            - production_rate: Production rate
            - uptake_rate: Uptake/consumption rate
            - initial_value: Initial concentration
            - boundary_value: Boundary concentration
            - boundary_type: "fixed" or "neumann"
            - unit: Concentration unit (e.g., "mM", "uM")
        associations: Dict mapping substance names to gene network inputs
        **kwargs: Additional parameters

    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Setting up substances and diffusion simulator")

    if substances is None:
        substances = []

    if associations is None:
        associations = {}

    # Parse JSON strings if needed
    substances = _parse_substances(substances)
    
    try:
        import sys
        from pathlib import Path

        # Add project root to path if not already there
        # __file__ is in src/workflow/functions/initialization/
        # Need to go up 5 levels: initialization -> functions -> workflow -> src -> project root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # Import helper to configure substances using existing simulator
        from src.workflow.functions.diffusion.run_diffusion_solver import _configure_substances

        config: Optional[IConfig] = context.get('config')
        simulator = context.get('simulator')

        if not config or not simulator:
            print("[ERROR] Config and simulator must be set up before substances")
            return False

        # Configure substances in the existing simulator
        _configure_substances(config, simulator, substances)

        # Merge any explicit associations passed separately
        if associations:
            if not hasattr(config, 'associations'):
                config.associations = {}
            config.associations.update(associations)

        log(context, f"Configured {len(getattr(config, 'substances', {}))} substances in diffusion solver", prefix="[+]", node_verbose=verbose)

        return True

    except Exception as e:
        log_always(f"[ERROR] Failed to setup substances: {e}")
        import traceback
        traceback.print_exc()
        return False

