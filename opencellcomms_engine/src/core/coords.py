"""Coordinate mapping between the biological cell grid and the solver mesh.

Cells live on the biological lattice (spacing = ``domain.cell_height``);
substance fields live on the FiPy solver mesh (``nx × ny`` or
``nx × ny × nz`` voxels). Every consumer that reads a field at a cell's
position must perform the same mapping — this module is that single law.

The formula is deliberately written exactly as the historical inline form
(``int(bio_index * cell_height_um / spacing)`` with
``spacing = size_um / n``, clamped to the mesh) so migrating a call site is
arithmetic-identical in 2D.
"""

from typing import Tuple


def cell_to_solver_index(config, position) -> Tuple[int, ...]:
    """Map a biological grid position to its solver voxel index.

    Returns ``(gx, gy)`` for 2D domains and ``(gx, gy, gz)`` for 3D domains —
    matching the key scheme of
    ``MultiSubstanceSimulator.get_substance_concentrations()``. A 2D position
    in a 3D domain maps to the z=0 layer.
    """
    dom = config.domain
    cell_um = dom.cell_height.micrometers

    spacing_x = dom.size_x.micrometers / dom.nx
    spacing_y = dom.size_y.micrometers / dom.ny
    gx = max(0, min(dom.nx - 1, int((position[0] * cell_um) / spacing_x)))
    gy = max(0, min(dom.ny - 1, int((position[1] * cell_um) / spacing_y)))

    if getattr(dom, 'dimensions', 2) == 3:
        spacing_z = dom.size_z.micrometers / dom.nz
        bio_z = position[2] if len(position) > 2 else 0
        gz = max(0, min(dom.nz - 1, int((bio_z * cell_um) / spacing_z)))
        return (gx, gy, gz)

    return (gx, gy)
