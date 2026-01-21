"""
Export final simulation state workflow function.

This function exports the final state of the simulation (cells, substances)
for analysis or visualization in external tools.
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Export Final State",
    description="Export final simulation state (cells and substances) to files",
    category="FINALIZATION",
    parameters=[
        {
            "name": "export_cells_csv",
            "type": "BOOL",
            "description": "Export cells to CSV",
            "default": True
        },
        {
            "name": "export_substances_csv",
            "type": "BOOL",
            "description": "Export substance concentrations to CSV",
            "default": True
        },
        {
            "name": "export_vtk",
            "type": "BOOL",
            "description": "Export to VTK format for ParaView",
            "default": False
        }
    ],
    outputs=[],
    cloneable=False
)
def export_final_state(
    context: Dict[str, Any],
    export_cells_csv: bool = True,
    export_substances_csv: bool = True,
    export_vtk: bool = False,
    **kwargs
) -> bool:
    """
    Export final simulation state.

    This function exports the final state of the simulation for analysis
    or visualization in external tools.

    Args:
        context: Workflow context containing population, simulator, config, etc.
        export_cells_csv: Whether to export cells to CSV
        export_substances_csv: Whether to export substance concentrations to CSV
        export_vtk: Whether to export to VTK format
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    print("[WORKFLOW] Exporting final simulation state...")

    try:
        population = context['population']
        simulator = context['simulator']
        config = context['config']
        step = context.get('step', 0)

        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export cells to CSV
        if export_cells_csv:
            from src.workflow.functions.output.export_csv import export_csv_cells
            cells_file = output_dir / f"final_cells_step_{step}.csv"
            export_csv_cells(
                context=context,
                file_path=str(cells_file),
                include_gene_states=True,
                include_metabolic_state=True
            )
            print(f"   [OK] Exported cells to {cells_file.name}")

        # Export substances to CSV
        if export_substances_csv:
            from src.workflow.functions.output.export_csv import export_csv_substances
            substances_file = output_dir / f"final_substances_step_{step}.csv"
            export_csv_substances(
                context=context,
                file_path=str(substances_file)
            )
            print(f"   [OK] Exported substances to {substances_file.name}")

        # Export to VTK
        if export_vtk:
            try:
                from src.workflow.functions.output.export_vtk import export_vtk_checkpoint
                export_vtk_checkpoint(context=context)
                print(f"   [OK] Exported VTK checkpoint")
            except ImportError:
                print(f"   [!] VTK export not available")

        print(f"[WORKFLOW] Final state exported to {output_dir}")
        return True

    except Exception as e:
        print(f"[WORKFLOW] Error exporting final state: {e}")
        import traceback
        traceback.print_exc()
        return False

