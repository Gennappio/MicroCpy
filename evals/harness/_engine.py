"""Bootstrap access to the engine's existing, reusable machinery.

The evaluation harness deliberately does NOT reimplement workflow parsing,
semantic canonicalization, structural validation, or numeric snapshotting. All
four already exist in the engine and are the same tools the `/occ_*` skills tell
the coding agent to satisfy. This module wires up `sys.path` and re-exports them
so the rest of the harness imports from one place.

Reused (do not fork):
  * ``oracle(doc)``               engine canonical form of a workflow document
                                  (tools/compact_workflow.py::_oracle)
  * ``SEMANTIC_NULL_FIELDS``      the node fields that are semantically null
                                  (compact_workflow's _FUNC/_CALL/_SW defaults)
  * ``check_workflow(path, reg)`` the readability/structure validator
  * ``derive_homed_kinds(...)``   strict name -> GUI-role homing map
  * ``load_registry()``           the function registry (for param typing)
  * ``compare_snapshots(...)``    the 3-level numeric diff (microc_golden.compare)
  * ``save_snapshot`` / ``load_snapshot``

Nothing here has side effects beyond extending ``sys.path`` and importing.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_DIR = REPO_ROOT / "opencellcomms_engine"

# The engine imports itself as both ``src.*`` and bare ``simulation.*`` etc.,
# and the adapters live at the repo root. Mirror scripts/validate_workflow.py.
for _p in (str(ENGINE_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _load_by_path(name: str, relpath: str) -> ModuleType:
    """Import a module that lives outside any package (tools/, scripts/) by file
    path, exactly as the engine's own tests do (test_validate_creation_structure)."""
    path = ENGINE_DIR / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --- compact_workflow: the semantic-equivalence oracle -----------------------
_compact = _load_by_path("occ_compact_workflow", "tools/compact_workflow.py")
oracle = _compact._oracle  # WorkflowDefinition.from_dict(doc).to_dict()

#: {node-scope -> {field: default}} — a field at its default carries no meaning
#: (except ``position`` and a non-empty ``description``, which are absent here).
SEMANTIC_NULL_FIELDS = {
    "function": dict(_compact._FUNC_DEFAULTS),
    "call": dict(_compact._CALL_DEFAULTS),
    "subworkflow": dict(_compact._SW_DEFAULTS),
}

# --- validate_workflow: the conformance oracle -------------------------------
_validate = _load_by_path("occ_validate_workflow", "scripts/validate_workflow.py")
check_workflow = _validate.check_workflow
derive_homed_kinds = _validate.derive_homed_kinds
called_targets = _validate.called_targets
load_registry = _validate.load_registry

# --- microc_golden: the numeric result diff ----------------------------------
_golden = _load_by_path("occ_microc_golden", "tools/migration/microc_golden.py")
compare_snapshots = _golden.compare
save_snapshot = _golden.save_snapshot
load_snapshot = _golden.load_snapshot


def load_workflow_json(path) -> dict:
    """Raw JSON of a workflow file (no engine parsing)."""
    import json

    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical(doc: dict) -> dict:
    """Engine canonical form: fills defaults, drops unknowns, stabilizes shape.
    Two docs differing only in GUI noise canonicalize identically."""
    return oracle(doc)


__all__ = [
    "REPO_ROOT",
    "ENGINE_DIR",
    "oracle",
    "canonical",
    "SEMANTIC_NULL_FIELDS",
    "check_workflow",
    "derive_homed_kinds",
    "called_targets",
    "load_registry",
    "compare_snapshots",
    "save_snapshot",
    "load_snapshot",
    "load_workflow_json",
]
