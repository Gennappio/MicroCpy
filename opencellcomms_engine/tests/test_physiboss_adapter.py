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
        assert c.alive[0] is True

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
        assert c.get_bool("TNF_node")[0] is True

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
        assert c.get_bool("TNF")[0] is True
        assert c.get_bool("Apoptosis")[0] is False
        assert v.state.gene_states == {"TNF": True, "Apoptosis": False}