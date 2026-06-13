"""
Tile grid and resource fields — the discrete "patch" environment.

A ``TileGrid`` is a NetLogo-style world: a rectangular grid of tiles, each
carrying named scalar state (a *field*, e.g. Sugarscape "sugar"). It is
deliberately independent of the FiPy diffusion mesh and of the biological cell
grid — it has its own resolution and its own per-axis topology (bounded or
toroidal). Cells map onto it through a shared physical coordinate frame
(micrometers); see :func:`tile_of_cell`.

A *field* is just a ``numpy`` array of shape ``(ny_t, nx_t)`` indexed
``field[tj, ti]`` (row = y index, column = x index), matching the substance
array convention. "Capacity" (Sugarscape ``max_sugar``) is not a special
concept — it is simply a second field.

Resource *behaviors* (growback, decay, random production, ...) are ordinary
workflow step functions that read and write these arrays. Nothing about a
field's update is hidden inside the engine: every step is a visible workflow
node. Diffusion is just one possible behavior, not the foundation.

Biologist-facing helpers (take the raw ``context`` dict, mirror the
``get_gene_network`` style)::

    from src.core.tile_grid import get_field_value, set_field_value, field_at_cell
"""

from typing import Dict, List, Optional, Tuple

import numpy as np

Topology = str  # 'bounded' | 'toroidal'

BOUNDED: Topology = "bounded"
TOROIDAL: Topology = "toroidal"


def _normalize_axis(i: int, n: int, topology: Topology) -> int:
    """Map a (possibly out-of-range) tile index onto a valid one for an axis."""
    if topology == TOROIDAL:
        return i % n
    # bounded: clamp to the edge
    return max(0, min(n - 1, i))


class TileGrid:
    """A discrete grid of tiles carrying named scalar fields.

    Args:
        size_x: Physical extent in X (micrometers).
        size_y: Physical extent in Y (micrometers).
        nx_t: Number of tiles in X (columns).
        ny_t: Number of tiles in Y (rows).
        topology_x: 'bounded' or 'toroidal' for the X axis.
        topology_y: 'bounded' or 'toroidal' for the Y axis.
    """

    def __init__(
        self,
        size_x: float,
        size_y: float,
        nx_t: int,
        ny_t: int,
        topology_x: Topology = BOUNDED,
        topology_y: Topology = BOUNDED,
    ) -> None:
        if nx_t <= 0 or ny_t <= 0:
            raise ValueError(f"TileGrid needs positive tile counts, got nx_t={nx_t}, ny_t={ny_t}")
        for axis, topo in (("x", topology_x), ("y", topology_y)):
            if topo not in (BOUNDED, TOROIDAL):
                raise ValueError(f"topology_{axis} must be '{BOUNDED}' or '{TOROIDAL}', got {topo!r}")

        self.size_x = float(size_x)
        self.size_y = float(size_y)
        self.nx_t = int(nx_t)
        self.ny_t = int(ny_t)
        self.topology_x = topology_x
        self.topology_y = topology_y
        self.tile_size_x = self.size_x / self.nx_t
        self.tile_size_y = self.size_y / self.ny_t
        self.fields: Dict[str, np.ndarray] = {}

    # -- fields ------------------------------------------------------------

    def add_field(self, name: str, initial_value: float = 0.0) -> np.ndarray:
        """Create a field filled with ``initial_value`` and return its array."""
        arr = np.full((self.ny_t, self.nx_t), float(initial_value), dtype=float)
        self.fields[name] = arr
        return arr

    def get(self, name: str) -> np.ndarray:
        """Return the raw ``(ny_t, nx_t)`` array for a field."""
        if name not in self.fields:
            raise KeyError(f"No field '{name}' on tile grid (have: {sorted(self.fields)})")
        return self.fields[name]

    def has_field(self, name: str) -> bool:
        return name in self.fields

    def value(self, name: str, ti: int, tj: int) -> float:
        """Read a field at a tile, normalizing indices to the topology."""
        ti = _normalize_axis(ti, self.nx_t, self.topology_x)
        tj = _normalize_axis(tj, self.ny_t, self.topology_y)
        return float(self.get(name)[tj, ti])

    def set_value(self, name: str, ti: int, tj: int, value: float) -> None:
        """Write a field at a tile, normalizing indices to the topology."""
        ti = _normalize_axis(ti, self.nx_t, self.topology_x)
        tj = _normalize_axis(tj, self.ny_t, self.topology_y)
        self.get(name)[tj, ti] = float(value)

    # -- geometry / mapping ------------------------------------------------

    def in_bounds(self, ti: int, tj: int) -> bool:
        return 0 <= ti < self.nx_t and 0 <= tj < self.ny_t

    def tile_of(self, position: Tuple[float, float]) -> Tuple[int, int]:
        """Map a physical (x, y) position in micrometers to a (ti, tj) tile."""
        ti = int(position[0] // self.tile_size_x)
        tj = int(position[1] // self.tile_size_y)
        ti = _normalize_axis(ti, self.nx_t, self.topology_x)
        tj = _normalize_axis(tj, self.ny_t, self.topology_y)
        return ti, tj

    def center_of(self, ti: int, tj: int) -> Tuple[float, float]:
        """Physical (x, y) micrometer center of a tile."""
        return (ti + 0.5) * self.tile_size_x, (tj + 0.5) * self.tile_size_y

    def neighbors(self, ti: int, tj: int, radius: int = 1) -> List[Tuple[int, int]]:
        """Moore neighborhood within ``radius``, honoring topology.

        Excludes the center tile. On a bounded axis, off-grid neighbors are
        dropped; on a toroidal axis they wrap. Duplicates from wrapping a very
        small grid are removed.
        """
        out: List[Tuple[int, int]] = []
        seen = set()
        for dj in range(-radius, radius + 1):
            for di in range(-radius, radius + 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = ti + di, tj + dj
                if self.topology_x == TOROIDAL:
                    ni %= self.nx_t
                elif not (0 <= ni < self.nx_t):
                    continue
                if self.topology_y == TOROIDAL:
                    nj %= self.ny_t
                elif not (0 <= nj < self.ny_t):
                    continue
                if (ni, nj) not in seen:
                    seen.add((ni, nj))
                    out.append((ni, nj))
        return out


# ============================================================================
# Biologist-facing context helpers (mirror get_gene_network / get_substance_*)
# ============================================================================

def get_tile_grid(context: Dict) -> Optional[TileGrid]:
    """Return the active TileGrid from the workflow context (or None)."""
    return context.get("tile_grid")


def get_field_value(context: Dict, name: str, ti: int, tj: int) -> float:
    """Read resource field ``name`` at tile (ti, tj)."""
    grid = context.get("tile_grid")
    if grid is None:
        raise RuntimeError("No 'tile_grid' in context — run setup_scene first")
    return grid.value(name, ti, tj)


def set_field_value(context: Dict, name: str, ti: int, tj: int, value: float) -> None:
    """Write resource field ``name`` at tile (ti, tj)."""
    grid = context.get("tile_grid")
    if grid is None:
        raise RuntimeError("No 'tile_grid' in context — run setup_scene first")
    grid.set_value(name, ti, tj, value)


def tile_of_cell(context: Dict, cell) -> Tuple[int, int]:
    """Map a biological cell's position to a tile (ti, tj).

    Cell positions are biological-grid indices; they are converted to physical
    micrometers (tile-center convention) using ``config.domain.cell_height``
    before being mapped onto the independent tile grid. When the tile grid and
    biological grid are configured to coincide (cell_height == tile size), this
    is just the identity.
    """
    grid = context.get("tile_grid")
    if grid is None:
        raise RuntimeError("No 'tile_grid' in context — run setup_scene first")
    pos = cell.position if hasattr(cell, "position") else cell.state.position
    config = context.get("config")
    cell_height = None
    if config is not None and getattr(config, "domain", None) is not None:
        try:
            cell_height = config.domain.cell_height.micrometers
        except Exception:
            cell_height = None
    if cell_height is None:
        # No domain info: treat the position as already physical (µm).
        px, py = float(pos[0]), float(pos[1])
    else:
        px = (float(pos[0]) + 0.5) * cell_height
        py = (float(pos[1]) + 0.5) * cell_height
    return grid.tile_of((px, py))


def field_at_cell(context: Dict, name: str, cell) -> float:
    """Read resource field ``name`` at the tile under a biological cell."""
    ti, tj = tile_of_cell(context, cell)
    return get_field_value(context, name, ti, tj)
