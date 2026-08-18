"""Replot-from-checkpoint sufficiency: the offline tool must reproduce the
live iteration plots pixel-for-pixel from a checkpoint alone.

Each sufficiency test runs the REAL plot node on stub state, saves a
checkpoint with the real save node, replots from the checkpoint files only,
and compares the outputs (PNG pixel buffers; viewer HTML text modulo the
random plotly div id).
"""
import json
import re
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

from src.biology.context import BiologicalContext  # noqa: E402
from src.io.state_checkpoint import checkpoint_paths, read_state_checkpoint  # noqa: E402
from src.workflow.functions.output.save_state_checkpoint import (  # noqa: E402
    save_state_checkpoint,
)
from tools.replot_checkpoint import load_plot_params, replot_2d, replot_3d  # noqa: E402


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
        associations={'Oxygen': 'Oxygen_supply', 'Glucose': 'Glucose_supply'},
        # int threshold on purpose: its type must survive the round trip or
        # plotly serializes 4 vs 4.0 and HTML parity breaks.
        thresholds={'Oxygen_supply': SimpleNamespace(threshold=0.022),
                    'Glucose_supply': SimpleNamespace(threshold=4)},
    )


def _cell(cid, position, phenotype="Quiescence", genes=None):
    return SimpleNamespace(state=SimpleNamespace(
        id=cid, position=position, phenotype=phenotype,
        gene_states=dict(genes or {}), metabolic_state={},
        age=0.0, division_count=0))


QUAD = {
    'Lactate': {'color': 'darkorange', 'vmin': 1, 'vmax': 5},
    'Glucose': {'color': 'teal', 'vmin': 0, 'vmax': 5},
    'TGFA': 'gold',
    'Oxygen': {'color': 'mediumvioletred', 'vmin': 0, 'vmax': 0.07},
}


def _fields_3d():
    ramp = np.linspace(0.0, 1.0, 15 * 15 * 15).reshape(15, 15, 15)
    return {
        'Lactate': 1.0 + 4.0 * ramp,
        'Glucose': 5.0 - 2.0 * ramp,
        'TGFA': 1e-7 + 1e-6 * ramp,
        'Oxygen': 0.07 * ramp,          # crosses 0.022 and 0.011
    }


def _ctx(cfg, fields, cells, plots_dir, iteration=3):
    population = SimpleNamespace(
        state=SimpleNamespace(cells={c.state.id: c for c in cells}),
        config=cfg,
        get_cell_positions=lambda: [(c.state.position, c.state.phenotype)
                                    for c in cells])
    simulator = SimpleNamespace(state=SimpleNamespace(substances={
        name: SimpleNamespace(concentrations=arr)
        for name, arr in fields.items()}))
    return {'population': population, 'simulator': simulator, 'config': cfg,
            'results': {'necrosis_thresholds': {'Oxygen': 0.011, 'Glucose': 3.9},
                        'time': []},
            'plots_dir': str(plots_dir), 'loop_iteration': iteration}


def test_load_plot_params_from_workflow_json(tmp_path):
    wf = {
        "version": "2.0", "name": "t",
        "subworkflows": {"iteration_plots": {
            "description": "",
            "functions": [
                {"id": "f1", "function_name": "generate_3d_plots",
                 "parameters": {"plot_interval": "1", "cell_band": "layer"},
                 "enabled": True, "parameter_nodes": ["d1", "l1", "l2"]},
                {"id": "f2", "function_name": "generate_quadrant_plots",
                 "parameters": {"autorange": False},
                 "enabled": True, "parameter_nodes": ["d1"]},
                {"id": "f3", "function_name": "generate_3d_plots",
                 "parameters": {"plot_interval": "99"},
                 "enabled": False, "parameter_nodes": []},
            ],
            "parameters": [
                {"id": "d1", "type": "dictParameterNode",
                 "target_param": "quadrant_substances",
                 "entries": [
                     {"key": "Oxygen", "valueType": "dict",
                      "value": {"color": "red", "vmin": 0, "vmax": 1}},
                     {"key": "Glucose", "valueType": "string", "value": "teal"},
                 ]},
                {"id": "l1", "type": "listParameterNode",
                 "target_param": "slices", "items": ["z:mid"]},
                {"id": "l2", "type": "listParameterNode",
                 "target_param": "substances_3d", "items": []},
            ],
            "execution_order": ["f1", "f2"],
        }},
    }
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(wf))

    params = load_plot_params(path)
    p3 = params['generate_3d_plots']
    assert p3['quadrant_substances'] == {
        'Oxygen': {'color': 'red', 'vmin': 0, 'vmax': 1}, 'Glucose': 'teal'}
    assert p3['slices'] == ['z:mid']
    assert p3['substances_3d'] == []
    assert p3['plot_interval'] == "1"          # disabled f3 did not win
    assert params['generate_quadrant_plots']['autorange'] is False


def _read_png(path):
    from matplotlib.image import imread
    return imread(str(path))


def test_sufficiency_3d_and_html(tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    pytest.importorskip("plotly")
    from opencellcomms_adapters.MicroC.functions.reporting.generate_3d_plots import (
        generate_3d_plots,
    )

    cfg = _cfg(3)
    fields = _fields_3d()
    cells = [  # bio layer 18 = the z:mid (voxel 7) band; one cell off-band
        _cell("p1", (10, 10, 18), "Proliferation",
              {'glycoATP': True, 'mitoATP': False}),
        _cell("n1", (12, 10, 18), "Necrosis", {}),
        _cell("a1", (20, 20, 18), "Apoptosis",
              {'glycoATP': True, 'mitoATP': True}),
        _cell("q1", (14, 14, 18), "Quiescence",
              {'glycoATP': False, 'mitoATP': True}),
        _cell("off", (5, 5, 30), "Quiescence", {}),
    ]
    live_dir = tmp_path / "live"
    params = {'quadrant_substances': QUAD, 'slices': ['z:mid'],
              'html_enabled': True, 'html_interval': 1}
    ctx = _ctx(cfg, fields, cells, live_dir)
    env = BiologicalContext(ctx)
    assert generate_3d_plots(env, slices=['z:mid'], quadrant_substances=QUAD,
                             html_enabled=True, html_interval=1)
    assert save_state_checkpoint(env)

    live_png = live_dir / "heatmaps" / "quadrants_heatmap_t0.000_ITER_003_slice_z07.png"
    live_html = live_dir / "viewer3d" / "spheroid3d_t0.000_ITER_003.html"
    assert live_png.exists() and live_html.exists()

    ckpt = read_state_checkpoint(
        checkpoint_paths(live_dir / "checkpoints", 3)[0])
    out_root = tmp_path / "replot"
    written = replot_3d(ckpt, params, out_root)
    replot_png = out_root / "heatmaps" / live_png.name
    replot_html = out_root / "viewer3d" / live_html.name
    assert replot_png in written and replot_html in written

    live_px, replot_px = _read_png(live_png), _read_png(replot_png)
    assert live_px.shape == replot_px.shape
    assert np.array_equal(live_px, replot_px)

    # Viewer HTML identical modulo the random plotly div id
    uuid_re = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
    live_text = uuid_re.sub("ID", live_html.read_text())
    replot_text = uuid_re.sub("ID", replot_html.read_text())
    assert live_text == replot_text


def test_sufficiency_2d(tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from opencellcomms_adapters.MicroC.functions.reporting.generate_quadrant_plots import (
        generate_quadrant_plots,
    )

    cfg = _cfg(2)
    ramp = np.linspace(0.0, 1.0, 15 * 15).reshape(15, 15)
    fields = {'Lactate': 1.0 + 4.0 * ramp, 'Glucose': 5.0 - 2.0 * ramp,
              'TGFA': 1e-6 * ramp, 'Oxygen': 0.07 * ramp}
    cells = [
        _cell("p1", (10, 10), "Proliferation",
              {'glycoATP': True, 'mitoATP': False}),
        _cell("n1", (12, 10), "Necrosis", {}),
        _cell("g1", (30, 30), "Growth_Arrest",
              {'glycoATP': False, 'mitoATP': True}),
    ]
    live_dir = tmp_path / "live"
    ctx = _ctx(cfg, fields, cells, live_dir)
    env = BiologicalContext(ctx)
    assert generate_quadrant_plots(env, quadrant_substances=QUAD)
    assert save_state_checkpoint(env)

    live_png = live_dir / "heatmaps" / "quadrants_heatmap_t0.000_ITER_003.png"
    assert live_png.exists()

    ckpt = read_state_checkpoint(
        checkpoint_paths(live_dir / "checkpoints", 3)[0])
    out_root = tmp_path / "replot"
    written = replot_2d(ckpt, {'quadrant_substances': QUAD}, out_root)
    replot_png = out_root / "heatmaps" / live_png.name
    assert written == [replot_png]

    live_px, replot_px = _read_png(live_png), _read_png(replot_png)
    assert live_px.shape == replot_px.shape
    assert np.array_equal(live_px, replot_px)
