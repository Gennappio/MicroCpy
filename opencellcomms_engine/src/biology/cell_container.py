"""
NumPy Structure-of-Arrays (SoA) cell container.

All cell properties are stored as contiguous NumPy arrays, enabling:
- Vectorized operations (100-1000× faster than per-cell Python loops)
- Zero-copy hand-off to C++ kernels via pybind11 buffer protocol
- Cache-friendly memory layout for large populations (10k+ cells)

This is the shared data layer for both PhysiBoss and MicroC adapters.

Design principles:
    1. Fixed columns (positions, phenotype_id, alive, ...) are always present.
    2. Custom float/bool columns can be added dynamically (e.g. BN node probs).
    3. Over-allocation with compaction avoids frequent realloc during division/death.
    4. CellView provides backward-compatible per-cell access (cell.position, etc).
    5. The container owns the memory; views are invalidated on compaction.
"""

from __future__ import annotations

import numpy as np
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


# ── Phenotype encoding ──────────────────────────────────────────────────────
# Integer IDs for fast array operations; string names kept in a class-level map.
PHENOTYPE_MAP: Dict[str, int] = {
    "Quiescent": 0,
    "Proliferation": 1,
    "Growth_Arrest": 2,
    "apoptotic": 3,
    "necrotic": 4,
    "dead": 5,
    "removed": 6,
}
PHENOTYPE_NAMES: Dict[int, str] = {v: k for k, v in PHENOTYPE_MAP.items()}
_NEXT_PHENOTYPE_ID = max(PHENOTYPE_MAP.values()) + 1


def phenotype_id(name: str) -> int:
    """Get or register an integer ID for a phenotype name."""
    global _NEXT_PHENOTYPE_ID
    if name not in PHENOTYPE_MAP:
        PHENOTYPE_MAP[name] = _NEXT_PHENOTYPE_ID
        PHENOTYPE_NAMES[_NEXT_PHENOTYPE_ID] = name
        _NEXT_PHENOTYPE_ID += 1
    return PHENOTYPE_MAP[name]


def phenotype_name(pid: int) -> str:
    """Get the string name for a phenotype integer ID."""
    return PHENOTYPE_NAMES.get(pid, f"unknown_{pid}")


# ── Constants ───────────────────────────────────────────────────────────────
_GROWTH_FACTOR = 2.0   # Over-allocate by 2× when capacity is exceeded
_INITIAL_CAPACITY = 1024


class CellContainer:
    """
    NumPy SoA container for all cell data.

    Fixed columns (always present):
        positions      : float64  (capacity, 3)   — x, y, z coordinates
        phenotype_ids  : int32    (capacity,)      — encoded phenotype
        alive          : bool     (capacity,)      — alive mask
        cell_type_ids  : int32    (capacity,)      — cell type (for multi-type)
        ages           : float64  (capacity,)      — cell age (minutes)
        division_counts: int32    (capacity,)      — number of divisions
        volumes        : float64  (capacity,)      — cell volume (µm³)
        radii          : float64  (capacity,)      — cell radius (µm)

    Dynamic columns:
        _float_columns : Dict[str, ndarray float64 (capacity,)]
        _bool_columns  : Dict[str, ndarray bool    (capacity,)]

    The container maintains:
        count    — number of active cells (indices 0..count-1 are valid)
        capacity — allocated array length (count <= capacity)
    """

    __slots__ = (
        "count", "capacity",
        "positions", "phenotype_ids", "alive", "cell_type_ids",
        "ages", "division_counts", "volumes", "radii",
        "_float_columns", "_bool_columns",
        "_ids",   # Optional string IDs for backward compatibility
    )

    def __init__(self, capacity: int = _INITIAL_CAPACITY, dimensions: int = 3):
        self.count = 0
        self.capacity = capacity
        # Fixed columns
        self.positions = np.zeros((capacity, dimensions), dtype=np.float64)
        self.phenotype_ids = np.zeros(capacity, dtype=np.int32)
        self.alive = np.zeros(capacity, dtype=np.bool_)
        self.cell_type_ids = np.zeros(capacity, dtype=np.int32)
        self.ages = np.zeros(capacity, dtype=np.float64)
        self.division_counts = np.zeros(capacity, dtype=np.int32)
        self.volumes = np.full(capacity, 2494.0, dtype=np.float64)  # PhysiCell default
        self.radii = np.full(capacity, 8.413, dtype=np.float64)     # default radius µm
        # Dynamic columns
        self._float_columns: Dict[str, np.ndarray] = {}
        self._bool_columns: Dict[str, np.ndarray] = {}
        # String IDs (optional, for legacy interop)
        self._ids: Optional[np.ndarray] = None

    # ── Properties (active slice) ───────────────────────────────────────

    @property
    def n(self) -> int:
        """Number of active (living) cells."""
        return int(self.alive[:self.count].sum())

    @property
    def dims(self) -> int:
        return self.positions.shape[1]

    # ── Column management ───────────────────────────────────────────────

    def add_float_column(self, name: str, default: float = 0.0) -> np.ndarray:
        """Register a new per-cell float column (e.g. 'apoptosis_rate')."""
        if name not in self._float_columns:
            arr = np.full(self.capacity, default, dtype=np.float64)
            self._float_columns[name] = arr
        return self._float_columns[name]

    def add_bool_column(self, name: str, default: bool = False) -> np.ndarray:
        """Register a new per-cell boolean column (e.g. 'TNF_node')."""
        if name not in self._bool_columns:
            arr = np.full(self.capacity, default, dtype=np.bool_)
            self._bool_columns[name] = arr
        return self._bool_columns[name]

    def get_float(self, name: str) -> np.ndarray:
        """Get a float column by name. Raises KeyError if not found."""
        return self._float_columns[name]

    def get_bool(self, name: str) -> np.ndarray:
        """Get a bool column by name. Raises KeyError if not found."""
        return self._bool_columns[name]

    def has_column(self, name: str) -> bool:
        return name in self._float_columns or name in self._bool_columns


    # ── Cell operations ─────────────────────────────────────────────────

    def add_cell(
        self,
        position: Sequence[float],
        phenotype: Union[str, int] = 0,
        cell_type: int = 0,
        volume: float = 2494.0,
        **custom_data: float,
    ) -> int:
        """
        Add a single cell. Returns the index of the new cell.

        Args:
            position: (x, y) or (x, y, z) coordinates.
            phenotype: Phenotype name (str) or integer ID.
            cell_type: Cell type integer.
            volume: Cell volume in µm³.
            **custom_data: Values for registered float columns.

        Returns:
            Index of the newly added cell.
        """
        if self.count >= self.capacity:
            self._grow()

        idx = self.count
        pos = list(position)
        while len(pos) < self.dims:
            pos.append(0.0)

        self.positions[idx, :] = pos[:self.dims]
        self.phenotype_ids[idx] = phenotype if isinstance(phenotype, int) else phenotype_id(phenotype)
        self.alive[idx] = True
        self.cell_type_ids[idx] = cell_type
        self.ages[idx] = 0.0
        self.division_counts[idx] = 0
        self.volumes[idx] = volume
        self.radii[idx] = (3.0 * volume / (4.0 * np.pi)) ** (1.0 / 3.0)

        for col_name, val in custom_data.items():
            if col_name in self._float_columns:
                self._float_columns[col_name][idx] = val
            elif col_name in self._bool_columns:
                self._bool_columns[col_name][idx] = bool(val)

        self.count += 1
        return idx

    def add_cells(
        self,
        positions: np.ndarray,
        phenotype: Union[str, int] = 0,
        cell_type: int = 0,
        volume: float = 2494.0,
    ) -> np.ndarray:
        """
        Add multiple cells at once (vectorized). Returns their indices.
        """
        n_new = positions.shape[0]
        while self.count + n_new > self.capacity:
            self._grow()

        start = self.count
        end = start + n_new
        indices = np.arange(start, end)

        if positions.shape[1] < self.dims:
            padded = np.zeros((n_new, self.dims), dtype=np.float64)
            padded[:, :positions.shape[1]] = positions
            positions = padded
        elif positions.shape[1] > self.dims:
            positions = positions[:, :self.dims]

        self.positions[start:end] = positions
        pid = phenotype if isinstance(phenotype, int) else phenotype_id(phenotype)
        self.phenotype_ids[start:end] = pid
        self.alive[start:end] = True
        self.cell_type_ids[start:end] = cell_type
        self.ages[start:end] = 0.0
        self.division_counts[start:end] = 0
        self.volumes[start:end] = volume
        self.radii[start:end] = (3.0 * volume / (4.0 * np.pi)) ** (1.0 / 3.0)

        self.count = end
        return indices

    def kill(self, mask: np.ndarray) -> int:
        """Mark cells as dead. Call compact() to reclaim space."""
        full_mask = np.zeros(self.count, dtype=np.bool_)
        full_mask[:len(mask)] = mask[:self.count]
        killed = int(full_mask.sum())
        self.alive[:self.count] &= ~full_mask
        return killed

    def compact(self) -> np.ndarray:
        """
        Remove dead cells by compacting arrays in-place.

        Returns:
            index_map (old_count,): index_map[old] = new, or -1 if removed.
        """
        alive_mask = self.alive[:self.count]
        n_alive = int(alive_mask.sum())
        if n_alive == self.count:
            return np.arange(self.count)

        index_map = np.full(self.count, -1, dtype=np.int64)
        index_map[alive_mask] = np.arange(n_alive)

        # Compact fixed columns
        self.positions[:n_alive] = self.positions[:self.count][alive_mask]
        self.phenotype_ids[:n_alive] = self.phenotype_ids[:self.count][alive_mask]
        self.alive[:n_alive] = True
        self.cell_type_ids[:n_alive] = self.cell_type_ids[:self.count][alive_mask]
        self.ages[:n_alive] = self.ages[:self.count][alive_mask]
        self.division_counts[:n_alive] = self.division_counts[:self.count][alive_mask]
        self.volumes[:n_alive] = self.volumes[:self.count][alive_mask]
        self.radii[:n_alive] = self.radii[:self.count][alive_mask]

        # Compact dynamic columns
        for arr in self._float_columns.values():
            arr[:n_alive] = arr[:self.count][alive_mask]
        for arr in self._bool_columns.values():
            arr[:n_alive] = arr[:self.count][alive_mask]

        if self._ids is not None:
            self._ids[:n_alive] = self._ids[:self.count][alive_mask]

        self.count = n_alive
        return index_map

    # ── Internal ────────────────────────────────────────────────────────

    def _grow(self):
        """Double the capacity of all arrays."""
        new_cap = max(int(self.capacity * _GROWTH_FACTOR), self.capacity + 64)
        self.positions = _resize_2d(self.positions, new_cap)
        self.phenotype_ids = _resize_1d(self.phenotype_ids, new_cap)
        self.alive = _resize_1d(self.alive, new_cap)
        self.cell_type_ids = _resize_1d(self.cell_type_ids, new_cap)
        self.ages = _resize_1d(self.ages, new_cap)
        self.division_counts = _resize_1d(self.division_counts, new_cap)
        self.volumes = _resize_1d(self.volumes, new_cap, fill=2494.0)
        self.radii = _resize_1d(self.radii, new_cap, fill=8.413)
        for name in list(self._float_columns):
            self._float_columns[name] = _resize_1d(self._float_columns[name], new_cap)
        for name in list(self._bool_columns):
            self._bool_columns[name] = _resize_1d(self._bool_columns[name], new_cap)
        if self._ids is not None:
            old = self._ids
            self._ids = np.empty(new_cap, dtype=old.dtype)
            self._ids[:len(old)] = old
        self.capacity = new_cap

    # ── Active-slice convenience views ──────────────────────────────────

    def active_positions(self) -> np.ndarray:
        """Return (N_alive, dims) view of alive cell positions."""
        return self.positions[:self.count][self.alive[:self.count]]

    def active_mask(self) -> np.ndarray:
        """Return (count,) boolean array of alive cells."""
        return self.alive[:self.count].copy()

    def alive_indices(self) -> np.ndarray:
        """Return integer indices of alive cells within [0, count)."""
        return np.where(self.alive[:self.count])[0]

    def phenotype_counts(self) -> Dict[str, int]:
        """Return a dict mapping phenotype names to cell counts."""
        active_phenos = self.phenotype_ids[:self.count][self.alive[:self.count]]
        counts: Dict[str, int] = {}
        for pid in np.unique(active_phenos):
            counts[phenotype_name(int(pid))] = int((active_phenos == pid).sum())
        return counts

    # ── Serialization helpers ───────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Export active cells as a dict of arrays (for JSON/output)."""
        mask = self.alive[:self.count]
        result: Dict[str, Any] = {
            "positions": self.positions[:self.count][mask].tolist(),
            "phenotypes": [phenotype_name(int(p)) for p in self.phenotype_ids[:self.count][mask]],
            "volumes": self.volumes[:self.count][mask].tolist(),
            "ages": self.ages[:self.count][mask].tolist(),
        }
        for name, arr in self._float_columns.items():
            result[name] = arr[:self.count][mask].tolist()
        for name, arr in self._bool_columns.items():
            result[name] = arr[:self.count][mask].tolist()
        return result

    def __iter__(self):
        """Iterate alive cells as CellView objects (legacy compat)."""
        from .cell_view import CellContainerIterator
        return CellContainerIterator(self)

    def __getitem__(self, idx: int) -> "CellView":
        """Get a CellView for cell at index idx."""
        from .cell_view import CellView
        if idx < 0 or idx >= self.count:
            raise IndexError(f"Cell index {idx} out of range [0, {self.count})")
        return CellView(self, idx, cell_id=str(idx))

    def __len__(self) -> int:
        return self.n

    def __repr__(self) -> str:
        return (
            f"CellContainer(count={self.count}, alive={self.n}, "
            f"capacity={self.capacity}, dims={self.dims}, "
            f"float_cols={list(self._float_columns)}, "
            f"bool_cols={list(self._bool_columns)})"
        )


# ── Module-level helpers ────────────────────────────────────────────────────

def _resize_1d(arr: np.ndarray, new_len: int, fill: float = 0) -> np.ndarray:
    """Resize a 1D array, preserving existing data."""
    new = np.full(new_len, fill, dtype=arr.dtype)
    new[:len(arr)] = arr
    return new


def _resize_2d(arr: np.ndarray, new_rows: int) -> np.ndarray:
    """Resize a 2D array along axis 0, preserving existing data."""
    new = np.zeros((new_rows, arr.shape[1]), dtype=arr.dtype)
    new[:arr.shape[0]] = arr
    return new