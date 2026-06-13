"""
ABM class layer — Space / Resource / Agent / Population / Domain.

A small, GUI-driven object model for spatial agent-based models. The polymorphic
``Space`` owns all spatial logic (geometry, topology, neighborhood, occupancy,
sampling); ``Agent``/``Population`` and ``Resource``/``Domain`` are generic
infrastructure plus user-authored Setup/Step behaviours. The layer wraps the
existing engine classes (CellPopulation, Cell) rather than replacing them.

See ``build_model`` for the data-driven entry point.
"""

from src.abm.agent import Agent
from src.abm.domain import Domain
from src.abm.model import build_model, build_space
from src.abm.population import Population
from src.abm.resource import FieldResource, Resource
from src.abm.space import LatticeSpace, Space

__all__ = [
    "Space",
    "LatticeSpace",
    "Resource",
    "FieldResource",
    "Agent",
    "Population",
    "Domain",
    "build_model",
    "build_space",
]
