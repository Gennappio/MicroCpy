"""Tests for the MaBoSS continuous-time stochastic update mode.

`BooleanNetwork.step_maboss` evolves the network as a continuous-time Markov
process driven by per-node `$u_`/`$d_` transition rates (loaded from a MaBoSS
`.cfg`). Unlike the discrete modes, a change to a single rate is meaningful --
which is exactly what a PhysiBoSS perturbation like `$u_FOXP3_2 = 0.2` is, and
the reason this mode exists.

The core tests build tiny synthetic networks whose kinetics have an exact
closed form, so they assert against analytic values rather than another
simulator. A driven node that flips toward its (true) logic and then stays put
is a Poisson first-event process: P(flipped by time T) = 1 - exp(-rate * T).

A final smoke test exercises the real 90-node `tcell_corral` network when the
PhysiCell tutorial files are present; it skips otherwise.
"""

import math
import os
import random
import sys
from pathlib import Path

import pytest

# Allow `from src...` imports when running this file directly.
_ENGINE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

from src.biology.gene_network import BooleanNetwork, _istate_to_bool


# --- synthetic networks: one internal node X driven by a clamped input ------

# X copies Drive. With Drive clamped ON, X wants to be ON and rises at $u_X;
# once ON it agrees with its logic and is absorbing. With Drive clamped OFF and
# X started ON, X wants OFF and falls at $d_X.
_DRIVEN_BND = """
Node Drive {
  logic = (Drive);
  rate_up = @logic ? $u_Drive : 0;
  rate_down = @logic ? 0 : $d_Drive;
}
Node X {
  logic = (Drive);
  rate_up = @logic ? $u_X : 0;
  rate_down = @logic ? 0 : $d_X;
}
"""

_UP_CFG = """
$u_Drive = 0;
$d_Drive = 0;
$u_X = 1.0;
$d_X = 1.0;
Drive.istate = TRUE;
X.istate = FALSE;
"""

_DOWN_CFG = """
$u_Drive = 0;
$d_Drive = 0;
$u_X = 1.0;
$d_X = 1.0;
Drive.istate = FALSE;
X.istate = TRUE;
"""

_N = 4000            # trajectories per estimate
_TOL = 0.04          # ~5 standard errors at N=4000, p~0.6


def _load(tmp_path, bnd, cfg):
    b = tmp_path / "n.bnd"
    c = tmp_path / "n.cfg"
    b.write_text(bnd)
    c.write_text(cfg)
    net = BooleanNetwork(network_file=b)
    net.load_cfg(c)
    return net


def _frac_on(net, node, T, istate, n=_N):
    """Fraction of n independent, seeded trajectories in which `node` ends ON.

    `istate` (captured while the network is clean) is re-applied before each
    run so trajectories are independent -- step_maboss mutates node state in
    place, so the initial condition must not be read back from the network.
    """
    on = 0
    for seed in range(n):
        for name, val in istate.items():
            net.nodes[name].current_state = val
        net.step_maboss(T, rng=random.Random(seed))
        on += net.nodes[node].current_state
    return on / n


# --- .cfg parsing -----------------------------------------------------------

def test_cfg_parses_rates_and_istates(tmp_path):
    net = _load(tmp_path, _DRIVEN_BND, _UP_CFG)
    assert net.nodes["X"].rate_up == 1.0
    assert net.nodes["X"].rate_down == 1.0
    # istate: Drive TRUE, X FALSE
    assert net.nodes["Drive"].current_state is True
    assert net.nodes["X"].current_state is False


def test_istate_to_bool_accepts_both_spellings():
    assert _istate_to_bool("TRUE") and _istate_to_bool("1.0") and _istate_to_bool("1")
    assert not _istate_to_bool("FALSE")
    assert not _istate_to_bool("0.0")
    assert not _istate_to_bool("0")


# --- CTMC kinetics vs analytic ---------------------------------------------

def test_up_transition_matches_analytic(tmp_path):
    net = _load(tmp_path, _DRIVEN_BND, _UP_CFG)
    istate = {name: nd.current_state for name, nd in net.nodes.items()}
    emp = _frac_on(net, "X", 1.0, istate)
    assert abs(emp - (1 - math.exp(-1.0))) < _TOL


def test_down_transition_matches_analytic(tmp_path):
    net = _load(tmp_path, _DRIVEN_BND, _DOWN_CFG)
    istate = {name: nd.current_state for name, nd in net.nodes.items()}
    # X starts ON, logic (=Drive) is FALSE -> falls at $d_X=1; measure ending OFF
    off = 1.0 - _frac_on(net, "X", 1.0, istate)
    assert abs(off - (1 - math.exp(-1.0))) < _TOL


def test_rate_perturbation_changes_kinetics(tmp_path):
    """The whole point: lowering a single $u_ rate slows that transition.

    Discrete Boolean modes cannot express this -- both would give the same
    (rate-free) result. Here u=0.2 must both match its own analytic value and
    sit well below the u=1.0 case.
    """
    net = _load(tmp_path, _DRIVEN_BND, _UP_CFG)
    istate = {name: nd.current_state for name, nd in net.nodes.items()}
    high = _frac_on(net, "X", 1.0, istate)     # u_X = 1.0

    net.set_rate("X", up=0.2)
    low = _frac_on(net, "X", 1.0, istate)      # u_X = 0.2

    assert abs(low - (1 - math.exp(-0.2))) < _TOL
    assert low < high - 0.2                    # clearly separated (0.18 vs 0.63)


def test_time_delta_zero_is_noop(tmp_path):
    net = _load(tmp_path, _DRIVEN_BND, _UP_CFG)
    before = net.get_all_states()
    net.step_maboss(0.0, rng=random.Random(0))
    assert net.get_all_states() == before


# --- input and knocked-out nodes never transition ---------------------------

def test_input_node_holds_its_clamped_state(tmp_path):
    net = _load(tmp_path, _DRIVEN_BND, _UP_CFG)
    # Drive is a self-referential input; it must keep whatever it was set to.
    net.nodes["Drive"].current_state = True
    net.step_maboss(5.0, rng=random.Random(1))
    assert net.nodes["Drive"].current_state is True


def test_fixed_node_is_a_knockout(tmp_path):
    """fix_node clamps a node -- the mutant/knockout mechanism.

    X wants to fall (Drive OFF), but fixed ON it must never flip.
    """
    net = _load(tmp_path, _DRIVEN_BND, _DOWN_CFG)
    net.fix_node("X", True)
    net.step_maboss(10.0, rng=random.Random(2))
    assert net.nodes["X"].current_state is True


# --- copy() carries rates (per-cell copies must keep the perturbation) ------

def test_copy_preserves_rates(tmp_path):
    net = _load(tmp_path, _DRIVEN_BND, _UP_CFG)
    net.set_rate("X", up=0.2, down=0.7)
    clone = net.copy()
    assert clone.nodes["X"].rate_up == 0.2
    assert clone.nodes["X"].rate_down == 0.7


# --- existing discrete modes are untouched ----------------------------------

def test_discrete_modes_still_work(tmp_path):
    net = _load(tmp_path, _DRIVEN_BND, _UP_CFG)
    # Neither call should raise; discrete modes ignore rates entirely.
    net.step(num_steps=3, mode="synchronous")
    net.step(num_steps=3, mode="netlogo")


# --- real 90-node network smoke (skips if PhysiCell files absent) -----------

_PHYSICELL_BN = Path(
    r"C:\Users\genna\Documents\PhysiCell\config\differentiation\boolean_network"
)


@pytest.mark.skipif(
    not _PHYSICELL_BN.exists(),
    reason="PhysiCell tcell_corral MaBoSS files not present on this machine",
)
def test_tcell_corral_loads_steps_and_perturbs():
    net = BooleanNetwork(network_file=_PHYSICELL_BN / "tcell_corral.bnd")
    net.load_cfg(_PHYSICELL_BN / "tcell_corral.cfg")

    # Real network parses and real per-node rates are read from the .cfg.
    assert len(net.nodes) > 50
    for name in ("FOXP3_2", "Treg", "Th1", "Th17"):
        assert name in net.nodes

    assert net.nodes["FOXP3_2"].rate_up == 1.0     # cfg default
    net.set_rate("FOXP3_2", up=0.2)                 # the FOXP3_2_lower perturbation
    assert net.nodes["FOXP3_2"].rate_up == 0.2

    states = net.step_maboss(6.0, rng=random.Random(0))
    assert len(states) == len(net.nodes)
