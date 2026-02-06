"""
Add a single substance to the simulation.

This function can be used multiple times to add different substances.
Each substance node in the GUI represents one substance.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from interfaces.base import IConfig


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
    inputs=["context"],
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
    concentration: float = None,  # Simple mode: just set concentration
    **kwargs
) -> bool:
    """
    Add a single substance to the simulation.

    Works in two modes:
    1. Full simulation mode (config + simulator present): configures diffusion solver
    2. Simple mode (no config/simulator): just stores concentration in context

    Args:
        context: Workflow context
        substance_name: Name of the substance
        diffusion_coeff: Diffusion coefficient (um^2/min) - full mode only
        production_rate: Production rate - full mode only
        uptake_rate: Uptake/consumption rate - full mode only
        initial_value: Initial concentration - full mode only
        boundary_value: Boundary concentration - full mode only
        boundary_type: "fixed" or "neumann" - full mode only
        unit: Concentration unit - full mode only
        concentration: Simple mode - just sets this concentration value
        **kwargs: Additional parameters

    Returns:
        True if successful
    """
    try:
        config: Optional[IConfig] = context.get('config')
        simulator = context.get('simulator')

        # If concentration is provided, use simple mode
        if concentration is not None:
            # Simple mode: just store concentration in context
            if 'substances' not in context:
                context['substances'] = {}
            context['substances'][substance_name] = concentration
            print(f"[SUBSTANCE] {substance_name} = {concentration}")
            return True

        # Full simulation mode
        if not config or not simulator:
            # Fallback to simple mode with initial_value as concentration
            if 'substances' not in context:
                context['substances'] = {}
            context['substances'][substance_name] = initial_value
            print(f"[SUBSTANCE] {substance_name} = {initial_value}")
            return True

        print(f"[WORKFLOW] Adding substance: {substance_name}")

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

        # Configure this single substance (don't reinitialize simulator yet)
        _configure_substances(config, simulator, [substance_def], reinitialize_simulator=False)

        print(f"   [+] Added {substance_name}: D={diffusion_coeff}, init={initial_value} {unit}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to add substance {substance_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

