"""
Print Gene Network States - Print current gene network states from all cells.

This function outputs statistics about gene network states across the population,
including fate nodes (Apoptosis, Proliferation, etc.) and metabolic nodes.
"""

from typing import Dict, Any
from collections import Counter
from src.workflow.decorators import register_function


@register_function(
    display_name="Print Gene Network States",
    description="Print current gene network states from all cells",
    category="FINALIZATION",
    parameters=[
        {"name": "show_per_cell", "type": "BOOL", "description": "Show per-cell results", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def print_gene_network_states(
    context: Dict[str, Any] = None,
    show_per_cell: bool = False,
    **kwargs
) -> bool:
    """
    Print gene network statistics from all cells.
    """
    # =========================================================================
    # VALIDATE CONTEXT
    # =========================================================================
    if not context:
        print("[ERROR] [print_gene_network_states] No context provided")
        return False

    # =========================================================================
    # GET REQUIRED ITEMS FROM CONTEXT
    # =========================================================================
    population = context.get('population')
    if population is None:
        print("[ERROR] [print_gene_network_states] No population in context")
        return False

    cells = population.state.cells
    num_cells = len(cells)

    if num_cells == 0:
        print("[ERROR] No cells in population")
        return False

    fate_nodes = ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']
    metabolic_nodes = ['mitoATP', 'glycoATP']
    all_nodes = fate_nodes + metabolic_nodes

    # Collect statistics
    node_stats = {node: Counter() for node in all_nodes}
    phenotype_counts = Counter()

    for cell_id, cell in cells.items():
        gene_states = cell.state.gene_states or {}
        phenotype = cell.state.phenotype if hasattr(cell.state, 'phenotype') else None

        # Count phenotypes (from hierarchical fate determination)
        if phenotype:
            phenotype_counts[phenotype] += 1

        if show_per_cell:
            fate_str = ", ".join([f"{n}={'ON' if gene_states.get(n, False) else 'OFF'}" for n in fate_nodes])
            meta_str = ", ".join([f"{n}={'ON' if gene_states.get(n, False) else 'OFF'}" for n in metabolic_nodes])
            pheno_str = f"PHENOTYPE={phenotype}" if phenotype else "PHENOTYPE=None"
            print(f"   {cell_id}: {pheno_str} | {fate_str} | {meta_str}")

        for node in all_nodes:
            state = gene_states.get(node, False)
            node_stats[node][state] += 1

    # Print summary
    print(f"\n[RESULTS] Gene Network Statistics ({num_cells} cells):")
    
    # Show phenotype distribution (determined by hierarchical fate logic)
    if phenotype_counts:
        print(f"   Cell Phenotypes (from hierarchical fate logic):")
        for phenotype, count in sorted(phenotype_counts.items(), key=lambda x: -x[1]):
            print(f"      {phenotype}: {count}/{num_cells} ({100*count/num_cells:.1f}%)")
        print()
    
    print(f"   Fate Node States (current boolean values):")
    for node in fate_nodes:
        on_count = node_stats[node][True]
        off_count = node_stats[node][False]
        total = on_count + off_count
        if total > 0:
            print(f"      {node}: ON={on_count}/{total} ({100*on_count/total:.1f}%), OFF={off_count}/{total} ({100*off_count/total:.1f}%)")

    print(f"   Metabolic Nodes:")
    for node in metabolic_nodes:
        on_count = node_stats[node][True]
        off_count = node_stats[node][False]
        total = on_count + off_count
        if total > 0:
            print(f"      {node}: ON={on_count}/{total} ({100*on_count/total:.1f}%), OFF={off_count}/{total} ({100*off_count/total:.1f}%)")

    return True

