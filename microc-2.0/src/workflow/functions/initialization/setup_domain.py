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
        from src.config.config import Config, DomainConfig, Length
        from src.diffusion.mesh_manager import MeshManager
        
        # Create minimal config object for domain
        if 'config' not in context:
            context['config'] = Config()
        
        config = context['config']
        
        # Setup domain configuration
        config.domain = DomainConfig()
        config.domain.dimensions = dimensions
        config.domain.size_x = Length(size_x, "um")
        config.domain.size_y = Length(size_y, "um")
        config.domain.size_z = Length(size_z, "um") if dimensions == 3 else Length(0, "um")
        config.domain.nx = nx
        config.domain.ny = ny
        config.domain.nz = nz if dimensions == 3 else 1
        config.domain.cell_height = Length(cell_height, "um")
        
        # Create mesh manager
        mesh_manager = MeshManager(config.domain)
        context['mesh_manager'] = mesh_manager
        
        print(f"   [+] Domain: {size_x}x{size_y}" + (f"x{size_z}" if dimensions == 3 else "") + " um")
        print(f"   [+] Mesh: {nx}x{ny}" + (f"x{nz}" if dimensions == 3 else "") + " cells")
        print(f"   [+] Cell height: {cell_height} um")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to setup domain: {e}")
        import traceback
        traceback.print_exc()
        return False

