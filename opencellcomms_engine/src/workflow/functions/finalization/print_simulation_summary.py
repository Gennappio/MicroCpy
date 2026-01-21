"""
Print simulation summary workflow function.

This function prints a summary of the simulation results at the end.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Print Simulation Summary",
    description="Print final simulation statistics and summary",
    category="FINALIZATION",
    outputs=[],
    cloneable=False
)
def print_simulation_summary(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Print simulation summary in finalization stage.

    Prints a summary of the simulation including:
    - Number of substances simulated
    - Number of simulation steps
    - Final cell count
    - Output directories

    Args:
        context: Workflow context containing population, simulator, config, etc.
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    try:
        config = context['config']
        results = context.get('results', {})
        population = context.get('population')

        print(f"\n" + "=" * 60)
        print("[+] SIMULATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"[STATS] Results summary:")
        print(f"   * Substances simulated: {len(config.substances)}")
        print(f"   * Simulation steps: {len(results.get('time', []))}")

        if population:
            total_cells = len(population.state.cells)
            print(f"   * Final cell count: {total_cells}")
            
            # Count phenotypes
            phenotype_counts = {}
            for cell in population.state.cells.values():
                phenotype = cell.state.phenotype
                phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1
            
            if phenotype_counts:
                print(f"   * Phenotype distribution:")
                for phenotype, count in sorted(phenotype_counts.items()):
                    pct = (count / total_cells * 100) if total_cells > 0 else 0
                    print(f"      - {phenotype}: {count} ({pct:.1f}%)")

        print(f"   * Output directory: {config.output_dir}")
        print(f"   * Plots directory: {config.plots_dir}")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"[WORKFLOW] Error printing summary: {e}")
        import traceback
        traceback.print_exc()
        return False

