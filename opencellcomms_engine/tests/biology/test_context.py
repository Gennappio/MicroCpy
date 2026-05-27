"""
Unit tests for BiologicalContext typed API.

These tests construct a BiologicalContext from a synthetic dict (no engine startup,
no JSON loading) and verify the public surface: phenotype mutations, coordinate
conversion, gene access, escape hatch.
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, Tuple

import pytest

# Allow `from src...` imports when running from tests/.
_THIS_DIR = os.path.dirname(__file__)
_ENGINE_ROOT = os.path.abspath(os.path.join(_THIS_DIR, '..', '..'))
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

from src.biology.context import (
    BiologicalContext,
    CellHandle,
    GeneNode,
    Phenotype,
)
from src.biology.cell import Cell


# --- Mocks ------------------------------------------------------------------

class _MockSimulator:
    """Minimal ISubstanceSimulator-like duck. Only what EnvironmentView calls."""

    def __init__(self, grids: Dict[str, Dict[Tuple[int, int], float]],
                 summary: Dict[str, Dict[str, float]] = None):
        self._grids = grids
        self._summary = summary or {}

    def get_substance_concentrations(self):
        return self._grids

    def get_summary_statistics(self):
        return self._summary


class _MockPopulationState:
    def __init__(self, cells):
        self.cells = cells


class _MockPopulation:
    """Minimal stand-in for CellPopulation: only `.state.cells` + `add_cell` + stats."""

    def __init__(self, cells):
        self.state = _MockPopulationState(cells)
        self._stats = {'total_cells': len(cells)}

    def add_cell(self, position, phenotype="normal"):
        new_id = f"new-{len(self.state.cells)}"
        cell = Cell(position=position, phenotype=phenotype, cell_id=new_id)
        self.state.cells[new_id] = cell
        return True

    def get_population_statistics(self):
        return {'total_cells': len(self.state.cells)}


class _MockGeneNode:
    def __init__(self, name, state=False):
        self.name = name
        self.current_state = state
        self.next_state = state


class _MockNetwork:
    def __init__(self, gene_states: Dict[str, bool]):
        self.nodes = {name: _MockGeneNode(name, state) for name, state in gene_states.items()}


def _make_cell(cell_id, position, phenotype=Phenotype.GROWTH_ARREST.value):
    return Cell(position=position, phenotype=phenotype, cell_id=cell_id)


def _make_env(cells=None,
              substances=None,
              gene_networks=None,
              config=None,
              step=0,
              dt=1.0):
    cells = cells or []
    cell_dict = {c.state.id: c for c in cells}
    ctx: Dict = {
        'population': _MockPopulation(cell_dict),
    }
    if substances:
        ctx['simulator'] = _MockSimulator(substances)
    if gene_networks:
        ctx['gene_networks'] = gene_networks
    if config is not None:
        ctx['config'] = config
    ctx['current_step'] = step
    ctx['dt'] = dt
    return BiologicalContext(ctx), ctx


# --- Phenotype enum ---------------------------------------------------------

def test_phenotype_enum_is_string():
    """Phenotype inherits from str so legacy comparisons keep working."""
    assert Phenotype.NECROSIS == 'Necrosis'
    assert Phenotype.NECROSIS.value == 'Necrosis'
    assert isinstance(Phenotype.NECROSIS, str)


# --- CellHandle mutations ---------------------------------------------------

def test_mark_necrotic_updates_phenotype():
    cell = _make_cell('c1', (0, 0))
    env, _ = _make_env(cells=[cell])
    handle = next(iter(env.cells))
    assert not handle.is_necrotic
    handle.mark_necrotic()
    assert handle.is_necrotic
    assert handle.phenotype == 'Necrosis'
    # Backing engine cell mutated in place via immutable update
    assert cell.state.phenotype == 'Necrosis'


def test_mark_proliferating_apoptotic_growth_quiescent():
    cell = _make_cell('c1', (0, 0))
    env, _ = _make_env(cells=[cell])
    handle = env.cells.by_id('c1')

    handle.mark_proliferating()
    assert handle.is_proliferating

    handle.mark_apoptotic()
    assert handle.is_apoptotic
    assert not handle.is_proliferating

    handle.mark_growth_arrested()
    assert handle.is_growth_arrested

    handle.mark_quiescent()
    assert handle.is_quiescent


def test_set_phenotype_accepts_enum_and_string():
    cell = _make_cell('c1', (0, 0))
    env, _ = _make_env(cells=[cell])
    handle = env.cells.by_id('c1')

    handle.set_phenotype(Phenotype.APOPTOSIS)
    assert handle.phenotype == 'Apoptosis'

    handle.set_phenotype('Proliferation')
    assert handle.phenotype == 'Proliferation'


# --- PopulationView ---------------------------------------------------------

def test_population_iteration_and_len():
    cells = [_make_cell(f'c{i}', (i, 0)) for i in range(5)]
    env, _ = _make_env(cells=cells)
    assert len(env.cells) == 5
    ids = {h.id for h in env.cells}
    assert ids == {f'c{i}' for i in range(5)}


def test_population_by_phenotype_filter():
    cells = [
        _make_cell('a', (0, 0), Phenotype.NECROSIS.value),
        _make_cell('b', (1, 0), Phenotype.PROLIFERATION.value),
        _make_cell('c', (2, 0), Phenotype.NECROSIS.value),
    ]
    env, _ = _make_env(cells=cells)
    necrotic_ids = {h.id for h in env.cells.by_phenotype(Phenotype.NECROSIS)}
    assert necrotic_ids == {'a', 'c'}
    # String form also works
    prolif_ids = {h.id for h in env.cells.by_phenotype('Proliferation')}
    assert prolif_ids == {'b'}


def test_population_add():
    env, ctx = _make_env(cells=[])
    assert len(env.cells) == 0
    ok = env.cells.add((3, 4), Phenotype.GROWTH_ARREST)
    assert ok
    assert len(env.cells) == 1


# --- EnvironmentView coordinate conversion ----------------------------------

def test_concentration_returns_grid_value_for_in_range_position():
    cell = _make_cell('c1', (1, 0))
    grids = {'Oxygen': {(0, 0): 0.5, (1, 0): 0.2, (2, 0): 0.1}}
    env, _ = _make_env(cells=[cell], substances=grids)
    handle = env.cells.by_id('c1')
    assert env.concentration('Oxygen', handle) == pytest.approx(0.2)


def test_concentration_case_insensitive_fallback():
    cell = _make_cell('c1', (0, 0))
    grids = {'oxygen': {(0, 0): 0.7}}
    env, _ = _make_env(cells=[cell], substances=grids)
    handle = env.cells.by_id('c1')
    assert env.concentration('Oxygen', handle) == pytest.approx(0.7)


def test_concentration_unknown_substance_returns_zero():
    cell = _make_cell('c1', (0, 0))
    grids = {'Oxygen': {(0, 0): 0.7}}
    env, _ = _make_env(cells=[cell], substances=grids)
    handle = env.cells.by_id('c1')
    assert env.concentration('Glucose', handle) == 0.0


def test_concentrations_at_returns_all_substances():
    cell = _make_cell('c1', (0, 0))
    grids = {
        'Oxygen': {(0, 0): 0.5},
        'Glucose': {(0, 0): 1.2},
    }
    env, _ = _make_env(cells=[cell], substances=grids)
    handle = env.cells.by_id('c1')
    snap = env.concentrations_at(handle)
    assert snap['Oxygen'] == pytest.approx(0.5)
    assert snap['Glucose'] == pytest.approx(1.2)


def test_concentration_with_position_tuple():
    grids = {'Oxygen': {(0, 0): 0.4, (1, 0): 0.9}}
    env, _ = _make_env(cells=[], substances=grids)
    assert env.concentration('Oxygen', (1, 0)) == pytest.approx(0.9)


def test_concentration_with_oversized_position_scales_down():
    """When cell position > grid size and no config, heuristic scaling kicks in."""
    cell = _make_cell('c1', (50, 0))  # Logical position larger than grid
    # Grid is 5 wide (indices 0-4)
    grids = {'Oxygen': {(i, 0): float(i) for i in range(5)}}
    env, _ = _make_env(cells=[cell], substances=grids)
    handle = env.cells.by_id('c1')
    # Heuristic should clamp to grid (max index 4)
    val = env.concentration('Oxygen', handle)
    assert 0.0 <= val <= 4.0


# --- Gene access -----------------------------------------------------------

def test_cell_gene_access_returns_node_wrapper():
    cell = _make_cell('c1', (0, 0))
    network = _MockNetwork({'Apoptosis': True, 'Proliferation': False})
    env, _ = _make_env(cells=[cell], gene_networks={'c1': network})
    handle = env.cells.by_id('c1')
    apo = handle.gene('Apoptosis')
    assert isinstance(apo, GeneNode)
    assert apo.is_on()
    assert not apo.is_off()


def test_cell_gene_turn_on_off():
    cell = _make_cell('c1', (0, 0))
    network = _MockNetwork({'X': False})
    env, _ = _make_env(cells=[cell], gene_networks={'c1': network})
    handle = env.cells.by_id('c1')
    g = handle.gene('X')
    assert g.is_off()
    g.turn_on()
    assert g.is_on()
    # Backing node mutated
    assert network.nodes['X'].current_state is True
    g.set(False)
    assert network.nodes['X'].current_state is False


def test_cell_gene_returns_none_when_missing():
    cell = _make_cell('c1', (0, 0))
    env, _ = _make_env(cells=[cell])  # no gene_networks
    handle = env.cells.by_id('c1')
    assert handle.gene('Apoptosis') is None
    assert not handle.has_gene('Apoptosis')


def test_env_gene_network_returns_underlying_network():
    cell = _make_cell('c1', (0, 0))
    network = _MockNetwork({'X': True})
    env, _ = _make_env(cells=[cell], gene_networks={'c1': network})
    handle = env.cells.by_id('c1')
    assert env.gene_network(handle) is network
    assert env.gene_network('c1') is network


# --- ResultsView -----------------------------------------------------------

def test_results_store_and_get():
    env, ctx = _make_env(cells=[])
    env.results.store('cell_count', 42)
    assert env.results.get('cell_count') == 42
    # Mirrored in raw context
    assert ctx['results']['cell_count'] == 42


def test_results_record_change():
    env, ctx = _make_env(cells=[])
    env.results.record_change('necrosis', {'newly_marked': 3})
    assert env.results.get_change('necrosis') == {'newly_marked': 3}
    assert ctx['changes']['necrosis'] == {'newly_marked': 3}


# --- Top-level env properties ----------------------------------------------

def test_step_and_dt():
    env, _ = _make_env(cells=[], step=7, dt=0.5)
    assert env.step == 7
    assert env.dt == pytest.approx(0.5)


def test_raw_context_returns_underlying_dict():
    env, ctx = _make_env(cells=[])
    assert env.raw_context is ctx


def test_empty_context_does_not_crash():
    """BiologicalContext(None) and ({}) should be safe — empty stubs use this."""
    env = BiologicalContext(None)
    assert len(env.cells) == 0
    assert env.environment.all_substances() == []
    assert env.step == 0
    assert env.dt == 1.0
