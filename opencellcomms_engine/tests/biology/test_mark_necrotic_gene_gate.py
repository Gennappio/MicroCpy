"""R1.4 consumption proof for the require_gene slot of mark_necrotic_cells.

The gene gate is a canvas-visible BOOL parameter on the node (R1.6), not a
key inside the necrosis_params dict. These tests pin both directions: the
slot changes the outcome, and the old dict key is rejected loudly.
"""
from types import SimpleNamespace

import pytest

from opencellcomms_adapters.MicroC.functions.fate.mark_necrotic_cells import (
    mark_necrotic_cells,
)


def _cell(gene_on):
    cell = SimpleNamespace(is_necrotic=False, marked=False)
    cell.gene = lambda name: SimpleNamespace(is_on=lambda: gene_on)
    cell.mark_necrotic = lambda: setattr(cell, "marked", True)
    return cell


def _env(cells, oxygen=0.001, glucose=0.1):
    results = SimpleNamespace(store=lambda *a, **k: None,
                              record_change=lambda *a, **k: None)
    return SimpleNamespace(cell=None, cells=cells, results=results,
                           concentration=lambda name, c: oxygen if name == "Oxygen" else glucose)


THRESHOLDS = {"oxygen_threshold": 0.011, "glucose_threshold": 3.9, "require_both": True}


def test_gene_gate_off_kills_on_environment_alone():
    cell = _cell(gene_on=False)
    mark_necrotic_cells(_env([cell]), necrosis_params=THRESHOLDS, require_gene=False)
    assert cell.marked


def test_gene_gate_on_spares_cell_whose_necrosis_node_is_off():
    cell = _cell(gene_on=False)
    mark_necrotic_cells(_env([cell]), necrosis_params=THRESHOLDS, require_gene=True)
    assert not cell.marked


def test_gene_gate_on_kills_when_node_on_and_environment_below():
    cell = _cell(gene_on=True)
    mark_necrotic_cells(_env([cell]), necrosis_params=THRESHOLDS, require_gene=True)
    assert cell.marked


def test_gui_string_true_is_honoured():
    cell = _cell(gene_on=False)
    mark_necrotic_cells(_env([cell]), necrosis_params=THRESHOLDS, require_gene="true")
    assert not cell.marked


def test_require_gene_inside_dict_is_rejected():
    with pytest.raises(ValueError, match="require_gene"):
        mark_necrotic_cells(_env([_cell(True)]),
                            necrosis_params={**THRESHOLDS, "require_gene": True})
