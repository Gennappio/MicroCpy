"""
Fix (clamp) gene nodes to constant values — gene mutation / knockout.

Unlike input nodes (which are already fixed via ``set_gene_network_inputs`` /
``initialize_netlogo_gene_networks``), an *internal* gene node such as ``p53``
has a Boolean ``logic`` rule and is therefore recomputed on every propagation
step. This function pins one or more such nodes to a constant value so the
rule can never override them — i.e. a permanent loss-of-function (clamp OFF) or
gain-of-function (clamp ON) mutation that lasts the whole run.

HOW THE CLAMP IS HONOURED:
    The clamp is stored on each cell's gene network as ``_clamped`` (a
    ``{node_name: bool}`` dict) and also in ``context['gene_network_clamped_nodes']``
    so daughter cells created by division inherit it (mutations are heritable).
    ``propagate_gene_networks_netlogo`` reads ``_clamped`` and, when the graph
    walk reaches a clamped node, re-asserts its value instead of evaluating its
    rule. Because every downstream rule reads the clamped node's current state,
    the mutation propagates to the rest of the network automatically.

This targets internal gene nodes. Clamping an input node works too but is
redundant (inputs are never recomputed); clamping a fate node is not supported
(fate nodes are transient triggers reset to OFF every step by NetLogo logic).
"""

from typing import Dict, List, Union
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


def _to_bool(val) -> bool:
    """Coerce a value to bool, tolerating GUI strings ("true"/"false")."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'on', 'yes')
    return bool(val)


@register_function(
    requires=['gene_networks', 'population'],
    display_name="Fix Gene Nodes (Mutation / Knockout)",
    description="Clamp internal gene nodes to constant ON/OFF values for the whole run (heritable across division)",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "fixed_nodes",
            "type": "DICT",
            "description": "Dict mapping gene node names to clamped boolean values, "
                           "e.g. {\"p53\": false} to knock out p53",
            "default": {},
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def fix_gene_nodes(
    env: BiologicalContext,
    fixed_nodes: Union[Dict, List, str] = None,
    **kwargs
) -> bool:
    if not fixed_nodes:
        print("[GENE_NETWORK] fix_gene_nodes: no nodes to clamp — skipping")
        return True

    clamped = {name: _to_bool(value) for name, value in dict(fixed_nodes).items()}

    # Store on the context so daughter cells (fresh networks built by
    # update_cell_division) inherit the mutation.
    env.raw_context['gene_network_clamped_nodes'] = clamped

    if len(env.cells) == 0:
        print("[GENE_NETWORK] fix_gene_nodes: no cells yet — clamp will apply to "
              "networks as they are created")
        return True

    cells_updated = 0
    missing_nodes = set()
    for cell in env.cells:
        cell_gn = env.gene_network(cell)
        if cell_gn is None:
            continue
        cell_gn._clamped = dict(clamped)
        for node_name, value in clamped.items():
            if node_name in cell_gn.nodes:
                cell_gn.nodes[node_name].current_state = value
            else:
                missing_nodes.add(node_name)
        # Reflect the clamp in the cell's reported gene states immediately.
        cell.set_gene_state_snapshot(
            {name: node.current_state for name, node in cell_gn.nodes.items()}
        )
        cells_updated += 1

    print(f"[GENE_NETWORK] Clamped {clamped} on {cells_updated} cells")
    if missing_nodes:
        print(f"   [!] These names are not nodes in the network and were ignored: "
              f"{sorted(missing_nodes)}")
    return True
