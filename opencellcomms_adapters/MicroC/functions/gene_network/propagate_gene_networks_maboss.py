"""
Propagate gene networks as a MaBoSS continuous-time Markov chain (CTMC).

The PhysiBoSS-style update: each scheduler step, every cell's Boolean network
is advanced over the same time window the transient PDEs just integrated —
window = dt × maboss_time_scale, with dt (hours) owned by the Setup
Simulation node and resolved at run time via ``get_simulation_dt_hours``
(deliberately NOT ``env.dt``, whose clockless fallback silently returns 1.0
in the v2.0 executor path).

THE LAW (implemented once, in ``BooleanNetwork.step_maboss`` — this node only
calls it, per R2.1): candidates are the non-input nodes with a logic rule,
minus fixed/clamped nodes; a candidate whose current state disagrees with its
logic value transitions TOWARD the logic value at ``rate_up`` (0→1) /
``rate_down`` (1→0); Gillespie draws exponential waiting times from the total
rate and flips one node at a time until the window is exhausted or a fixed
point is reached.

RATE PROVENANCE: jaya.bnd writes ``rate_up = @logic ? 1 : 0`` on every
internal node. The .bnd parser does not evaluate rate expressions, but the
parser defaults (rate_up = rate_down = 1.0) are exactly equivalent under
``step_maboss`` semantics, which already only fires a rate when the state
disagrees with the logic. So no .cfg is needed; ``maboss_time_scale`` is the
single knob (it rescales all rates uniformly: scale s ≡ every rate = s per
simulated hour).

GENE CLAMPS ARE HONOURED: ``fix_gene_nodes`` stores clamps on the network's
``_clamped`` dict (heritable across division via
``context['gene_network_clamped_nodes']`` — see ``update_cell_division``),
while ``step_maboss`` excludes only ``fixed_nodes``. This node bridges the
two for the duration of the call (re-asserting the clamped values first), so
a p53/MCT1 knockout survives the whole run exactly as it does under the
single-gene updater.

REPRODUCIBILITY: draws come from ``env.rng`` — the executor-seeded run RNG —
never the unseeded global ``random`` module. ``step_maboss`` only calls
``rng.random()``, which the numpy Generator provides.

Necrotic cells are frozen (NetLogo semantics: a dead cell's genes stop
moving), matching the other MicroC propagate functions. Fate nodes are
ordinary Boolean nodes here — no latch, no reset — read directly by the fate
functions afterwards, same as the single-gene variant.
"""

from typing import Dict

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext
from src.workflow.functions.initialization.setup_simulation import get_simulation_dt_hours


@register_function(
    requires=['gene_networks', 'population'],
    display_name="Propagate Gene Networks (MaBoSS CTMC)",
    description="MaBoSS continuous-time Gillespie advance of each cell's Boolean "
                "network over window = dt × maboss_time_scale (dt owned by Setup "
                "Simulation) — the PhysiBoSS event check for the step's time "
                "window. Honours gene clamps set by Fix Gene Nodes; necrotic "
                "cells frozen; scale 0 freezes all networks.",
    category="INTRACELLULAR",
    parameters=[
        {"name": "maboss_time_scale", "type": "FLOAT",
         "description": "MaBoSS time units advanced per simulated hour. CTMC window "
                        "per scheduler step = dt × this scale (default 1.0 = one "
                        "MaBoSS time unit per hour; 0 freezes the networks).",
         "default": 1.0,
         "min_value": 0.0},
        {"name": "verbose", "type": "BOOL",
         "description": "Log how many cells were advanced and which nodes are clamped",
         "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def propagate_gene_networks_maboss(
    env: BiologicalContext,
    maboss_time_scale: float = 1.0,
    verbose: bool = False,
    **kwargs
) -> bool:
    dt_hours = get_simulation_dt_hours(env.raw_context)
    window = dt_hours * float(maboss_time_scale)
    rng = env.rng

    # R1.5: announce the effective law once per run (per-agent calls would
    # flood the log with one line per cell per step).
    if not env.raw_context.get('_maboss_window_logged'):
        env.raw_context['_maboss_window_logged'] = True
        print(f"[GENE_NETWORK] MaBoSS CTMC window = dt x maboss_time_scale = "
              f"{dt_hours:g} h x {float(maboss_time_scale):g} = {window:g} MaBoSS "
              f"time units/step (rates: jaya.bnd '@logic ? 1 : 0' == engine "
              f"defaults 1.0)")

    # Per-cell when the executor's per-agent ask bound a cell, else the whole
    # population. Each cell's CTMC is independent, so the two are equivalent.
    cell_source = [env.cell] if env.cell is not None else list(env.cells)

    cells_done = 0
    cells_without_gn = 0
    cells_frozen = 0
    clamped_seen: Dict[str, bool] = {}

    for cell in cell_source:
        # NetLogo freezes the network of necrotic cells (gene updates run only
        # while my-fate != "Necrosis"): a dead cell's genes stop moving.
        if cell.is_necrotic:
            cells_frozen += 1
            continue

        gn = env.gene_network(cell)
        if gn is None:
            cells_without_gn += 1
            continue

        clamped = dict(getattr(gn, '_clamped', None) or {})
        clamped_seen.update(clamped)
        for name, value in clamped.items():
            if name in gn.nodes:
                gn.nodes[name].current_state = value

        # step_maboss honours only gn.fixed_nodes; MicroC clamps live on
        # gn._clamped — bridge for the duration of the call so a knockout is
        # never selected as a transition candidate.
        saved_fixed = gn.fixed_nodes
        try:
            gn.fixed_nodes = {**saved_fixed, **clamped}
            gn.step_maboss(window, rng)
        finally:
            gn.fixed_nodes = saved_fixed

        cell.set_gene_state_snapshot(gn.get_all_states())
        cells_done += 1

    if env.cell is None and verbose:
        print(f"[GENE_NETWORK] MaBoSS CTMC: window {window:g} on {cells_done} cells")
        if clamped_seen:
            print(f"   [+] clamped (never a candidate): {clamped_seen}")
        if cells_without_gn:
            print(f"   [!] skipped {cells_without_gn} cells with no gene network")
        if cells_frozen:
            print(f"   [+] frozen {cells_frozen} necrotic cells (networks stop at death)")

    return True
