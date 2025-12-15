"""
Setup substances and diffusion simulator.

This function initializes substances and creates the diffusion simulator.
"""

from typing import Dict, Any, List
from src.workflow.decorators import register_function


@register_function(
    display_name="Setup Substances",
    description="Initialize substances and diffusion simulator",
    category="INITIALIZATION",
    outputs=["simulator"],
    cloneable=False
)
def setup_substances(
    context: Dict[str, Any],
    substances: List[Dict[str, Any]] = None,
    associations: Dict[str, str] = None,
    **kwargs
) -> bool:
    """
    Setup substances and diffusion simulator.
    
    Args:
        context: Workflow context (must contain config and mesh_manager)
        substances: List of substance definitions, each with:
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
    
    try:
        import sys
        from pathlib import Path

        # Add microc-2.0 root to path if not already there
        # __file__ is in src/workflow/functions/initialization/
        # Need to go up 5 levels: initialization -> functions -> workflow -> src -> microc-2.0
        microc_root = Path(__file__).parent.parent.parent.parent.parent
        if str(microc_root) not in sys.path:
            sys.path.insert(0, str(microc_root))

        # Import helper to configure substances using existing simulator
        from src.workflow.functions.diffusion.run_diffusion_solver import _configure_substances

        config = context.get('config')
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

        print(f"   [+] Configured {len(getattr(config, 'substances', {}))} substances in diffusion solver")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup substances: {e}")
        import traceback
        traceback.print_exc()
        return False

