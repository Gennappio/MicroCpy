"""
ABM class layer — World / Resource / Agent / Population / Domain.

A small, GUI-driven object model for spatial agent-based models. The polymorphic
``World`` owns all spatial logic (geometry, topology, neighborhood, occupancy,
sampling); ``Agent``/``Population`` and ``Resource``/``Domain`` are generic
infrastructure plus user-authored Setup/Step behaviours. The layer wraps the
existing engine classes (CellPopulation, Cell) rather than replacing them.

See ``build_model`` for the data-driven entry point.
"""

from src.abm.agent import Agent
from src.abm.domain import Domain
from src.abm.model import build_model, build_world
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
    "build_model",
    "build_world",
]
