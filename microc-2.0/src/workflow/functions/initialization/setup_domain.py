"""
Setup domain and mesh.

This function initializes the spatial domain and mesh for the simulation.
"""

from typing import Dict, Any


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
    print(f"[WORKFLOW] Setting up {dimensions}D domain and mesh")

    try:
        from src.config.config import DomainConfig
        from src.core.units import Length
        from src.core.domain import MeshManager

        # Get config from context (should be created by setup_simulation)
        config = context.get('config')
        if not config:
            print("[ERROR] Config must be set up before domain (run setup_simulation first)")
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

        print(f"   [+] Domain: {size_x}x{size_y}" + (f"x{size_z}" if dimensions == 3 else "") + " um")
        print(f"   [+] Mesh: {nx}x{ny}" + (f"x{nz}" if dimensions == 3 else "") + " cells")
        print(f"   [+] Cell height: {cell_height} um")
        print(f"   [+] Created simulator with {len(simulator.state.substances)} substances")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup domain: {e}")
        import traceback
        traceback.print_exc()
        return False

