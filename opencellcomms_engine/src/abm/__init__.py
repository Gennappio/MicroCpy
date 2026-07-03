"""
ABM class layer — World / Resource / Agent / Population / Domain.

A small, GUI-driven object model for spatial agent-based models. The polymorphic
``World`` owns all spatial logic (geometry, topology, neighborhood, occupancy,
sampling); ``Agent``/``Population`` and ``Resource``/``Domain`` are generic
infrastructure the node-authored behaviours act on. The layer wraps the existing
engine classes (CellPopulation, Cell) rather than replacing them.

These objects are built and driven by the workflow executor via the node path
(the ``setup_world`` / ``setup_resource`` init nodes create them; the scheduler's
per-entity ``for_each`` ask runs the behaviour subworkflows over them). There is
no separate library-side run loop — the executor owns the loop.
"""

from src.abm.agent import Agent
from src.abm.domain import Domain
from src.abm.population import Population
from src.abm.resource import (
    DiffusingResource,
    FieldResource,
    Resource,
    add_diffusing_resources,
)
from src.abm.world import LatticeWorld, World

__all__ = [
    "World",
    "LatticeWorld",
    "Resource",
    "FieldResource",
    "DiffusingResource",
    "add_diffusing_resources",
    "Agent",
    "Population",
    "Domain",
]
