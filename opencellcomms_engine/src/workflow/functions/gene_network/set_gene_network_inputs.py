"""
Set Gene Network Input States - Set input states for all cells.

Input nodes (is_input=True) are NEVER updated during propagation.
They stay FIXED at the values set here.

Gene networks are accessed from context['gene_networks'] (dict mapping cell_id → BooleanNetwork).
"""

from typing import Dict, Any, List, Optional, Union
from src.workflow.decorators import register_function
from interfaces.base import IGeneNetwork


@register_function(
    display_name="Set Gene Network Input States",
    description="Set input node states for all cells. These stay FIXED during propagation.",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "fixed_substances",
            "type": "DICT",
            "description": "Dict mapping gene input names to boolean values (True/False)",
            "default": {
                "Oxygen_supply": True,
                "Glucose_supply": True,
                "MCT1_stimulus": False,
                "Proton_level": False,
                "FGFR_stimulus": False,
                "EGFR_stimulus": False,
                "cMET_stimulus": False,
                "Growth_Inhibitor": False,
                "DNA_damage": False,
                "TGFBR_stimulus": False,
            }
        }
    ],
    outputs=[],
    cloneable=False
)
def set_gene_network_inputs(
    context: Dict[str, Any],
    fixed_substances: Union[Dict, List, str] = None,
    **kwargs
) -> bool:
    """
    Set input node states for all cells in population.

    Input nodes (is_input=True) are NEVER updated during propagation.
    They stay FIXED at the values set here.

    Gene networks are accessed from context['gene_networks'].

    Args:
        context: Workflow context containing population and gene_networks
        fixed_substances: Dict mapping gene input names to boolean values
            Example: {"Oxygen_supply": True, "Glucose_supply": True, "FGFR_stimulus": False}
    """
    print(f"[GENE_NETWORK] Setting input states for all cells")

    # Use fixed_substances parameter or default values
    if fixed_substances is None:
        fixed_substances = {
            'Oxygen_supply': True,
            'Glucose_supply': True,
            'MCT1_stimulus': False,
            'Proton_level': False,
            'FGFR_stimulus': False,
            'EGFR_stimulus': False,
            'cMET_stimulus': False,
            'Growth_Inhibitor': False,
            'DNA_damage': False,
            'TGFBR_stimulus': False,
        }

    # Build input states dict from fixed_substances
    input_states = dict(fixed_substances)

    # Store for later use
    context['gene_network_inputs'] = input_states

    # Get gene networks from context
    gene_networks = context.get('gene_networks', {})

    # Apply to all cells in population
    population = context.get('population')
    cells_updated = 0

    if population and gene_networks:
        cells = population.state.cells
        for cell_id, cell in cells.items():
            cell_gn: Optional[IGeneNetwork] = gene_networks.get(cell_id)
            if cell_gn:
                cell_gn.set_input_states(input_states)
                cells_updated += 1
        print(f"   [+] Applied input states to {cells_updated} cells")
    elif population and not gene_networks:
        print(f"   [!] No gene networks in context - run 'Initialize Gene Networks' first")
    else:
        print(f"   [!] No population yet - inputs will be applied when gene networks are created")

    # Print active inputs
    active_inputs = [k for k, v in input_states.items() if v]
    print(f"   [+] Active inputs (FIXED): {active_inputs}")

    return True

