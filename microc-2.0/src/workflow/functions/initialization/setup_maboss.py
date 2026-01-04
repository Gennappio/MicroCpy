"""
Setup MaBoSS simulation parameters.

This function initializes pyMaBoSS with the Boolean network model (.bnd/.cfg files)
and configures time parameters for stochastic simulation.
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Setup MaBoSS",
    description="Initialize pyMaBoSS with Boolean network model and time parameters",
    category="INITIALIZATION",
    parameters=[
        {"name": "bnd_file", "type": "STRING", "description": "Path to .bnd file (Boolean network definition)", "default": "cell_fate.bnd"},
        {"name": "cfg_file", "type": "STRING", "description": "Path to .cfg file (configuration/rates)", "default": "cell_fate.cfg"},
        {"name": "max_time", "type": "FLOAT", "description": "Maximum simulation time for MaBoSS", "default": 20.0},
        {"name": "time_tick", "type": "FLOAT", "description": "Time step for MaBoSS simulation", "default": 0.1},
        {"name": "sample_count", "type": "INT", "description": "Number of stochastic samples", "default": 1000},
    ],
    outputs=[],
    cloneable=False
)
def setup_maboss(
    context: Dict[str, Any],
    bnd_file: str = "cell_fate.bnd",
    cfg_file: str = "cell_fate.cfg",
    max_time: float = 20.0,
    time_tick: float = 0.1,
    sample_count: int = 1000,
    **kwargs
) -> bool:
    """
    Setup MaBoSS simulation parameters.

    Loads the Boolean network model using pyMaBoSS and stores it in the context
    for use by run_maboss_step during simulation.

    Args:
        context: Workflow context
        bnd_file: Path to .bnd file (Boolean network definition)
        cfg_file: Path to .cfg file (configuration/rates)
        max_time: Maximum simulation time for MaBoSS
        time_tick: Time step for MaBoSS simulation
        sample_count: Number of stochastic samples
        **kwargs: Additional parameters

    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Setting up MaBoSS simulation")

    try:
        # Try to import maboss
        try:
            import maboss
        except ImportError:
            print("[ERROR] pyMaBoSS is not installed.")
            print("        Install with: pip install maboss")
            print("        Or with conda: conda install -c colomoto pymaboss")
            return False

        # Resolve file paths
        bnd_path = _resolve_file_path(bnd_file, context)
        cfg_path = _resolve_file_path(cfg_file, context)

        if not bnd_path or not bnd_path.exists():
            print(f"[ERROR] BND file not found: {bnd_file}")
            return False

        if not cfg_path or not cfg_path.exists():
            print(f"[ERROR] CFG file not found: {cfg_file}")
            return False

        print(f"   [+] Loading MaBoSS model:")
        print(f"       BND: {bnd_path}")
        print(f"       CFG: {cfg_path}")

        # Load the MaBoSS model
        maboss_sim = maboss.load(str(bnd_path), str(cfg_path))

        # Configure time parameters
        maboss_sim.param["max_time"] = max_time
        maboss_sim.param["time_tick"] = time_tick
        maboss_sim.param["sample_count"] = sample_count

        # Calculate number of macrosteps based on time parameters
        num_steps = int(max_time / time_tick)

        # Get node names for reference
        node_names = list(maboss_sim.network.keys())

        # Store MaBoSS in multiple locations for accessibility
        # 1. Store in context for same-stage access
        context['maboss_sim'] = maboss_sim
        context['maboss_config'] = {
            'bnd_file': str(bnd_path),
            'cfg_file': str(cfg_path),
            'max_time': max_time,
            'time_tick': time_tick,
            'sample_count': sample_count,
            'num_steps': num_steps,
        }
        context['maboss_nodes'] = node_names

        # 2. Store as module-level global for cross-stage access
        import src.workflow.functions.initialization.setup_maboss as maboss_module
        maboss_module._MABOSS_SIM = maboss_sim
        maboss_module._MABOSS_CONFIG = context['maboss_config']
        maboss_module._MABOSS_NODES = node_names

        print(f"   [+] MaBoSS model loaded successfully")
        print(f"   [+] Nodes: {node_names}")
        print(f"   [+] Time parameters: max_time={max_time}, time_tick={time_tick}")
        print(f"   [+] Sample count: {sample_count}")
        print(f"   [+] Calculated macrosteps: {num_steps}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to setup MaBoSS: {e}")
        import traceback
        traceback.print_exc()
        return False


def _resolve_file_path(file_path: str, context: Dict[str, Any]) -> Path:
    """Resolve file path relative to workflow or microc root."""
    path = Path(file_path)

    if path.is_absolute() and path.exists():
        return path

    microc_root = Path(__file__).parent.parent.parent.parent.parent

    # Strategy 1: Relative to workflow file directory
    workflow_file = context.get('workflow_file')
    if workflow_file:
        workflow_dir = Path(workflow_file).parent
        resolved_path = workflow_dir / file_path
        if resolved_path.exists():
            return resolved_path

    # Strategy 2: Relative to microc-2.0 root
    resolved_path = microc_root / file_path
    if resolved_path.exists():
        return resolved_path

    # Strategy 3: Check maboss_example directory
    maboss_example_dir = microc_root.parent / "ABM_GUI" / "server" / "workflows" / "maboss_example"
    resolved_path = maboss_example_dir / Path(file_path).name
    if resolved_path.exists():
        return resolved_path

    return path

