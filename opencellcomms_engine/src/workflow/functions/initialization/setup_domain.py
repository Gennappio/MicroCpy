"""
Setup domain and mesh.

This function initializes the spatial domain and mesh for the simulation.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from interfaces.base import IConfig
from src.workflow.logging import log, log_always


@register_function(
    display_name="Setup Domain",
    description="Initialize spatial domain and mesh",
    category="INITIALIZATION",
    parameters=[
        {"name": "dimensions", "type": "INT", "description": "2 or 3 for 2D/3D simulation", "default": 2},
        {"name": "size_x", "type": "FLOAT", "description": "Domain size in X (micrometers)", "default": 500.0},
        {"name": "size_y", "type": "FLOAT", "description": "Domain size in Y (micrometers)", "default": 500.0},
        {"name": "size_z", "type": "FLOAT", "description": "Domain size in Z (micrometers, 3D only)", "default": 400.0},
        {"name": "nx", "type": "INT", "description": "Mesh cells in X direction", "default": 25},
        {"name": "ny", "type": "INT", "description": "Mesh cells in Y direction", "default": 25},
        {"name": "nz", "type": "INT", "description": "Mesh cells in Z direction (3D only)", "default": 25},
        {"name": "cell_height", "type": "FLOAT", "description": "Biological cell height (micrometers)", "default": 20.0},
        {"name": "verbose", "type": "BOOL", "description": "Enable detailed logging", "default": None},
    ],
    inputs=["context"],
    outputs=["domain", "mesh"],
    cloneable=False
)
def setup_domain(
    context: Dict[str, Any],
    dimensions: int = 3,
    size_x: float = 400.0,
    size_y: float = 400.0,
    size_z: float = 400.0,
    nx: int = 25,
    ny: int = 25,
    nz: int = 25,
    cell_height: float = 5.0,
    verbose: Optional[bool] = None,
    **kwargs
) -> bool:
    """
    Setup domain and mesh.
    
    Args:
        context: Workflow context
        dimensions: 2 or 3 for 2D/3D simulation
        size_x: Domain size in X direction (micrometers)
        size_y: Domain size in Y direction (micrometers)
        size_z: Domain size in Z direction (micrometers)
        nx: Number of mesh cells in X direction
        ny: Number of mesh cells in Y direction
        nz: Number of mesh cells in Z direction
        cell_height: Biological cell height/thickness (micrometers)
        **kwargs: Additional parameters
        
    Returns:
        True if successful
    """
    log(context, f"Setting up {dimensions}D domain and mesh", prefix="[WORKFLOW]", node_verbose=verbose)

    try:
        from src.config.config import DomainConfig
        from src.core.units import Length
        from src.core.domain import MeshManager

        # Get config from context (should be created by setup_simulation)
        config: Optional[IConfig] = context.get('config')
        if not config:
            log_always("[ERROR] Config must be set up before domain (run setup_simulation first)")
            return False

        # Setup domain configuration
        config.domain = DomainConfig(
            dimensions=dimensions,
            size_x=Length(size_x, "um"),
            size_y=Length(size_y, "um"),
            size_z=Length(size_z, "um") if dimensions == 3 else None,
            nx=nx,
            ny=ny,
            nz=nz if dimensions == 3 else None,
            cell_height=Length(cell_height, "um")
        )
        
        # Create mesh manager
        mesh_manager = MeshManager(config.domain)
        context['mesh_manager'] = mesh_manager

        # Create multi-substance simulator
        from src.simulation.multi_substance_simulator import MultiSubstanceSimulator
        simulator = MultiSubstanceSimulator(config, mesh_manager, verbose=False)
        context['simulator'] = simulator

        log(context, f"Domain: {size_x}x{size_y}" + (f"x{size_z}" if dimensions == 3 else "") + " um", prefix="[+]", node_verbose=verbose)
        log(context, f"Mesh: {nx}x{ny}" + (f"x{nz}" if dimensions == 3 else "") + " cells", prefix="[+]", node_verbose=verbose)
        log(context, f"Cell height: {cell_height} um", prefix="[+]", node_verbose=verbose)
        log(context, f"Created simulator with {len(simulator.state.substances)} substances", prefix="[+]", node_verbose=verbose)
        
        return True
        
    except Exception as e:
        log_always(f"[ERROR] Failed to setup domain: {e}")
        import traceback
        traceback.print_exc()
        return False

