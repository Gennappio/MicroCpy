"""
ValidatedContext - Runtime enforcement wrapper for workflow context.

Per CONTEXT_MANAGEMENT.md Phase 3: Runtime Enforcement

This wrapper enforces:
- Type checking based on registry definitions
- Write policy enforcement (read_only, write_once, read_write)
- Delete policy enforcement
- Logging of all context mutations for debugging
"""

import json
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Set, List, Callable
from enum import Enum


class EnforcementMode(Enum):
    """Context enforcement modes."""
    STRICT = "strict"   # Raise exceptions on violations
    WARN = "warn"       # Log warnings but allow operations
    OFF = "off"         # No enforcement (passthrough)


class WritePolicy(Enum):
    """Write policies for context keys."""
    READ_ONLY = "read_only"
    WRITE_ONCE = "write_once"
    READ_WRITE = "read_write"


class DeletePolicy(Enum):
    """Delete policies for context keys."""
    ALLOWED = "allowed"
    FORBIDDEN = "forbidden"


class ContextViolation(Exception):
    """Exception raised when context policy is violated."""
    pass


class ValidatedContext:
    """
    A dict-like wrapper that enforces context registry policies.
    
    Usage:
        registry = load_registry("path/to/context_registry.json")
        ctx = ValidatedContext(initial_data, registry, mode=EnforcementMode.STRICT)
        
        # Use like a dict
        ctx['my_key'] = value  # Validated against registry
        value = ctx['my_key']
        del ctx['my_key']      # Checked against delete policy
    """
    
    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        registry: Optional[Dict] = None,
        mode: EnforcementMode = EnforcementMode.WARN,
        on_violation: Optional[Callable[[str, str], None]] = None
    ):
        """
        Initialize ValidatedContext.
        
        Args:
            data: Initial context data
            registry: Context registry dict (with 'keys' array)
            mode: Enforcement mode (strict, warn, off)
            on_violation: Optional callback for violations (key, message)
        """
        self._data = dict(data) if data else {}
        self._registry = registry
        self._mode = mode
        self._on_violation = on_violation
        
        # Build lookup maps from registry
        self._key_by_name: Dict[str, Dict] = {}
        self._key_by_id: Dict[str, Dict] = {}
        self._written_once: Set[str] = set()  # Track write_once keys
        
        if registry and 'keys' in registry:
            for key in registry['keys']:
                self._key_by_name[key['name']] = key
                self._key_by_id[key['id']] = key
                # Also map aliases
                for alias in key.get('aliases', []):
                    self._key_by_name[alias] = key
    
    def _get_key_def(self, name: str) -> Optional[Dict]:
        """Get key definition from registry by name or ID."""
        return self._key_by_name.get(name) or self._key_by_id.get(name)
    
    def _handle_violation(self, key: str, message: str):
        """Handle a policy violation based on enforcement mode."""
        full_message = f"Context violation for '{key}': {message}"
        
        if self._on_violation:
            self._on_violation(key, message)
        
        if self._mode == EnforcementMode.STRICT:
            raise ContextViolation(full_message)
        elif self._mode == EnforcementMode.WARN:
            warnings.warn(full_message, RuntimeWarning)
    
    def _validate_type(self, key: str, value: Any, key_def: Dict) -> bool:
        """Validate value type against key definition."""
        type_def = key_def.get('type', {})
        type_kind = type_def.get('kind', 'any')
        type_name = type_def.get('name', 'any')
        
        if type_kind == 'any' or type_name == 'any':
            return True
        
        # Map type names to Python types
        type_map = {
            'string': str,
            'str': str,
            'int': int,
            'integer': int,
            'float': (int, float),
            'bool': bool,
            'boolean': bool,
            'list': list,
            'array': list,
            'dict': dict,
            'dictionary': dict,
        }
        
        expected_type = type_map.get(type_name.lower())
        if expected_type and not isinstance(value, expected_type):
            self._handle_violation(
                key,
                f"Expected type '{type_name}', got '{type(value).__name__}'"
            )
            return False
        
        return True
    
    def __getitem__(self, key: str) -> Any:
        """Get a value from context."""
        return self._data[key]
    
    def __setitem__(self, key: str, value: Any):
        """Set a value in context with validation."""
        if self._mode == EnforcementMode.OFF:
            self._data[key] = value
            return
        
        key_def = self._get_key_def(key)
        
        if key_def:
            # Check write policy
            write_policy = key_def.get('write_policy', 'read_write')
            
            if write_policy == WritePolicy.READ_ONLY.value:
                self._handle_violation(key, "Key is read-only")
                if self._mode == EnforcementMode.STRICT:
                    return
            
            elif write_policy == WritePolicy.WRITE_ONCE.value:
                if key in self._written_once:
                    self._handle_violation(key, "Key can only be written once")
                    if self._mode == EnforcementMode.STRICT:
                        return
                self._written_once.add(key)
            
            # Validate type
            self._validate_type(key, value, key_def)

        self._data[key] = value

    def __delitem__(self, key: str):
        """Delete a value from context with validation."""
        if self._mode == EnforcementMode.OFF:
            del self._data[key]
            return

        key_def = self._get_key_def(key)

        if key_def:
            delete_policy = key_def.get('delete_policy', 'allowed')

            if delete_policy == DeletePolicy.FORBIDDEN.value:
                self._handle_violation(key, "Key cannot be deleted")
                if self._mode == EnforcementMode.STRICT:
                    return

        del self._data[key]

    def __contains__(self, key: str) -> bool:
        """Check if key exists in context."""
        return key in self._data

    def __iter__(self):
        """Iterate over context keys."""
        return iter(self._data)

    def __len__(self) -> int:
        """Get number of keys in context."""
        return len(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value with optional default."""
        return self._data.get(key, default)

    def keys(self):
        """Get context keys."""
        return self._data.keys()

    def values(self):
        """Get context values."""
        return self._data.values()

    def items(self):
        """Get context items."""
        return self._data.items()

    def update(self, other: Dict[str, Any]):
        """Update context with multiple values (each validated)."""
        for key, value in other.items():
            self[key] = value

    def pop(self, key: str, *args) -> Any:
        """Remove and return a value."""
        if self._mode != EnforcementMode.OFF:
            key_def = self._get_key_def(key)
            if key_def:
                delete_policy = key_def.get('delete_policy', 'allowed')
                if delete_policy == DeletePolicy.FORBIDDEN.value:
                    self._handle_violation(key, "Key cannot be deleted")
                    if self._mode == EnforcementMode.STRICT:
                        if args:
                            return args[0]
                        raise KeyError(key)

        return self._data.pop(key, *args)

    def setdefault(self, key: str, default: Any = None) -> Any:
        """Set default value if key doesn't exist."""
        if key not in self._data:
            self[key] = default
        return self._data[key]

    def copy(self) -> Dict[str, Any]:
        """Return a shallow copy of the underlying data."""
        return self._data.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to regular dict (for serialization)."""
        return self._data.copy()

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        registry_path: Optional[str] = None,
        mode: str = "warn"
    ) -> 'ValidatedContext':
        """
        Create ValidatedContext from dict and optional registry file.

        Args:
            data: Initial context data
            registry_path: Path to context_registry.json
            mode: Enforcement mode string ("strict", "warn", "off")

        Returns:
            ValidatedContext instance
        """
        registry = None
        if registry_path:
            registry_file = Path(registry_path)
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    registry = json.load(f)

        mode_enum = EnforcementMode(mode.lower())
        return cls(data, registry, mode_enum)

    def fork(self, sandbox_keys: Optional[Set[str]] = None) -> 'ValidatedContext':
        """
        Create a forked context for sandboxed subworkflow execution.

        Per CONTEXT_MANAGEMENT.md Phase 4: Fork + Merge

        Args:
            sandbox_keys: Optional set of keys to include in sandbox.
                         If None, all keys are copied.

        Returns:
            New ValidatedContext with copied data
        """
        if sandbox_keys:
            forked_data = {k: v for k, v in self._data.items() if k in sandbox_keys}
        else:
            forked_data = self._data.copy()

        return ValidatedContext(
            forked_data,
            self._registry,
            self._mode,
            self._on_violation
        )

    def merge(
        self,
        child_context: 'ValidatedContext',
        merge_keys: Optional[Set[str]] = None,
        overwrite: bool = False
    ):
        """
        Merge results from a child (sandboxed) context back into this context.

        Per CONTEXT_MANAGEMENT.md Phase 4: Fork + Merge

        Args:
            child_context: The child context to merge from
            merge_keys: Optional set of keys to merge. If None, merge all.
            overwrite: If True, overwrite existing keys. If False, only add new keys.
        """
        for key, value in child_context.items():
            if merge_keys and key not in merge_keys:
                continue

            if overwrite or key not in self._data:
                self[key] = value


def load_registry(path: str) -> Optional[Dict]:
    """
    Load a context registry from a JSON file.

    Args:
        path: Path to context_registry.json

    Returns:
        Registry dict or None if file doesn't exist
    """
    registry_file = Path(path)
    if registry_file.exists():
        with open(registry_file, 'r') as f:
            return json.load(f)
    return None


def wrap_context(
    context: Dict[str, Any],
    project_root: Optional[str] = None,
    mode: str = "warn"
) -> ValidatedContext:
    """
    Wrap a plain dict context with validation.

    Convenience function for use in workflow executor.

    Args:
        context: Plain dict context
        project_root: Project root directory (to find .microc/context_registry.json)
        mode: Enforcement mode ("strict", "warn", "off")

    Returns:
        ValidatedContext wrapping the original data
    """
    registry = None
    if project_root:
        registry_path = Path(project_root) / ".microc" / "context_registry.json"
        registry = load_registry(str(registry_path))

    return ValidatedContext(context, registry, EnforcementMode(mode.lower()))

