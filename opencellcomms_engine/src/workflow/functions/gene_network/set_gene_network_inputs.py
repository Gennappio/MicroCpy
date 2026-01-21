"""
Set Gene Network Input States - Set input states for all cells.

Input nodes (is_input=True) are NEVER updated during propagation.
They stay FIXED at the values set here.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Set Gene Network Input States",
    description="Set input node states for all cells. These stay FIXED during propagation.",
    category="INITIALIZATION",
    parameters=[
        {"name": "Oxygen_supply", "type": "BOOL", "description": "Oxygen supply input", "default": True},
        {"name": "Glucose_supply", "type": "BOOL", "description": "Glucose supply input", "default": True},
        {"name": "MCT1_stimulus", "type": "BOOL", "description": "MCT1 stimulus input", "default": False},
        {"name": "Proton_level", "type": "BOOL", "description": "Proton level input", "default": False},
        {"name": "FGFR_stimulus", "type": "BOOL", "description": "FGFR stimulus input", "default": False},
        {"name": "EGFR_stimulus", "type": "BOOL", "description": "EGFR stimulus input", "default": False},
        {"name": "cMET_stimulus", "type": "BOOL", "description": "cMET stimulus input", "default": False},
        {"name": "Growth_Inhibitor", "type": "BOOL", "description": "Growth inhibitor input", "default": False},
        {"name": "DNA_damage", "type": "BOOL", "description": "DNA damage input", "default": False},
        {"name": "TGFBR_stimulus", "type": "BOOL", "description": "TGFBR stimulus input", "default": False},
    ],
    outputs=[],
    cloneable=False
)
def set_gene_network_inputs(
    context: Dict[str, Any],
    Oxygen_supply: bool = True,
    Glucose_supply: bool = True,
    MCT1_stimulus: bool = False,
    Proton_level: bool = False,
    FGFR_stimulus: bool = False,
    EGFR_stimulus: bool = False,
    cMET_stimulus: bool = False,
    Growth_Inhibitor: bool = False,
    DNA_damage: bool = False,
    TGFBR_stimulus: bool = False,
    **kwargs
) -> bool:
    """
    Set input node states for all cells in population.

    Input nodes (is_input=True) are NEVER updated during propagation.
    They stay FIXED at the values set here.
    """
    print(f"[GENE_NETWORK] Setting input states for all cells")

    # Build input states dict
    input_states = {
        'Oxygen_supply': Oxygen_supply,
        'Glucose_supply': Glucose_supply,
        'MCT1_stimulus': MCT1_stimulus,
        'Proton_level': Proton_level,
        'FGFR_stimulus': FGFR_stimulus,
        'EGFR_stimulus': EGFR_stimulus,
        'cMET_stimulus': cMET_stimulus,
        'Growth_Inhibitor': Growth_Inhibitor,
        'DNA_damage': DNA_damage,
        'TGFBR_stimulus': TGFBR_stimulus,
    }

    # Store for later use
    context['gene_network_inputs'] = input_states

    # Apply to all cells in population
    population = context.get('population')
    if population:
        cells = population.state.cells
        for cell_id, cell in cells.items():
            if cell.state.gene_network:
                cell.state.gene_network.set_input_states(input_states)
        print(f"   [+] Applied input states to {len(cells)} cells")
    else:
        print(f"   [!] No population yet - inputs will be applied when gene networks are created")

    # Print active inputs
    active_inputs = [k for k, v in input_states.items() if v]
    print(f"   [+] Active inputs (FIXED): {active_inputs}")

    return True

