"""
Resource — a scalar field over a Space, with Unity-style Setup/Step behaviours.

A Resource is non-agent state that lives on the world: sugar, oxygen, a
pheromone. Slice 1 ships ``FieldResource`` (a plain, non-diffusing field).
Diffusion is *one* possible Step behavior, not the foundation — a later
``DiffusingResource`` will wrap the FiPy substance solver behind this same
interface.

Agent coupling is order-safe: agents never scribble on the field directly, they
``deposit`` source/sink terms that ``apply_sources`` commits once per step.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from src.abm.space import Position, Space


class Resource:
    """Base resource: a named field bound to a Space + Setup/Step hooks."""

    def __init__(self, name: str, space: Space):
        self.name = name
        self.space = space
        self.params: dict = {}
        self._setup_fn: Optional[Callable] = None
        self._step_fn: Optional[Callable] = None

    # behaviour binding (the model builder attaches registered functions here) --
    def on_setup(self, fn: Optional[Callable]) -> "Resource":
        self._setup_fn = fn
        return self

    def on_step(self, fn: Optional[Callable]) -> "Resource":
        self._step_fn = fn
        return self

    def run_setup(self, env) -> None:
        if self._setup_fn:
            self._setup_fn(env)

    def run_step(self, env) -> None:
        """Commit deposited source/sink terms, then run the Step behaviour."""
        self.apply_sources()
        if self._step_fn:
            self._step_fn(env)

    # subclasses implement the field mechanics
    def at(self, pos: Position) -> float:
        raise NotImplementedError

    def deposit(self, pos: Position, amount: float) -> None:
        raise NotImplementedError

    def apply_sources(self) -> None:
        raise NotImplementedError


class FieldResource(Resource):
    """A scalar field stored as a numpy array over a (lattice) Space."""

    def __init__(self, name: str, space: Space, initial: float = 0.0, capacity: Optional[float] = None):
        super().__init__(name, space)
        self._values = np.full(space.shape, float(initial), dtype=float)
        self._sources = np.zeros(space.shape, dtype=float)
        self.capacity = None if capacity is None else np.full(space.shape, float(capacity), dtype=float)

    # read --------------------------------------------------------------------
    def at(self, pos: Position) -> float:
        return self.space.interpolate(self._values, pos)

    def values(self) -> np.ndarray:
        return self._values

    def total(self) -> float:
        return float(self._values.sum())

    def max(self) -> float:
        return float(self._values.max())

    def min(self) -> float:
        return float(self._values.min())

    # write: self / deferred --------------------------------------------------
    def set_at(self, pos: Position, value: float) -> None:
        ti, tj = self.space.normalize(pos)
        self._values[tj, ti] = float(value)

    def deposit(self, pos: Position, amount: float) -> None:
        """Accumulate a source(+)/sink(-) term to be applied this step."""
        ti, tj = self.space.normalize(pos)
        self._sources[tj, ti] += float(amount)

    def apply_sources(self) -> None:
        if self._sources.any():
            self._values += self._sources
            np.clip(self._values, 0.0, None, out=self._values)
            self._sources.fill(0.0)

    # reusable field ops a Step behaviour can call ----------------------------
    def fill(self, value: float) -> None:
        self._values.fill(float(value))

    def map(self, fn: Callable[[float], float]) -> None:
        self._values = np.vectorize(fn)(self._values)

    def decay(self, rate: float) -> None:
        self._values *= (1.0 - rate)

    def grow_to(self, capacity: np.ndarray, rate: float) -> None:
        """Regrow toward a capacity field by ``rate`` (Sugarscape growback)."""
        np.minimum(self._values + rate, capacity, out=self._values)

    def clamp_to(self, capacity: np.ndarray) -> None:
        np.minimum(self._values, capacity, out=self._values)
