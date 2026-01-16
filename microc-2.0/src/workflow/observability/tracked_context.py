"""
TrackedContext: A dictionary wrapper that tracks read and write operations.

Used to detect which context keys a node reads during execution,
enabling accurate "reads" tracking in observability events.
"""

from typing import Any, Callable, Dict, Iterator, List, Optional, Set


class TrackedContext(dict):
    """
    A dict subclass that tracks all read and write operations.
    
    This allows the observability system to know exactly which keys
    a node read (accessed) and wrote (modified) during execution.
    
    Usage:
        tracked = TrackedContext(original_context)
        tracked.start_tracking()
        # ... execute node function with tracked as context ...
        reads, writes = tracked.stop_tracking()
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tracking = False
        self._read_keys: Set[str] = set()
        self._written_keys: Set[str] = set()
        self._on_read: Optional[Callable[[str], None]] = None
        self._on_write: Optional[Callable[[str], None]] = None
    
    def start_tracking(
        self,
        on_read: Optional[Callable[[str], None]] = None,
        on_write: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Start tracking read/write operations.
        
        Args:
            on_read: Optional callback invoked on each read (for real-time logging)
            on_write: Optional callback invoked on each write
        """
        self._tracking = True
        self._read_keys.clear()
        self._written_keys.clear()
        self._on_read = on_read
        self._on_write = on_write
    
    def stop_tracking(self) -> tuple[List[str], List[str]]:
        """
        Stop tracking and return the read/written keys.
        
        Returns:
            Tuple of (read_keys, written_keys) as sorted lists
        """
        self._tracking = False
        reads = sorted(self._read_keys)
        writes = sorted(self._written_keys)
        self._read_keys.clear()
        self._written_keys.clear()
        self._on_read = None
        self._on_write = None
        return reads, writes
    
    def get_tracked_reads(self) -> List[str]:
        """Get list of keys read so far (sorted)."""
        return sorted(self._read_keys)
    
    def get_tracked_writes(self) -> List[str]:
        """Get list of keys written so far (sorted)."""
        return sorted(self._written_keys)
    
    def _record_read(self, key: str) -> None:
        """Record a read operation."""
        if self._tracking and isinstance(key, str):
            self._read_keys.add(key)
            if self._on_read:
                self._on_read(key)
    
    def _record_write(self, key: str) -> None:
        """Record a write operation."""
        if self._tracking and isinstance(key, str):
            self._written_keys.add(key)
            if self._on_write:
                self._on_write(key)
    
    # Override dict methods to track access
    
    def __getitem__(self, key: str) -> Any:
        self._record_read(key)
        return super().__getitem__(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        self._record_write(key)
        super().__setitem__(key, value)
    
    def __delitem__(self, key: str) -> None:
        self._record_write(key)
        super().__delitem__(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        self._record_read(key)
        return super().get(key, default)
    
    def setdefault(self, key: str, default: Any = None) -> Any:
        # setdefault is a read if key exists, write if it doesn't
        if key not in self:
            self._record_write(key)
        else:
            self._record_read(key)
        return super().setdefault(key, default)
    
    def pop(self, key: str, *args) -> Any:
        self._record_write(key)
        return super().pop(key, *args)
    
    def update(self, *args, **kwargs) -> None:
        # Record all keys being updated as writes
        if args:
            other = args[0]
            if isinstance(other, dict):
                for key in other:
                    self._record_write(key)
            else:
                for key, _ in other:
                    self._record_write(key)
        for key in kwargs:
            self._record_write(key)
        super().update(*args, **kwargs)
    
    def __contains__(self, key: object) -> bool:
        # __contains__ is a read (checking if key exists)
        if isinstance(key, str):
            self._record_read(key)
        return super().__contains__(key)
    
    def copy(self) -> "TrackedContext":
        """Return a new TrackedContext with the same data (not tracking)."""
        new_ctx = TrackedContext(super().copy())
        return new_ctx
    
    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict copy (for serialization)."""
        return dict(self)

