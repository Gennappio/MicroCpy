"""Clamp (knock out / fix) T0 gene nodes for the _mutant Corral perturbations.

Mirrors MicroC's ``fix_gene_nodes``, but uses ``BooleanNetwork.fix_node`` so the
clamp is honoured by the continuous-time MaBoSS step (``step_maboss`` skips fixed
nodes). The ``FOXP3_2_mutant`` / ``NFKB_mutant`` runs are ``{"FOXP3_2": false}`` /
``{"NFKB": false}``; empty = wild type. Runs in the tcell Setup, after
``build_tcell_networks``.
"""
from typing import Dict, Union

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


def _to_bool(val) -> bool:
    """Coerce a value to bool, tolerating GUI strings ("true"/"false")."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "on", "yes")
    return bool(val)


@register_function(
    display_name="Fix T-cell Gene Nodes (Mutation / Knockout)",
    description="Clamp T0 gene nodes to constant ON/OFF for the whole run (honoured by the "
                "MaBoSS step). FOXP3_2_mutant = {FOXP3_2: false}; empty = wild type.",
    category="INITIALIZATION",
    parameters=[
        {"name": "fixed_nodes", "type": "DICT",
         "description": "Node name -> clamped bool, e.g. {\"FOXP3_2\": false}. Empty = wild type.",
         "default": {}},
        {"name": "kind", "type": "STRING",
         "description": "Only clamp cells of this ABM kind.", "default": "tcell"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["gene_networks", "population"],
)
def fix_tcell_nodes(
    env: BiologicalContext,
    fixed_nodes: Union[Dict, None] = None,
    kind: str = "tcell",
    **kwargs,
) -> bool:
    if not fixed_nodes:
        print("[TCELL_CORRAL] fix_tcell_nodes: no nodes to clamp (wild type)")
        return True

    clamped = {name: _to_bool(v) for name, v in dict(fixed_nodes).items()}
    fixed = 0
    missing = set()
    # Per-agent when called with for_each (env.cell bound); else the whole pop --
    # the same function works under both conventions (see BiologicalContext.cell).
    for cell in ([env.cell] if env.cell is not None else env.cells):
        if cell.raw.state.metabolic_state.get("_kind") not in (None, kind):
            continue
        gn = env.gene_network(cell)
        if gn is None:
            continue
        for node, state in clamped.items():
            if node in gn.nodes:
                gn.fix_node(node, state)
            else:
                missing.add(node)
        cell.set_gene_state_snapshot(gn.get_all_states())
        fixed += 1

    print(f"[TCELL_CORRAL] Clamped {clamped} on {fixed} '{kind}' cells")
    if missing:
        print(f"   [!] not nodes in the network, ignored: {sorted(missing)}")
    return True
