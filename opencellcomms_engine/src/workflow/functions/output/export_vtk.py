"""VTK export workflow functions for 3D simulations.

These functions export cell states and substance fields to VTK format,
typically used for 3D simulations.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig


@register_function(
    display_name="Export VTK Checkpoint",
    description="Export 3D simulation checkpoint (cells + substances) to VTK format",
    category="UTILITY",
    outputs=[],
    cloneable=True
)
def export_vtk_checkpoint(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Export 3D simulation checkpoint (cells + substances) to VTK format.

    This function exports both cell states and substance fields to VTK files,
    organized in a checkpoint folder.

    Args:
        context: Workflow context containing population, simulator, config, step
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    try:
        import sys
        from pathlib import Path

        # Get required objects from context
        population = context.get('population')
        simulator = context.get('simulator')
        config: Optional[IConfig] = context.get('config')
        _clock = context.get('clock')
        step = _clock.step if _clock is not None else 0

        if not all([population, simulator, config]):
            print("[VTK] Error: Missing required objects in context (population, simulator, config)")
            return False

        # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
        if 'engine_root' in context:
            tools_dir = Path(context['engine_root']) / "tools"
        else:
            tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))

        from vtk_export import export_vtk_checkpoint as vtk_export_func

        print(f"\n[VTK] Exporting 3D simulation checkpoint at step {step}...")

        # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
        if 'output_dir' in context:
            output_dir = Path(context['output_dir'])
        else:
            output_dir = Path(config.output_dir) if hasattr(config, 'output_dir') else Path('results')

        vtk_output_dir = output_dir / "vtk_checkpoints"
        checkpoint_folder = vtk_export_func(
            population=population,
            simulator=simulator,
            output_dir=str(vtk_output_dir),
            step=step,
            cell_size_um=config.output.cell_size_um
        )

        if checkpoint_folder:
            print(f"[+] Checkpoint exported successfully")
            return True
        else:
            print(f"[!] VTK checkpoint export failed")
            return False

    except Exception as e:
        print(f"[!] VTK export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

