"""Record and print Treg / Th1 / Th17 proportions across the T0 cells.

Counts each fate two ways: (1) the live MaBoSS output-node state
(``Treg``/``Th1``/``Th17`` currently ON) for cells still cycling, and (2) the
committed ``fate`` field once ``commit_tcell_fate`` (Increment 5) has fixed it.
Proportions are stored via ``env.record`` so a downstream plot node can chart them
over time, and printed each call for the CLI checkpoint (baseline is roughly
Treg 0.5 / Th1 0.26 / Th17 0.22 — see NEXT_STEPS.md Section 0).
"""
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext

_FATES = ("Treg", "Th1", "Th17")


@register_function(
    display_name="Record Fate Counts",
    description="Count Treg/Th1/Th17 across T0 cells (live output nodes plus committed "
                "fate) and record the proportions for plotting.",
    category="FINALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["gene_networks", "population"],
)
def record_fate_counts(env: BiologicalContext, **kwargs) -> bool:
    counts = {f: 0 for f in _FATES}
    committed = {f: 0 for f in _FATES}
    n_tcell = 0
    for cell in env.cells:
        if cell.raw.state.metabolic_state.get("_kind") != "tcell":
            continue                       # ignore DC / endothelial cells
        gn = env.gene_network(cell)
        if gn is None:
            continue
        n_tcell += 1
        for f in _FATES:
            node = gn.nodes.get(f)
            if node is not None and node.current_state:
                counts[f] += 1
        fate = cell.raw.state.metabolic_state.get("fate")
        if fate in committed:
            committed[fate] += 1

    if n_tcell:
        frac = {f: counts[f] / n_tcell for f in _FATES}
        for f in _FATES:
            env.record(f"{f}_frac", frac[f])   # one scalar series per fate for plotting
        for f in _FATES:
            env.record(f"{f}_committed", float(committed[f]))
        live = ", ".join(f"{f} {frac[f]:.3f}" for f in _FATES)
        comm = ", ".join(f"{f} {committed[f]}" for f in _FATES)
        print(f"[FATE] {n_tcell} T0 | live: {live} | committed: {comm} (total {sum(committed.values())})")
    else:
        print("[FATE] no T0 cells with a gene network found")
    return True
