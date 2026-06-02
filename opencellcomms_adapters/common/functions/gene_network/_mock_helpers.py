"""
Mock classes for lightweight gene network testing (no FiPy/diffusion required).

These classes allow testing gene network workflows without the full simulation
infrastructure. They provide minimal implementations of Population, Cell, and
related classes.

Note: Gene networks are stored in context['gene_networks'] (dict mapping cell_id → BooleanNetwork)
rather than in the cell state. This matches the real architecture.
"""

from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class MockPosition:
    """Mock position for a cell."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __iter__(self):
        return iter((self.x, self.y))

    def __hash__(self):
        return hash((self.x, self.y, self.z))


@dataclass
class MockCellState:
    """Mock cell state (gene networks are in context, not here)."""
    id: str = ""
    position: MockPosition = field(default_factory=MockPosition)
    phenotype: str = "Quiescent"
    gene_states: Dict[str, bool] = field(default_factory=dict)

    def with_updates(self, **kwargs):
        """Return a copy with updated fields.

        Note: Filters out 'gene_network' for backward compatibility.
        """
        # Filter out gene_network if passed (for backward compatibility)
        kwargs.pop('gene_network', None)

        new_state = MockCellState(
            id=self.id,
            position=self.position,
            phenotype=kwargs.get('phenotype', self.phenotype),
            gene_states=kwargs.get('gene_states', self.gene_states)
        )
        return new_state


@dataclass
class MockCell:
    """Mock cell containing state and gene network."""
    id: str = ""
    state: MockCellState = field(default_factory=MockCellState)
    _cached_gene_states: Dict[str, bool] = field(default_factory=dict)
    _cached_local_env: Dict[str, float] = field(default_factory=dict)


@dataclass
class MockPopulationState:
    """Mock population state."""
    cells: Dict[str, MockCell] = field(default_factory=dict)

    def with_updates(self, **kwargs):
        """Return a copy with updated cells."""
        new_state = MockPopulationState(
            cells=kwargs.get('cells', self.cells)
        )
        return new_state


@dataclass
class MockPopulation:
    """Mock population for gene network testing."""
    state: MockPopulationState = field(default_factory=MockPopulationState)


class UniformConcentration:
    """A concentration 'grid' that returns the same value for any position."""
    def __init__(self, value: float):
        self.value = value

    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        return self.value


class MockSimulator:
    """Mock simulator that returns fixed substance concentrations."""

    def __init__(self, concentrations: Dict[str, float] = None):
        self.concentrations = concentrations or {}

    def get_substance_concentrations(self) -> Dict[str, Dict]:
        result = {}
        for substance, conc in self.concentrations.items():
            result[substance] = UniformConcentration(conc)
        return result


@dataclass
class MockTime:
    """Mock time configuration."""
    dt: float = 1.0


@dataclass
class MockConfig:
    """Mock config for gene network testing."""
    associations: Dict[str, str] = field(default_factory=dict)
    thresholds: Dict[str, Dict[str, float]] = field(default_factory=dict)
    gene_network: Any = None
    time: MockTime = field(default_factory=MockTime)

