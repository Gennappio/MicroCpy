"""
CellView — lightweight proxy that exposes a single row of a CellContainer
as an object with the same interface as the legacy Cell/CellState classes.

This allows existing workflow functions that use:
    cell.state.position, cell.state.phenotype, cell.state.gene_states
to work transparently with a CellContainer backend.

A CellView does NOT copy data — it reads/writes directly into the
CellContainer's NumPy arrays.  This means:
    - Mutations through the view are immediately reflected in the container.
    - Views are invalidated if the container is compacted (indices shift).

Usage:
    container = CellContainer()
    container.add_cell(position=(5, 10), phenotype="Quiescent")
    view = CellView(container, index=0)
    print(view.state.position)   # [5.0, 10.0, 0.0]
    view.state.phenotype = "apoptotic"
    assert container.phenotype_ids[0] == phenotype_id("apoptotic")
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .cell_container import CellContainer

from .cell_container import phenotype_id, phenotype_name


class _CellStateProxy:
    """
    Proxy for cell.state that reads/writes from CellContainer arrays.

    Provides the same attribute interface as the legacy CellState dataclass:
        .position, .phenotype, .age, .division_count, .gene_states
    Plus .with_updates(**kw) for immutable-style updates (mutates in-place).
    """

    __slots__ = ("_container", "_idx")

    def __init__(self, container: "CellContainer", idx: int):
        object.__setattr__(self, "_container", container)
        object.__setattr__(self, "_idx", idx)

    # ── Read-only properties ────────────────────────────────────────────

    @property
    def position(self) -> np.ndarray:
        """Return position as a NumPy array view (x, y, z)."""
        return self._container.positions[self._idx]

    @position.setter
    def position(self, val):
        c = self._container
        pos = list(val)
        while len(pos) < c.dims:
            pos.append(0.0)
        c.positions[self._idx, :] = pos[:c.dims]

    @property
    def phenotype(self) -> str:
        return phenotype_name(int(self._container.phenotype_ids[self._idx]))

    @phenotype.setter
    def phenotype(self, val: str):
        self._container.phenotype_ids[self._idx] = phenotype_id(val)

    @property
    def age(self) -> float:
        return float(self._container.ages[self._idx])

    @age.setter
    def age(self, val: float):
        self._container.ages[self._idx] = val

    @property
    def division_count(self) -> int:
        return int(self._container.division_counts[self._idx])

    @division_count.setter
    def division_count(self, val: int):
        self._container.division_counts[self._idx] = val

    @property
    def gene_states(self) -> Dict[str, bool]:
        """Return boolean columns as a {name: bool} dict (legacy compat)."""
        result = {}
        for name, arr in self._container._bool_columns.items():
            result[name] = bool(arr[self._idx])
        return result

    @gene_states.setter
    def gene_states(self, val: Dict[str, bool]):
        for name, state in val.items():
            if name in self._container._bool_columns:
                self._container._bool_columns[name][self._idx] = state
            else:
                self._container.add_bool_column(name, default=False)
                self._container._bool_columns[name][self._idx] = state

    @property
    def volume(self) -> float:
        return float(self._container.volumes[self._idx])

    @volume.setter
    def volume(self, val: float):
        self._container.volumes[self._idx] = val
        self._container.radii[self._idx] = (
            3.0 * val / (4.0 * np.pi)
        ) ** (1.0 / 3.0)

    def with_updates(self, **kw) -> "_CellStateProxy":
        """
        Mutate in-place and return self (legacy CellState.with_updates compat).

        Supports: position, phenotype, age, division_count, gene_states, volume
        """
        if "position" in kw:
            self.position = kw["position"]
        if "phenotype" in kw:
            self.phenotype = kw["phenotype"]
        if "age" in kw:
            self.age = kw["age"]
        if "division_count" in kw:
            self.division_count = kw["division_count"]
        if "gene_states" in kw:
            self.gene_states = kw["gene_states"]
        if "volume" in kw:
            self.volume = kw["volume"]
        return self

    def __repr__(self) -> str:
        return (
            f"CellState(idx={self._idx}, pos={list(self.position)}, "
            f"phenotype={self.phenotype!r}, age={self.age:.1f})"
        )



class CellView:
    """
    Lightweight proxy for a single cell inside a CellContainer.

    Mimics the legacy Cell interface:
        view.state.position     → container.positions[idx]
        view.state.phenotype    → phenotype_name(container.phenotype_ids[idx])
        view.state.gene_states  → dict of bool columns at idx
        view.id                 → string or integer cell identifier
        view.custom_functions   → None (placeholder for legacy compat)
    """

    __slots__ = ("_container", "_idx", "state", "id", "custom_functions",
                 "_physiboss_bn_outputs", "_physiboss_local_concs")

    def __init__(self, container: "CellContainer", idx: int, cell_id: Optional[str] = None):
        self._container = container
        self._idx = idx
        self.state = _CellStateProxy(container, idx)
        self.id = cell_id or str(idx)
        self.custom_functions = None
        self._physiboss_bn_outputs: Optional[Dict[str, float]] = None
        self._physiboss_local_concs: Optional[Dict[str, float]] = None

    @property
    def position(self) -> np.ndarray:
        """Shortcut: cell.position → cell.state.position."""
        return self.state.position

    @property
    def index(self) -> int:
        return self._idx

    def __repr__(self) -> str:
        return f"CellView(id={self.id!r}, idx={self._idx}, {self.state})"


class CellContainerIterator:
    """
    Iterate over alive cells in a CellContainer, yielding CellView objects.

    Supports legacy pattern: for cell in container: cell.state.phenotype = ...
    """

    def __init__(self, container: "CellContainer"):
        self._container = container
        self._alive_indices = container.alive_indices()
        self._pos = 0

    def __iter__(self):
        return self

    def __next__(self) -> CellView:
        if self._pos < len(self._alive_indices):
            idx = int(self._alive_indices[self._pos])
            self._pos += 1
            return CellView(self._container, idx, cell_id=str(idx))
        raise StopIteration