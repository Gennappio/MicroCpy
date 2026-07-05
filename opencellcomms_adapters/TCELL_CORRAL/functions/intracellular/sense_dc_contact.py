"""Gate a T0 cell's MaBoSS inputs on real contact with a dendritic cell.

This is the spatial replacement for the ``activate_all_tcells`` scaffold: a naive
T0 cell drives its nine "contact with dendritic_cell" input nodes ON only while a
dendritic cell is adjacent, and OFF otherwise. Sustained contact (the DC stops on
contact — see ``chemotax_ccl21``) lets the network settle into a Treg/Th1/Th17
attractor; transient contact does not commit. Once the cell has committed a fate
(``fate != naive``), contact is ignored — the network is no longer consulted.

Runs per T0 cell (``for_each {kind: tcell}``), before ``step_tcell_network``.
"""
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext

# The nine "contact with dendritic_cell" input nodes (PhysiCell settings.xml).
_CONTACT_INPUTS = ("IL1_In", "MHCII_b1", "MHCII_b2", "IL12_In", "IL6_In",
                   "CD80", "CD4", "IL23_In", "PIP2")


@register_function(
    display_name="Sense DC Contact",
    description="Drive a naive T0 cell's nine DC-contact input nodes ON while a dendritic "
                "cell is adjacent, OFF otherwise; committed cells are left alone.",
    category="INTRACELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["gene_networks", "abm_population"],
)
def sense_dc_contact(env: BiologicalContext, **kwargs) -> bool:
    agent = env.agent
    if agent is None:
        return True
    if agent.get("fate", "naive") != "naive":
        return True                       # already committed; network not consulted

    gn = env.gene_network(env.cell)
    if gn is None:
        return True

    in_contact = any(nb.kind == "dendritic_cell" for nb in agent.neighbors(radius=1))
    gn.set_input_states({node: in_contact for node in _CONTACT_INPUTS})
    return True
