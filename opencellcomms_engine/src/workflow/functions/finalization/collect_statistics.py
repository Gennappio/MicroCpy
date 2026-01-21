"""
Collect simulation statistics workflow function.

This function collects and computes final statistics about the simulation
including cell population statistics, substance concentration statistics, etc.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Collect Statistics",
    description="Collect final simulation statistics (cell counts, phenotypes, substance stats)",
    category="FINALIZATION",
    outputs=["statistics"],
    cloneable=False
)
def collect_statistics(
    context: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """
    Collect final simulation statistics.

    Collects comprehensive statistics about the simulation:
    - Cell population statistics (counts, phenotypes, ages)
    - Substance concentration statistics (mean, min, max)
    - Metabolic state distribution

    Args:
        context: Workflow context containing population, simulator, config, etc.
        **kwargs: Additional parameters (ignored)

    Returns:
        Dictionary containing all collected statistics
    """
    print("[WORKFLOW] Collecting final simulation statistics...")

    try:
        population = context['population']
        simulator = context['simulator']
        config = context['config']

        statistics = {
            'cell_statistics': {},
            'substance_statistics': {},
            'metabolic_statistics': {}
        }

        # Collect cell statistics
        cells = population.state.cells
        total_cells = len(cells)
        statistics['cell_statistics']['total_cells'] = total_cells

        if total_cells > 0:
            # Phenotype distribution
            phenotype_counts = {}
            ages = []
            for cell in cells.values():
                phenotype = cell.state.phenotype
                phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1
                ages.append(cell.state.age)

            statistics['cell_statistics']['phenotype_distribution'] = phenotype_counts
            statistics['cell_statistics']['mean_age'] = sum(ages) / len(ages)
            statistics['cell_statistics']['max_age'] = max(ages)
            statistics['cell_statistics']['min_age'] = min(ages)

            # Metabolic state distribution
            metabolic_counts = {'mitoATP': 0, 'glycoATP': 0, 'both': 0, 'none': 0}
            for cell in cells.values():
                gene_states = cell.state.gene_states
                mito = gene_states.get('mitoATP', False)
                glyco = gene_states.get('glycoATP', False)
                if mito and glyco:
                    metabolic_counts['both'] += 1
                elif mito:
                    metabolic_counts['mitoATP'] += 1
                elif glyco:
                    metabolic_counts['glycoATP'] += 1
                else:
                    metabolic_counts['none'] += 1

            statistics['metabolic_statistics'] = metabolic_counts

        # Collect substance statistics
        substance_concentrations = simulator.get_substance_concentrations()
        for substance_name, conc_grid in substance_concentrations.items():
            if hasattr(conc_grid, 'value'):
                values = conc_grid.value.flatten()
            else:
                values = list(conc_grid.values()) if isinstance(conc_grid, dict) else [conc_grid]
            
            import numpy as np
            values = np.array(values)
            statistics['substance_statistics'][substance_name] = {
                'mean': float(np.mean(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'std': float(np.std(values))
            }

        # Store in context for other functions
        context['final_statistics'] = statistics

        print(f"   [OK] Collected statistics for {total_cells} cells")
        print(f"   [OK] Collected statistics for {len(substance_concentrations)} substances")

        return statistics

    except Exception as e:
        print(f"[WORKFLOW] Error collecting statistics: {e}")
        import traceback
        traceback.print_exc()
        return {}

