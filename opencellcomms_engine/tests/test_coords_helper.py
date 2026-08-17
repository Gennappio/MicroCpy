"""cell_to_solver_index: the single bio-grid -> solver-voxel law.

Pins that the helper reproduces the historical inline arithmetic exactly in
2D (identity on 1:1 grids, the legacy expression on scaled grids) and extends
it per-axis in 3D with clamping.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.core.coords import cell_to_solver_index  # noqa: E402


def _cfg(dimensions, size_um, n, cell_um=20.0, size_z_um=None, nz=None):
    dim = lambda v: SimpleNamespace(micrometers=v)
    domain = SimpleNamespace(
        dimensions=dimensions,
        size_x=dim(size_um), size_y=dim(size_um),
        nx=n, ny=n,
        cell_height=dim(cell_um),
    )
    if dimensions == 3:
        domain.size_z = dim(size_z_um if size_z_um is not None else size_um)
        domain.nz = nz if nz is not None else n
    return SimpleNamespace(domain=domain)


def test_2d_identity_on_one_to_one_grid():
    # 100 um, 5 voxels, 20 um cells: bio grid == voxel grid
    cfg = _cfg(2, 100.0, 5)
    for x in range(5):
        for y in range(5):
            assert cell_to_solver_index(cfg, (x, y)) == (x, y)


def test_2d_matches_legacy_expression_on_scaled_grid():
    # MicroC geometry: 1500 um, 30 voxels, 20 um cells (75 bio sites)
    cfg = _cfg(2, 1500.0, 30)
    spacing = 1500.0 / 30
    for bio in range(75):
        legacy = max(0, min(29, int((bio * 20.0) / spacing)))
        assert cell_to_solver_index(cfg, (bio, bio)) == (legacy, legacy)


def test_3d_mapping_and_arity():
    # Planned microc_3d geometry: 750 um cube, 15 voxels, 20 um cells (37 sites)
    cfg = _cfg(3, 750.0, 15)
    assert cell_to_solver_index(cfg, (18, 18, 18)) == (7, 7, 7)
    assert cell_to_solver_index(cfg, (36, 0, 36)) == (14, 0, 14)
    # clamping: bio index past the domain edge stays on the last voxel
    assert cell_to_solver_index(cfg, (40, -3, 40)) == (14, 0, 14)


def test_3d_accepts_2d_position_as_z0():
    cfg = _cfg(3, 750.0, 15)
    assert cell_to_solver_index(cfg, (18, 18)) == (7, 7, 0)


def test_2d_ignores_z_of_3d_position():
    cfg = _cfg(2, 100.0, 5)
    assert cell_to_solver_index(cfg, (2, 3, 4)) == (2, 3)
