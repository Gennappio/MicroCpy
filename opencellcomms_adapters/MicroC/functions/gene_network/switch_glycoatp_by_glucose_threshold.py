"""
Glucose gate: glycoATP follows the local glucose against the Glucose_supply
association threshold, with no Boolean network in between.

Stability-search protocol (stabilitysearch.json). The full MicroC network
relays Glucose_supply to glycoATP through ~11 Boolean layers; this node is
the zero-delay limit of that relay so the glucose loop can be studied on its
own:

    glycoATP = local Glucose > threshold      (ON: glycolytic consumer)
    mitoATP  = OFF                            (no oxygen field in this protocol)

    threshold = the Glucose row of the Associations table on Setup
                Associations (config.associations['Glucose'] ->
                config.thresholds[gene_input].threshold), the same owner the
                plot isolines and apply_associations_to_inputs read, and the
                same strict "concentration > threshold" test that node applies
                to Glucose_supply. This node keeps no threshold of its own and
                fails loudly when the table has no Glucose row.

A cell with the gene OFF is a quiescent, non-consuming cell (this workflow
has no proliferation node, so every living cell keeps the Quiescent
phenotype whichever way the gate falls). Necrotic cells are skipped: their
genes were frozen OFF when the necrotic disc reached them.

The gene states are written straight into the cell's gene_states snapshot
(the store the metabolism node reads); no BooleanNetwork is needed, and the
workflow creates none (Setup Cell Population with the gene network disabled).

PER-AGENT
    Scheduled with a per-agent ask (for_each) so it acts on env.cell; when
    called with no cell bound it sweeps the whole population once.
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext
from src.io.state_checkpoint import resolve_association_threshold


@register_function(
    requires=['population', 'simulator'],
    display_name="Glucose Gate: glycoATP ON Above Threshold",
    description="Zero-delay glucose relay: glycoATP = local Glucose > the "
                "Glucose_supply threshold owned by the Associations table "
                "(Setup Associations); mitoATP always OFF. Below threshold the "
                "cell is a quiescent non-consumer. Necrotic cells are skipped.",
    category="INTRACELLULAR",
    parameters=[
        {"name": "verbose", "type": "BOOL",
         "description": "Log the threshold in effect and the ON/OFF census "
                        "(whole-population calls only)",
         "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def switch_glycoatp_by_glucose_threshold(
    env: BiologicalContext,
    verbose: bool = False,
    **kwargs
) -> bool:
    threshold = resolve_association_threshold(env.config, 'Glucose')
    if threshold is None:
        raise ValueError(
            "switch_glycoatp_by_glucose_threshold: no Glucose row in the "
            "Associations table (Setup Associations). That row owns the "
            "Glucose_supply threshold this gate applies; add it instead of "
            "hardcoding a value here.")
    threshold = float(threshold)

    targets = [env.cell] if env.cell is not None else list(env.cells)

    n_on = n_off = n_frozen = 0
    for cell in targets:
        if cell.is_necrotic:
            n_frozen += 1
            continue
        glucose = env.concentration('Glucose', cell)
        is_on = glucose > threshold
        genes = cell.gene_states
        genes['glycoATP'] = is_on
        genes['mitoATP'] = False
        cell.set_gene_state_snapshot(genes)
        if is_on:
            n_on += 1
        else:
            n_off += 1

    if env.cell is None and verbose:
        print(f"[GLUCOSE-GATE] rule: glycoATP = Glucose > {threshold:g} mM "
              f"(Associations table), mitoATP = OFF: {n_on} ON, {n_off} OFF, "
              f"{n_frozen} necrotic skipped")
    return True
