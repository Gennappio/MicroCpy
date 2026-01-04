"""
Save MaBoSS simulation results for GUI visualization.

This function saves results from MaBoSS simulations in a format
that can be read and displayed by the ABM_GUI.
"""

import json
from pathlib import Path
from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Save MaBoSS Results",
    description="Save MaBoSS simulation results and generate plots for GUI",
    category="FINALIZATION",
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def save_maboss_results(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Save MaBoSS simulation results and generate plots.

    This function:
    1. Collects gene state history from MaBoSS simulation
    2. Generates time-series plots of gene states
    3. Saves cell fate statistics

    Args:
        context: Workflow context containing population, config, etc.
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful, False otherwise
    """
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np

    print("[WORKFLOW] Saving MaBoSS simulation results...")

    try:
        # Get simulation objects from context
        population = context.get('population')
        config = context.get('config')

        if population is None or config is None:
            print("[WARNING] Missing population or config in context")
            return False

        # Get output directory
        output_dir = Path(config.output_dir)
        plots_dir = output_dir / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)

        # Get MaBoSS config from module
        try:
            from src.workflow.functions.initialization import setup_maboss as maboss_module
            maboss_nodes = getattr(maboss_module, '_MABOSS_NODES', [])
            maboss_config = getattr(maboss_module, '_MABOSS_CONFIG', {})
        except ImportError:
            maboss_nodes = []
            maboss_config = {}

        # Collect final gene states from all cells
        gene_state_counts = {}
        phenotype_counts = {}

        for cell_id, cell in population.state.cells.items():
            # Count gene states
            gene_states = cell.state.gene_states
            for gene, state in gene_states.items():
                if gene not in gene_state_counts:
                    gene_state_counts[gene] = {'True': 0, 'False': 0}
                gene_state_counts[gene]['True' if state else 'False'] += 1

            # Count phenotypes
            phenotype = cell.state.phenotype
            phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1

        # Generate gene state distribution plot
        if gene_state_counts:
            fig, ax = plt.subplots(figsize=(10, 6))
            genes = list(gene_state_counts.keys())
            true_counts = [gene_state_counts[g]['True'] for g in genes]
            false_counts = [gene_state_counts[g]['False'] for g in genes]

            x = np.arange(len(genes))
            width = 0.35

            ax.bar(x - width/2, true_counts, width, label='Active (True)', color='green')
            ax.bar(x + width/2, false_counts, width, label='Inactive (False)', color='red')

            ax.set_ylabel('Number of Cells')
            ax.set_title('Final Gene State Distribution')
            ax.set_xticks(x)
            ax.set_xticklabels(genes, rotation=45, ha='right')
            ax.legend()

            plt.tight_layout()
            plot_path = plots_dir / "gene_state_distribution.png"
            plt.savefig(plot_path, dpi=150)
            plt.close()
            print(f"   [OK] Saved: {plot_path.name}")

        # Generate phenotype distribution plot
        if phenotype_counts:
            fig, ax = plt.subplots(figsize=(8, 6))
            phenotypes = list(phenotype_counts.keys())
            counts = list(phenotype_counts.values())

            colors = plt.cm.Set3(np.linspace(0, 1, len(phenotypes)))
            ax.pie(counts, labels=phenotypes, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.set_title('Cell Phenotype Distribution')

            plot_path = plots_dir / "phenotype_distribution.png"
            plt.savefig(plot_path, dpi=150)
            plt.close()
            print(f"   [OK] Saved: {plot_path.name}")

        # Save summary JSON
        summary = {
            'simulation_type': 'MaBoSS',
            'total_cells': len(population.state.cells),
            'maboss_config': maboss_config,
            'final_gene_states': gene_state_counts,
            'final_phenotypes': phenotype_counts,
        }

        summary_path = output_dir / "maboss_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"   [OK] Saved: maboss_summary.json")

        print(f"[WORKFLOW] Results saved to: {output_dir}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to save MaBoSS results: {e}")
        import traceback
        traceback.print_exc()
        return False

