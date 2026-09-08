"""CSV seeds with an optional z column: 2D loading byte-identical, 3D real.

Pins: a z-less CSV loads exactly as before (2-tuple positions, z=0 physical);
a z CSV in a 3D domain yields 3-tuple positions with clamping and real
physical z; a 3D domain with a z-less CSV fails with the informative error;
a 2D domain ignores a stray z column.

Seed coordinates are centre-relative, so a 160 um domain at 20 um cells
(8x8 biological grid) shifts every index by +4 onto the corner-origin grid.
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
    p.write_text('# origin=center, cell_size_um=20.0, domain_size_um=100.0, description="t"\n'
                 + header + "\n" + "\n".join(rows) + "\n")
    return p


def test_2d_csv_loads_as_before(tmp_path):
    p = _write(tmp_path, "flat.csv", "x,y,phenotype,gene_mitoATP",
               ["-3,-2,Quiescent,true", "-1,0,Proliferation,false"])
    mgr = InitialStateManager(_config(2))
    cells, cell_um = mgr.load_initial_state_from_csv(str(p))
    assert cell_um == 20.0
    assert [c['position'] for c in cells] == [(1, 2), (3, 4)]
    assert cells[0]['original_physical_position'] == (20.0, 40.0, 0.0)
    assert cells[0]['gene_states'] == {'mitoATP': True}


def test_3d_csv_loads_with_z(tmp_path):
    p = _write(tmp_path, "ball.csv", "x,y,z,phenotype",
               ["-3,-2,-1,Quiescent", "0,0,7,Proliferation"])  # z=7+4 clamps to 7
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
    p = _write(tmp_path, "ball.csv", "x,y,z,phenotype", ["-3,-2,3,Quiescent"])
    mgr = InitialStateManager(_config(2))
    cells, _ = mgr.load_initial_state_from_csv(str(p))
    assert cells[0]['position'] == (1, 2)
    assert cells[0]['original_physical_position'] == (20.0, 40.0, 0.0)


def test_seed_stays_centred_when_cell_height_changes(tmp_path):
    """The point of centre-relative seeds: (0,0) is the middle of the domain
    at every Cell Height, so raising it grows a colony in place instead of
    sliding it toward a corner."""
    p = _write(tmp_path, "centred.csv", "x,y,phenotype",
               ["0,0,Quiescent", "-1,1,Quiescent"])

    for cell_um, grid in ((20.0, 8), (40.0, 4)):
        cfg = _config(2)
        cfg.domain.cell_height = Length(cell_um, "um")
        cells, _ = InitialStateManager(cfg).load_initial_state_from_csv(str(p))

        # The (0,0) cell sits on the domain's middle index whatever the size...
        assert cells[0]['position'] == (grid // 2, grid // 2)
        # ...which is the middle of the 160 um domain, up to one half-cell.
        x_um = cells[0]['original_physical_position'][0]
        assert abs(x_um - 80.0) <= cell_um / 2
        # ...and its neighbour keeps its offset from it.
        assert cells[1]['position'] == (grid // 2 - 1, grid // 2 + 1)


def test_generator_and_loader_agree_on_the_centre(tmp_path):
    """The generator subtracts the domain centre and the loader adds it back.
    Each computes that index itself, so pin the round trip: a colony written by
    the generator must land back on the grid squares it was laid out on."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from csv_cell_generator import (assign_phenotypes_and_genes,
                                    generate_spheroid_pattern,
                                    recenter_positions, write_csv_file)

    grid = 8  # the 160 um / 20 um domain of _config()
    absolute = generate_spheroid_pattern(grid // 2, grid // 2, 9)
    seed = tmp_path / "roundtrip.csv"
    write_csv_file(assign_phenotypes_and_genes(
        recenter_positions(absolute, (grid // 2,) * 2), 'spheroid'), seed)

    cells, _ = InitialStateManager(_config(2)).load_initial_state_from_csv(str(seed))
    assert [c['position'] for c in cells] == absolute


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
    # The packing is exactly centred: its centre of mass is the requested centre
    assert all(sum(p[i] for p in pos) == 18 * 500 for i in range(3))


def test_generator_centre_of_mass_is_exact_for_both_grid_parities():
    """A seed's centre of mass must sit on the domain centre: a cell centre
    (integer) on an odd grid, a cell corner (half-integer) on an even grid."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from csv_cell_generator import generate_spheroid_pattern, symmetry_centre
    assert symmetry_centre(75) == 37.0 and symmetry_centre(150) == 74.5
    for grid, count in ((75, 1000), (75, 999), (150, 1000), (75, 100)):
        c = symmetry_centre(grid)
        pos = generate_spheroid_pattern(c, c, count)
        assert len(pos) == count == len(set(pos))
        assert all(abs(sum(p[i] for p in pos) - count * c) < 1e-9 for i in range(2))
    import pytest
    with pytest.raises(ValueError):
        generate_spheroid_pattern(74.5, 74.5, 999)  # odd count on a cell corner
