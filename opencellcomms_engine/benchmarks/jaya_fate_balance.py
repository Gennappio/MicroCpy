#!/usr/bin/env python3
"""
Jaya fate-balance harness: why does this network reach Apoptosis so much more
readily than Proliferation, and does the answer depend on the update scheme?

===============================================================================
QUICK START
===============================================================================

    cd opencellcomms_engine
    python benchmarks/jaya_fate_balance.py ../opencellcomms_adapters/MicroC/data/jaya.bnd

    # compare the original against a repair variant
    python benchmarks/jaya_fate_balance.py \\
        ../opencellcomms_adapters/MicroC/data/jaya.bnd \\
        ../opencellcomms_adapters/MicroC/data/jaya_p38gate.bnd

    # emit a MaBoSS .cfg for a .bnd (needed by maboss.load, which requires one)
    python benchmarks/jaya_fate_balance.py <bnd> --emit-cfg <out.cfg>

===============================================================================
WHY THIS EXISTS
===============================================================================

jaya.bnd behaves completely differently under synchronous and asynchronous
update.  Synchronously it settles into a limit cycle in which Apoptosis is never
ON; asynchronously essentially every cell reaches Apoptosis.  That disagreement
is the bug signature -- a Boolean model whose biology depends on the update
scheme is under-specified.  This harness measures the disagreement, and is the
acceptance test for candidate repairs: a repaired network is one whose update
schemes AGREE.

The five schemes:

    synchronous     BooleanNetwork.step(n, mode="synchronous")
    netlogo         BooleanNetwork.step(n, mode="netlogo")   -- one random gene
    graphwalk       MicroC's real per-tick walk, reusing
                    propagate_gene_networks_netlogo's own helpers
    maboss_internal BooleanNetwork.step_maboss(dt) -- the engine's Gillespie CTMC
    maboss_ref      pyMaBoSS/cmaboss, as an external check on maboss_internal

Note that jaya.bnd gives every node `rate_up = @logic ? 1 : 0` and there is no
jaya.cfg, so all MaBoSS rates default to 1.0.  A uniform-rate CTMC is uniform
random asynchronous updating up to a time reparametrisation -- so `netlogo`,
`maboss_internal` and `maboss_ref` are expected to agree closely.  They are run
side by side precisely to confirm that, because "it also happens in MaBoSS" is
otherwise easy to mistake for independent evidence.

===============================================================================
WHAT IS REPORTED, AND THE ONE SUBTLETY
===============================================================================

Each cell is run for `--burn-in` ticks that are NOT recorded, then `--ticks`
ticks that are.  The burn-in matters more than it looks: MicroC initialises gene
states randomly (`random_initialization: true`), and a random starting state sits
a couple of ticks away from satisfying `!BCL2 & !ERK & FOXO3 & p53` by chance
alone.  Without a burn-in every condition reports the same large apoptosis rate
and the network's actual behaviour is invisible.  That transient is reported
separately as `initApo`, because it is not an artefact of this harness -- every
cell, and every daughter cell (`_create_fresh_daughter_network` re-randomises),
pays it once in a real MicroC run.

Per (network x scheme x condition):

    initApo     fraction of cells that hit Apoptosis during the UNRECORDED
                burn-in, i.e. purely from the random-initialisation transient
    P(Apo)      steady-state probability the Apoptosis node is ON
    P(Prol)     ... Proliferation
    P(GA)       ... Growth_Arrest
    P(Nec)      ... Necrosis
    ever_Apo    fraction of cells that were Apoptosis-ON at ANY recorded tick
    ever_Prol   ... Proliferation
    t_Apo       median first recorded tick at which Apoptosis was ON
    t_Prol      ... Proliferation

`ever_Apo` is usually the number that matters, and it is not P(Apo).  MicroC
latches the fate and `remove_apoptotic_cells` deletes the cell, so a single
transient visit to Apoptosis is fatal; a steady-state probability understates
that badly.  `t_Apo` vs `t_Prol` shows the race: Apoptosis is assemblable from
shallow nodes while Proliferation sits behind an 11-layer glycolysis chain.

SUBTLETY 1 -- the graphwalk scheme reads fate from the `_fate` latch, not from
the node state.  MicroC's walk always resets a fate node to False right after
evaluating it (fate nodes are transient triggers), so reading node state under
graphwalk would report ~0% for every fate.  The other four schemes read node
state directly.  This is a real difference in what the model means by "the cell's
fate", not a difference in bookkeeping.

SUBTLETY 2 -- comparing schemes requires an equal update budget.  One tick is
one sweep-equivalent (`n_updatable` node updates) for every scheme, so a tick
means the same amount of network activity everywhere.  In particular the
graph walk defaults to `n_updatable` steps per tick, NOT to microc.json's
`propagation_steps: 5`.  Five walk steps on a 106-node network is about 1/16th
of a sweep, so a graph walk run at 5 is still deep in its transient after any
burn-in that settles the other schemes, and would look apoptotic for reasons
that have nothing to do with the network's attractors.  Pass
`--propagation-steps 5` to reproduce MicroC's actual (under-converged) regime,
but do not read scheme agreement off that run.
"""

import argparse
import random
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional

_BENCHMARKS = Path(__file__).resolve().parent
_ENGINE = _BENCHMARKS.parent
_REPO = _ENGINE.parent
for _p in (str(_ENGINE), str(_REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.biology.gene_network import BooleanNetwork  # noqa: E402

FATES = ["Apoptosis", "Proliferation", "Growth_Arrest", "Necrosis"]

# Input conditions.  The first five inputs are the ones MicroC actually drives
# via setup_associations (Oxygen->Oxygen_supply, Glucose->Glucose_supply,
# Lactate->MCT1_stimulus, HGF->cMET_stimulus, TGFA->EGFR_stimulus).  Because the
# gene TGFA is itself HIF1-driven and the association threshold is 1e-6, cells
# secrete their own EGFR ligand -- so the growth-factor-stimulated rows, not the
# unstimulated one, are the realistic ones.
#
# dna_damage and tgfb are controls: they must still produce apoptosis in a
# repaired network, otherwise the "repair" has simply deleted the death pathway.
CONDITIONS: Dict[str, Dict[str, bool]] = {
    "normoxia_no_gf":   dict(Oxygen_supply=True,  Glucose_supply=True),
    "normoxia_egfr":    dict(Oxygen_supply=True,  Glucose_supply=True, EGFR_stimulus=True),
    "normoxia_all_gf":  dict(Oxygen_supply=True,  Glucose_supply=True, EGFR_stimulus=True,
                             FGFR_stimulus=True, cMET_stimulus=True),
    "hypoxia_egfr":     dict(Oxygen_supply=False, Glucose_supply=True, EGFR_stimulus=True),
    "no_glucose_egfr":  dict(Oxygen_supply=True,  Glucose_supply=False, EGFR_stimulus=True),
    "starved":          dict(Oxygen_supply=False, Glucose_supply=False, EGFR_stimulus=True),
    "dna_damage":       dict(Oxygen_supply=True,  Glucose_supply=True, EGFR_stimulus=True,
                             DNA_damage=True),
    "tgfb":             dict(Oxygen_supply=True,  Glucose_supply=True, EGFR_stimulus=True,
                             TGFBR_stimulus=True),
}

SCHEMES = ["synchronous", "netlogo", "graphwalk", "maboss_internal", "maboss_ref"]


# ---------------------------------------------------------------------------
# network setup
# ---------------------------------------------------------------------------

def load_network(bnd_path: Path) -> BooleanNetwork:
    net = BooleanNetwork(network_file=bnd_path)
    if not net.nodes:
        raise SystemExit(f"no nodes parsed from {bnd_path}")
    return net


def seed_states(net: BooleanNetwork, inputs: Dict[str, bool], init: str) -> None:
    """Set every node's starting state.

    `random` mirrors MicroC's initialize_netlogo_gene_networks with
    random_initialization=True: fate nodes OFF, other non-input nodes random,
    inputs clamped to the condition.  `off` starts everything OFF, which is the
    cleanest way to read activation latency.
    """
    for node in net.nodes.values():
        if node.is_input:
            node.current_state = False
        elif node.name in FATES:
            node.current_state = False
        else:
            node.current_state = random.choice([True, False]) if init == "random" else False
    net.set_input_states(inputs)


def _reclamp(net: BooleanNetwork, inputs: Dict[str, bool]) -> None:
    """Re-assert the condition.

    Inputs have no update function so no scheme should move them, but every
    scheme is re-clamped after each tick anyway so that a parsing surprise (a
    node the parser did not classify as an input) shows up as a discrepancy
    between schemes rather than silently drifting.
    """
    net.set_input_states(inputs)


# ---------------------------------------------------------------------------
# observation
# ---------------------------------------------------------------------------

class Trace:
    """Accumulates fate observations across independent cells.

    Each cell contributes the full observation list; the first `burn_in` entries
    are scored separately (`burn`) and excluded from everything else, so the
    random-initialisation transient never contaminates the attractor statistics.
    """

    def __init__(self) -> None:
        self.final = {f: 0 for f in FATES}
        self.ever = {f: 0 for f in FATES}
        self.burn = {f: 0 for f in FATES}
        self.first: Dict[str, List[int]] = {f: [] for f in FATES}
        self.cells = 0

    def add_cell(self, observations: List[Dict[str, bool]], burn_in: int) -> None:
        self.cells += 1
        warmup, recorded = observations[:burn_in], observations[burn_in:]
        for f in FATES:
            if any(obs.get(f) for obs in warmup):
                self.burn[f] += 1
            hit = [i for i, obs in enumerate(recorded) if obs.get(f)]
            if hit:
                self.ever[f] += 1
                self.first[f].append(hit[0])
        if recorded:
            for f in FATES:
                if recorded[-1].get(f):
                    self.final[f] += 1

    def row(self) -> Dict[str, Optional[float]]:
        n = self.cells or 1
        out: Dict[str, Optional[float]] = {}
        for f in FATES:
            out[f"P({f})"] = self.final[f] / n
            out[f"ever({f})"] = self.ever[f] / n
            out[f"burn({f})"] = self.burn[f] / n
        for f in ("Apoptosis", "Proliferation"):
            out[f"t({f})"] = statistics.median(self.first[f]) if self.first[f] else None
        return out


# ---------------------------------------------------------------------------
# schemes
# ---------------------------------------------------------------------------

def run_discrete(net: BooleanNetwork, inputs: Dict[str, bool], mode: str,
                 ticks: int, burn_in: int, tick_size: int, cells: int,
                 init: str, seed: int) -> Trace:
    """synchronous / netlogo.  Fate is read from the node states."""
    trace = Trace()
    for c in range(cells):
        random.seed(seed + c)
        seed_states(net, inputs, init)
        obs = []
        for _ in range(burn_in + ticks):
            net.step(tick_size, mode=mode)
            _reclamp(net, inputs)
            obs.append({f: net.nodes[f].current_state for f in FATES if f in net.nodes})
        trace.add_cell(obs, burn_in)
    return trace


def run_maboss_internal(net: BooleanNetwork, inputs: Dict[str, bool], ticks: int,
                        burn_in: int, dt: float, cells: int, init: str, seed: int) -> Trace:
    """The engine's own Gillespie CTMC.  Fate is read from the node states."""
    trace = Trace()
    for c in range(cells):
        rng = random.Random(seed + c)
        random.seed(seed + c)
        seed_states(net, inputs, init)
        obs = []
        for _ in range(burn_in + ticks):
            net.step_maboss(dt, rng=rng)
            _reclamp(net, inputs)
            obs.append({f: net.nodes[f].current_state for f in FATES if f in net.nodes})
        trace.add_cell(obs, burn_in)
    return trace


def run_graphwalk(net: BooleanNetwork, inputs: Dict[str, bool], ticks: int, burn_in: int,
                  propagation_steps: int, cells: int, init: str, seed: int,
                  reversible: bool = False, reset_fate: bool = True) -> Trace:
    """MicroC's real per-tick graph walk.

    Reuses propagate_gene_networks_netlogo's own helpers rather than
    reimplementing the walk, so this cannot drift from what MicroC runs.
    Fate is read from the `_fate` latch -- see the module docstring.
    """
    from opencellcomms_adapters.MicroC.functions.gene_network import (
        propagate_gene_networks_netlogo as walk,
    )
    _ensure_netlogo_attrs = walk._ensure_netlogo_attrs
    _get_random_start_node = walk._get_random_start_node
    _netlogo_downstream_change = walk._netlogo_downstream_change

    trace = Trace()
    _ensure_netlogo_attrs(net)  # builds the out-links once; they never change
    for c in range(cells):
        random.seed(seed + c)
        seed_states(net, inputs, init)
        net._fate = None
        net._last_node = _get_random_start_node(net)
        obs = []
        for _ in range(burn_in + ticks):
            if reset_fate:
                net._fate = None
            for _ in range(propagation_steps):
                if reversible:
                    if net._fate == "Necrosis":
                        continue
                elif net._fate is not None:
                    continue
                _netlogo_downstream_change(net, current_tick=0)
                _reclamp(net, inputs)
            obs.append({f: (net._fate == f) for f in FATES})
        trace.add_cell(obs, burn_in)
    return trace


# ---------------------------------------------------------------------------
# MaBoSS .cfg generation + reference run
# ---------------------------------------------------------------------------

def build_cfg(net: BooleanNetwork, inputs: Dict[str, bool], init: str,
              max_time: float, sample_count: int, seed: int) -> str:
    """Render a MaBoSS .cfg for this network and condition.

    Rates are all 1.0, matching both jaya.bnd's `rate_up = @logic ? 1 : 0` and
    NetworkNode's defaults, so maboss_ref and maboss_internal are comparable by
    construction rather than by luck.
    """
    lines = [
        "// Generated by benchmarks/jaya_fate_balance.py (--emit-cfg).",
        "//",
        "// Unit rates: jaya.bnd declares rate_up/rate_down of 1, and NetworkNode",
        "// defaults to 1.0, so this file states the defaults rather than changing them.",
        "// This is why MaBoSS and the engine's netlogo/asynchronous modes agree on this",
        "// model -- a uniform-rate CTMC is uniform random asynchronous update.",
        "//",
        "// Input nodes start OFF unless set below, so out of the box this describes a",
        "// starved cell (no Oxygen_supply, no Glucose_supply -> Necrosis). Edit the",
        "// <Input>.istate lines to pick a condition, e.g.:",
        "//     Oxygen_supply.istate = 1;",
        "//     Glucose_supply.istate = 1;",
        "//     EGFR_stimulus.istate = 1;",
        "",
    ]
    for name in sorted(net.nodes):
        lines.append(f"$u_{name} = 1.0;")
        lines.append(f"$d_{name} = 1.0;")
    lines.append("")
    for name in sorted(net.nodes):
        node = net.nodes[name]
        if node.is_input:
            lines.append(f"{name}.istate = {1 if inputs.get(name, False) else 0};")
        elif name in FATES or init != "random":
            lines.append(f"{name}.istate = 0;")
        else:
            # Probabilistic istates need the bracketed-node-list form; the bare
            # `Name.istate = 0.5 [0], ...` spelling is a cfg syntax error.
            lines.append(f"[{name}].istate = 0.5 [0], 0.5 [1];")
    lines += [
        "",
        "time_tick = 0.5;",
        f"max_time = {max_time};",
        f"sample_count = {sample_count};",
        "discrete_time = 0;",
        "use_physrandgen = 0;",
        f"seed_pseudorandom = {seed};",
        "display_traj = 0;",
        "statdist_traj_count = 0;",
        "statdist_cluster_threshold = 1;",
        "thread_count = 4;",
        "",
    ]
    return "\n".join(lines)


def run_maboss_ref(net: BooleanNetwork, bnd_path: Path, inputs: Dict[str, bool],
                   init: str, max_time: float, cells: int, seed: int,
                   scratch: Path) -> Optional[Dict[str, float]]:
    """pyMaBoSS/cmaboss reference.

    Returns steady-state P(ON) only.  pyMaBoSS reports a probability trajectory,
    not per-cell traces, so `ever(...)` and first-passage are not available here
    -- that is why maboss_internal exists alongside it.
    """
    try:
        import maboss
    except ImportError:
        return None

    scratch.mkdir(parents=True, exist_ok=True)
    cfg_path = scratch / f"{bnd_path.stem}_ref.cfg"
    cfg_path.write_text(build_cfg(net, inputs, init, max_time, cells, seed))
    try:
        sim = maboss.load(str(bnd_path), str(cfg_path), cmaboss=True)
        probs = sim.run().get_last_nodes_probtraj().iloc[0]
    except Exception as exc:  # cmaboss raises bare RuntimeError on parse trouble
        print(f"    [maboss_ref unavailable: {exc}]")
        return None
    return {f: float(probs.get(f, 0.0)) for f in FATES}


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def _fmt(v: Optional[float], width: int = 7) -> str:
    if v is None:
        return "-".rjust(width)
    return f"{v:{width}.2f}"


def report(title: str, rows: Dict[str, Dict[str, Optional[float]]]) -> None:
    print(f"\n{title}")
    header = (f"  {'condition':<18}{'initApo':>9}{'P(Apo)':>8}{'P(Prol)':>8}{'P(GA)':>8}"
              f"{'P(Nec)':>8}{'everApo':>9}{'everProl':>9}{'t(Apo)':>8}{'t(Prol)':>8}")
    print(header)
    print("  " + "-" * (len(header) - 2))
    for cond, r in rows.items():
        print(f"  {cond:<18}"
              f"{_fmt(r.get('burn(Apoptosis)'), 9)}"
              f"{_fmt(r.get('P(Apoptosis)'), 8)}{_fmt(r.get('P(Proliferation)'), 8)}"
              f"{_fmt(r.get('P(Growth_Arrest)'), 8)}{_fmt(r.get('P(Necrosis)'), 8)}"
              f"{_fmt(r.get('ever(Apoptosis)'), 9)}{_fmt(r.get('ever(Proliferation)'), 9)}"
              f"{_fmt(r.get('t(Apoptosis)'), 8)}{_fmt(r.get('t(Proliferation)'), 8)}")


def check_acceptance(results: Dict[str, Dict[str, Dict[str, Optional[float]]]]) -> None:
    """The four criteria that separate a repair from a deletion of the death path.

    1. synchronous stays non-apoptotic under normoxia + growth factor
    2. the asynchronous schemes AGREE with synchronous (the present disagreement
       is the bug; agreement is the fix)
    3. apoptosis is still reachable when it should be -- DNA damage restores it,
       and total starvation still gives necrosis
    4. proliferation still requires fuel -- no glucose, no proliferation
    """
    print("\n  acceptance criteria")
    print("  " + "-" * 68)

    def get(scheme: str, cond: str, key: str) -> Optional[float]:
        return results.get(scheme, {}).get(cond, {}).get(key)

    verdicts: List[Optional[bool]] = []

    def state(ok: Optional[bool], text: str) -> None:
        """A criterion whose inputs were not measured reports SKIP, not FAIL --
        otherwise running a subset of schemes looks like a rejected network."""
        verdicts.append(ok)
        print(f"  [{'SKIP' if ok is None else 'PASS' if ok else 'FAIL'}] {text}")

    sync_apo = get("synchronous", "normoxia_egfr", "ever(Apoptosis)")
    state(None if sync_apo is None else sync_apo <= 0.05,
          f"1. synchronous non-apoptotic under normoxia+EGFR "
          f"(ever_Apo={_fmt(sync_apo, 5).strip()})")

    async_apo = [v for v in (get(s, "normoxia_egfr", "ever(Apoptosis)")
                             for s in ("netlogo", "graphwalk", "maboss_internal"))
                 if v is not None]
    spread = (max(async_apo) - sync_apo) if async_apo and sync_apo is not None else None
    state(None if spread is None else spread <= 0.15,
          f"2. async schemes agree with synchronous "
          f"(max gap={_fmt(spread, 5).strip()}, need <=0.15)")

    dmg = get("netlogo", "dna_damage", "ever(Apoptosis)")
    nec = get("netlogo", "starved", "ever(Necrosis)")
    state(None if dmg is None or nec is None else (dmg >= 0.20 and nec >= 0.20),
          f"3. death still reachable "
          f"(DNA_damage ever_Apo={_fmt(dmg, 5).strip()}, starved ever_Nec={_fmt(nec, 5).strip()})")

    noglc = get("netlogo", "no_glucose_egfr", "ever(Proliferation)")
    state(None if noglc is None else noglc <= 0.05,
          f"4. proliferation still needs glucose (ever_Prol={_fmt(noglc, 5).strip()})")

    if any(v is None for v in verdicts):
        print("\n  VERDICT: INCOMPLETE (run all schemes to score this network)")
    else:
        print(f"\n  VERDICT: {'ACCEPTED' if all(verdicts) else 'REJECTED'}")


# ---------------------------------------------------------------------------

def analyse(bnd_path: Path, args: argparse.Namespace, scratch: Path) -> None:
    net = load_network(bnd_path)
    n_updatable = len([n for n in net.nodes.values()
                       if not n.is_input and n.update_function])

    # One tick = one sweep-equivalent for every scheme, so the update budget is
    # equal and the schemes are actually comparable. --propagation-steps opts out
    # of that in order to reproduce MicroC's under-converged regime.
    walk_steps = args.propagation_steps or n_updatable

    print("\n" + "=" * 88)
    print(f"NETWORK: {bnd_path.name}   ({len(net.nodes)} nodes, "
          f"{len(net.input_nodes)} inputs, {n_updatable} updatable)")
    print("=" * 88)
    if args.propagation_steps:
        print(f"  NOTE: graph walk forced to {args.propagation_steps} steps/tick "
              f"({args.propagation_steps / n_updatable:.2f} sweep-equivalents). This is "
              f"MicroC's regime,\n        not a converged one -- do not read scheme "
              f"agreement off this run.")

    overlay = {}
    for item in args.overlay:
        name, _, val = item.partition("=")
        overlay[name] = val.strip().upper() in ("ON", "1", "TRUE")
    if overlay:
        unknown = [n for n in overlay if n not in net.input_nodes]
        print(f"  overlay: {overlay}")
        if unknown:
            print(f"  WARNING: {unknown} are not input nodes in this .bnd, so they will be "
                  f"recomputed and NOT held. Make them inputs first.")

    results: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {}

    for scheme in args.schemes:
        rows: Dict[str, Dict[str, Optional[float]]] = {}
        for cond, base_inputs in CONDITIONS.items():
            inputs = {**base_inputs, **overlay}
            if scheme == "synchronous":
                rows[cond] = run_discrete(net, inputs, "synchronous", args.ticks,
                                          args.burn_in, 1, args.cells, args.init,
                                          args.seed).row()
            elif scheme == "netlogo":
                # one tick = one sweep-equivalent, so tick indices are comparable
                # with synchronous steps rather than being 106x finer.
                rows[cond] = run_discrete(net, inputs, "netlogo", args.ticks,
                                          args.burn_in, n_updatable, args.cells,
                                          args.init, args.seed).row()
            elif scheme == "graphwalk":
                rows[cond] = run_graphwalk(net, inputs, args.ticks, args.burn_in,
                                           walk_steps, args.cells,
                                           args.init, args.seed).row()
            elif scheme == "maboss_internal":
                rows[cond] = run_maboss_internal(net, inputs, args.ticks, args.burn_in,
                                                 1.0, args.cells, args.init,
                                                 args.seed).row()
            elif scheme == "maboss_ref":
                p = run_maboss_ref(net, bnd_path, inputs, args.init,
                                   float(args.burn_in + args.ticks), args.cells,
                                   args.seed, scratch)
                rows[cond] = ({f"P({f})": v for f, v in p.items()} if p else {})
        results[scheme] = rows
        label = f"scheme: {scheme}"
        if scheme == "graphwalk":
            label += f"   ({walk_steps} walk steps/tick, fate read from _fate latch)"
        elif scheme == "maboss_ref":
            label += "   (steady-state probabilities only)"
        report(label, rows)

    check_acceptance(results)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compare fate outcomes for a .bnd across update schemes.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bnd", nargs="+", type=Path, help="one or more .bnd files to compare")
    ap.add_argument("--schemes", nargs="+", default=SCHEMES, choices=SCHEMES)
    ap.add_argument("--cells", type=int, default=200, help="independent cells per condition")
    ap.add_argument("--ticks", type=int, default=40, help="recorded observations per cell")
    ap.add_argument("--burn-in", type=int, default=30,
                    help="unrecorded ticks first, to skip the random-init transient")
    ap.add_argument("--propagation-steps", type=int, default=0,
                    help="graph-walk steps per tick; 0 (default) means one "
                         "sweep-equivalent, so the budget matches the other schemes. "
                         "Pass 5 to reproduce microc.json's under-converged regime.")
    ap.add_argument("--init", choices=["random", "off"], default="random",
                    help="random mirrors MicroC's random_initialization=true")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--set", nargs="+", default=[], dest="overlay", metavar="NODE=ON|OFF",
                    help="Overlay these node states on every condition. Only affects "
                         "nodes the parser treats as inputs, so to pin a logic node such "
                         "as p53 you must first make it an input in the .bnd (which is "
                         "what a knockout is).")
    ap.add_argument("--emit-cfg", type=Path,
                    help="write a MaBoSS .cfg for the first .bnd and exit")
    ap.add_argument("--scratch", type=Path, default=Path("/tmp/jaya_fate_balance"),
                    help="directory for generated .cfg files")
    args = ap.parse_args()

    if args.emit_cfg:
        net = load_network(args.bnd[0])
        args.emit_cfg.write_text(
            build_cfg(net, {}, args.init, float(args.ticks), args.cells, args.seed))
        print(f"wrote {args.emit_cfg}")
        return

    for path in args.bnd:
        analyse(path, args, args.scratch)


if __name__ == "__main__":
    main()
