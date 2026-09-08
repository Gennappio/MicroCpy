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


# Single-colour ("fill") law: one solid disc per cell, no border. Necrosis wins
# and paints the cell black; every living cell is coloured by its ATP pathway
# (green glycoATP, blue mitoATP, violet both) and gray when neither is ON.
# Living phenotypes other than Necrosis are NOT distinguished in this mode.
FATE_FILL_LEGEND: Dict[str, str] = {
    'black': 'Necrosis',
    'green': 'glycoATP',
    'blue': 'mitoATP',
    'violet': 'glycoATP + mitoATP',
    'gray': 'Quiescent (no ATP pathway)',
}


def fate_fill_cell_color(cell, gene_states: Dict[str, bool], config: Any) -> str:
    """Return "colour|colour" for the fill mode: black if necrotic, else the
    ATP-pathway colour of jayatilake_cell_color's interior, gray if none."""
    phenotype = cell.state.phenotype if hasattr(cell.state, 'phenotype') else ''
    if str(phenotype).lower() == 'necrosis':
        colour = 'black'
    else:
        interior = jayatilake_cell_color(cell, gene_states, config).split('|', 1)[0]
        colour = 'gray' if interior == 'lightgray' else interior
    return f"{colour}|{colour}"
