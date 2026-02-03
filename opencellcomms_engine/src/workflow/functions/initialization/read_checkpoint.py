"""Read checkpoint file with cell positions and gene states.

This function loads cell data from a checkpoint CSV file and initializes
the population with the loaded cell states.
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Read Checkpoint",
    description="Load cell positions and gene states from a checkpoint CSV file",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "file_path",
            "type": "STRING",
            "description": "Path to checkpoint CSV file (relative to project root or absolute)",
            "default": "initial_cells.csv",
            "required": True
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def read_checkpoint(
    context: Dict[str, Any],
    file_path: str,
    **kwargs
) -> bool:
    """
    Load cell positions and gene states from a checkpoint CSV file.

    This function reads a checkpoint file (typically created by save_checkpoint)
    and initializes the population with the loaded cell data. If gene states
    are present in the file, they are also loaded.

    Args:
        context: Workflow context containing population, config, etc.
        file_path: Path to checkpoint CSV file (relative to project root or absolute)
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    population = context.get('population')
    config = context.get('config')
    
    if not population or not config:
        print("[ERROR] Population and config must be set up before reading checkpoint")
        return False

    print(f"[WORKFLOW] Reading checkpoint from: {file_path}")

    # === CLEAN ARCHITECTURE: Use context['resolve_path'] if available ===
    if 'resolve_path' in context:
        resolve_path = context['resolve_path']
        checkpoint_path = resolve_path(file_path)
    else:
        # Fallback to local resolution for legacy contexts
        checkpoint_path = Path(file_path)
        if not checkpoint_path.is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent.parent
            checkpoint_path = project_root / file_path

    if not checkpoint_path.exists():
        print(f"[ERROR] Checkpoint file not found: {checkpoint_path}")
        return False

    try:
        from src.io.initial_state import InitialStateManager
        
        # Create initial state manager
        initial_state_manager = InitialStateManager(config)

        # Load cell data from checkpoint
        cell_data = initial_state_manager.load_initial_state(str(checkpoint_path))

        if not cell_data:
            print(f"[ERROR] No cell data loaded from checkpoint")
            return False

        print(f"[WORKFLOW] Loaded {len(cell_data)} cells from checkpoint")

        # Initialize cells in population
        cells_loaded = population.initialize_cells(cell_data)

        print(f"[WORKFLOW] Successfully initialized {cells_loaded} cells from checkpoint")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to read checkpoint file: {e}")
        import traceback
        traceback.print_exc()
        return False

