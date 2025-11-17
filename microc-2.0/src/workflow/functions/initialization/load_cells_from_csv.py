"""
Load cells from CSV file.

This function loads initial cell state from a CSV file (for 2D simulations).
"""

from typing import Dict, Any
from pathlib import Path


def load_cells_from_csv(
    context: Dict[str, Any],
    file_path: str,
    **kwargs
) -> bool:
    """
    Load cells from a CSV file during workflow initialization.

    This function loads cell data from a CSV file and initializes the population.
    It should be used in the initialization stage of a workflow for 2D simulations.

    Args:
        context: Workflow context containing population, config, etc.
        file_path: Path to CSV file (relative to microc-2.0 root or absolute)
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    population = context.get('population')
    config = context.get('config')
    
    if not population or not config:
        print("[ERROR] Population and config must be set up before loading cells")
        return False

    print(f"[WORKFLOW] Loading cells from CSV: {file_path}")

    # Resolve file path
    csv_path = Path(file_path)
    if not csv_path.is_absolute():
        # Try relative to microc-2.0 root
        microc_root = Path(__file__).parent.parent.parent.parent.parent
        csv_path = microc_root / file_path

    if not csv_path.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        return False

    try:
        from src.initial_state.initial_state_manager import InitialStateManager
        
        # Create initial state manager
        initial_state_manager = InitialStateManager(config)

        # Load cell data from CSV
        cell_data = initial_state_manager.load_initial_state_from_csv(str(csv_path))

        print(f"[WORKFLOW] Loaded {len(cell_data)} cells from CSV")

        # Initialize cells in population
        cells_loaded = population.initialize_cells(cell_data)

        print(f"[WORKFLOW] Successfully initialized {cells_loaded} cells")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to load CSV file: {e}")
        import traceback
        traceback.print_exc()
        return False

