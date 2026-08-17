"""generate_3d_plots helpers: slice orientation, band rule, render + HTML smoke.

The ramp field arr[z, y, x] = 100z + 10y + x makes every orientation error
visible by value. Band selection is checked against the shared coords law on
the planned microc_3d geometry (750 um cube, 15 voxels, 20 um cells).
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

from opencellcomms_adapters.MicroC.functions.reporting.generate_3d_plots import (  # noqa: E402
    parse_slice_spec,
    plane_geometry,
    select_band_cells,
    slice_bio_layers,
    slice_field,
)


def _dim(v, unit="um"):
    return SimpleNamespace(value=v, micrometers=v, unit=unit)


def _cfg():
    return SimpleNamespace(domain=SimpleNamespace(
        dimensions=3,
        size_x=_dim(750.0), size_y=_dim(750.0), size_z=_dim(750.0),
        nx=15, ny=15, nz=15, cell_height=_dim(20.0),
    ))


def _cell(x, y, z, phenotype="Quiescent"):
    return SimpleNamespace(state=SimpleNamespace(
        position=(x, y, z), phenotype=phenotype, gene_states={}))


RAMP = (100 * np.arange(3)[:, None, None]
        + 10 * np.arange(4)[None, :, None]
        + np.arange(5)[None, None, :]).astype(float)  # (nz=3, ny=4, nx=5)


def test_slice_field_orientation_per_axis():
    z1 = slice_field(RAMP, 'z', 1)          # [y, x]
    assert z1.shape == (4, 5) and z1[2, 3] == 100 + 20 + 3
    y2 = slice_field(RAMP, 'y', 2)          # [z, x]
    assert y2.shape == (3, 5) and y2[1, 4] == 100 + 20 + 4
    x0 = slice_field(RAMP, 'x', 0)          # [z, y]
    assert x0.shape == (3, 4) and x0[2, 1] == 200 + 10 + 0


def test_parse_slice_spec():
    dims = (5, 4, 3)  # (nx, ny, nz)
    assert parse_slice_spec("z:mid", dims) == ('z', 1)
    assert parse_slice_spec("x:4", dims) == ('x', 4)
    assert parse_slice_spec("y:99", dims) == ('y', 3)  # clamped
    with pytest.raises(ValueError):
        parse_slice_spec("w:1", dims)


def test_layer_band_is_slab_center_and_consistent_with_coords_law():
    from src.core.coords import cell_to_solver_index
    cfg = _cfg()
    # voxel 7 of 15 over 750 um: slab centre 375 um -> bio layer 18
    assert slice_bio_layers(cfg, 'z', 7, 'layer') == [18]
    # the chosen layer maps back into the plotted voxel
    assert cell_to_solver_index(cfg, (18, 18, 18))[2] == 7
    # slab mode: every bio layer whose voxel index is 7 under the shared law
    # (18*20/50 -> 7.2, 19*20/50 -> 7.6; layer 20 already maps to voxel 8)
    assert slice_bio_layers(cfg, 'z', 7, 'slab') == [18, 19]


def test_select_band_cells_projection():
    cfg = _cfg()
    cells = [_cell(5, 6, 18), _cell(5, 6, 19), _cell(5, 6, 30), _cell(2, 9, 18)]
    triples, layers = select_band_cells(cells, cfg, 'z', 7, 'layer')
    assert layers == [18]
    assert [(t[0]) for t in triples] == [(5, 6), (2, 9)]  # (x, y) plane

    triples, layers = select_band_cells(cells, cfg, 'z', 7, 'slab')
    assert layers == [18, 19]
    assert len(triples) == 3  # (5,6,18), (5,6,19), (2,9,18); z=30 excluded

    # y-normal slice: plane coords are (x, z)
    cells = [_cell(4, 18, 11)]
    triples, _ = select_band_cells(cells, cfg, 'y', 7, 'layer')
    assert triples[0][0] == (4, 11)


def test_plane_geometry_labels():
    sizes, labels = plane_geometry(_cfg(), 'y')
    assert sizes == (750.0, 750.0)
    assert labels == ('X Position (um)', 'Z Position (um)')


def test_render_slice_smoke_with_triples(tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from opencellcomms_adapters.MicroC.functions.reporting.generate_quadrant_plots import (
        render_quadrant_plot,
    )

    cfg = _cfg()
    plane = np.linspace(0.0, 1.0, 15 * 15).reshape(15, 15)
    fields = {n: plane for n in ("Lactate", "Glucose", "TGFA", "H")}
    specs = {n: {"color": c, "vmin": None, "vmax": None}
             for n, c in [("Lactate", "darkorange"), ("Glucose", "teal"),
                          ("TGFA", "gold"), ("H", "mediumvioletred")]}

    def color_fn(cell=None, gene_states=None, config=None):
        return "green|black"  # glyco interior, necrotic border

    triples = [((10, 10), "Necrosis", _cell(10, 10, 18))]
    out = tmp_path / "slice.png"
    render_quadrant_plot(cfg, fields, specs, triples, color_fn, None, {},
                         1.0, "[test]", out,
                         plane_sizes=(750.0, 750.0),
                         axis_labels=("X Position (um)", "Z Position (um)"))
    assert out.exists() and out.stat().st_size > 10_000


def test_viewer_html_smoke(tmp_path):
    pytest.importorskip("plotly")
    from opencellcomms_adapters.MicroC.functions.reporting.generate_3d_plots import (
        write_viewer_html,
    )

    cfg = _cfg()
    arr = np.full((15, 15, 15), 0.07)
    arr[7, 7, 7] = 0.001  # dip so the 0.022 isosurface exists
    fields = {"Oxygen": arr}
    specs = {"Oxygen": {"color": "mediumvioletred", "vmin": None, "vmax": None}}
    isolines = {"Oxygen": [(0.022, 'threshold')]}
    cells = [_cell(18, 18, 18), _cell(19, 18, 18, "Necrosis")]

    def color_fn(cell=None, gene_states=None, config=None):
        return "blue|gray" if cell.state.phenotype != "Necrosis" else "lightgray|black"

    out = tmp_path / "viewer3d" / "v.html"
    written = write_viewer_html(cfg, fields, specs, cells, color_fn, isolines,
                                ["Oxygen"], True, True, 1.0, "[test]", out)
    assert written == out and out.exists()
    text = out.read_text()
    assert "plotly.min.js" in text
    assert (tmp_path / "viewer3d" / "plotly.min.js").exists()
