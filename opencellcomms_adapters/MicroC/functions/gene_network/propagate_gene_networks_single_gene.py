"""
Propagate gene networks by NetLogo single-gene random update.

This is the update rule used by ``opencellcomms_engine/benchmarks/
gene_network_standalone.py``: per step, pick ONE gene uniformly at random from
all non-input genes that have a logic rule, evaluate its rule against the
current state of every node, and write back only that gene. Nothing else moves.

WHY THIS EXISTS ALONGSIDE propagate_gene_networks_netlogo
    ``propagate_gene_networks_netlogo`` implements the NetLogo *graph walk*:
    it follows out-edges from a remembered ``_last_node``, treats the four fate
    nodes as transient triggers (fire -> latch into ``_fate`` -> reset to OFF ->
    jump to a random input), and can stop at the first fate. That is a
    different process, and it is what microc.json uses.

    This function is the plain single-gene sampler instead. Fate nodes are
    ordinary nodes: they are updated like any other and read directly at the
    end, with no latch and no reset. So the fate a cell reports here is its
    Boolean state, not "the last trigger that fired" -- which is what makes the
    results comparable with the standalone benchmark.

    Both are registered. microc.json keeps the graph walk; microc_p53.json uses
    this one. Neither replaces the other.

GENE CLAMPS ARE HONOURED
    Nodes listed in the cell's ``_clamped`` dict (set by ``fix_gene_nodes``, and
    inherited by daughter cells through ``context['gene_network_clamped_nodes']``)
    are excluded from the sampling pool and re-asserted, so a knockout survives
    the whole run. This matters: neither ``BooleanNetwork.fix_node`` nor
    ``_clamped`` is honoured by the engine's own discrete update modes, so a
    clamp applied there is silently lost after a few hundred steps.

HOW MANY STEPS
    Far more than microc.json's 5. One node is touched per step and jaya.bnd has
    81 updatable genes, so a gene gets its turn about once per 81 steps.
    ``Proliferation`` sits behind an 11-layer glycolysis chain to
    ``ATP_Production_Rate``, needing on the order of 1000 steps to become
    reachable at all, whereas ``Apoptosis`` is ~6 layers deep. Below that the
    result measures which fate is reachable fastest rather than which fate the
    cell is in, and apoptosis wins regardless of the biology.
"""

import random
from typing import Dict

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    requires=['gene_networks', 'population'],
    display_name="Propagate Gene Networks (Single-Gene Random)",
    description="NetLogo single-gene random update matching gene_network_standalone.py; "
                "honours gene clamps set by Fix Gene Nodes",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT",
         "description": "Single-gene updates per cell per call. Needs to be ~1000+ on a "
                        "network this size for Proliferation to become reachable.",
         "default": 1000},
        {"name": "verbose", "type": "BOOL",
         "description": "Log how many cells were propagated and which nodes are clamped",
         "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def propagate_gene_networks_single_gene(
    env: BiologicalContext,
    propagation_steps: int = 1000,
    verbose: bool = False,
    **kwargs
) -> bool:
    # Per-cell when the executor's per-agent ask bound a cell, else the whole
    # population. Each cell's walk is independent, so the two are equivalent.
    cell_source = [env.cell] if env.cell is not None else list(env.cells)

    cells_done = 0
    cells_without_gn = 0
    clamped_seen: Dict[str, bool] = {}

    for cell in cell_source:
        gn = env.gene_network(cell)
        if gn is None:
            cells_without_gn += 1
            continue

        clamped = dict(getattr(gn, '_clamped', None) or {})
        clamped_seen.update(clamped)

        # Sampling pool: non-input genes that have a rule, minus anything
        # clamped. Excluding clamped nodes is what makes the knockout stick --
        # a clamped node is never selected, so its rule is never evaluated.
        genes = [
            name for name, node in gn.nodes.items()
            if not node.is_input and node.update_function is not None
            and name not in clamped
        ]

        # One mutable state dict maintained across the walk. Semantically
        # identical to rebuilding it every step (only one entry changes per
        # step) but avoids rebuilding a 106-entry dict per update.
        states = {name: node.current_state for name, node in gn.nodes.items()}
        for name, value in clamped.items():
            if name in states:
                states[name] = value

        if genes:
            for _ in range(propagation_steps):
                selected = random.choice(genes)
                states[selected] = bool(gn.nodes[selected].update_function(states))

        for name, value in states.items():
            gn.nodes[name].current_state = value
        cell.set_gene_state_snapshot(states)
        cells_done += 1

    if env.cell is None and verbose:
        print(f"[GENE_NETWORK] Single-gene update: {propagation_steps} steps on "
              f"{cells_done} cells")
        if clamped_seen:
            print(f"   [+] clamped (never sampled): {clamped_seen}")
        if cells_without_gn:
            print(f"   [!] skipped {cells_without_gn} cells with no gene network")

    return True
