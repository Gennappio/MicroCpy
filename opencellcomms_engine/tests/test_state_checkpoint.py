"""State-checkpoint format: write/read round-trip, node gating, edge cases.

The checkpoint (json + npz pair) must carry everything the plot renderers
consume — fields verbatim, cells in draw order, resolved thresholds and
domain geometry — so `tests/test_replot_checkpoint.py` can prove plots are
reproducible offline. Stubs follow the `test_plot3d_slicing.py` pattern.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ENGINE = Path(__file__).resolve().parents[1]
_SRC = str(_ENGINE / "src")
for p in (_SRC, str(_ENGINE), str(_ENGINE.parent)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

from src.io.state_checkpoint import (  # noqa: E402
    checkpoint_paths,
    read_state_checkpoint,
    resolve_association_threshold,
    write_state_checkpoint,
)


def _dim(v, unit="um"):
    return SimpleNamespace(value=v, micrometers=v, unit=unit)


def _cfg(dimensions=3):
    domain = SimpleNamespace(
        dimensions=dimensions,
        size_x=_dim(750.0), size_y=_dim(750.0),
        size_z=_dim(750.0) if dimensions == 3 else None,
        nx=15, ny=15, nz=15 if dimensions == 3 else None,
        cell_height=_dim(20.0),
    )
    return SimpleNamespace(
        domain=domain,
        time=SimpleNamespace(dt=0.01, end_time=1.0),
        associations={'Oxygen': 'Oxygen_supply'},
        thresholds={'Oxygen_supply': SimpleNamespace(threshold=0.022)},
    )


def _cell(cid, position, phenotype="Quiescent", genes=None, metabolic=None,
          age=0.0, divisions=0):
    return SimpleNamespace(state=SimpleNamespace(
        id=cid, position=position, phenotype=phenotype,
        gene_states=dict(genes or {}), metabolic_state=metabolic,
        age=age, division_count=divisions))


def _write(tmp_path, cfg, cells, fields, iteration=3, necrosis=None):
    return write_state_checkpoint(
        tmp_path / "checkpoints", iteration,
        fields=fields, cells=cells, config=cfg,
        necrosis_thresholds=necrosis or {'Oxygen': 0.011, 'Glucose': 3.9},
        time=iteration * 0.01, render_time=0.0, dt=0.01,
        dt_source="config.time.dt")


def test_roundtrip_3d(tmp_path):
    cfg = _cfg(3)
    rng = np.random.default_rng(1)
    fields = {'Oxygen': rng.random((15, 15, 15)),
              'Glucose': np.full((15, 15, 15), 5.0)}
    cells = [
        _cell("c2", (10, 11, 18), "Proliferation",
              {'glycoATP': True, 'mitoATP': False}, {'atp_rate': 1.5e-16},
              age=2.5, divisions=3),
        _cell("c1", (10, 12, 18), "Necrosis",
              {'glycoATP': False, 'mitoATP': False}),
    ]
    json_path, npz_path = _write(tmp_path, cfg, cells, fields)
    assert json_path.exists() and npz_path.exists()
    assert (json_path, npz_path) == checkpoint_paths(tmp_path / "checkpoints", 3)

    ckpt = read_state_checkpoint(json_path)
    assert ckpt.iteration == 3
    assert ckpt.time == pytest.approx(0.03)
    assert ckpt.render_time == 0.0
    assert ckpt.dimensions == 3
    assert ckpt.meta["domain"]["size_z"]["micrometers"] == 750.0
    for name, arr in fields.items():
        assert np.array_equal(ckpt.fields[name], arr)
        assert ckpt.fields[name].dtype == arr.dtype
    # cells: order preserved (draw order), all attributes intact
    stubs = ckpt.cell_stubs()
    assert [s.state.id for s in stubs] == ["c2", "c1"]
    assert stubs[0].state.position == (10, 11, 18)
    assert stubs[0].state.phenotype == "Proliferation"
    assert stubs[0].state.gene_states == {'glycoATP': True, 'mitoATP': False}
    assert stubs[0].state.metabolic_state == {'atp_rate': 1.5e-16}
    assert stubs[0].state.age == 2.5 and stubs[0].state.division_count == 3
    # resolved isolines: association (Oxygen only) + necrosis where published
    iso = ckpt.isolines()
    assert iso['Oxygen'] == [(0.022, 'threshold'), (0.011, 'Necrosis')]
    assert iso['Glucose'] == [(3.9, 'Necrosis')]


def test_roundtrip_2d(tmp_path):
    cfg = _cfg(2)
    fields = {'Oxygen': np.linspace(0, 1, 15 * 15).reshape(15, 15)}
    cells = [_cell("a", (3, 4), genes={'mitoATP': True, 'glycoATP': False})]
    json_path, _ = _write(tmp_path, cfg, cells, fields)
    ckpt = read_state_checkpoint(json_path)
    assert ckpt.dimensions == 2
    assert ckpt.meta["domain"]["size_z"] is None
    assert ckpt.meta["domain"]["nz"] is None
    assert np.array_equal(ckpt.fields['Oxygen'], fields['Oxygen'])
    assert ckpt.cell_stubs()[0].state.position == (3, 4)  # 2-tuple stays 2-tuple
    stub_dom = ckpt.config_stub().domain
    assert stub_dom.size_z is None and stub_dom.nz is None
    assert stub_dom.cell_height.value == 20.0


def test_edge_cases(tmp_path):
    cfg = _cfg(3)
    fields = {'file': np.ones((2, 2, 2)),      # np.savez-reserved name
              'Oxygen': np.zeros((2, 2, 2))}   # unplotted substances saved too
    cells = [
        _cell("empty", (0, 0, 0), genes={}, metabolic=None),
        _cell("odd", (1, 1, 1), genes={'OnlyHere': True}),  # differs from union
    ]
    json_path, _ = _write(tmp_path, cfg, cells, fields)
    ckpt = read_state_checkpoint(json_path)
    assert ckpt.meta["npz_keys"]["file"] == "field_00"
    assert np.array_equal(ckpt.fields['file'], fields['file'])
    stubs = ckpt.cell_stubs()
    assert stubs[0].state.gene_states == {}
    assert stubs[0].state.metabolic_state == {}
    assert stubs[1].state.gene_states == {'OnlyHere': True}


def test_association_threshold_matches_adapter():
    from opencellcomms_adapters.MicroC.functions.reporting.generate_quadrant_plots import (
        _association_threshold,
    )
    cfg = _cfg(3)
    for name in ('Oxygen', 'Glucose', 'Nope'):
        assert resolve_association_threshold(cfg, name) == _association_threshold(cfg, name)
    assert resolve_association_threshold(SimpleNamespace(), 'Oxygen') is None


def test_node_gating_and_paths(tmp_path):
    from src.biology.context import BiologicalContext
    from src.workflow.functions.output.save_state_checkpoint import (
        save_state_checkpoint,
    )

    cfg = _cfg(3)
    cells = {"a": _cell("a", (1, 2, 3), genes={'glycoATP': True, 'mitoATP': False})}
    population = SimpleNamespace(state=SimpleNamespace(cells=cells))
    simulator = SimpleNamespace(state=SimpleNamespace(substances={
        'Oxygen': SimpleNamespace(concentrations=np.ones((15, 15, 15)))}))
    written = []
    for iteration in (1, 2, 3, 4):
        ctx = {'population': population, 'simulator': simulator, 'config': cfg,
               'results': {'necrosis_thresholds': {'Oxygen': 0.011}},
               'plots_dir': str(tmp_path), 'loop_iteration': iteration}
        assert save_state_checkpoint(BiologicalContext(ctx), interval=2)
        json_path, _ = checkpoint_paths(tmp_path / "checkpoints", iteration)
        if json_path.exists():
            written.append(iteration)
    assert written == [2, 4]

    ckpt = read_state_checkpoint(checkpoint_paths(tmp_path / "checkpoints", 2)[0])
    assert ckpt.meta["dt"] == 0.01 and ckpt.meta["dt_source"] == "config.time.dt"
    assert ckpt.time == pytest.approx(0.02)

    # interval=0 disables entirely
    ctx = {'population': population, 'simulator': simulator, 'config': cfg,
           'results': {}, 'plots_dir': str(tmp_path / "off"), 'loop_iteration': 5}
    assert save_state_checkpoint(BiologicalContext(ctx), interval=0)
    assert not (tmp_path / "off").exists()


def test_node_keeps_only_newest_checkpoint_pairs(tmp_path):
    from src.biology.context import BiologicalContext
    from src.workflow.functions.output.save_state_checkpoint import (
        save_state_checkpoint,
    )

    cfg = _cfg(2)
    cells = {"a": _cell("a", (1, 2), genes={"p53": True})}
    population = SimpleNamespace(state=SimpleNamespace(cells=cells))
    simulator = SimpleNamespace(state=SimpleNamespace(substances={
        "Oxygen": SimpleNamespace(concentrations=np.ones((4, 4)))
    }))

    for iteration in range(1, 6):
        context = {
            "population": population,
            "simulator": simulator,
            "config": cfg,
            "results": {},
            "plots_dir": str(tmp_path),
            "loop_iteration": iteration,
        }
        assert save_state_checkpoint(
            BiologicalContext(context),
            interval=1,
            max_checkpoints=2,
        )

    checkpoint_dir = tmp_path / "checkpoints"
    assert sorted(path.name for path in checkpoint_dir.glob("*.json")) == [
        "checkpoint_ITER_000004.json",
        "checkpoint_ITER_000005.json",
    ]
    assert sorted(path.name for path in checkpoint_dir.glob("*_fields.npz")) == [
        "checkpoint_ITER_000004_fields.npz",
        "checkpoint_ITER_000005_fields.npz",
    ]
