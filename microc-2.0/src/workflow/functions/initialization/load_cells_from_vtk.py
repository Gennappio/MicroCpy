"""
Load cells from VTK file.

This function loads initial cell state from a VTK file.
"""

from typing import Dict, Any
from pathlib import Path


def load_cells_from_vtk(
    context: Dict[str, Any],
    file_path: str,
    **kwargs
) -> bool:
    """
    Load cells from a VTK file during workflow initialization.

    This function loads cell data from a VTK file and initializes the population.
    It should be used in the initialization stage of a workflow.

    Args:
        context: Workflow context containing population, config, etc.
        file_path: Path to VTK file (relative to microc-2.0 root or absolute)
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    population = context.get('population')
    config = context.get('config')
    
    if not population or not config:
        print("[ERROR] Population and config must be set up before loading cells")
        return False

    print(f"[WORKFLOW] Loading cells from VTK: {file_path}")

    # Resolve file path
    vtk_path = Path(file_path)
    if not vtk_path.is_absolute():
        # Try relative to microc-2.0 root
        microc_root = Path(__file__).parent.parent.parent.parent.parent
        vtk_path = microc_root / file_path

    if not vtk_path.exists():
        print(f"[ERROR] VTK file not found: {vtk_path}")
        return False

    try:
        from src.initial_state.initial_state_manager import InitialStateManager
        from src.config.config import Length
        
        # Create initial state manager
        initial_state_manager = InitialStateManager(config)

        # Load cell data from VTK
        cell_data, detected_cell_size_um = initial_state_manager.load_initial_state_from_vtk(str(vtk_path))

        print(f"[WORKFLOW] Loaded {len(cell_data)} cells from VTK")
        print(f"[WORKFLOW] Detected cell size: {detected_cell_size_um:.2f} um")

        # Initialize cells in population
        cells_loaded = population.initialize_cells(cell_data)

        print(f"[WORKFLOW] Successfully initialized {cells_loaded} cells")

        # Update config with detected cell size if needed
        if detected_cell_size_um:
            config.domain.cell_height = Length(detected_cell_size_um, "um")
            print(f"[WORKFLOW] Updated cell_height to {detected_cell_size_um:.2f} um")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to load VTK file: {e}")
        import traceback
        traceback.print_exc()
        return False

