"""
Node Observability module for MicroC workflow system.

Provides runtime instrumentation for debugging and inspecting workflow execution:
- NodeEventEmitter: Writes structured events to JSONL
- TrackedContext: Wrapper that tracks read/write operations
- ValidatedContext: TrackedContext with write policy enforcement
- ContextSnapshot: Immutable snapshots of context state
"""

from .event_emitter import NodeEventEmitter
from .tracked_context import TrackedContext
from .validated_context import ValidatedContext, ContextWriteError
from .context_snapshot import ContextSnapshotManager

__all__ = [
    'NodeEventEmitter',
    'TrackedContext',
    'ValidatedContext',
    'ContextWriteError',
    'ContextSnapshotManager',
]

