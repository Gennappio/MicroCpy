"""Coordinate mapping between the biological cell grid and the solver mesh,
and the centred coordinate frame used by seed files and every figure.

TWO FRAMES
    internal  corner-origin: the solver mesh spans [0, size] along each axis
              and bio-grid index i covers [i*h, (i+1)*h) with h = cell_height.
              Everything the engine computes with lives here.
    centred   0 at the domain centre, axes from -size/2 to +size/2. Seed CSV
              files store cell coordinates in this frame (in cell units, the
              ``origin=center`` header) and every plot draws in it, so the
              domain reads as -750..+750 um and a centred colony has its
              centre of mass at (0, 0). ``centred_um`` / ``cell_centre_um``
              are the single law for the conversion: the centre of bio cell
              index i is (i + 0.5) * h - size / 2.

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


def centred_um(index: float, cell_um: float, size_um: float) -> float:
    """Centred physical coordinate (um) of the centre of bio-grid cell ``index``
    along an axis of length ``size_um``: (index + 0.5) * cell_um - size_um / 2."""
    return (float(index) + 0.5) * cell_um - size_um / 2.0


def domain_half_sizes_um(config) -> Tuple[float, ...]:
    """Half the domain size per axis in um: the centred frame runs from
    -half to +half. (size_x/2, size_y/2) in 2D, plus size_z/2 in 3D."""
    dom = config.domain
    halves = [dom.size_x.micrometers / 2.0, dom.size_y.micrometers / 2.0]
    if getattr(dom, 'dimensions', 2) == 3 and getattr(dom, 'size_z', None) is not None:
        halves.append(dom.size_z.micrometers / 2.0)
    return tuple(halves)


def cell_centre_um(config, position) -> Tuple[float, ...]:
    """Centred physical coordinates (um) of a cell at bio-grid ``position``,
    one value per axis of the position (2D or 3D)."""
    dom = config.domain
    cell_um = dom.cell_height.micrometers
    sizes = [dom.size_x.micrometers, dom.size_y.micrometers]
    if len(position) > 2:
        sizes.append(dom.size_z.micrometers)
    return tuple(centred_um(position[i], cell_um, sizes[i]) for i in range(min(len(position), len(sizes))))
