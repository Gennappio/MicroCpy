"""
NodeEventEmitter: Writes structured node execution events to JSONL.

Events are appended to results/observability/events.jsonl during execution.
Each run overwrites previous data (no run history).
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class NodeEventEmitter:
    """
    Emits structured events for node execution observability.
    
    Thread-safe: uses a lock for file writes.
    """
    
    def __init__(self, results_dir: Path, enabled: bool = True):
        """
        Initialize the event emitter.
        
        Args:
            results_dir: Base results directory (e.g., Path('results'))
            enabled: Whether event emission is enabled (default True)
        """
        self.results_dir = Path(results_dir)
        self.enabled = enabled
        self._lock = threading.Lock()
        self._events_file: Optional[Path] = None
        self._initialized = False
        
    def initialize(self) -> None:
        """
        Initialize observability directory and files.
        
        Creates results/observability/ and clears previous data.
        Should be called once at the start of a run.
        """
        if not self.enabled:
            return
            
        obs_dir = self.results_dir / "observability"
        obs_dir.mkdir(parents=True, exist_ok=True)
        
        # Clear and create events file
        self._events_file = obs_dir / "events.jsonl"
        self._events_file.write_text("")  # Clear previous content
        
        # Write run metadata
        meta_file = obs_dir / "run_meta.json"
        meta = {
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "status": "running",
        }
        meta_file.write_text(json.dumps(meta, indent=2))
        
        self._initialized = True
        
    def finalize(self, status: str = "completed") -> None:
        """
        Finalize the run metadata.
        
        Args:
            status: Final run status (completed, failed, cancelled)
        """
        if not self.enabled or not self._initialized:
            return
            
        meta_file = self.results_dir / "observability" / "run_meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            meta["status"] = status
            meta["endedAt"] = datetime.now(timezone.utc).isoformat()
            meta_file.write_text(json.dumps(meta, indent=2))
    
    def _emit(self, event: Dict[str, Any]) -> None:
        """Write an event to the JSONL file (thread-safe)."""
        if not self.enabled or not self._initialized or self._events_file is None:
            return
            
        # Add timestamp if not present
        if "ts" not in event:
            event["ts"] = datetime.now(timezone.utc).isoformat()
            
        with self._lock:
            with open(self._events_file, "a") as f:
                f.write(json.dumps(event) + "\n")
    
    def emit_node_start(
        self,
        node_id: str,
        function_name: str,
        subworkflow_kind: str,
        subworkflow_name: str,
        execution_id: Optional[str] = None,
        before_context_version: Optional[int] = None,
        call_path: Optional[List[str]] = None,
        node_type: str = "workflowFunction",
        step_index: Optional[int] = None,
        time_value: Optional[float] = None,
    ) -> str:
        """
        Emit a node_start event.
        
        Returns:
            execution_id: The execution ID for this node execution
        """
        exec_id = execution_id or str(uuid.uuid4())
        
        self._emit({
            "event": "node_start",
            "level": "INFO",
            "kind": subworkflow_kind,
            "subworkflowKind": subworkflow_kind,
            "subworkflowName": subworkflow_name,
            "nodeId": node_id,
            "nodeType": node_type,
            "functionName": function_name,
            "executionId": exec_id,
            "callPath": call_path or [],
            "payload": {
                "beforeContextVersion": before_context_version,
                "stepIndex": step_index,
                "time": time_value,
            }
        })
        
        return exec_id
    
    def emit_node_end(
        self,
        node_id: str,
        function_name: str,
        subworkflow_kind: str,
        subworkflow_name: str,
        execution_id: str,
        status: str,
        duration_ms: float,
        after_context_version: Optional[int] = None,
        written_keys: Optional[List[str]] = None,
        read_keys: Optional[List[str]] = None,
        call_path: Optional[List[str]] = None,
        node_type: str = "workflowFunction",
        error_message: Optional[str] = None,
    ) -> None:
        """Emit a node_end event."""
        level = "ERROR" if status == "error" else "INFO"
        
        self._emit({
            "event": "node_end",
            "level": level,
            "kind": subworkflow_kind,
            "subworkflowKind": subworkflow_kind,
            "subworkflowName": subworkflow_name,
            "nodeId": node_id,
            "nodeType": node_type,
            "functionName": function_name,
            "executionId": execution_id,
            "callPath": call_path or [],
            "payload": {
                "status": status,
                "durationMs": duration_ms,
                "afterContextVersion": after_context_version,
                "writtenKeys": written_keys or [],
                "readKeys": read_keys or [],
                "errorMessage": error_message,
            }
        })

    def emit_log(
        self,
        message: str,
        level: str = "INFO",
        node_id: Optional[str] = None,
        function_name: Optional[str] = None,
        subworkflow_kind: Optional[str] = None,
        subworkflow_name: Optional[str] = None,
        execution_id: Optional[str] = None,
        logger_name: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        """Emit a log event."""
        self._emit({
            "event": "log",
            "level": level.upper(),
            "kind": subworkflow_kind,
            "subworkflowKind": subworkflow_kind,
            "subworkflowName": subworkflow_name,
            "nodeId": node_id,
            "functionName": function_name,
            "executionId": execution_id,
            "payload": {
                "message": message,
                "loggerName": logger_name,
                "source": source,
            }
        })

    def emit_context_write(
        self,
        key: str,
        node_id: Optional[str] = None,
        subworkflow_kind: Optional[str] = None,
        subworkflow_name: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> None:
        """Emit a context_write event."""
        self._emit({
            "event": "context_write",
            "level": "DEBUG",
            "kind": subworkflow_kind,
            "subworkflowKind": subworkflow_kind,
            "subworkflowName": subworkflow_name,
            "nodeId": node_id,
            "executionId": execution_id,
            "payload": {
                "key": key,
            }
        })

    def emit_context_read(
        self,
        key: str,
        node_id: Optional[str] = None,
        subworkflow_kind: Optional[str] = None,
        subworkflow_name: Optional[str] = None,
        execution_id: Optional[str] = None,
    ) -> None:
        """Emit a context_read event."""
        self._emit({
            "event": "context_read",
            "level": "DEBUG",
            "kind": subworkflow_kind,
            "subworkflowKind": subworkflow_kind,
            "subworkflowName": subworkflow_name,
            "nodeId": node_id,
            "executionId": execution_id,
            "payload": {
                "key": key,
            }
        })

