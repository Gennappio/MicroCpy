"""
Load cells from CSV file.

This function loads initial cell state from a CSV file (for 2D simulations).
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Load Cells from CSV File",
    description="Load initial cell state from a CSV file (2D only)",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "file_path",
            "type": "STRING",
            "description": "Path to CSV file (relative to project root or absolute)",
            "default": "initial_state.csv",
            "required": True
        }
    ],
    inputs=["context"],
    outputs=["loaded_cells"],
    cloneable=False
)
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
        file_path: Path to CSV file (relative to project root or absolute)
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

    # === CLEAN ARCHITECTURE: Use context['resolve_path'] if available ===
    if 'resolve_path' in context:
        resolve_path = context['resolve_path']
        csv_path = resolve_path(file_path)
    else:
        # Fallback to local resolution for legacy contexts
        csv_path = Path(file_path)
        if not csv_path.is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent.parent
            csv_path = project_root / file_path

    if not csv_path.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        return False

    try:
        from src.io.initial_state import InitialStateManager

        # Create initial state manager
        initial_state_manager = InitialStateManager(config)

        # Load cell data from CSV (returns tuple: cell_data, cell_size_um)
        cell_data, detected_cell_size_um = initial_state_manager.load_initial_state_from_csv(str(csv_path))

        print(f"[WORKFLOW] Loaded {len(cell_data)} cells from CSV")
        print(f"[WORKFLOW] Detected cell size: {detected_cell_size_um:.2f} um")

        # Build metabolic_state from SubstanceConfig uptake/production rates
        default_metabolic_state = _build_metabolic_state_from_config(config)
        if default_metabolic_state:
            print(f"[WORKFLOW] Setting default metabolic state from SubstanceConfig:")
            for key, val in default_metabolic_state.items():
                if val != 0.0:
                    print(f"           {key}: {val:.2e}")

        # Add metabolic_state to each cell's data
        for cell_info in cell_data:
            if 'metabolic_state' not in cell_info or not cell_info['metabolic_state']:
                cell_info['metabolic_state'] = default_metabolic_state.copy()

        # Initialize cells in population
        cells_loaded = population.initialize_cells(cell_data)

        print(f"[WORKFLOW] Successfully initialized {cells_loaded} cells")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to load CSV file: {e}")
        import traceback
        traceback.print_exc()
        return False


def _build_metabolic_state_from_config(config) -> dict:
    """
    Build metabolic_state dictionary from SubstanceConfig uptake/production rates.

    This creates a static metabolic state for cells based on the rates defined
    in the workflow's substance configuration. No gene network needed.

    Args:
        config: Configuration object with substances attribute

    Returns:
        Dict with consumption/production rates for diffusion solver
    """
    metabolic_state = {
        'oxygen_consumption': 0.0,
        'glucose_consumption': 0.0,
        'lactate_production': 0.0,
        'lactate_consumption': 0.0,
    }

    if not config or not hasattr(config, 'substances'):
        return metabolic_state

    substances = config.substances
    if not isinstance(substances, dict):
        return metabolic_state

    # Map substance names to metabolic_state keys
    for substance_name, substance_cfg in substances.items():
        name_lower = substance_name.lower()

        # Get uptake_rate (consumption)
        uptake_rate = 0.0
        if hasattr(substance_cfg, 'uptake_rate'):
            uptake_rate = float(substance_cfg.uptake_rate) if substance_cfg.uptake_rate else 0.0

        # Get production_rate
        production_rate = 0.0
        if hasattr(substance_cfg, 'production_rate'):
            production_rate = float(substance_cfg.production_rate) if substance_cfg.production_rate else 0.0

        # Map to standard metabolic_state keys
        if name_lower == 'oxygen':
            metabolic_state['oxygen_consumption'] = uptake_rate
        elif name_lower == 'glucose':
            metabolic_state['glucose_consumption'] = uptake_rate
        elif name_lower == 'lactate':
            metabolic_state['lactate_production'] = production_rate
            metabolic_state['lactate_consumption'] = uptake_rate

        # Also store raw rates for the diffusion solver to use directly
        # Key format: "{Substance}_consumption" or "{Substance}_production"
        if uptake_rate > 0:
            metabolic_state[f'{substance_name}_consumption'] = uptake_rate
        if production_rate > 0:
            metabolic_state[f'{substance_name}_production'] = production_rate

    return metabolic_state

