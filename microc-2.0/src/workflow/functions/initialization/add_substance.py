"""
Add a single substance to the simulation.

This function can be used multiple times to add different substances.
Each substance node in the GUI represents one substance.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Add Substance",
    description="Add a substance to the simulation (use one node per substance)",
    category="INITIALIZATION",
    parameters=[
        {"name": "substance_name", "type": "STRING", "description": "Name of the substance (e.g., Oxygen, Glucose)", "default": "Oxygen"},
        {"name": "diffusion_coeff", "type": "FLOAT", "description": "Diffusion coefficient (um^2/min)", "default": 100000.0},
        {"name": "production_rate", "type": "FLOAT", "description": "Production rate", "default": 0.0},
        {"name": "uptake_rate", "type": "FLOAT", "description": "Uptake/consumption rate", "default": 10.0},
        {"name": "initial_value", "type": "FLOAT", "description": "Initial concentration", "default": 0.285},
        {"name": "boundary_value", "type": "FLOAT", "description": "Boundary concentration", "default": 0.285},
        {"name": "boundary_type", "type": "STRING", "description": "Boundary type: fixed or neumann", "default": "fixed"},
        {"name": "unit", "type": "STRING", "description": "Concentration unit (mM, uM, etc.)", "default": "mM"},
    ],
    outputs=["substance"],
    cloneable=True
)
def add_substance(
    context: Dict[str, Any],
    substance_name: str = "Oxygen",
    diffusion_coeff: float = 100000.0,
    production_rate: float = 0.0,
    uptake_rate: float = 10.0,
    initial_value: float = 0.285,
    boundary_value: float = 0.285,
    boundary_type: str = "fixed",
    unit: str = "mM",
    **kwargs
) -> bool:
    """
    Add a single substance to the simulation.
    
    Args:
        context: Workflow context (must contain config and simulator)
        substance_name: Name of the substance
        diffusion_coeff: Diffusion coefficient (um^2/min)
        production_rate: Production rate
        uptake_rate: Uptake/consumption rate
        initial_value: Initial concentration
        boundary_value: Boundary concentration
        boundary_type: "fixed" or "neumann"
        unit: Concentration unit
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Adding substance: {substance_name}")

    try:
        config = context.get('config')
        simulator = context.get('simulator')

        if not config or not simulator:
            print("[ERROR] Config and simulator must be set up before adding substances")
            return False

        # Build substance definition
        substance_def = {
            'name': substance_name,
            'diffusion_coeff': diffusion_coeff,
            'production_rate': production_rate,
            'uptake_rate': uptake_rate,
            'initial_value': initial_value,
            'boundary_value': boundary_value,
            'boundary_type': boundary_type,
            'unit': unit,
        }

        # Import helper to configure substances
        from src.workflow.functions.diffusion.run_diffusion_solver import _configure_substances

        # Configure this single substance
        _configure_substances(config, simulator, [substance_def])

        print(f"   [+] Added {substance_name}: D={diffusion_coeff}, init={initial_value} {unit}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to add substance {substance_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

