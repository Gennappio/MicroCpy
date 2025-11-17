"""
Setup substances and diffusion simulator.

This function initializes substances and creates the diffusion simulator.
"""

from typing import Dict, Any, List


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
        from src.config.config import SubstanceConfig
        from src.diffusion.multi_substance_simulator import MultiSubstanceSimulator
        
        config = context.get('config')
        mesh_manager = context.get('mesh_manager')
        
        if not config or not mesh_manager:
            print("[ERROR] Config and mesh_manager must be set up before substances")
            return False
        
        # Initialize substances dict
        config.substances = {}
        
        # Add each substance
        for sub_def in substances:
            name = sub_def['name']
            sub_config = SubstanceConfig()
            sub_config.diffusion_coeff = sub_def.get('diffusion_coeff', 1e-10)
            sub_config.production_rate = sub_def.get('production_rate', 0.0)
            sub_config.uptake_rate = sub_def.get('uptake_rate', 0.0)
            sub_config.initial_value = sub_def.get('initial_value', 0.0)
            sub_config.boundary_value = sub_def.get('boundary_value', 0.0)
            sub_config.boundary_type = sub_def.get('boundary_type', 'fixed')
            sub_config.unit = sub_def.get('unit', 'mM')
            
            config.substances[name] = sub_config
            print(f"   [+] Added substance: {name} (D={sub_config.diffusion_coeff:.2e}, init={sub_config.initial_value})")
        
        # Set associations
        config.associations = associations
        
        # Create diffusion simulator
        simulator = MultiSubstanceSimulator(config, mesh_manager)
        context['simulator'] = simulator
        
        print(f"   [+] Created diffusion simulator with {len(config.substances)} substances")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup substances: {e}")
        import traceback
        traceback.print_exc()
        return False

