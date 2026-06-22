"""
Domain — the collective over resources; owns the World.

Domain orchestrates its resources' Setup/Step (and, later, world-level dynamics
like boundary changes or cross-resource reactions). ``run_step`` is the
composite "Domain Step": it runs each resource's step in insertion order, which
is visible and controllable, not hidden.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from src.abm.resource import Resource
from src.abm.world import Position, World


class Domain:
    """Owns the World and its Resources; orchestrates resource updates."""

    def __init__(self, world: World):
        self.world = world
        self.params: Dict = {}
        self._resources: "Dict[str, Resource]" = {}
        self._setup_fn: Optional[Callable] = None
        self._step_fn: Optional[Callable] = None

    def add_resource(self, resource: Resource) -> "Domain":
        self._resources[resource.name] = resource
        return self

    def resource(self, name: str) -> Resource:
        if name not in self._resources:
            raise KeyError(f"No resource '{name}' (have: {sorted(self._resources)})")
        return self._resources[name]

    def resources(self) -> List[Resource]:
        return list(self._resources.values())

    def sample(self, name: str, pos: Position) -> float:
        return self.resource(name).at(pos)

    def on_setup(self, fn): self._setup_fn = fn; return self
    def on_step(self, fn): self._step_fn = fn; return self

    def run_setup(self, env) -> None:
        if self._setup_fn:
            self._setup_fn(env)
        for r in self._resources.values():
            r.run_setup(env)

    def run_step(self, env) -> None:
        if self._step_fn:
            self._step_fn(env)
        for r in self._resources.values():
            r.run_step(env)
