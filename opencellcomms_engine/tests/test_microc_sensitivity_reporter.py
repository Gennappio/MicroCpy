"""Focused tests for the MicroC sensitivity reporter and the shared laws it imports.

The fixture is a synthetic MicroC-like context: a 1500 um square domain on a
30x30 solver grid (50 um voxels) with 15 um cells, so a cell at bio-grid index
(50, 50) sits on the domain centre and index (60, 50) is 150 um away.
"""
import csv
from types import SimpleNamespace

import numpy as np
import pytest

from src.biology.cell import CellState
from src.biology.context import BiologicalContext
from src.config.config import DomainConfig
from src.core.coords import cell_to_solver_index
from src.core.units import Length

from opencellcomms_adapters.MicroC.functions.fate.mark_proliferating_cells_gated import (
    atp_gate_passes,
)
from opencellcomms_adapters.MicroC.functions.reporting.record_metabolic_symbiosis import (
    oxygen_region_census,
)
from opencellcomms_adapters.MicroC.functions.reporting.record_sensitivity_metrics import (
    record_sensitivity_metrics,
)

ATP_MAX = 1.5e-16


def _cell(cid, position, phenotype="Quiescent", genes=None, metabolic=None):
    state = CellState(id=cid, position=position, phenotype=phenotype, age=0.0,
                      division_count=0, metabolic_state=dict(metabolic or {}),
                      gene_states=dict(genes or {}))
    return SimpleNamespace(state=state)


class _Simulator:
    """Field arrays plus the (x, y)-keyed snapshot the typed env reads."""

    def __init__(self, fields):
        self.state = SimpleNamespace(substances={
            name: SimpleNamespace(concentrations=arr) for name, arr in fields.items()})

    def get_substance_concentrations(self):
        out = {}
        for name, sub in self.state.substances.items():
            arr = sub.concentrations
            ny, nx = arr.shape
            out[name] = {(x, y): float(arr[y, x]) for y in range(ny) for x in range(nx)}
        return out


def _population():
    return [
        # centre cell: mitoATP, passes the 0.5 gate (ratio 0.667)
        _cell("centre", (50, 50), "Proliferation", {"mitoATP": True},
              {"atp_rate": 1.0e-16, "atp_rate_max": ATP_MAX}),
        # 150 um out along x, glycolytic, hypoxic voxel, fails the gate (0.333)
        _cell("far", (60, 50), "Quiescent", {"glycoATP": True},
              {"atp_rate": 0.5e-16, "atp_rate_max": ATP_MAX}),
        # zeroed like calculate_cell_metabolism's _ZERO_METABOLISM: no atp_rate_max
        _cell("dead", (50, 52), "Necrosis", {}, {"atp_rate": 0.0}),
        # would pass the gate but is not viable
        _cell("apo", (48, 50), "Apoptosis", {"mitoATP": True},
              {"atp_rate": 1.4e-16, "atp_rate_max": ATP_MAX}),
        # growth-arrested cells keep ATP data and are viable (ratio 0.8)
        _cell("ga", (50, 48), "Growth_Arrest", {},
              {"atp_rate": 1.2e-16, "atp_rate_max": ATP_MAX}),
    ]


def _fields(config):
    oxygen = np.full((30, 30), 0.05)
    # The "far" cell's voxel, mapped by the shared cell-to-voxel law (index 60
    # x 15 um / 50 um; unit round-trips add float noise, so never hardcode it).
    gx, gy = cell_to_solver_index(config, (60, 50))
    oxygen[gy, gx] = 0.01
    glucose = np.full((30, 30), 4.0)
    glucose[3, 7] = 2.5
    return {"Oxygen": oxygen, "Glucose": glucose}


def _context(tmp_path, cells=None, gate=0.5, iteration=1):
    domain = DomainConfig(Length(1500.0, "um"), Length(1500.0, "um"), 30, 30,
                          cell_height=Length(15.0, "um"))
    config = SimpleNamespace(domain=domain, substances={})
    cells = _population() if cells is None else cells
    results = {} if gate is None else {
        "proliferation_gate": {"atp_threshold1": gate, "cell_cycle_time": 2.0}}
    return {
        "population": SimpleNamespace(state=SimpleNamespace(
            cells={c.state.id: c for c in cells})),
        "simulator": _Simulator(_fields(config)),
        "config": config,
        "results": results,
        "plots_dir": tmp_path,
        "loop_iteration": iteration,
    }


def _rows(tmp_path):
    with (tmp_path / "timeseries" / "sensitivity_metrics_over_time.csv").open() as f:
        return list(csv.DictReader(f))


def test_row_metrics(tmp_path):
    ctx = _context(tmp_path)
    assert record_sensitivity_metrics(BiologicalContext(ctx), hypoxia_threshold=0.022)
    rows = _rows(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["iteration"] == "1"
    assert (row["N_total"], row["N_viable"]) == ("5", "3")
    assert (row["N_proliferating"], row["N_quiescent"], row["N_growth_arrest"],
            row["N_apoptotic"], row["N_necrotic"]) == ("1", "1", "1", "1", "1")
    assert (row["N_mitoATP"], row["N_glycoATP"], row["R_MG"]) == ("2", "1", "2.0")
    # ATP gate over viable cells only: centre and ga pass, far fails, apo excluded
    assert (row["N_atp_ok"], row["F_ATP"], row["atp_threshold1"]) == ("2", "0.666667", "0.5")
    assert row["F_proliferating"] == "0.2"
    assert row["F_inactive"] == "0.8"
    assert (row["N_oxygenated"], row["N_hypoxic"], row["F_hypoxic"]) == ("4", "1", "0.2")
    assert row["hypoxia_threshold_mM"] == "0.022"
    # oxygenated: 2 mitoATP of 4, no glycoATP; hypoxic: 1 glycoATP of 1 -> gate open
    assert (row["MSI_mito"], row["MSI_mct1"]) == ("1.0", "0.0")
    assert (row["glucose_min_mM"], row["oxygen_min_mM"]) == ("2.5", "0.01")
    assert (row["tumor_radius_um"], row["domain_size_um"], row["relative_tumor_size"]) == (
        "150.0", "1500.0", "0.2")


def test_hypoxia_threshold_is_consumed(tmp_path):
    ctx = _context(tmp_path)
    record_sensitivity_metrics(BiologicalContext(ctx), hypoxia_threshold=1.0)
    row = _rows(tmp_path)[0]
    assert (row["N_hypoxic"], row["F_hypoxic"], row["hypoxia_threshold_mM"]) == ("5", "1.0", "1.0")


def test_missing_gate_leaves_atp_columns_blank(tmp_path, capsys):
    ctx = _context(tmp_path, gate=None)
    record_sensitivity_metrics(BiologicalContext(ctx))
    row = _rows(tmp_path)[0]
    assert (row["N_atp_ok"], row["F_ATP"], row["atp_threshold1"]) == ("", "", "")
    assert "not published" in capsys.readouterr().out


def test_one_row_per_iteration(tmp_path):
    ctx = _context(tmp_path)
    record_sensitivity_metrics(BiologicalContext(ctx))
    record_sensitivity_metrics(BiologicalContext(ctx))
    assert len(_rows(tmp_path)) == 1
    ctx["loop_iteration"] = 2
    record_sensitivity_metrics(BiologicalContext(ctx))
    assert [r["iteration"] for r in _rows(tmp_path)] == ["1", "2"]


def test_blank_r_mg_without_glycolytic_cells(tmp_path):
    cells = [c for c in _population() if c.state.id != "far"]
    ctx = _context(tmp_path, cells=cells)
    record_sensitivity_metrics(BiologicalContext(ctx))
    row = _rows(tmp_path)[0]
    assert (row["N_glycoATP"], row["R_MG"]) == ("0", "")
    assert row["tumor_radius_um"] == "30.0"   # apo at index 48: 2 cells x 15 um


@pytest.mark.parametrize("state, threshold", [
    ({}, 0.5),
    ({"atp_rate": None, "atp_rate_max": ATP_MAX}, 0.5),
    ({"atp_rate": 0.0}, 0.5),
    ({"atp_rate": 1.0e-16, "atp_rate_max": 0.0}, 0.5),
    ({"atp_rate": 1.0e-16, "atp_rate_max": ATP_MAX}, 0.5),
    ({"atp_rate": 0.5e-16, "atp_rate_max": ATP_MAX}, 0.5),
    ({"atp_rate": 0.75e-16, "atp_rate_max": ATP_MAX}, 0.5),   # exactly on the threshold
])
def test_atp_gate_matches_previous_inline_law(state, threshold):
    atp_rate = state.get("atp_rate")
    atp_rate_max = state.get("atp_rate_max")
    has_atp = atp_rate is not None and bool(atp_rate_max)
    atp_ok = has_atp and atp_rate > threshold * atp_rate_max
    assert atp_gate_passes(state, threshold) == (has_atp, atp_ok)


def test_oxygen_region_census_matches_previous_inline_loop(tmp_path):
    env = BiologicalContext(_context(tmp_path))
    threshold = 0.022
    counts = {
        ('oxy', 'glyco'): 0, ('oxy', 'mito'): 0, ('oxy', 'mct1'): 0,
        ('hypo', 'glyco'): 0, ('hypo', 'mito'): 0, ('hypo', 'mct1'): 0,
    }
    n_region = {'oxy': 0, 'hypo': 0}
    n_glyco = n_mito = n_mct1 = n_mct4 = 0
    for cell in env.cells:
        region = 'oxy' if env.concentration('Oxygen', cell) >= threshold else 'hypo'
        n_region[region] += 1
        states = cell.gene_states
        if states.get('glycoATP', False):
            counts[(region, 'glyco')] += 1
            n_glyco += 1
        if states.get('mitoATP', False):
            counts[(region, 'mito')] += 1
            n_mito += 1
        if states.get('MCT1', False):
            counts[(region, 'mct1')] += 1
            n_mct1 += 1
        if states.get('MCT4', False):
            n_mct4 += 1
    census = oxygen_region_census(env, threshold)
    assert tuple(census) == (counts, n_region, n_glyco, n_mito, n_mct1, n_mct4)
    assert census.n_region == {'oxy': 4, 'hypo': 1}
