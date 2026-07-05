"""(Increment 2 scaffold) Force every T0 cell's DC-contact inputs ON.

The Corral network only differentiates once a dendritic cell contacts the T0 cell
and switches on nine input nodes. Before the spatial contact layer exists, this
node sets those nine inputs ON for every ``tcell`` so the intracellular layer can
be exercised end-to-end. Increment 4 replaces it with ``sense_dc_contact``, which
gates activation on real DC adjacency.

Input nodes are sources (no update rule), so once set ON they stay ON through
``step_maboss`` — this only needs to run once, in the tcell Setup.
"""
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext

# The nine "contact with dendritic_cell" input nodes (PhysiCell settings.xml).
_CONTACT_INPUTS = ("IL1_In", "MHCII_b1", "MHCII_b2", "IL12_In", "IL6_In",
                   "CD80", "CD4", "IL23_In", "PIP2")


@register_function(
    display_name="Activate All T-cells (scaffold)",
    description="Increment-2 scaffold: force the nine DC-contact input nodes ON for every "
                "T0 cell (replaced by sense_dc_contact once the spatial layer exists).",
    category="INTRACELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["gene_networks", "population"],
)
def activate_all_tcells(env: BiologicalContext, **kwargs) -> bool:
    cell_source = [env.cell] if env.cell is not None else env.cells
    on = {node: True for node in _CONTACT_INPUTS}
    activated = 0
    for cell in cell_source:
        if cell.raw.state.metabolic_state.get("_kind") != "tcell":
            continue                       # DC / endothelial cells have no T0 network
        gn = env.gene_network(cell)
        if gn is None:
            continue
        gn.set_input_states(on)
        cell.set_gene_state_snapshot(gn.get_all_states())
        activated += 1
    print(f"[TCELL_CORRAL] Forced DC-contact inputs ON for {activated} T0 cells (scaffold)")
    return True
