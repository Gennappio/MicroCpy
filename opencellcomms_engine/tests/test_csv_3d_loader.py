"""CSV seeds with an optional z column: 2D loading byte-identical, 3D real.

Pins: a z-less CSV loads exactly as before (2-tuple positions, z=0 physical);
a z CSV in a 3D domain yields 3-tuple positions with clamping and real
physical z; a 3D domain with a z-less CSV fails with the informative error;
a 2D domain ignores a stray z column.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.io.initial_state import InitialStateManager  # noqa: E402
from src.core.units import Length  # noqa: E402


def _config(dimensions):
    # 160 um (not 100): Length round-trips 160 um exactly through meters,
    # while 100 um comes back as 99.999...; the loader's int() bio-grid
    # computation is sensitive to that pre-existing quirk.
    domain = SimpleNamespace(
        dimensions=dimensions,
        size_x=Length(160.0, "um"), size_y=Length(160.0, "um"),
        cell_height=Length(20.0, "um"),
    )
    if dimensions == 3:
        domain.size_z = Length(160.0, "um")
        domain.nz = 8
    return SimpleNamespace(domain=domain)


def _write(tmp_path, name, header, rows):
    p = tmp_path / name
    p.write_text('# cell_size_um=20.0, domain_size_um=100.0, description="t"\n'
                 + header + "\n" + "\n".join(rows) + "\n")
    return p


def test_2d_csv_loads_as_before(tmp_path):
    p = _write(tmp_path, "flat.csv", "x,y,phenotype,gene_mitoATP",
               ["1,2,Quiescent,true", "3,4,Proliferation,false"])
    mgr = InitialStateManager(_config(2))
    cells, cell_um = mgr.load_initial_state_from_csv(str(p))
    assert cell_um == 20.0
    assert [c['position'] for c in cells] == [(1, 2), (3, 4)]
    assert cells[0]['original_physical_position'] == (20.0, 40.0, 0.0)
    assert cells[0]['gene_states'] == {'mitoATP': True}


def test_3d_csv_loads_with_z(tmp_path):
    p = _write(tmp_path, "ball.csv", "x,y,z,phenotype",
               ["1,2,3,Quiescent", "4,4,11,Proliferation"])  # z=11 clamps to 7
    mgr = InitialStateManager(_config(3))
    cells, cell_um = mgr.load_initial_state_from_csv(str(p))
    assert [c['position'] for c in cells] == [(1, 2, 3), (4, 4, 7)]
    assert cells[0]['original_physical_position'] == (20.0, 40.0, 60.0)


def test_3d_domain_rejects_zless_csv(tmp_path):
    p = _write(tmp_path, "flat.csv", "x,y,phenotype", ["1,2,Quiescent"])
    mgr = InitialStateManager(_config(3))
    with pytest.raises(ValueError, match="requires a 'z' column"):
        mgr.load_initial_state_from_csv(str(p))


def test_2d_domain_ignores_stray_z_column(tmp_path):
    p = _write(tmp_path, "ball.csv", "x,y,z,phenotype", ["1,2,3,Quiescent"])
    mgr = InitialStateManager(_config(2))
    cells, _ = mgr.load_initial_state_from_csv(str(p))
    assert cells[0]['position'] == (1, 2)
    assert cells[0]['original_physical_position'] == (20.0, 40.0, 0.0)


def test_generator_3d_ball_shape(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from csv_cell_generator import generate_spheroid_pattern_3d
    pos = generate_spheroid_pattern_3d(18, 18, 18, 500)
    assert len(pos) == 500
    assert len(set(pos)) == 500
    import math
    rmax = max(math.dist(p, (18, 18, 18)) for p in pos)
    analytic = (3 * 500 / (4 * math.pi)) ** (1 / 3)
    assert rmax <= analytic + 1.5
