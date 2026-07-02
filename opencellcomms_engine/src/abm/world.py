"""
World — the polymorphic spatial seam for the ABM class layer.

A World owns everything spatial: geometry, topology (bounded/toroidal),
neighborhoods, distance, occupancy (who is where), and field sampling. Agents
and resources delegate every spatial question to it, so a hex grid, a 3D
lattice, a continuous plane, or a network differ in exactly one place — here.

Slice 1 ships ``LatticeWorld`` (a discrete grid). It works in integer tile
coordinates ``(ti, tj)``, which for Sugarscape coincide with cell positions, so
no physical-unit conversion is needed yet. Occupancy is read from a shared dict
(the wrapped ``CellPopulation.spatial_grid``) so there is a single source of
truth; the Population owns the writes.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np

from src.core.tile_grid import TileGrid, TOROIDAL

Position = Tuple[int, ...]


class World(ABC):
    """Abstract spatial topology. Implementations vary; the interface is fixed."""

    dimension: int

    @abstractmethod
    def bounds(self) -> Tuple[Position, Position]:
        """Inclusive-min / exclusive-max corners of the world."""

    @abstractmethod
    def contains(self, pos: Position) -> bool:
        """Is this an occupiable position (in-domain and not an obstacle)?"""

    @abstractmethod
    def normalize(self, pos: Position) -> Position:
        """Map a position onto a valid one for the topology (wrap or clamp)."""

    @abstractmethod
    def neighbors(self, pos: Position, radius: int = 1, pattern: str = "moore") -> List[Position]:
        """Neighbor positions, honoring topology. Excludes the center."""

    @abstractmethod
    def distance(self, a: Position, b: Position) -> float:
        ...

    @abstractmethod
    def interpolate(self, values: np.ndarray, pos: Position) -> float:
        """Sample a field defined over this world at a position."""

    # -- occupancy (read side; Population owns writes via the shared dict) ----

    def bind_occupancy(self, occupancy: Dict[Position, str]) -> None:
        self._occ = occupancy

    def occupants(self, pos: Position) -> List[str]:
        occ = getattr(self, "_occ", {})
        cid = occ.get(self.normalize(pos))
        return [cid] if cid is not None else []

    def is_free(self, pos: Position) -> bool:
        pos = self.normalize(pos)
        return self.contains(pos) and pos not in getattr(self, "_occ", {})

    def within(self, pos: Position, radius: int, pattern: str = "moore") -> List[str]:
        out: List[str] = []
        for n in self.neighbors(pos, radius=radius, pattern=pattern):
            out.extend(self.occupants(n))
        return out


class LatticeWorld(World):
    """A discrete 2D grid in integer tile coordinates.

    2D only: every spatial method here (normalize/neighbors/bounds/interpolate)
    works in (ti, tj). A 3D lattice would be a separate World implementation, not
    a flag on this one — so ``dimension`` other than 2 is rejected rather than
    silently flattened.
    """

    def __init__(
        self,
        size_x: float,
        size_y: float,
        tile_size: float,
        topology_x: str = "bounded",
        topology_y: str = "bounded",
        dimension: int = 2,
    ) -> None:
        if dimension != 2:
            raise NotImplementedError(
                f"LatticeWorld is 2D only; got dimension={dimension}. A 3D lattice "
                "needs a dedicated World implementation (its spatial methods are all 2D)."
            )
        nx = max(1, int(round(size_x / tile_size)))
        ny = max(1, int(round(size_y / tile_size)))
        self._grid = TileGrid(size_x, size_y, nx, ny, topology_x, topology_y)
        self.dimension = dimension
        self.nx = nx
        self.ny = ny
        self._occ: Dict[Position, str] = {}

    # geometry / topology -----------------------------------------------------

    @property
    def shape(self) -> Tuple[int, int]:
        """Numpy field shape (ny, nx) for resources defined over this world."""
        return (self.ny, self.nx)

    def bounds(self) -> Tuple[Position, Position]:
        return ((0, 0), (self.nx, self.ny))

    def contains(self, pos: Position) -> bool:
        ti, tj = pos[0], pos[1]
        x_ok = self._grid.topology_x == TOROIDAL or 0 <= ti < self.nx
        y_ok = self._grid.topology_y == TOROIDAL or 0 <= tj < self.ny
        return x_ok and y_ok

    def normalize(self, pos: Position) -> Position:
        ti, tj = int(pos[0]), int(pos[1])
        ti = ti % self.nx if self._grid.topology_x == TOROIDAL else max(0, min(self.nx - 1, ti))
        tj = tj % self.ny if self._grid.topology_y == TOROIDAL else max(0, min(self.ny - 1, tj))
        return (ti, tj)

    def iter_positions(self) -> Iterator[Position]:
        for tj in range(self.ny):
            for ti in range(self.nx):
                yield (ti, tj)

    def _offsets(self, radius: int, pattern: str) -> List[Tuple[int, int]]:
        offs: List[Tuple[int, int]] = []
        for dj in range(-radius, radius + 1):
            for di in range(-radius, radius + 1):
                if di == 0 and dj == 0:
                    continue
                if pattern == "vonneumann" and abs(di) + abs(dj) > radius:
                    continue
                if pattern == "axial" and di != 0 and dj != 0:
                    continue  # only the four rays (Sugarscape vision)
                offs.append((di, dj))
        return offs

    def neighbors(self, pos: Position, radius: int = 1, pattern: str = "moore") -> List[Position]:
        ti, tj = int(pos[0]), int(pos[1])
        out: List[Position] = []
        seen = set()
        for di, dj in self._offsets(radius, pattern):
            ni, nj = ti + di, tj + dj
            if self._grid.topology_x == TOROIDAL:
                ni %= self.nx
            elif not (0 <= ni < self.nx):
                continue
            if self._grid.topology_y == TOROIDAL:
                nj %= self.ny
            elif not (0 <= nj < self.ny):
                continue
            if (ni, nj) not in seen:
                seen.add((ni, nj))
                out.append((ni, nj))
        return out

    def distance(self, a: Position, b: Position) -> float:
        di = abs(a[0] - b[0])
        dj = abs(a[1] - b[1])
        if self._grid.topology_x == TOROIDAL:
            di = min(di, self.nx - di)
        if self._grid.topology_y == TOROIDAL:
            dj = min(dj, self.ny - dj)
        return math.hypot(di, dj)

    def direction(self, a: Position, b: Position) -> Tuple[float, float]:
        di, dj = b[0] - a[0], b[1] - a[1]
        norm = math.hypot(di, dj) or 1.0
        return (di / norm, dj / norm)

    def interpolate(self, values: np.ndarray, pos: Position) -> float:
        ti, tj = self.normalize(pos)
        return float(values[tj, ti])  # nearest-tile lookup on a lattice

    def random_position(self, rng: np.random.Generator, empty: bool = False) -> Optional[Position]:
        if not empty:
            ti = int(rng.integers(0, self.nx))
            tj = int(rng.integers(0, self.ny))
            return (ti, tj)
        free = [p for p in self.iter_positions() if p not in self._occ]
        if not free:
            return None
        return free[int(rng.integers(0, len(free)))]
