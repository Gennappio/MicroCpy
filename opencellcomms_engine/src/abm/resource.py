"""
Resource — a scalar field over a World, with Unity-style Setup/Step behaviours.

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

from src.abm.world import Position, World


class Resource:
    """Base resource: a named field bound to a World + Setup/Step hooks."""

    def __init__(self, name: str, world: World):
        self.name = name
        self.world = world
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

    # observability -----------------------------------------------------------
    def heatmap(self, ax=None, cmap: str = "YlOrBr", origin: str = "lower", **imshow_kw):
        """Draw this field as a heatmap and return the matplotlib Axes. Creates a
        figure if ``ax`` is None. Uses ``values()`` (the (ny, nx) field), so it
        works for any resource that exposes a field. Extra keyword args
        (``extent``, ``zorder``, ...) pass through to ``imshow``."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if ax is None:
            _fig, ax = plt.subplots(figsize=(5, 5))
        imshow_kw.setdefault("aspect", "equal")
        ax.imshow(self.values(), origin=origin, cmap=cmap, **imshow_kw)
        return ax


class FieldResource(Resource):
    """A scalar field stored as a numpy array over a (lattice) World."""

    def __init__(self, name: str, world: World, initial: float = 0.0, capacity: Optional[float] = None):
        super().__init__(name, world)
        self._values = np.full(world.shape, float(initial), dtype=float)
        self._sources = np.zeros(world.shape, dtype=float)
        self.capacity = None if capacity is None else np.full(world.shape, float(capacity), dtype=float)

    # read --------------------------------------------------------------------
    def at(self, pos: Position) -> float:
        return self.world.interpolate(self._values, pos)

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
        ti, tj = self.world.normalize(pos)
        self._values[tj, ti] = float(value)

    def deposit(self, pos: Position, amount: float) -> None:
        """Accumulate a source(+)/sink(-) term to be applied this step."""
        ti, tj = self.world.normalize(pos)
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


class DiffusingResource(Resource):
    """A substance concentration field that diffuses via the existing FiPy solver.

    This is the ``DiffusingResource`` the resource layer always intended (see the
    module docstring): unlike ``FieldResource`` (a self-contained array), it is a
    Resource-shaped VIEW onto one substance inside a shared
    ``MultiSubstanceSimulator`` (``src/simulation/multi_substance_simulator.py``),
    which owns the FiPy mesh and runs the steady-state diffusion-reaction solve.
    Wrapping the existing solver keeps the numerics identical to the legacy
    diffusion path by construction.

    Field and mesh are 1:1: ``values()[y, x]`` is the concentration at world tile
    ``(x, y)`` — no interpolation. Diffusion is a COLLECTIVE step (the simulator
    solves all coupled substances together), so the solve is driven once per tick
    by a resource behaviour via :meth:`diffuse`, not per-resource; :meth:`run_step`
    is therefore a no-op.

    Two coupling modes (both first-class):
      * continuum (MicroC) — reaction rates are computed from cell metabolism and
        passed to ``diffuse(reactions=...)``.
      * discrete (Sugarscape-style) — :meth:`deposit` accumulates per-tile
        source/sink terms that the next solve injects via :meth:`take_pending`.
    """

    def __init__(self, name: str, world: World, simulator):
        super().__init__(name, world)
        self.simulator = simulator
        self._pending: dict = {}     # (x, y) -> rate, for discrete deposit coupling

    @property
    def _substance(self):
        return self.simulator.state.substances[self.name]

    # read --------------------------------------------------------------------
    def values(self) -> np.ndarray:
        """The full concentration field, shape ``(ny, nx)``, 1:1 with the mesh."""
        return self._substance.concentrations

    def at(self, pos: Position) -> float:
        # Normalize first (wrap/clamp per topology) so boundary queries answer the
        # same way as FieldResource.at, which goes through world.normalize.
        return self._substance.get_concentration_at(self.world.normalize(pos))   # field[y, x]

    def total(self) -> float:
        return float(self.values().sum())

    def max(self) -> float:
        return float(self.values().max())

    def min(self) -> float:
        return float(self.values().min())

    # discrete coupling (MicroC uses continuum reactions via diffuse() instead) -
    def deposit(self, pos: Position, amount: float) -> None:
        # Key by the normalized position (as FieldResource.deposit does) so a
        # deposit at an out-of-bounds/toroidal position lands on the same tile a
        # read would.
        key = self.world.normalize(pos)
        self._pending[key] = self._pending.get(key, 0.0) + float(amount)

    def apply_sources(self) -> None:
        # A diffusing field commits sources through the solve, not by writing the
        # field directly; pending deposits are consumed by diffuse().
        pass

    def take_pending(self) -> dict:
        """Return and clear pending per-tile deposits (for the diffuse driver)."""
        pending, self._pending = self._pending, {}
        return pending

    # collective solve --------------------------------------------------------
    def diffuse(self, reactions=None) -> None:
        """Run one diffusion-reaction solve on the shared simulator.

        NOTE: this solves ALL substances the simulator holds (they are coupled),
        so it is meant to be called once per tick by the collective diffuse
        behaviour, not once per resource. ``reactions`` maps a world position to
        ``{substance_name: rate}`` (negative = consumption).
        """
        self.simulator.update(reactions or {})

    def run_step(self, env) -> None:
        # Diffusion is collective (see diffuse); nothing to do per-resource.
        pass


def add_diffusing_resources(domain, world: World, simulator) -> "object":
    """Register every substance held by a ``MultiSubstanceSimulator`` as a
    ``DiffusingResource`` on ``domain`` — so the (8, for MicroC) coupled
    substances become first-class resources that show up on the Resources tab.

    All resources share the one simulator: they diffuse together via the
    collective solve (``DiffusingResource.diffuse`` / the diffuse_substances
    behaviour), not independently. Returns the domain for chaining.
    """
    for name in simulator.state.substances:
        domain.add_resource(DiffusingResource(name, world, simulator))
    return domain
