"""Transient (implicit Euler) mode of MultiSubstanceSimulator.update().

update(..., transient_dt=seconds) must take exactly one backward Euler step of
∂c/∂t = ∇·(D∇c) − k·c + S from the field's current values; transient_dt=None
must remain the historical steady-state solve. Pinned here:

- pure first-order decay of a uniform zero-flux field reproduces the backward
  Euler value c0/(1 + k·dt) exactly (diffusion vanishes on a uniform field,
  so the PDE step degenerates to the scalar scheme);
- uniform production in a zero-flux domain integrates c0 + S·dt exactly and
  linearly in dt — the direct proof that transient_dt reaches the PDE, on the
  very configuration (pure-Neumann net production) whose STEADY solve is
  singular and historically froze or drifted;
- one transient step with an enormous dt converges to the steady-state
  solution of the same (nonsingular) problem — TransientTerm's V/dt diagonal
  vanishes — tying the two code paths to the same operator assembly;
- the steady default is untouched: its result is independent of the field's
  starting values (no time term), and the solve is non-vacuous.
"""
import sys
from pathlib import Path

import pytest

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

pytest.importorskip("fipy")

import numpy as np  # noqa: E402

from src.config.config import DiffusionConfig, DomainConfig, SubstanceConfig  # noqa: E402
from src.core.domain import MeshManager  # noqa: E402
from src.core.units import Concentration, Length  # noqa: E402
from src.simulation.multi_substance_simulator import MultiSubstanceSimulator  # noqa: E402

NX = NY = 5
CELL_UM = 20.0
SIZE = NX * CELL_UM
# 2D volumetric conversion applied by _create_source_field_from_reactions:
# rate [mol/s/cell] / (dx·dy) [m²] × adjustment(1.0) × 1000  →  mM/s
AREA_M2 = (CELL_UM * 1e-6) ** 2
VOL_RATE_PER_MOL_S = 1.0 / AREA_M2 * 1000.0


def _build_sim_2d(initial=1.0, boundary_type="fixed", decay_rate=0.0):
    domain = DomainConfig(
        dimensions=2,
        size_x=Length(SIZE, "um"), size_y=Length(SIZE, "um"),
        nx=NX, ny=NY, cell_height=Length(CELL_UM, "um"),
    )

    class Cfg:
        pass

    cfg = Cfg()
    cfg.domain = domain
    cfg.diffusion = DiffusionConfig()
    cfg.substances = {
        "Oxygen": SubstanceConfig(
            name="Oxygen", diffusion_coeff=1e-9,
            production_rate=0.0, uptake_rate=0.0,
            initial_value=Concentration(initial, "mM"),
            boundary_value=Concentration(initial, "mM"),
            boundary_type=boundary_type,
            decay_rate=decay_rate),
    }
    return MultiSubstanceSimulator(cfg, MeshManager(domain, verbose=False), verbose=False)


def _um(i, j):
    """Voxel (i, j) as a micrometer cell-center position. Deliberately NOT a
    bare grid index: the position-unit heuristic in
    _create_source_field_from_reactions derives the bio-grid size from a
    µm→m→µm round-trip (100 µm → 99.999… µm), which shrinks bio_grid_nx to 4
    on this 5-voxel fixture and misroutes index 4. Micrometer centers map
    bijectively."""
    return ((i + 0.5) * CELL_UM, (j + 0.5) * CELL_UM)


# Strong enough that the steady drawdown (~S·dx²/D ≈ 3e-3 mM) is far above the
# solver's relative-residual cutoff (the hardcoded 1e-6 tolerance makes FiPy
# return the initial guess untouched for weaker sources) — keeps the
# steady-vs-transient comparisons non-vacuous.
SINK_MOL_S = -3.0e-15
SINK = {_um(2, 2): {"Oxygen": SINK_MOL_S}}


def test_transient_pure_decay_matches_backward_euler():
    """Uniform zero-flux field, first-order decay k: one transient step of dt
    must land exactly on the implicit Euler value c0/(1 + k·dt)."""
    c0, k, dt = 2.0, 0.004, 100.0
    sim = _build_sim_2d(initial=c0, boundary_type="neumann", decay_rate=k)

    sim.update({}, transient_dt=dt)
    field = sim.state.substances["Oxygen"].concentrations
    assert np.allclose(field, c0 / (1.0 + k * dt), rtol=1e-9)

    # A second step compounds the same factor.
    sim.update({}, transient_dt=dt)
    field = sim.state.substances["Oxygen"].concentrations
    assert np.allclose(field, c0 / (1.0 + k * dt) ** 2, rtol=1e-9)


def test_transient_uniform_production_integrates_linearly_in_dt():
    """Zero-flux domain, the same production in every voxel: the field stays
    uniform and one implicit step lands exactly on c0 + S·dt, for any dt.
    This is the configuration whose STEADY solve is singular (pure Neumann
    with net production) — the transient step must integrate it exactly."""
    c0 = 1.0
    rate = 1.0e-16                                # mol/s/cell, production
    s_mm_per_s = rate * VOL_RATE_PER_MOL_S        # 2.5e-4 mM/s
    reactions = {_um(i, j): {"Oxygen": rate} for i in range(NX) for j in range(NY)}

    for dt in (50.0, 100.0):
        sim = _build_sim_2d(initial=c0, boundary_type="neumann")
        sim.update(reactions, transient_dt=dt)
        field = sim.state.substances["Oxygen"].concentrations
        assert np.allclose(field, c0 + s_mm_per_s * dt, rtol=1e-9), \
            f"dt={dt}: expected uniform {c0 + s_mm_per_s * dt}"


def test_transient_huge_dt_converges_to_steady_solution():
    """With dt → ∞ the TransientTerm diagonal vanishes, so one transient step
    must reproduce the steady-state solve of the identical problem."""
    steady = _build_sim_2d()
    steady.update(SINK)
    steady_field = steady.state.substances["Oxygen"].concentrations.copy()
    assert steady_field.min() < 1.0 - 1e-4, "steady solve must be non-vacuous"

    transient = _build_sim_2d()
    transient.update(SINK, transient_dt=1.0e30)
    transient_field = transient.state.substances["Oxygen"].concentrations.copy()

    assert np.allclose(transient_field, steady_field, rtol=1e-6, atol=1e-12)


def test_transient_dt_is_consumed():
    """A shorter step draws the sink voxel down less than a longer one, and a
    short step sits well above the steady state — dt actually reaches the PDE.
    (Diffusive time scale here is dx²/D ≈ 0.4 s, so use sub-second steps.)"""
    def min_after(dt_seconds):
        sim = _build_sim_2d()
        sim.update(SINK, transient_dt=dt_seconds)
        return float(sim.state.substances["Oxygen"].concentrations.min())

    min_short, min_long = min_after(0.05), min_after(0.4)
    assert min_short > min_long, "longer dt must draw the field down further"
    assert min_long < 1.0 - 1e-4

    steady = _build_sim_2d()
    steady.update(SINK)
    steady_min = float(steady.state.substances["Oxygen"].concentrations.min())
    assert min_short > steady_min + 1e-4, \
        "a 0.05 s transient step must not already sit at the steady state"


def test_steady_state_default_untouched():
    """transient_dt=None keeps the historical steady solve: the result is
    independent of the field's starting values (no time term)."""
    a = _build_sim_2d()
    a.update(SINK)
    a_field = a.state.substances["Oxygen"].concentrations
    assert a_field.min() < 1.0 - 1e-4, "steady solve must be non-vacuous"

    b = _build_sim_2d()
    b.state.substances["Oxygen"].concentrations[:] = 123.0  # scramble start
    b.fipy_variables["Oxygen"].setValue(123.0)
    b.update(SINK)

    assert np.allclose(a_field, b.state.substances["Oxygen"].concentrations,
                       rtol=1e-9)
