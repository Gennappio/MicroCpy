"""
Data-driven model builder — the contract the GUI targets.

``build_model`` turns a plain description (dict / JSON) into a wired Domain +
Population, resolving behaviour *names* to callables (from a supplied map or the
function registry). This is what decouples the class library from any particular
GUI node layout: the GUI authors the description; the engine builds the model.

Description schema (slice 1)::

    {
      "world": {"type": "lattice", "size_x": 500, "size_y": 500,
                "tile_size": 10, "topology_x": "toroidal", "topology_y": "toroidal"},
      "resources": [
        {"name": "max_sugar", "setup": "seed_max_sugar"},
        {"name": "sugar", "setup": "seed_sugar", "step": "grow_sugar"}
      ],
      "agents": {"kind": "sugar_agent", "step": "sugar_agent_step"},
      "population": {"setup": "place_agents", "step": "cull_starved", "count": 300}
    }

Resource order matters (it is the Setup/Step order).
"""

from __future__ import annotations

import importlib
from typing import Callable, Dict, Optional, Tuple

from src.abm.domain import Domain
from src.abm.population import Population
from src.abm.resource import FieldResource
from src.abm.world import LatticeWorld


def _resolve(name: Optional[str], behaviours: Optional[Dict[str, Callable]], registry) -> Optional[Callable]:
    """Resolve a behaviour name to a callable: explicit map first, then registry."""
    if not name:
        return None
    if behaviours and name in behaviours:
        return behaviours[name]
    if registry is not None:
        md = registry.get(name)
        if md is not None and md.module_path:
            module = importlib.import_module(md.module_path)
            return getattr(module, name)
    raise KeyError(f"Behaviour '{name}' not found in behaviours map or registry")


def build_world(spec: Dict) -> LatticeWorld:
    kind = spec.get("type", "lattice")
    if kind != "lattice":
        raise NotImplementedError(f"World type '{kind}' not in slice 1 (only 'lattice')")
    return LatticeWorld(
        size_x=spec["size_x"],
        size_y=spec["size_y"],
        tile_size=spec["tile_size"],
        topology_x=spec.get("topology_x", "bounded"),
        topology_y=spec.get("topology_y", "bounded"),
    )


def build_model(
    description: Dict,
    registry=None,
    behaviours: Optional[Dict[str, Callable]] = None,
    config=None,
    seed: int = 0,
) -> Tuple[Domain, Population]:
    world = build_world(description["world"])
    population = Population(world, config=config, seed=seed)
    domain = Domain(world)

    for rd in description.get("resources", []):
        r = FieldResource(rd["name"], world, initial=rd.get("initial", 0.0), capacity=rd.get("capacity"))
        r.params = rd
        r.on_setup(_resolve(rd.get("setup"), behaviours, registry))
        r.on_step(_resolve(rd.get("step"), behaviours, registry))
        domain.add_resource(r)

    dd = description.get("domain", {}) or {}
    domain.params = dd
    domain.on_setup(_resolve(dd.get("setup"), behaviours, registry))
    domain.on_step(_resolve(dd.get("step"), behaviours, registry))

    # Agents are a list of kinds, each with its own Setup/Step and trait params.
    for ad in description.get("agents", []):
        name = ad.get("kind", "agent")
        params = {"count": ad.get("count", 0), **ad.get("traits", {})}
        population.add_kind(
            name,
            setup=_resolve(ad.get("setup"), behaviours, registry),
            step=_resolve(ad.get("step"), behaviours, registry),
            params=params,
        )

    pp = description.get("population", {}) or {}
    population.params = pp
    population.on_setup(_resolve(pp.get("setup"), behaviours, registry))
    population.on_step(_resolve(pp.get("step"), behaviours, registry))

    population.domain = domain
    return domain, population
