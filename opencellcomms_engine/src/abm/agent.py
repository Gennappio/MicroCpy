"""
Agent — an individual, wrapping an engine ``Cell``.

An Agent is a thin handle: it holds per-instance state (traits) and delegates
every spatial question to its Space (via the Population). It follows the
read/write discipline: it reads the neighborhood, writes only itself
(position/traits), and *requests* structural change (``die``) that the
Population commits later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from src.abm.space import Position

if TYPE_CHECKING:
    from src.abm.population import Population
    from src.biology.cell import Cell


class Agent:
    """Typed wrapper over a Cell, bound to its Population (and thus its Space)."""

    def __init__(self, cell: "Cell", population: "Population"):
        self._cell = cell
        self._pop = population

    # identity / state --------------------------------------------------------
    @property
    def id(self) -> str:
        return self._cell.state.id

    @property
    def position(self) -> Position:
        return self._cell.state.position

    @property
    def kind(self) -> Optional[str]:
        return self._cell.state.metabolic_state.get("_kind")

    def get(self, key: str, default=None):
        return self._cell.state.metabolic_state.get(key, default)

    def set(self, key: str, value) -> None:
        self._cell.state.metabolic_state[key] = value

    def is_alive(self) -> bool:
        return not self._cell.state.metabolic_state.get("_dead", False)

    # spatial reads (delegate to Space) ---------------------------------------
    @property
    def space(self):
        return self._pop.space

    def neighbors(self, radius: int = 1, pattern: str = "moore") -> List["Agent"]:
        ids = self.space.within(self.position, radius, pattern)
        return [a for a in (self._pop.agent_by_id(i) for i in ids) if a is not None]

    def empty_cells(self, radius: int = 1, pattern: str = "moore") -> List[Position]:
        return [p for p in self.space.neighbors(self.position, radius, pattern) if self.space.is_free(p)]

    def is_free(self, pos: Position) -> bool:
        return self.space.is_free(pos)

    def sense(self, resource: str) -> float:
        return self._pop.domain.resource(resource).at(self.position)

    def distance_to(self, other: "Agent") -> float:
        return self.space.distance(self.position, other.position)

    # writes: self ------------------------------------------------------------
    def move_to(self, pos: Position) -> None:
        self._pop.relocate(self, self.space.normalize(pos))

    def move_toward(self, target: Position) -> None:
        options = self.empty_cells() + [self.position]
        best = min(options, key=lambda p: self.space.distance(p, target))
        if best != self.position:
            self.move_to(best)

    # writes: resource coupling (deferred via deposit) ------------------------
    def consume(self, resource: str, amount: float) -> None:
        self._pop.domain.resource(resource).deposit(self.position, -abs(amount))

    def produce(self, resource: str, amount: float) -> None:
        self._pop.domain.resource(resource).deposit(self.position, abs(amount))

    # writes: structural change (request; Population commits) -----------------
    def die(self) -> None:
        self._cell.state.metabolic_state["_dead"] = True
