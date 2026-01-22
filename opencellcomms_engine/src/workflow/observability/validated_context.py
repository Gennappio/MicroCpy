"""
ValidatedContext: A context wrapper that enforces write policies.

Extends TrackedContext to add write protection for core context keys.
Core keys (population, simulator, config, etc.) cannot be overwritten once set,
but the objects they reference remain mutable (you can modify population.cells,
but cannot do context['population'] = new_population).

User keys can be freely read and written.

Write Policies:
- read_only: Cannot be written after initialization (e.g., dt, step, time)
- write_once: Can be written once, then becomes read-only (e.g., population, simulator)
- mutable: Can be freely overwritten (e.g., user custom keys, results)
"""

from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set
import warnings

from .tracked_context import TrackedContext


# Write policy constants
WRITE_POLICY_READ_ONLY = "read_only"
WRITE_POLICY_WRITE_ONCE = "write_once"
WRITE_POLICY_MUTABLE = "mutable"


# Default core keys and their write policies
# These are keys provided by the simulation engine that should be protected
DEFAULT_CORE_KEYS: Dict[str, str] = {
    # Write-once keys (initialized once, then protected)
    # These can be set by setup_simulation or by SimulationEngine, but not changed after
    'step': WRITE_POLICY_WRITE_ONCE,
    'dt': WRITE_POLICY_WRITE_ONCE,
    'time': WRITE_POLICY_WRITE_ONCE,
    'current_step': WRITE_POLICY_WRITE_ONCE,
    'population': WRITE_POLICY_WRITE_ONCE,
    'simulator': WRITE_POLICY_WRITE_ONCE,
    'gene_network': WRITE_POLICY_WRITE_ONCE,
    'config': WRITE_POLICY_WRITE_ONCE,
    'mesh_manager': WRITE_POLICY_WRITE_ONCE,
    'helpers': WRITE_POLICY_WRITE_ONCE,  # Can be initialized by workflows

    # Mutable core keys (can be updated during simulation)
    'substance_concentrations': WRITE_POLICY_MUTABLE,
    'results': WRITE_POLICY_MUTABLE,
    'substances': WRITE_POLICY_MUTABLE,
    'simulation_params': WRITE_POLICY_MUTABLE,  # Updated by setup functions
}


class ContextWriteError(Exception):
    """Raised when attempting to write to a protected context key."""
    pass


class ValidatedContext(TrackedContext):
    """
    A TrackedContext subclass that enforces write policies on context keys.
    
    Core context keys (like population, simulator, config) are protected from
    being overwritten, while the objects they reference remain fully mutable.
    
    User context keys can be freely read and written.
    
    Usage:
        ctx = ValidatedContext(initial_data, enforcement="strict")
        ctx.lock_core_keys()  # Lock core keys after initialization
        
        # This works - reading and modifying the object
        population = ctx['population']
        population.add_cell(...)
        
        # This raises ContextWriteError in strict mode
        ctx['population'] = new_population
        
        # User keys work normally
        ctx['my_custom_key'] = value
    """
    
    def __init__(
        self, 
        *args, 
        enforcement: str = "warn",
        core_keys: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Initialize ValidatedContext.
        
        Args:
            *args: Passed to TrackedContext/dict
            enforcement: "strict" (raise), "warn" (warn+allow), or "off" (allow)
            core_keys: Custom core key definitions {key: policy}. 
                      If None, uses DEFAULT_CORE_KEYS.
            **kwargs: Passed to TrackedContext/dict
        """
        super().__init__(*args, **kwargs)
        self._enforcement = enforcement
        self._core_keys = core_keys if core_keys is not None else DEFAULT_CORE_KEYS.copy()
        self._locked = False  # Whether core keys are locked
        self._initialized_keys: Set[str] = set()  # Keys that have been set at least once
    
    def lock_core_keys(self) -> None:
        """
        Lock core keys after initialization.
        
        After calling this, write_once keys cannot be overwritten,
        and read_only keys cannot be written at all.
        """
        self._locked = True
        # Mark all current keys as initialized
        self._initialized_keys = set(self.keys())
    
    def unlock_core_keys(self) -> None:
        """
        Unlock core keys (for testing or special cases).
        """
        self._locked = False
    
    def is_locked(self) -> bool:
        """Check if core keys are locked."""
        return self._locked
    
    def get_write_policy(self, key: str) -> str:
        """Get the write policy for a key."""
        return self._core_keys.get(key, WRITE_POLICY_MUTABLE)
    
    def register_core_key(self, key: str, policy: str = WRITE_POLICY_WRITE_ONCE) -> None:
        """
        Register a new core key with a write policy.
        
        Args:
            key: The key name
            policy: One of "read_only", "write_once", "mutable"
        """
        if policy not in (WRITE_POLICY_READ_ONLY, WRITE_POLICY_WRITE_ONCE, WRITE_POLICY_MUTABLE):
            raise ValueError(f"Invalid write policy: {policy}")
        self._core_keys[key] = policy
    
    def _validate_write(self, key: str) -> bool:
        """
        Validate whether a write to the given key is allowed.
        
        Returns:
            True if write is allowed, False otherwise.
            
        Raises:
            ContextWriteError: In strict mode when write is not allowed.
        """
        if not self._locked:
            return True  # Before locking, all writes are allowed
        
        policy = self.get_write_policy(key)
        
        if policy == WRITE_POLICY_MUTABLE:
            return True  # Always allowed
        
        if policy == WRITE_POLICY_READ_ONLY:
            msg = f"Cannot write to read-only context key: '{key}'"
            if self._enforcement == "strict":
                raise ContextWriteError(msg)
            elif self._enforcement == "warn":
                warnings.warn(msg, stacklevel=3)
            return self._enforcement != "strict"

        if policy == WRITE_POLICY_WRITE_ONCE:
            if key in self._initialized_keys:
                msg = f"Cannot overwrite write-once context key: '{key}'. The object is mutable, but the key binding is protected."
                if self._enforcement == "strict":
                    raise ContextWriteError(msg)
                elif self._enforcement == "warn":
                    warnings.warn(msg, stacklevel=3)
                return self._enforcement != "strict"

        return True

    def _validate_delete(self, key: str) -> bool:
        """
        Validate whether deletion of the given key is allowed.

        Returns:
            True if delete is allowed, False otherwise.
        """
        if not self._locked:
            return True

        if key in self._core_keys:
            msg = f"Cannot delete core context key: '{key}'"
            if self._enforcement == "strict":
                raise ContextWriteError(msg)
            elif self._enforcement == "warn":
                warnings.warn(msg, stacklevel=3)
            return self._enforcement != "strict"

        return True

    # Override write methods to add validation

    def __setitem__(self, key: str, value: Any) -> None:
        if self._validate_write(key):
            super().__setitem__(key, value)
            # Track initialized keys (for write_once protection after first write)
            self._initialized_keys.add(key)

    def __delitem__(self, key: str) -> None:
        if self._validate_delete(key):
            super().__delitem__(key)
            self._initialized_keys.discard(key)

    def setdefault(self, key: str, default: Any = None) -> Any:
        if key not in self:
            if self._validate_write(key):
                result = super().setdefault(key, default)
                if not self._locked:
                    self._initialized_keys.add(key)
                return result
            else:
                return self.get(key, default)
        else:
            return super().setdefault(key, default)

    def pop(self, key: str, *args) -> Any:
        if self._validate_delete(key):
            self._initialized_keys.discard(key)
            return super().pop(key, *args)
        elif args:
            return args[0]
        else:
            raise KeyError(key)

    def update(self, *args, **kwargs) -> None:
        # Validate all keys before updating
        keys_to_update = set()
        if args:
            other = args[0]
            if isinstance(other, dict):
                keys_to_update.update(other.keys())
            else:
                keys_to_update.update(k for k, _ in other)
        keys_to_update.update(kwargs.keys())

        # Check each key
        allowed_updates = {}
        if args:
            other = args[0]
            if isinstance(other, dict):
                for k, v in other.items():
                    if self._validate_write(k):
                        allowed_updates[k] = v
            else:
                for k, v in other:
                    if self._validate_write(k):
                        allowed_updates[k] = v
        for k, v in kwargs.items():
            if self._validate_write(k):
                allowed_updates[k] = v

        # Perform the update with allowed keys only
        for k, v in allowed_updates.items():
            super().__setitem__(k, v)
            self._record_write(k)
            if not self._locked:
                self._initialized_keys.add(k)

    def copy(self) -> "ValidatedContext":
        """Return a new ValidatedContext with the same data and settings."""
        new_ctx = ValidatedContext(
            super().copy(),
            enforcement=self._enforcement,
            core_keys=self._core_keys.copy()
        )
        new_ctx._locked = self._locked
        new_ctx._initialized_keys = self._initialized_keys.copy()
        return new_ctx

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict copy (for serialization)."""
        return dict(self)

    def get_enforcement(self) -> str:
        """Get the current enforcement level."""
        return self._enforcement

    def set_enforcement(self, enforcement: str) -> None:
        """Set the enforcement level."""
        if enforcement not in ("strict", "warn", "off"):
            raise ValueError(f"Invalid enforcement level: {enforcement}")
        self._enforcement = enforcement

