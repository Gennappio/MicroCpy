"""CSV export workflow functions for 2D simulations.

These functions export cell states and substance fields to CSV format,
typically used for 2D simulations.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig


@register_function(
    display_name="Export CSV Checkpoint",
    description="Export 2D simulation checkpoint (cells + substances) to CSV format",
    category="UTILITY",
    outputs=[],
    cloneable=True
)
def export_csv_checkpoint(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Export 2D simulation checkpoint (cells + substances) to CSV format.

    This function exports both cell states and substance fields to separate
    CSV files, organized in subdirectories.

    Args:
        context: Workflow context containing population, simulator, config, step
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    try:
        import sys
        import os
        from pathlib import Path

        # Get required objects from context
        population = context.get('population')
        simulator = context.get('simulator')
        config: Optional[IConfig] = context.get('config')
        _clock = context.get('clock')
        step = _clock.step if _clock is not None else 0

        if not all([population, simulator, config]):
            print("[CSV] Error: Missing required objects in context (population, simulator, config)")
            return False

        # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
        if 'engine_root' in context:
            tools_dir = Path(context['engine_root']) / "tools"
        else:
            tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))

        from csv_export import export_csv_cell_state, export_csv_substance_fields

        print(f"\n[CSV] Exporting 2D simulation checkpoint at step {step}...")

        # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
        if 'output_dir' in context:
            output_dir = Path(context['output_dir'])
        else:
            output_dir = Path(config.output_dir) if hasattr(config, 'output_dir') else Path('results')

        csv_cells_dir = output_dir / "csv_cells"
        csv_substances_dir = output_dir / "csv_substances"

        # Export cell states
        cell_file = export_csv_cell_state(
            population=population,
            output_dir=str(csv_cells_dir),
            step=step,
            cell_size_um=config.domain.cell_height.micrometers
        )

        # Export substance fields
        substance_files = export_csv_substance_fields(
            simulator=simulator,
            output_dir=str(csv_substances_dir),
            step=step
        )

        if cell_file and substance_files:
            print(f"[+] Checkpoint exported: {len(substance_files)} substances + cells")
            return True
        else:
            print(f"[!] CSV checkpoint export failed")
            return False

    except Exception as e:
        print(f"[!] CSV export failed: {e}")
        import traceback
        traceback.print_exc()
        return False


@register_function(
    display_name="Export CSV Cells",
    description="Export only cell states to CSV format",
    category="UTILITY",
    outputs=[],
    cloneable=True
)
def export_csv_cells(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Export only cell states to CSV format.

    Args:
        context: Workflow context containing population, config, step
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    try:
        import sys
        from pathlib import Path

        population = context.get('population')
        config: Optional[IConfig] = context.get('config')
        _clock = context.get('clock')
        step = _clock.step if _clock is not None else 0

        if not all([population, config]):
            print("[CSV] Error: Missing required objects in context (population, config)")
            return False

        # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
        if 'engine_root' in context:
            tools_dir = Path(context['engine_root']) / "tools"
        else:
            tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))

        from csv_export import export_csv_cell_state

        # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
        if 'output_dir' in context:
            output_dir = Path(context['output_dir'])
        else:
            output_dir = Path(config.output_dir) if hasattr(config, 'output_dir') else Path('results')

        csv_cells_dir = output_dir / "csv_cells"
        cell_file = export_csv_cell_state(
            population=population,
            output_dir=str(csv_cells_dir),
            step=step,
            cell_size_um=config.domain.cell_height.micrometers
        )

        return cell_file is not None

    except Exception as e:
        print(f"[!] CSV cell export failed: {e}")
        return False


@register_function(
    display_name="Export CSV Substances",
    description="Export only substance fields to CSV format",
    category="UTILITY",
    outputs=[],
    cloneable=True
)
def export_csv_substances(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Export only substance fields to CSV format.

    Args:
        context: Workflow context containing simulator, config, step
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    try:
        import sys
        from pathlib import Path

        simulator = context.get('simulator')
        config: Optional[IConfig] = context.get('config')
        _clock = context.get('clock')
        step = _clock.step if _clock is not None else 0

        if not all([simulator, config]):
            print("[CSV] Error: Missing required objects in context (simulator, config)")
            return False

        # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
        if 'engine_root' in context:
            tools_dir = Path(context['engine_root']) / "tools"
        else:
            tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))

        from csv_export import export_csv_substance_fields

        # === CLEAN ARCHITECTURE: Use context paths (set by executor) ===
        if 'output_dir' in context:
            output_dir = Path(context['output_dir'])
        else:
            output_dir = Path(config.output_dir) if hasattr(config, 'output_dir') else Path('results')

        csv_substances_dir = output_dir / "csv_substances"
        substance_files = export_csv_substance_fields(
            simulator=simulator,
            output_dir=str(csv_substances_dir),
            step=step
        )

        return substance_files is not None and len(substance_files) > 0

    except Exception as e:
        print(f"[!] CSV substance export failed: {e}")
        return False


@register_function(
	    display_name="Export CSV Checkpoint (Conditional)",
	    description="Export CSV checkpoint only if current step matches configured interval",
	    category="UTILITY",
	    parameters=[
	        {
	            "name": "interval",
	            "type": "INT",
	            "description": (
	                "Checkpoint interval in physical steps. If >0 this overrides "
	                "both context['checkpoint_interval'] and the YAML "
	                "config.output.save_cellstate_interval."
	            ),
	            "default": 0,
	            "required": False,
	            "min_value": 0,
	        }
	    ],
	    outputs=[],
	    cloneable=True
	)
def export_csv_checkpoint_conditional(
	    context: Dict[str, Any],
	    interval: int = 0,
	    **kwargs
) -> bool:
	    """Conditionally export a CSV checkpoint based on a configurable interval.

	    Priority for determining the export interval (in physical steps):

	    1. Explicit ``interval`` parameter provided via the workflow GUI.
	    2. ``context['checkpoint_interval']`` (typically set by
	       ``configure_time_and_steps`` in the initialization stage).
	    3. Legacy YAML setting ``config.output.save_cellstate_interval``.

	    If the resolved interval is ``<= 0``, exports are considered disabled and the
	    function returns ``True`` without exporting.
	    """
	    try:
	        config: Optional[IConfig] = context.get('config')
	        _clock = context.get('clock')
	        step = _clock.step if _clock is not None else 0

	        if not config:
	            print("[CSV] Error: Missing config in context")
	            return False

	        # 1) Explicit interval parameter from GUI (highest priority)
	        effective_interval = 0
	        if interval is not None:
	            try:
	                effective_interval = int(interval)
	            except (TypeError, ValueError):
	                effective_interval = 0

	        # 2) Fallback to context['checkpoint_interval'] (from configure_time_and_steps)
	        if effective_interval <= 0:
	            ctx_interval = context.get('checkpoint_interval')
	            if ctx_interval is not None:
	                try:
	                    effective_interval = int(ctx_interval)
	                except (TypeError, ValueError):
	                    effective_interval = 0

	        # 3) Fallback to YAML config interval (legacy behaviour)
	        if effective_interval <= 0:
	            effective_interval = getattr(config.output, 'save_cellstate_interval', 0)

	        # If interval <= 0 -> exports disabled
	        if effective_interval <= 0:
	            return True

	        # Check whether this step should trigger an export
	        if step % effective_interval != 0:
	            return True

	        # Time to export - call the main export function
	        return export_csv_checkpoint(context, **kwargs)

	    except Exception as e:
	        print(f"[!] Conditional CSV export failed: {e}")
	        import traceback
	        traceback.print_exc()
	        return False

