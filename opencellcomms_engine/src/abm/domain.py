"""
Domain — the collective over resources; owns the World.

Domain is the registry of resource fields on the world: init nodes add resources
to it (``setup_resource``) and behaviours read/sample them (``env.resource(name)``).
Resource dynamics are ordinary behaviour nodes on the Resources/Scheduler
canvases, run by the executor — the Domain holds the fields, it does not drive a
hidden step loop.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.abm.resource import Resource
from src.abm.world import Position, World


class Domain:
    """Owns the World and its Resources; the registry behaviours read fields from."""

    def __init__(self, world: World):
        self.world = world
        self.params: Dict = {}
        self._resources: "Dict[str, Resource]" = {}
        # Per-step totals history (opt-in; see record_totals).
        self.history: List[Dict] = []

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

    def totals(self) -> Dict[str, float]:
        """Total field amount per resource, right now (resources exposing total())."""
        return {name: r.total() for name, r in self._resources.items()
                if hasattr(r, "total")}

    def to_observation(self) -> Dict:
        """Compact, JSON-able summary the observability snapshot/diff layer reads
        (via ``summarize_value``) instead of a constant object address — so a diff
        shows resource fields changing over steps: the field total per resource."""
        return {"resources": sorted(self._resources), "totals": self.totals()}

    def record_totals(self, step: Optional[int] = None) -> Dict:
        """Append the current per-resource totals to ``self.history`` and return
        the snapshot. Opt-in — call once per step to build a resource-over-time
        series."""
        snapshot = {"step": step, "totals": self.totals()}
        self.history.append(snapshot)
        return snapshot
