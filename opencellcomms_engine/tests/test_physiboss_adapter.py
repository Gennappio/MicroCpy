#!/usr/bin/env python3
"""
Tests for the PhysiBoss adapter.

Covers:
  1. Config loader dataclasses and XML parsing
  2. Substrate coupling (concentration → BN inputs, BN outputs → rates)
  3. Phenotype mapper (rates → stochastic fate decisions)
  4. Cycle model (stochastic phase transitions)
  5. Workflow functions (setup, treatment, run step, phenotype, division)
"""

import sys
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.physiboss.config_loader import (
    PhysiBossConfig,
    PhysiBossConfigLoader,
    DomainConfig,
    TimingConfig,
    SubstrateConfig,
    CellDefinitionConfig,
    IntracellularConfig,
    CouplingConfig,
    InputMapping,
    OutputMapping,
)
from src.adapters.physiboss.coupling import PhysiBossSubstrateCoupling
from src.adapters.physiboss.phenotype_mapper import PhysiBossPhenotypeMapper
from src.adapters.physiboss.cycle_model import CycleModel, Phase


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

@dataclass
class _MockCellState:
    """Lightweight cell state for workflow function tests."""
    id: str = "cell_0"
    position: Tuple[float, float] = (5.0, 5.0)
    phenotype: str = "Quiescent"
    age: float = 0.0
    division_count: int = 0
    gene_states: Dict[str, bool] = field(default_factory=dict)

    def with_updates(self, **kw):
        kw.pop("gene_network", None)
        return _MockCellState(
            id=self.id,
            position=kw.get("position", self.position),
            phenotype=kw.get("phenotype", self.phenotype),
            age=kw.get("age", self.age),
            division_count=kw.get("division_count", self.division_count),
            gene_states=kw.get("gene_states", dict(self.gene_states)),
        )


@dataclass
class _MockCell:
    state: _MockCellState = field(default_factory=_MockCellState)
    custom_functions: Any = None
    _physiboss_bn_outputs: Optional[Dict[str, float]] = None
    _physiboss_local_concs: Optional[Dict[str, float]] = None


@dataclass
class _MockPopulationState:
    cells: Dict[str, "_MockCell"] = field(default_factory=dict)
    total_cells: int = 0

    def with_updates(self, **kw):
        cells = kw.get("cells", self.cells)
        return _MockPopulationState(
            cells=cells,
            total_cells=kw.get("total_cells", len(cells)),
        )


@dataclass
class _MockPopulation:
    state: _MockPopulationState = field(default_factory=_MockPopulationState)


def _make_population(n: int = 5, phenotype: str = "Quiescent") -> _MockPopulation:
    """Create a small mock population."""
    cells = {}
    for i in range(n):
        cid = f"cell_{i}"
        cell = _MockCell(
            state=_MockCellState(id=cid, position=(float(i), float(i)), phenotype=phenotype)
        )
        cells[cid] = cell
    return _MockPopulation(state=_MockPopulationState(cells=cells, total_cells=n))


class _MockSimulator:
    """Simulator that returns fixed concentrations everywhere."""

    def __init__(self, concs: Dict[str, float]):
        self._concs = concs
        self.substances = list(concs.keys())

    def get_substance_concentration(self, name: str, x: float, y: float) -> float:
        return self._concs.get(name, 0.0)

    def get_all_concentrations_at(self, x: float, y: float) -> Dict[str, float]:
        return dict(self._concs)


SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<PhysiCell_settings version="devel-version">
  <domain>
    <x_min>-250</x_min><x_max>250</x_max>
    <y_min>-250</y_min><y_max>250</y_max>
    <z_min>-5</z_min><z_max>5</z_max>
    <dx>10</dx><dy>10</dy><dz>10</dz>
    <use_2D>true</use_2D>
  </domain>
  <overall>
    <max_time units="min">5040</max_time>
    <dt_diffusion units="min">0.02</dt_diffusion>
    <dt_mechanics units="min">0.1</dt_mechanics>
    <dt_phenotype units="min">6</dt_phenotype>
  </overall>
  <microenvironment_setup>
    <variable name="tnf" units="dimensionless" ID="0">
      <physical_parameter_set>
        <diffusion_coefficient units="micron^2/min">1200</diffusion_coefficient>
        <decay_rate units="1/min">0.002</decay_rate>
      </physical_parameter_set>
      <initial_condition units="dimensionless">0</initial_condition>
      <Dirichlet_boundary_condition units="dimensionless" enabled="true">0.5</Dirichlet_boundary_condition>
    </variable>
  </microenvironment_setup>
</PhysiCell_settings>
"""


# ===================================================================
# 1. Config Loader Tests
# ===================================================================

class TestConfigLoaderDataclasses:
    """Verify default values and construction of all dataclasses."""

    def test_domain_defaults(self):
        d = DomainConfig()
        assert d.x_min == -500.0
        assert d.dx == 20.0
        assert d.use_2D is True

    def test_timing_defaults(self):
        t = TimingConfig()
        assert t.max_time == 10080.0
        assert t.dt_diffusion == 0.01
        assert t.intracellular_dt == 12.0

    def test_substrate_config(self):
        s = SubstrateConfig(name="tnf", diffusion_coefficient=1200.0, decay_rate=0.002)
        assert s.name == "tnf"
        assert s.diffusion_coefficient == 1200.0
        assert s.dirichlet.enabled is False

    def test_input_mapping(self):
        im = InputMapping(substance_name="tnf", node_name="TNF", threshold=0.5)
        assert im.action == "activation"
        assert im.smoothing == 0.0

    def test_output_mapping(self):
        om = OutputMapping(node_name="Apoptosis", behaviour_name="apoptosis", value=1e6)
        assert om.base_value == 0.0
        assert om.action == "activation"

    def test_coupling_config(self):
        cc = CouplingConfig(
            inputs=[InputMapping(substance_name="tnf", node_name="TNF", threshold=0.5)],
            outputs=[OutputMapping(node_name="Apoptosis", behaviour_name="apoptosis", value=100)],
        )
        assert len(cc.inputs) == 1
        assert len(cc.outputs) == 1

    def test_intracellular_config(self):
        ic = IntracellularConfig(bnd_file="model.bnd", cfg_file="model.cfg")
        assert ic.intracellular_dt == 12.0
        assert ic.inheritance_global == 1.0

    def test_cell_definition_config(self):
        cd = CellDefinitionConfig(name="tumor")
        assert cd.name == "tumor"
        assert cd.intracellular is None
        assert cd.death_models == []

    def test_physiboss_config_convenience_accessors(self):
        ic = IntracellularConfig(bnd_file="m.bnd", cfg_file="m.cfg")
        cd = CellDefinitionConfig(name="tumor", intracellular=ic)
        cfg = PhysiBossConfig(cell_definitions=[cd])
        assert cfg.intracellular is ic
        assert cfg.coupling is ic.coupling

    def test_physiboss_config_no_intracellular(self):
        cfg = PhysiBossConfig()
        assert cfg.intracellular is None
        assert cfg.coupling is None


class TestConfigLoaderXMLParsing:
    """Test XML parsing with a minimal inline XML config."""

    @pytest.fixture()
    def xml_file(self, tmp_path):
        p = tmp_path / "test_config.xml"
        p.write_text(SAMPLE_XML)
        return p

    def test_load_domain(self, xml_file):
        cfg = PhysiBossConfigLoader(str(xml_file)).load()
        assert cfg.domain.x_min == -250.0
        assert cfg.domain.x_max == 250.0
        assert cfg.domain.dx == 10.0
        assert cfg.domain.use_2D is True

    def test_load_timing(self, xml_file):
        cfg = PhysiBossConfigLoader(str(xml_file)).load()
        assert cfg.timing.max_time == 5040.0
        assert cfg.timing.dt_diffusion == 0.02
        assert cfg.timing.dt_phenotype == 6.0

    def test_load_substrates(self, xml_file):
        cfg = PhysiBossConfigLoader(str(xml_file)).load()
        assert len(cfg.substrates) == 1
        tnf = cfg.substrates[0]
        assert tnf.name == "tnf"
        assert tnf.diffusion_coefficient == 1200.0
        assert tnf.decay_rate == 0.002
        assert tnf.initial_condition == 0.0
        assert tnf.dirichlet.enabled is True
        assert tnf.dirichlet.value == 0.5


# ===================================================================
# 2. Coupling Tests
# ===================================================================

class TestPhysiBossSubstrateCoupling:
    """Test bidirectional substance ↔ BN coupling logic."""

    def _make_coupling(self, **kw):
        inputs = kw.get("inputs", [
            InputMapping(substance_name="tnf", node_name="TNF", threshold=0.5),
        ])
        outputs = kw.get("outputs", [
            OutputMapping(
                node_name="Apoptosis",
                behaviour_name="apoptosis",
                value=1e6,
                base_value=0.0,
            ),
        ])
        return PhysiBossSubstrateCoupling(inputs=inputs, outputs=outputs)

    # -- compute_bn_inputs ---------------------------------------------------

    def test_activation_above_threshold(self):
        c = self._make_coupling()
        result = c.compute_bn_inputs({"tnf": 1.0})
        assert result == {"TNF": True}

    def test_activation_below_threshold(self):
        c = self._make_coupling()
        result = c.compute_bn_inputs({"tnf": 0.1})
        assert result == {"TNF": False}

    def test_activation_at_threshold(self):
        c = self._make_coupling()
        result = c.compute_bn_inputs({"tnf": 0.5})
        assert result == {"TNF": True}

    def test_missing_substance_defaults_to_zero(self):
        c = self._make_coupling()
        result = c.compute_bn_inputs({})
        assert result == {"TNF": False}

    def test_inhibition_flips(self):
        c = self._make_coupling(inputs=[
            InputMapping(
                substance_name="tnf", node_name="TNF",
                threshold=0.5, action="inhibition",
            ),
        ])
        result = c.compute_bn_inputs({"tnf": 1.0})
        assert result == {"TNF": False}

    def test_hill_smoothing(self):
        c = self._make_coupling(inputs=[
            InputMapping(
                substance_name="tnf", node_name="TNF",
                threshold=0.5, smoothing=2.0,
            ),
        ])
        # conc = 1.0, threshold = 0.5, n=2: ratio = 4, prob = 4/5 = 0.8 > 0.5
        assert c.compute_bn_inputs({"tnf": 1.0}) == {"TNF": True}
        # conc = 0.1: ratio = (0.2)^2 = 0.04, prob = 0.04/1.04 ≈ 0.038 < 0.5
        assert c.compute_bn_inputs({"tnf": 0.1}) == {"TNF": False}

    def test_inact_threshold_hysteresis(self):
        c = self._make_coupling(inputs=[
            InputMapping(
                substance_name="tnf", node_name="TNF",
                threshold=0.5, inact_threshold=0.3,
            ),
        ])
        # Above threshold → True
        assert c.compute_bn_inputs({"tnf": 0.6})["TNF"] is True
        # Below inact_threshold → forced False
        assert c.compute_bn_inputs({"tnf": 0.2})["TNF"] is False
        # Between inact and threshold → False (below threshold)
        assert c.compute_bn_inputs({"tnf": 0.4})["TNF"] is False

    # -- apply_phenotype_outputs --------------------------------------------

    def test_output_binary_active(self):
        c = self._make_coupling()
        rates = c.apply_phenotype_outputs({"Apoptosis": 0.8}, {})
        assert rates["apoptosis"] == 1e6

    def test_output_binary_inactive(self):
        c = self._make_coupling()
        rates = c.apply_phenotype_outputs({"Apoptosis": 0.3}, {})
        assert rates["apoptosis"] == 0.0

    def test_output_smoothing(self):
        c = self._make_coupling(outputs=[
            OutputMapping(
                node_name="Apoptosis", behaviour_name="apoptosis",
                value=100.0, base_value=10.0, smoothing=1.0,
            ),
        ])
        rates = c.apply_phenotype_outputs({"Apoptosis": 0.5}, {})
        # rate = 10 + 0.5*(100-10) = 55
        assert rates["apoptosis"] == pytest.approx(55.0)

    def test_output_inhibition(self):
        c = self._make_coupling(outputs=[
            OutputMapping(
                node_name="Apoptosis", behaviour_name="apoptosis",
                value=100.0, base_value=0.0, action="inhibition",
            ),
        ])
        # node ON (prob=0.8) + inhibition → rate = value+base-value = 0
        rates = c.apply_phenotype_outputs({"Apoptosis": 0.8}, {})
        assert rates["apoptosis"] == 0.0

    def test_from_config(self):
        cc = CouplingConfig(
            inputs=[InputMapping(substance_name="x", node_name="X", threshold=1.0)],
            outputs=[OutputMapping(node_name="Y", behaviour_name="y", value=5.0)],
        )
        coupling = PhysiBossSubstrateCoupling.from_config(cc)
        assert len(coupling.inputs) == 1
        assert len(coupling.outputs) == 1



# ===================================================================
# 3. Phenotype Mapper Tests
# ===================================================================

class TestPhysiBossPhenotypeMapper:
    """Test stochastic rate-to-phenotype conversion."""

    def test_no_rates_keeps_phenotype(self):
        m = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        assert m.apply_rates({}, "Quiescent") == "Quiescent"

    def test_zero_rates_keeps_phenotype(self):
        m = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        rates = {"apoptosis": 0.0, "necrosis": 0.0, "proliferation": 0.0}
        assert m.apply_rates(rates, "Quiescent") == "Quiescent"

    def test_dead_cells_stay_dead(self):
        m = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        rates = {"apoptosis": 1e10}
        assert m.apply_rates(rates, "apoptotic") == "apoptotic"
        assert m.apply_rates(rates, "necrotic") == "necrotic"
        assert m.apply_rates(rates, "dead") == "dead"

    def test_high_apoptosis_rate_triggers_death(self):
        random.seed(42)
        m = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        result = m.apply_rates({"apoptosis": 1e6}, "Quiescent")
        assert result == "apoptotic"

    def test_high_necrosis_rate_triggers_death(self):
        random.seed(42)
        m = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        result = m.apply_rates({"necrosis": 1e6}, "Quiescent")
        assert result == "necrotic"

    def test_necrosis_has_priority_over_apoptosis(self):
        random.seed(42)
        m = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        result = m.apply_rates(
            {"necrosis": 1e6, "apoptosis": 1e6}, "Quiescent"
        )
        assert result == "necrotic"

    def test_high_proliferation_rate(self):
        random.seed(42)
        m = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        result = m.apply_rates({"proliferation": 1e6}, "Quiescent")
        assert result == "Proliferation"

    def test_statistical_correctness(self):
        """Low rate should trigger probabilistically, not always."""
        random.seed(123)
        m = PhysiBossPhenotypeMapper(dt_phenotype=1.0)
        triggered = sum(
            1
            for _ in range(1000)
            if m.apply_rates({"apoptosis": 0.01}, "Quiescent") == "apoptotic"
        )
        assert 1 <= triggered <= 50


# ===================================================================
# 4. Cycle Model Tests
# ===================================================================

class TestCycleModel:
    """Test stochastic cell-cycle phase transitions."""

    def test_default_cycle_model(self):
        cfg = type("C", (), {"phase_durations": [], "phase_transition_rates": []})()
        cm = CycleModel.from_config(cfg)
        assert len(cm.phases) == 2

    def test_from_durations(self):
        cfg = type("C", (), {"phase_durations": [300, 480], "phase_transition_rates": []})()
        cm = CycleModel.from_config(cfg)
        assert len(cm.phases) == 2
        assert cm.phases[0].duration == 300
        assert cm.phases[1].duration == 480

    def test_from_rates(self):
        cfg = type("C", (), {"phase_durations": [], "phase_transition_rates": [0.01, 0.002]})()
        cm = CycleModel.from_config(cfg)
        assert len(cm.phases) == 2
        assert cm.phases[0].duration == pytest.approx(100.0)
        assert cm.phases[1].duration == pytest.approx(500.0)

    def test_fixed_duration_advances(self):
        cm = CycleModel(phases=[
            Phase(name="G1", index=0, duration=10.0, fixed_duration=True),
            Phase(name="S", index=1, duration=10.0, fixed_duration=True),
        ])
        div, rem = cm.advance(9.0)
        assert cm.current_phase_index == 0
        assert not div and not rem
        div, rem = cm.advance(2.0)
        assert cm.current_phase_index == 1
        assert cm.elapsed_time == 0.0

    def test_division_at_exit(self):
        cm = CycleModel(phases=[
            Phase(name="G1", index=0, duration=5.0, fixed_duration=True, division_at_exit=True),
            Phase(name="G0", index=1, duration=100.0, fixed_duration=True),
        ])
        div, rem = cm.advance(6.0)
        assert div is True
        assert rem is False

    def test_removal_at_exit(self):
        cm = CycleModel(phases=[
            Phase(name="dying", index=0, duration=5.0, fixed_duration=True, removal_at_exit=True),
        ])
        div, rem = cm.advance(6.0)
        assert div is False
        assert rem is True

    def test_phase_wraps_around(self):
        cm = CycleModel(phases=[
            Phase(name="A", index=0, duration=1.0, fixed_duration=True),
            Phase(name="B", index=1, duration=1.0, fixed_duration=True),
        ])
        cm.advance(2.0)
        assert cm.current_phase_index == 1
        cm.advance(2.0)
        assert cm.current_phase_index == 0

    def test_reset(self):
        cm = CycleModel(phases=[Phase(name="X", index=0, duration=10.0)])
        cm.advance(5.0)
        cm.reset()
        assert cm.current_phase_index == 0
        assert cm.elapsed_time == 0.0

    def test_copy_independence(self):
        cm = CycleModel(phases=[Phase(name="A", index=0, duration=10.0)])
        cm.advance(3.0)
        cm2 = cm.copy()
        cm2.advance(5.0)
        assert cm.elapsed_time == pytest.approx(3.0)
        assert cm2.elapsed_time == pytest.approx(8.0)


# ===================================================================
# 5. Workflow Function Tests (unit-level, no MaBoSS required)
# ===================================================================

class TestApplyPhysiBossPhenotype:
    """Test the apply_physiboss_phenotype workflow function."""

    def test_no_population_is_noop(self):
        from src.workflow.functions.intercellular.apply_physiboss_phenotype import (
            apply_physiboss_phenotype,
        )
        ctx = {}
        apply_physiboss_phenotype(ctx)  # should not raise

    def test_applies_apoptosis(self):
        from src.workflow.functions.intercellular.apply_physiboss_phenotype import (
            apply_physiboss_phenotype,
        )
        random.seed(42)
        pop = _make_population(3)
        coupling = PhysiBossSubstrateCoupling(
            inputs=[],
            outputs=[
                OutputMapping(
                    node_name="Apoptosis", behaviour_name="apoptosis",
                    value=1e6, base_value=0.0,
                ),
            ],
        )
        mapper = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        pb_config = PhysiBossConfig(timing=TimingConfig(dt_phenotype=6.0))

        # Give all cells BN outputs with Apoptosis ON
        for cell in pop.state.cells.values():
            cell._physiboss_bn_outputs = {"Apoptosis": 0.9}

        ctx = {
            "population": pop,
            "physiboss_coupling": coupling,
            "physiboss_phenotype_mapper": mapper,
            "physiboss_config": pb_config,
            "log_verbose": False,
        }
        apply_physiboss_phenotype(ctx)

        # All cells should now be apoptotic (rate=1e6 → probability≈1)
        for cell in pop.state.cells.values():
            assert cell.state.phenotype == "apoptotic"

    def test_skips_dead_cells(self):
        from src.workflow.functions.intercellular.apply_physiboss_phenotype import (
            apply_physiboss_phenotype,
        )
        pop = _make_population(1, phenotype="necrotic")
        for cell in pop.state.cells.values():
            cell._physiboss_bn_outputs = {"Apoptosis": 0.9}

        coupling = PhysiBossSubstrateCoupling(
            inputs=[],
            outputs=[OutputMapping(node_name="Apoptosis", behaviour_name="apoptosis", value=1e6)],
        )
        mapper = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        pb_config = PhysiBossConfig(timing=TimingConfig(dt_phenotype=6.0))

        ctx = {
            "population": pop,
            "physiboss_coupling": coupling,
            "physiboss_phenotype_mapper": mapper,
            "physiboss_config": pb_config,
        }
        apply_physiboss_phenotype(ctx)
        # Should remain necrotic, not change to apoptotic
        for cell in pop.state.cells.values():
            assert cell.state.phenotype == "necrotic"


class TestPhysiBossCellDivision:
    """Test the physiboss_cell_division workflow function."""

    def test_no_population_is_noop(self):
        from src.workflow.functions.intercellular.physiboss_cell_division import (
            physiboss_cell_division,
        )
        ctx = {}
        physiboss_cell_division(ctx)  # should not raise

    def test_divides_proliferating_cells(self):
        from src.workflow.functions.intercellular.physiboss_cell_division import (
            physiboss_cell_division,
        )
        pop = _make_population(2, phenotype="Proliferation")
        # Give cells gene states to inherit
        for cell in pop.state.cells.values():
            cell.state = cell.state.with_updates(gene_states={"TNF": True, "Apoptosis": False})

        ctx = {
            "population": pop,
            "dimensions": 2,
        }
        physiboss_cell_division(ctx)

        # Should now have 4 cells (2 parents + 2 daughters)
        assert len(pop.state.cells) == 4
        # Parents should be reset to Quiescent
        quiescent_count = sum(
            1 for c in pop.state.cells.values() if c.state.phenotype == "Quiescent"
        )
        assert quiescent_count == 4  # both parents and daughters are Quiescent

    def test_does_not_divide_quiescent(self):
        from src.workflow.functions.intercellular.physiboss_cell_division import (
            physiboss_cell_division,
        )
        pop = _make_population(3, phenotype="Quiescent")
        ctx = {"population": pop, "dimensions": 2}
        physiboss_cell_division(ctx)
        assert len(pop.state.cells) == 3

    def test_inheritance_fraction_full(self):
        from src.workflow.functions.intercellular.physiboss_cell_division import (
            physiboss_cell_division,
        )
        random.seed(42)
        pop = _make_population(1, phenotype="Proliferation")
        parent = list(pop.state.cells.values())[0]
        parent.state = parent.state.with_updates(gene_states={"A": True, "B": False, "C": True})

        ctx = {"population": pop, "dimensions": 2}
        physiboss_cell_division(ctx, inheritance_fraction=1.0)

        daughters = [c for c in pop.state.cells.values() if c.state.age == 0.0]
        assert len(daughters) >= 1
        for d in daughters:
            # Full inheritance: daughter has exact same gene states
            assert d.state.gene_states == {"A": True, "B": False, "C": True}


class TestPhysiBossTreatment:
    """Test the physiboss_treatment workflow function."""

    def test_treatment_off_before_start(self):
        from src.workflow.functions.initialization.physiboss_treatment import (
            physiboss_treatment,
        )
        ctx = {"current_step": 0, "dt": 1.0}
        physiboss_treatment(ctx, substrate="tnf", start_time=100.0, period=60.0, duration=30.0)
        state = ctx.get("physiboss_treatment_state", {})
        assert state.get("tnf") is False

    def test_treatment_on_during_active_phase(self):
        from src.workflow.functions.initialization.physiboss_treatment import (
            physiboss_treatment,
        )
        ctx = {"current_step": 110, "dt": 1.0}
        physiboss_treatment(ctx, substrate="tnf", start_time=100.0, period=60.0, duration=30.0)
        state = ctx.get("physiboss_treatment_state", {})
        assert state.get("tnf") is True

    def test_treatment_off_during_rest_phase(self):
        from src.workflow.functions.initialization.physiboss_treatment import (
            physiboss_treatment,
        )
        # t=145, start=100, period=60, duration=30
        # time_in_cycle = (145-100) % 60 = 45 >= 30 → OFF
        ctx = {"current_step": 145, "dt": 1.0}
        physiboss_treatment(ctx, substrate="tnf", start_time=100.0, period=60.0, duration=30.0)
        state = ctx.get("physiboss_treatment_state", {})
        assert state.get("tnf") is False


# ===================================================================
# 6. CellContainer Tests
# ===================================================================

class TestCellContainer:
    """Test NumPy SoA CellContainer core operations."""

    def test_create_empty(self):
        from src.biology.cell_container import CellContainer
        c = CellContainer(capacity=128, dimensions=2)
        assert c.count == 0
        assert c.capacity == 128
        assert c.dims == 2
        assert len(c) == 0

    def test_add_single_cell(self):
        from src.biology.cell_container import CellContainer, phenotype_id
        c = CellContainer(capacity=16, dimensions=2)
        idx = c.add_cell(position=(10.0, 20.0), phenotype="Quiescent")
        assert idx == 0
        assert c.count == 1
        assert c.n == 1
        assert c.positions[0, 0] == pytest.approx(10.0)
        assert c.positions[0, 1] == pytest.approx(20.0)
        assert c.phenotype_ids[0] == phenotype_id("Quiescent")
        assert c.alive[0] == True

    def test_add_multiple_cells(self):
        import numpy as np
        from src.biology.cell_container import CellContainer
        c = CellContainer(capacity=16, dimensions=3)
        positions = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.float64)
        indices = c.add_cells(positions, phenotype="Quiescent")
        assert len(indices) == 3
        assert c.count == 3
        assert c.n == 3
        np.testing.assert_array_equal(c.positions[0], [1, 2, 3])
        np.testing.assert_array_equal(c.positions[2], [7, 8, 9])

    def test_kill_and_compact(self):
        import numpy as np
        from src.biology.cell_container import CellContainer
        c = CellContainer(capacity=16, dimensions=2)
        for i in range(5):
            c.add_cell(position=(float(i), 0.0))
        assert c.count == 5

        # Kill cells 1 and 3
        mask = np.array([False, True, False, True, False])
        killed = c.kill(mask)
        assert killed == 2
        assert c.n == 3  # 5 - 2 alive

        # Compact
        index_map = c.compact()
        assert c.count == 3
        assert c.n == 3
        # Surviving cells: 0, 2, 4 → new indices 0, 1, 2
        assert c.positions[0, 0] == pytest.approx(0.0)
        assert c.positions[1, 0] == pytest.approx(2.0)
        assert c.positions[2, 0] == pytest.approx(4.0)

    def test_auto_grow(self):
        from src.biology.cell_container import CellContainer
        c = CellContainer(capacity=4, dimensions=2)
        for i in range(10):
            c.add_cell(position=(float(i), 0.0))
        assert c.count == 10
        assert c.capacity >= 10

    def test_float_column(self):
        import numpy as np
        from src.biology.cell_container import CellContainer
        c = CellContainer(capacity=16, dimensions=2)
        c.add_float_column("apoptosis_rate", default=0.0)
        c.add_cell(position=(0, 0))
        c.add_cell(position=(1, 1))
        c.get_float("apoptosis_rate")[0] = 1e6
        c.get_float("apoptosis_rate")[1] = 0.0
        assert c.get_float("apoptosis_rate")[0] == 1e6
        assert c.has_column("apoptosis_rate")

    def test_bool_column(self):
        from src.biology.cell_container import CellContainer
        c = CellContainer(capacity=16, dimensions=2)
        c.add_bool_column("TNF_node", default=False)
        c.add_cell(position=(0, 0))
        c.get_bool("TNF_node")[0] = True
        assert c.get_bool("TNF_node")[0] == True

    def test_phenotype_counts(self):
        from src.biology.cell_container import CellContainer, phenotype_id
        c = CellContainer(capacity=16, dimensions=2)
        c.add_cell(position=(0, 0), phenotype="Quiescent")
        c.add_cell(position=(1, 0), phenotype="Quiescent")
        c.add_cell(position=(2, 0), phenotype="apoptotic")
        counts = c.phenotype_counts()
        assert counts["Quiescent"] == 2
        assert counts["apoptotic"] == 1

    def test_iteration(self):
        from src.biology.cell_container import CellContainer
        c = CellContainer(capacity=16, dimensions=2)
        for i in range(3):
            c.add_cell(position=(float(i), 0.0), phenotype="Quiescent")
        views = list(c)
        assert len(views) == 3
        assert views[0].state.phenotype == "Quiescent"
        assert views[1].state.position[0] == pytest.approx(1.0)

    def test_to_dict(self):
        from src.biology.cell_container import CellContainer
        c = CellContainer(capacity=16, dimensions=2)
        c.add_cell(position=(5, 10), phenotype="Quiescent")
        d = c.to_dict()
        assert len(d["positions"]) == 1
        assert d["phenotypes"] == ["Quiescent"]


class TestCellView:
    """Test CellView backward-compatible proxy."""

    def test_read_properties(self):
        from src.biology.cell_container import CellContainer, phenotype_id
        from src.biology.cell_view import CellView
        c = CellContainer(capacity=16, dimensions=2)
        c.add_cell(position=(3.0, 7.0), phenotype="Quiescent")
        v = CellView(c, 0)
        assert v.state.position[0] == pytest.approx(3.0)
        assert v.state.position[1] == pytest.approx(7.0)
        assert v.state.phenotype == "Quiescent"
        assert v.state.age == 0.0

    def test_write_through(self):
        from src.biology.cell_container import CellContainer, phenotype_id
        from src.biology.cell_view import CellView
        c = CellContainer(capacity=16, dimensions=2)
        c.add_cell(position=(0, 0), phenotype="Quiescent")
        v = CellView(c, 0)
        v.state.phenotype = "apoptotic"
        assert c.phenotype_ids[0] == phenotype_id("apoptotic")
        v.state.age = 42.0
        assert c.ages[0] == pytest.approx(42.0)

    def test_with_updates(self):
        from src.biology.cell_container import CellContainer, phenotype_id
        from src.biology.cell_view import CellView
        c = CellContainer(capacity=16, dimensions=2)
        c.add_cell(position=(0, 0), phenotype="Quiescent")
        v = CellView(c, 0)
        v.state.with_updates(phenotype="necrotic", age=10.0)
        assert c.phenotype_ids[0] == phenotype_id("necrotic")
        assert c.ages[0] == pytest.approx(10.0)

    def test_gene_states(self):
        from src.biology.cell_container import CellContainer
        from src.biology.cell_view import CellView
        c = CellContainer(capacity=16, dimensions=2)
        c.add_bool_column("TNF", default=False)
        c.add_bool_column("Apoptosis", default=False)
        c.add_cell(position=(0, 0))
        v = CellView(c, 0)
        v.state.gene_states = {"TNF": True, "Apoptosis": False}
        assert c.get_bool("TNF")[0] == True
        assert c.get_bool("Apoptosis")[0] == False
        assert v.state.gene_states == {"TNF": True, "Apoptosis": False}



# ---------------------------------------------------------------------------
# PhysiCell Mechanics (C++ / NumPy fallback)
# ---------------------------------------------------------------------------

class TestMechanicsKernel:
    """Verify the C++/NumPy mechanics kernels give identical results."""

    def _two_cells(self, dx):
        import numpy as np
        pos = np.array([[0.0, 0.0, 0.0], [dx, 0.0, 0.0]], dtype=np.float64)
        radii = np.array([8.0, 8.0], dtype=np.float64)
        alive = np.array([True, True])
        rep = np.array([10.0, 10.0], dtype=np.float64)
        adh = np.array([0.0, 0.0], dtype=np.float64)
        max_adh = np.array([10.0, 10.0], dtype=np.float64)
        vel = np.zeros((2, 3), dtype=np.float64)
        vp = np.zeros((2, 3), dtype=np.float64)
        press = np.zeros(2, dtype=np.float64)
        return pos, radii, alive, rep, adh, max_adh, vel, vp, press

    def test_fallback_pure_repulsion(self):
        from src.adapters.physicell_mechanics.fallback import update_velocities_numpy
        pos, radii, alive, rep, adh, max_adh, vel, vp, press = self._two_cells(12.0)
        update_velocities_numpy(pos, radii, alive, rep, adh, max_adh, vel, press)
        # Expected: (1 - 12/16)^2 * sqrt(10*10) = 0.0625 * 10 = 0.625
        assert vel[0, 0] == pytest.approx(-0.625, abs=1e-6)
        assert vel[1, 0] == pytest.approx(+0.625, abs=1e-6)
        assert press[0] > 0

    def test_fallback_far_apart_zero(self):
        from src.adapters.physicell_mechanics.fallback import update_velocities_numpy
        pos, radii, alive, rep, adh, max_adh, vel, vp, press = self._two_cells(100.0)
        update_velocities_numpy(pos, radii, alive, rep, adh, max_adh, vel, press)
        assert vel[0, 0] == pytest.approx(0.0)
        assert vel[1, 0] == pytest.approx(0.0)

    def test_fallback_adhesion_dominates(self):
        import numpy as np
        from src.adapters.physicell_mechanics.fallback import update_velocities_numpy
        pos, radii, alive, rep, _, _, vel, _, press = self._two_cells(14.0)
        adh = np.array([5.0, 5.0], dtype=np.float64)
        max_adh = np.array([10.0, 10.0], dtype=np.float64)  # S = 20
        update_velocities_numpy(pos, radii, alive, rep, adh, max_adh, vel, press)
        # rep = (1-14/16)^2 * 10 = 0.15625; adh = (1-14/20)^2 * 5 = 0.45; net = -0.294
        assert vel[1, 0] == pytest.approx(-0.29375, abs=1e-6)
        assert vel[0, 0] == pytest.approx(+0.29375, abs=1e-6)

    def test_fallback_adams_bashforth_first_step(self):
        import numpy as np
        from src.adapters.physicell_mechanics.fallback import update_mechanics_numpy
        pos, radii, alive, rep, adh, max_adh, vel, vp, press = self._two_cells(12.0)
        update_mechanics_numpy(pos, radii, alive, rep, adh, max_adh,
                               vel, vp, press, 0.1,
                               -100, -100, -100, 100, 100, 100, True)
        # First step: x_new = x + dt*(1.5*v - 0.5*0) = x + 0.15*v
        assert pos[0, 0] == pytest.approx(-0.09375, abs=1e-6)
        assert pos[1, 0] == pytest.approx(+12.09375, abs=1e-6)
        # velocities_prev stores current velocities
        assert vp[0, 0] == pytest.approx(-0.625, abs=1e-6)

    def test_cxx_matches_fallback(self):
        """If the C++ extension is built, it must match the NumPy fallback."""
        import numpy as np
        from src.adapters.physicell_mechanics import get_extension
        from src.adapters.physicell_mechanics.fallback import update_mechanics_numpy

        ext = get_extension()
        if ext is None:
            pytest.skip("C++ extension not built")

        rng = np.random.default_rng(42)
        N = 20
        pos_cxx = rng.uniform(-30, 30, (N, 3)).astype(np.float64)
        pos_np = pos_cxx.copy()
        radii = np.full(N, 8.0, dtype=np.float64)
        alive = np.ones(N, dtype=np.bool_)
        rep = np.full(N, 10.0, dtype=np.float64)
        adh = np.full(N, 0.4, dtype=np.float64)
        max_adh = np.full(N, 10.0, dtype=np.float64)

        vel_cxx = np.zeros((N, 3), dtype=np.float64)
        vp_cxx = np.zeros((N, 3), dtype=np.float64)
        press_cxx = np.zeros(N, dtype=np.float64)

        vel_np = np.zeros((N, 3), dtype=np.float64)
        vp_np = np.zeros((N, 3), dtype=np.float64)
        press_np = np.zeros(N, dtype=np.float64)

        ext.update_mechanics(pos_cxx, radii, alive, rep, adh, max_adh,
                             vel_cxx, vp_cxx, press_cxx, 0.1,
                             -100, -100, -100, 100, 100, 100, 8.5, False)
        update_mechanics_numpy(pos_np, radii, alive, rep, adh, max_adh,
                               vel_np, vp_np, press_np, 0.1,
                               -100, -100, -100, 100, 100, 100, False)

        assert np.allclose(pos_cxx, pos_np, atol=1e-6)
        assert np.allclose(vel_cxx, vel_np, atol=1e-6)
        assert np.allclose(press_cxx, press_np, atol=1e-6)


class TestMechanicsWorkflow:
    """Test the update_mechanics_physicell workflow function."""

    def _make_context(self, n_cells=4, dx=12.0, dims=3):
        from src.biology.cell_container import CellContainer
        import numpy as np
        c = CellContainer(capacity=32, dimensions=dims)
        for i in range(n_cells):
            pos = [i * dx, 0.0] + ([0.0] if dims == 3 else [])
            c.add_cell(position=tuple(pos), phenotype="Quiescent")
        return {"cell_container": c, "dt": 0.1, "dimensions": dims}

    def test_runs_on_container(self):
        from src.workflow.functions.intercellular.update_mechanics_physicell import (
            update_mechanics_physicell,
        )
        ctx = self._make_context(n_cells=4, dx=12.0)
        ok = update_mechanics_physicell(ctx, dt=0.1, use_fallback=True)
        assert ok is True
        # positions should have moved (repulsion)
        c = ctx["cell_container"]
        assert abs(c.positions[0, 0] - 0.0) > 1e-6 or abs(c.positions[1, 0] - 12.0) > 1e-6

    def test_creates_mechanics_state(self):
        from src.workflow.functions.intercellular.update_mechanics_physicell import (
            update_mechanics_physicell,
        )
        ctx = self._make_context(n_cells=2, dx=12.0)
        update_mechanics_physicell(ctx, use_fallback=True)
        assert "mechanics" in ctx
        assert ctx["mechanics"]["velocities"].shape[1] == 3

    def test_lazy_columns(self):
        from src.workflow.functions.intercellular.update_mechanics_physicell import (
            update_mechanics_physicell,
        )
        ctx = self._make_context(n_cells=2)
        update_mechanics_physicell(ctx, use_fallback=True)
        c = ctx["cell_container"]
        assert c.has_column("repulsion_strength")
        assert c.has_column("adhesion_strength")
        assert c.has_column("max_adh_distance")
        assert c.has_column("pressure")

    def test_no_container_returns_false(self):
        from src.workflow.functions.intercellular.update_mechanics_physicell import (
            update_mechanics_physicell,
        )
        ok = update_mechanics_physicell({"dt": 0.1}, use_fallback=True)
        assert ok is False




# ---------------------------------------------------------------------------
# End-to-end TNF tutorial integration test (Phase 3.9)
# ---------------------------------------------------------------------------

class TestTNFTutorialIntegration:
    """
    Runs the full coupling → phenotype → mechanics pipeline on a small
    CellContainer with a mocked MaBoSS output (TNF-ON drives Apoptosis≈0.7,
    NonACD≈0.3, matching 1_Long_TNF.xml behaviour).

    Verifies invariants that must hold regardless of randomness:
    * total cell count is conserved (no cell is lost silently)
    * high TNF monotonically drives apoptotic fraction upward
    * zero TNF leaves the population quiescent
    * mechanics step keeps all cells inside the domain
    """

    def _build_context(self, n_cells=80, tnf_level=10.0, seed=42, dims=2):
        """Build a minimal context: CellContainer + coupling + mapper."""
        import numpy as np
        from src.biology.cell_container import CellContainer
        from src.adapters.physiboss.coupling import PhysiBossSubstrateCoupling
        from src.adapters.physiboss.phenotype_mapper import PhysiBossPhenotypeMapper
        from src.adapters.physiboss.config_loader import (
            PhysiBossConfig, TimingConfig, InputMapping, OutputMapping,
        )

        rng = np.random.default_rng(seed)
        container = CellContainer(capacity=n_cells * 2, dimensions=dims)

        # Cells on a disc (r=200 um)
        angles = rng.uniform(0, 2 * np.pi, n_cells)
        radii_arr = 200.0 * np.sqrt(rng.uniform(0, 1, n_cells))
        if dims == 2:
            positions = np.column_stack([radii_arr * np.cos(angles),
                                         radii_arr * np.sin(angles)])
        else:
            positions = np.column_stack([radii_arr * np.cos(angles),
                                         radii_arr * np.sin(angles),
                                         np.zeros(n_cells)])
        container.add_cells(positions, phenotype="Quiescent")

        # Pre-register BN output columns (apply_physiboss_phenotype reads these)
        container.add_float_column("bn_prob_Apoptosis", default=0.0)
        container.add_float_column("bn_prob_NonACD", default=0.0)

        coupling = PhysiBossSubstrateCoupling(
            inputs=[InputMapping(substance_name="TNF", node_name="TNF",
                                 threshold=1.0, action="activation")],
            outputs=[
                OutputMapping(node_name="Apoptosis", behaviour_name="apoptosis",
                              value=1e6, base_value=0.0, action="activation"),
                OutputMapping(node_name="NonACD", behaviour_name="necrosis",
                              value=1e6, base_value=0.0, action="activation"),
            ],
        )
        mapper = PhysiBossPhenotypeMapper(dt_phenotype=6.0)
        pb_config = PhysiBossConfig(timing=TimingConfig(dt_phenotype=6.0))

        ctx = {
            "cell_container": container,
            "physiboss_coupling": coupling,
            "physiboss_phenotype_mapper": mapper,
            "physiboss_config": pb_config,
            "dt": 6.0,
            "dimensions": dims,
            "_tnf_level": tnf_level,
        }
        return ctx

    def _step_pipeline(self, ctx, n_steps):
        """Run `n_steps` of (mock MaBoSS → phenotype → mechanics)."""
        import numpy as np
        from src.workflow.functions.intercellular.apply_physiboss_phenotype import (
            apply_physiboss_phenotype,
        )
        from src.workflow.functions.intercellular.update_mechanics_physicell import (
            update_mechanics_physicell,
        )

        container = ctx["cell_container"]
        coupling = ctx["physiboss_coupling"]
        tnf = ctx["_tnf_level"]

        for _ in range(n_steps):
            N = container.count
            if N == 0:
                break
            # ---- mock MaBoSS: TNF concentration → BN inputs → fate probs ----
            tnf_arr = np.full(N, tnf, dtype=np.float64)
            bn_inputs = coupling.compute_bn_inputs_vectorized({"TNF": tnf_arr})
            tnf_on = bn_inputs.get("TNF", np.zeros(N, dtype=np.bool_))
            container.get_float("bn_prob_Apoptosis")[:N] = np.where(tnf_on, 0.7, 0.0)
            container.get_float("bn_prob_NonACD")[:N] = np.where(tnf_on, 0.3, 0.0)

            apply_physiboss_phenotype(ctx)
            update_mechanics_physicell(ctx, dt=0.1, use_fallback=True,
                                       repulsion_strength=10.0,
                                       adhesion_strength=0.4)

    def test_high_tnf_drives_apoptosis(self):
        """With TNF >> threshold, apoptotic fraction should become majority."""
        import random
        random.seed(7)
        ctx = self._build_context(n_cells=80, tnf_level=10.0, seed=7)
        container = ctx["cell_container"]
        n0 = container.count

        self._step_pipeline(ctx, n_steps=6)

        counts = container.phenotype_counts()
        apop = counts.get("apoptotic", 0)
        necro = counts.get("necrotic", 0)
        assert container.count == n0, "cell count must be conserved (no divisions here)"
        assert apop + necro >= int(0.5 * n0), \
            f"expected majority apoptotic/necrotic, got apop={apop} necro={necro} of {n0}"

    def test_zero_tnf_keeps_cells_quiescent(self):
        """With TNF below threshold, no cell should die."""
        import random
        random.seed(11)
        ctx = self._build_context(n_cells=40, tnf_level=0.0, seed=11)
        container = ctx["cell_container"]

        self._step_pipeline(ctx, n_steps=5)

        counts = container.phenotype_counts()
        assert counts.get("apoptotic", 0) == 0
        assert counts.get("necrotic", 0) == 0
        assert counts.get("Quiescent", 0) == container.count

    def test_mechanics_keeps_cells_in_domain(self):
        """Mechanics integration must never push cells outside the domain."""
        import random
        random.seed(23)
        ctx = self._build_context(n_cells=30, tnf_level=0.0, seed=23)
        # Shrink domain
        from dataclasses import dataclass

        @dataclass
        class _Len:
            micrometers: float

        class _Dom:
            dimensions = 2
            size_x = _Len(400.0)
            size_y = _Len(400.0)
            size_z = _Len(0.0)

        class _Cfg:
            domain = _Dom()

        ctx["config"] = _Cfg()

        self._step_pipeline(ctx, n_steps=8)

        container = ctx["cell_container"]
        N = container.count
        pos = container.positions[:N]
        assert (pos[:, 0] >= -200.0).all() and (pos[:, 0] <= 200.0).all()
        assert (pos[:, 1] >= -200.0).all() and (pos[:, 1] <= 200.0).all()

    def test_apoptosis_is_monotonic_in_tnf(self):
        """Apoptotic fraction under high TNF >= under zero TNF (same seed)."""
        import random
        random.seed(31)
        hi = self._build_context(n_cells=60, tnf_level=10.0, seed=31)
        random.seed(31)
        lo = self._build_context(n_cells=60, tnf_level=0.0, seed=31)

        self._step_pipeline(hi, n_steps=6)
        self._step_pipeline(lo, n_steps=6)

        apop_hi = hi["cell_container"].phenotype_counts().get("apoptotic", 0)
        apop_lo = lo["cell_container"].phenotype_counts().get("apoptotic", 0)
        assert apop_hi > apop_lo
