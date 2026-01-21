"""
ContextSnapshotManager: Manages versioned snapshots of context state.

Persists immutable snapshots and diffs for debugging.
Storage: results/observability/context/<scopeKey>/v000001.json
"""

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Size limits for inline values
INLINE_VALUE_LIMIT = 10 * 1024  # 10KB
MAX_ARTIFACT_SIZE = 1024 * 1024  # 1MB


class ValueSummary:
    """Represents a summarized value for snapshots."""
    
    def __init__(
        self,
        value_type: str,
        preview: Any,
        truncated: bool = False,
        shape: Optional[Tuple[int, ...]] = None,
        length: Optional[int] = None,
        pointer: Optional[str] = None,
    ):
        self.type = value_type
        self.preview = preview
        self.truncated = truncated
        self.shape = shape
        self.len = length
        self.pointer = pointer
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "preview": self.preview,
            "truncated": self.truncated,
        }
        if self.shape is not None:
            result["shape"] = self.shape
        if self.len is not None:
            result["len"] = self.len
        if self.pointer is not None:
            result["pointer"] = self.pointer
        return result


def summarize_value(value: Any, max_preview_len: int = 200) -> ValueSummary:
    """
    Create a ValueSummary for any Python value.
    
    Handles common types: scalars, strings, lists, dicts, numpy arrays, DataFrames.
    """
    # Handle None
    if value is None:
        return ValueSummary("null", None)
    
    # Handle scalars
    if isinstance(value, bool):
        return ValueSummary("boolean", value)
    if isinstance(value, int):
        return ValueSummary("number", value)
    if isinstance(value, float):
        return ValueSummary("number", value)
    
    # Handle strings
    if isinstance(value, str):
        if len(value) <= max_preview_len:
            return ValueSummary("string", value, length=len(value))
        return ValueSummary(
            "string",
            value[:max_preview_len] + "...",
            truncated=True,
            length=len(value),
        )
    
    # Handle lists
    if isinstance(value, (list, tuple)):
        type_name = "list" if isinstance(value, list) else "tuple"
        if len(value) <= 5:
            # Summarize each element
            preview = [_simple_preview(v) for v in value]
            return ValueSummary(type_name, preview, length=len(value))
        preview = [_simple_preview(v) for v in value[:3]] + ["..."]
        return ValueSummary(type_name, preview, truncated=True, length=len(value))
    
    # Handle dicts
    if isinstance(value, dict):
        if len(value) <= 5:
            preview = {k: _simple_preview(v) for k, v in list(value.items())[:5]}
            return ValueSummary("dict", preview, length=len(value))
        preview = {k: _simple_preview(v) for k, v in list(value.items())[:3]}
        preview["..."] = f"({len(value) - 3} more keys)"
        return ValueSummary("dict", preview, truncated=True, length=len(value))
    
    # Handle numpy arrays
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            return ValueSummary(
                "ndarray",
                f"array({value.dtype}, shape={value.shape})",
                truncated=True,
                shape=value.shape,
            )
    except ImportError:
        pass
    
    # Handle pandas DataFrames
    try:
        import pandas as pd
        if isinstance(value, pd.DataFrame):
            return ValueSummary(
                "DataFrame",
                f"DataFrame({len(value)} rows, {len(value.columns)} cols)",
                truncated=True,
                shape=(len(value), len(value.columns)),
            )
    except ImportError:
        pass
    
    # Handle Path objects
    if isinstance(value, Path):
        return ValueSummary("Path", str(value))
    
    # Fallback: use repr with truncation
    try:
        repr_str = repr(value)
        if len(repr_str) > max_preview_len:
            return ValueSummary(
                type(value).__name__,
                repr_str[:max_preview_len] + "...",
                truncated=True,
            )
        return ValueSummary(type(value).__name__, repr_str)
    except Exception:
        return ValueSummary(type(value).__name__, "<unrepresentable>", truncated=True)


def _simple_preview(value: Any) -> Any:
    """Get a simple preview of a value (for nested structures)."""
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:50] + "..." if len(value) > 50 else value
    if isinstance(value, (list, tuple)):
        return f"[{len(value)} items]"
    if isinstance(value, dict):
        return f"{{{len(value)} keys}}"
    return f"<{type(value).__name__}>"


class ContextSnapshotManager:
    """
    Manages versioned context snapshots for observability.

    Each scope (subworkflowKind:subworkflowName) maintains its own version counter.
    Snapshots are saved as JSON files, diffs are computed and saved separately.
    """

    def __init__(self, results_dir: Path, enabled: bool = True):
        """
        Initialize the snapshot manager.

        Args:
            results_dir: Base results directory (e.g., Path('results'))
            enabled: Whether snapshotting is enabled
        """
        self.results_dir = Path(results_dir)
        self.enabled = enabled
        self._lock = threading.Lock()
        self._versions: Dict[str, int] = {}  # scope_key -> current version
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the snapshot directories."""
        if not self.enabled:
            return

        context_dir = self.results_dir / "observability" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)
        self._versions.clear()
        self._initialized = True

    def _get_scope_dir(self, scope_key: str) -> Path:
        """Get the directory for a scope, creating if needed."""
        # scope_key format: "subworkflowKind:subworkflowName"
        # Replace ':' with safe separator for filesystem
        safe_key = scope_key.replace(":", "_")
        scope_dir = self.results_dir / "observability" / "context" / safe_key
        scope_dir.mkdir(parents=True, exist_ok=True)
        (scope_dir / "diff").mkdir(exist_ok=True)
        return scope_dir

    def get_current_version(self, scope_key: str) -> int:
        """Get the current version number for a scope."""
        return self._versions.get(scope_key, 0)

    def take_snapshot(
        self,
        scope_key: str,
        context: Dict[str, Any],
        node_id: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> int:
        """
        Take a snapshot of the current context state.

        Args:
            scope_key: The scope key (e.g., "composer:main")
            context: The context dictionary to snapshot
            node_id: Optional node ID that triggered this snapshot
            execution_id: Optional execution ID

        Returns:
            The version number of this snapshot
        """
        if not self.enabled or not self._initialized:
            return 0

        with self._lock:
            # Increment version
            current_version = self._versions.get(scope_key, 0)
            new_version = current_version + 1
            self._versions[scope_key] = new_version

            # Create snapshot
            snapshot = {
                "version": new_version,
                "scopeKey": scope_key,
                "nodeId": node_id,
                "executionId": execution_id,
                "keys": {},
            }

            # Summarize each key
            for key, value in context.items():
                try:
                    summary = summarize_value(value)
                    snapshot["keys"][key] = summary.to_dict()
                except Exception as e:
                    snapshot["keys"][key] = {
                        "type": "error",
                        "preview": f"<error summarizing: {e}>",
                        "truncated": True,
                    }

            # Save snapshot
            scope_dir = self._get_scope_dir(scope_key)
            snapshot_file = scope_dir / f"v{new_version:06d}.json"
            snapshot_file.write_text(json.dumps(snapshot, indent=2, default=str))

            # If there's a previous version, compute diff
            if current_version > 0:
                self._compute_and_save_diff(scope_key, current_version, new_version, scope_dir)

            return new_version

    def _compute_and_save_diff(
        self,
        scope_key: str,
        from_version: int,
        to_version: int,
        scope_dir: Path,
    ) -> None:
        """Compute and save a diff between two versions."""
        try:
            from_file = scope_dir / f"v{from_version:06d}.json"
            to_file = scope_dir / f"v{to_version:06d}.json"

            if not from_file.exists() or not to_file.exists():
                return

            from_snapshot = json.loads(from_file.read_text())
            to_snapshot = json.loads(to_file.read_text())

            from_keys = set(from_snapshot.get("keys", {}).keys())
            to_keys = set(to_snapshot.get("keys", {}).keys())

            diff = {
                "fromVersion": from_version,
                "toVersion": to_version,
                "scopeKey": scope_key,
                "added": {},
                "removed": {},
                "changed": {},
            }

            # Added keys
            for key in to_keys - from_keys:
                diff["added"][key] = to_snapshot["keys"][key]

            # Removed keys
            for key in from_keys - to_keys:
                diff["removed"][key] = from_snapshot["keys"][key]

            # Changed keys (compare previews)
            for key in from_keys & to_keys:
                from_val = from_snapshot["keys"][key]
                to_val = to_snapshot["keys"][key]
                if from_val != to_val:
                    diff["changed"][key] = {
                        "before": from_val,
                        "after": to_val,
                    }

            # Save diff
            diff_file = scope_dir / "diff" / f"v{from_version:06d}_to_v{to_version:06d}.json"
            diff_file.write_text(json.dumps(diff, indent=2, default=str))

        except Exception as e:
            # Don't fail the snapshot if diff computation fails
            print(f"[OBSERVABILITY] Warning: Failed to compute diff: {e}")

