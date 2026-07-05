"""Cross-checks of step_maboss against the reference MaBoSS engine (cmaboss).

These lock fidelity: the continuous-time engine must reproduce *real MaBoSS's*
attractor / steady-state probabilities, not merely analytic toy cases.

We compare at steady state on purpose. MaBoSS's `probtraj` value at index t is
the time-average over the window [t, t+time_tick], so a transient-time
comparison would differ from step_maboss (which reports the instantaneous
state) by a reporting convention, not a real disagreement. At convergence that
window is stationary and the two engines agree by construction -- which is
exactly the attractor regime that matters for the science.

The module skips cleanly where the compiled `cmaboss` engine (or, for the real
network, the PhysiCell tcell_corral files) is unavailable.
"""

import os
import random
import sys
from pathlib import Path

import pytest

_ENGINE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

from src.biology.gene_network import BooleanNetwork

maboss = pytest.importorskip("maboss")
pytest.importorskip("cmaboss")  # the compiled engine maboss.load(cmaboss=True) needs


# Vendored copy of the PhysiCell/PhysiBoSS Corral network (byte-identical to the
# source), so this cross-check runs anywhere cmaboss is installed rather than only
# on a machine with a local PhysiCell checkout.
_PHYSICELL_BN = (
    Path(__file__).resolve().parents[3]
    / "opencellcomms_adapters" / "TCELL_CORRAL" / "data"
)
_HAVE_TCELL = (_PHYSICELL_BN / "tcell_corral.bnd").exists()
_TCELL_REASON = "TCELL_CORRAL tcell_corral MaBoSS files not found in the adapter data dir"

# The nine nodes PhysiCell's "contact with dendritic_cell" signal drives ON.
CONTACT_INPUTS = ["IL1_In", "MHCII_b1", "MHCII_b2", "IL12_In",
                  "IL6_In", "CD80", "CD4", "IL23_In", "PIP2"]
FATES = ["Treg", "Th1", "Th17"]

# Minimal MaBoSS engine parameters for the synthetic toggle .cfg.
_SIMPARAMS = (
    "\ntime_tick = 0.5;\nmax_time = 100;\nsample_count = 100000;\n"
    "discrete_time = 0;\nthread_count = 1;\nseed_pseudorandom = 0;\n"
)

_T = 100.0     # horizon; the tcell attractors converge well before this
_N = 400       # trajectories for the engine's Monte-Carlo estimate
_TOL = 0.06    # ~2x the N=400 standard error; cmaboss ref error is negligible


def _maboss_probs(bnd, cfg, clamp_on=(), params=None, nodes=()):
    """Reference steady-state P(node ON) from cmaboss."""
    sim = maboss.load(str(bnd), str(cfg), cmaboss=True)
    for n in clamp_on:
        sim.network.set_istate(n, [0.0, 1.0])
    for key, val in (params or {}).items():
        sim.param[key] = val
    last = sim.run().get_last_nodes_probtraj()
    return {n: float(last[n].values[0]) for n in nodes}


def _my_probs(bnd, cfg, clamp_on, nodes, T=_T, N=_N, rate_overrides=None):
    """Monte-Carlo P(node ON at time T) from step_maboss over N seeded cells."""
    net = BooleanNetwork(network_file=Path(bnd))
    net.load_cfg(Path(cfg))
    for name, up in (rate_overrides or {}).items():
        net.set_rate(name, up=up)

    istate = {k: v.current_state for k, v in net.nodes.items()}
    for n in clamp_on:
        istate[n] = True

    counts = {n: 0 for n in nodes}
    for seed in range(N):
        for k, v in istate.items():
            net.nodes[k].current_state = v
        net.step_maboss(T, rng=random.Random(seed))
        for n in nodes:
            counts[n] += net.nodes[n].current_state
    return {n: counts[n] / N for n in nodes}


# --- exact intermediate attractor probability (self-contained) --------------

_TOGGLE_BND = """
Node A { logic = (!B); rate_up = @logic ? $u_A : 0; rate_down = @logic ? 0 : $d_A; }
Node B { logic = (!A); rate_up = @logic ? $u_B : 0; rate_down = @logic ? 0 : $d_B; }
"""
_TOGGLE_CFG = ("$u_A = 3;\n$d_A = 1;\n$u_B = 1;\n$d_B = 1;\n"
               "A.istate = FALSE;\nB.istate = FALSE;\n" + _SIMPARAMS)


def test_toggle_attractor_probability_matches_maboss(tmp_path):
    """A rate-asymmetric toggle settles into A=1 with prob u_A/(u_A+u_B)=0.75.

    Both engines must land on that intermediate, rate-dependent probability --
    a value discrete Boolean updating structurally cannot produce.
    """
    bnd = tmp_path / "toggle.bnd"
    cfg = tmp_path / "toggle.cfg"
    bnd.write_text(_TOGGLE_BND)
    cfg.write_text(_TOGGLE_CFG)

    ref = _maboss_probs(bnd, cfg, nodes=["A"])["A"]
    mine = _my_probs(bnd, cfg, clamp_on=(), nodes=["A"], T=50.0, N=4000)["A"]

    assert abs(ref - 0.75) < 0.02      # the reference is itself on the mark
    assert abs(mine - ref) < 0.03      # step_maboss matches the reference


# --- real 90-node attractor distribution + FOXP3_2 perturbation -------------

@pytest.mark.slow
@pytest.mark.skipif(not _HAVE_TCELL, reason=_TCELL_REASON)
def test_tcell_corral_baseline_matches_maboss():
    """With DC contact, the T0 network's Treg/Th1/Th17 split must match MaBoSS."""
    bnd = _PHYSICELL_BN / "tcell_corral.bnd"
    cfg = _PHYSICELL_BN / "tcell_corral.cfg"

    ref = _maboss_probs(bnd, cfg, clamp_on=CONTACT_INPUTS, nodes=FATES)
    mine = _my_probs(bnd, cfg, CONTACT_INPUTS, FATES)

    for f in FATES:
        assert abs(mine[f] - ref[f]) < _TOL, f"{f}: mine={mine[f]:.3f} ref={ref[f]:.3f}"


@pytest.mark.slow
@pytest.mark.skipif(not _HAVE_TCELL, reason=_TCELL_REASON)
def test_tcell_corral_foxp3_perturbation_matches_maboss():
    """Lowering $u_FOXP3_2 moves the attractor split the same way in both
    engines: Treg collapses. This is the exact perturbation the user ran, and
    the reason the CTMC mode exists -- discrete Boolean is blind to a rate.
    """
    bnd = _PHYSICELL_BN / "tcell_corral.bnd"
    cfg = _PHYSICELL_BN / "tcell_corral.cfg"

    ref_base = _maboss_probs(bnd, cfg, CONTACT_INPUTS, nodes=FATES)
    ref_pert = _maboss_probs(bnd, cfg, CONTACT_INPUTS,
                             params={"$u_FOXP3_2": 0.2}, nodes=FATES)
    my_base = _my_probs(bnd, cfg, CONTACT_INPUTS, FATES)
    my_pert = _my_probs(bnd, cfg, CONTACT_INPUTS, FATES,
                        rate_overrides={"FOXP3_2": 0.2})

    # The perturbation genuinely collapses Treg in the reference...
    assert ref_base["Treg"] - ref_pert["Treg"] > 0.1
    # ...and step_maboss reproduces that drop, and the perturbed distribution.
    assert abs((my_base["Treg"] - my_pert["Treg"])
               - (ref_base["Treg"] - ref_pert["Treg"])) < _TOL
    for f in FATES:
        assert abs(my_pert[f] - ref_pert[f]) < _TOL, \
            f"{f}: mine={my_pert[f]:.3f} ref={ref_pert[f]:.3f}"
