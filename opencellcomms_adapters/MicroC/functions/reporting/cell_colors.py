"""
Jayatilake cell colouring for MicroC plots.

Interior colour encodes the metabolic mode read from the gene network
(glycoATP / mitoATP); border colour encodes the committed phenotype. The
plugin's reporting functions pass this explicitly to AutoPlotter — there is
no hidden hook module.
"""

from typing import Any, Dict


def jayatilake_cell_color(cell, gene_states: Dict[str, bool], config: Any) -> str:
    """Return "interior|border" colours for one cell."""
    actual_phenotype = cell.state.phenotype if hasattr(cell.state, 'phenotype') else 'normal'

    phenotype_border_colors = {
        'Necrosis': 'black',
        'necrosis': 'black',
        'Apoptosis': 'red',
        'apoptosis': 'red',
        'Growth_Arrest': 'orange',
        'growth_arrest': 'orange',
        'Proliferation': 'lightgreen',
        'proliferation': 'lightgreen',
        'normal': 'gray',
        'quiescent': 'gray',
    }
    border_color = phenotype_border_colors.get(actual_phenotype, 'gray')

    glyco_active = gene_states.get('glycoATP', False)
    mito_active = gene_states.get('mitoATP', False)

    if glyco_active and mito_active:
        interior_color = "violet"     # mixed metabolism
    elif glyco_active:
        interior_color = "green"      # glycolysis only
    elif mito_active:
        interior_color = "blue"       # OXPHOS only
    else:
        interior_color = "lightgray"  # neither pathway active

    return f"{interior_color}|{border_color}"
