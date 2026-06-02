"""PhysiCell black-box facade backend.

When a workflow declares ``kernel: "physicell"``, the executor hands the
run off to this module instead of stepping through Python stages. The
backend:

1. Lifts the codegen spec out of the workflow JSON.
2. Generates a project directory under ``context['output_dir']``.
3. Runs ``make`` in that directory (uses ``PHYSICELL_CPP`` env var if set).
4. Spawns the built binary and tails ``output/occ_events.jsonl``
   line-by-line, forwarding events to stdout (prefixed ``[OCC_EVENT]``)
   so the existing Flask SSE log pipe surfaces them to the GUI.

PhysiBoSS-master location:
- ``PHYSIBOSS_ROOT`` env var, if set.
- Otherwise: walk up from this file looking for a sibling
  ``PhysiBoSS-master/`` directory.

See ``docs/Physicell_Facade_plan.md`` §4 Phase 4.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from opencellcomms_adapters.PhysiBoSS.codegen.scaffold import SpecError, generate_project
from opencellcomms_adapters.PhysiBoSS.codegen.spec_from_workflow import (
    WorkflowSpecError,
    spec_from_workflow,
)

# Prefix on every tailed event line. The GUI's log consumer can grep for
# this to split observability events from PhysiCell's own stdout.
EVENT_PREFIX = "[OCC_EVENT] "

# How often the tail thread polls for new bytes.
_TAIL_POLL_SECONDS = 0.1
# Cap on how long we wait for the binary to start writing the JSONL.
_INIT_WAIT_SECONDS = 30.0


class PhysiCellBackendError(RuntimeError):
    """Raised when codegen, make, or the native run fails."""


# -- PhysiBoSS root discovery -------------------------------------------------

def _find_physiboss_root() -> Path:
    explicit = os.environ.get("PHYSIBOSS_ROOT")
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not (p / "core").is_dir():
            raise PhysiCellBackendError(
                f"PHYSIBOSS_ROOT={p} does not look like a PhysiBoSS-master "
                f"tree (missing core/ subdirectory)."
            )
        return p

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "PhysiBoSS-master"
        if (candidate / "core").is_dir():
            return candidate

    raise PhysiCellBackendError(
        "Could not locate PhysiBoSS-master/. Set PHYSIBOSS_ROOT or place it "
        "as a sibling of the OpenCellComms repo."
    )


# -- JSONL tailing ------------------------------------------------------------

def _tail_jsonl(jsonl_path: Path, stop_event: threading.Event) -> None:
    """Read appended lines from jsonl_path until stop_event fires.

    Each complete line is written to the parent process's stdout prefixed
    with EVENT_PREFIX. Partial lines are buffered until terminated.
    """
    deadline = time.monotonic() + _INIT_WAIT_SECONDS
    while not jsonl_path.exists():
        if stop_event.is_set():
            return
        if time.monotonic() > deadline:
            print(f"[BACKEND] timed out waiting for {jsonl_path.name} to appear")
            return
        time.sleep(_TAIL_POLL_SECONDS)

    buf = ""
    with jsonl_path.open("r") as f:
        while True:
            chunk = f.read()
            if chunk:
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if line:
                        sys.stdout.write(EVENT_PREFIX + line + "\n")
                        sys.stdout.flush()
                continue
            if stop_event.is_set():
                # Final drain: anything left after the binary exited.
                tail = f.read()
                if tail:
                    buf += tail
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        if line:
                            sys.stdout.write(EVENT_PREFIX + line + "\n")
                            sys.stdout.flush()
                return
            time.sleep(_TAIL_POLL_SECONDS)


def _sanitize_name(raw: str) -> str:
    """[A-Za-z0-9_] only — collapses other chars to '_'. Makefile-safe."""
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_")
    return safe or "physicell_workflow"


# -- Lower-level entry: run a fully assembled spec --------------------------

def run_with_spec(
    spec: Dict[str, Any],
    output_dir: Path,
    name: str = "physicell_workflow",
) -> Dict[str, Any]:
    """Codegen → make → spawn → tail, given an already-assembled spec dict.

    The composable workflow node and the legacy kernel-dispatch path both
    funnel through here.

    Returns:
        {"project_dir", "binary_path", "exit_code", "events_jsonl"}
    """
    safe_name = _sanitize_name(name)
    physiboss_root = _find_physiboss_root()
    print(f"[BACKEND] PhysiBoSS-master: {physiboss_root}")

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[BACKEND] Codegen: {len(spec.get('substrates') or [])} substrates, "
          f"{len(spec.get('cell_types') or [])} cell types, "
          f"{len(spec.get('hill_rules') or [])} Hill rules")
    try:
        project_dir = generate_project(
            spec=spec,
            output_dir=output_dir,
            physiboss_root=physiboss_root,
            project_name=f"{safe_name}_project",
        )
    except SpecError as e:
        raise PhysiCellBackendError(f"Codegen failed: {e}") from e
    print(f"[BACKEND] Project: {project_dir}")

    # -- make ----------------------------------------------------------------
    print("[BACKEND] make -j2 ...")
    build = subprocess.run(
        ["make", "-j2"],
        cwd=project_dir,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if build.returncode != 0:
        raise PhysiCellBackendError(
            "make failed. Set PHYSICELL_CPP to an OpenMP-capable g++.\n"
            f"stderr tail:\n{build.stderr[-2000:]}"
        )

    binary = project_dir / f"{safe_name}_project"
    if not binary.exists():
        raise PhysiCellBackendError(
            f"make succeeded but binary {binary} not found. "
            f"stdout tail:\n{build.stdout[-500:]}"
        )

    # -- run + tail ----------------------------------------------------------
    jsonl_path = project_dir / "output" / "occ_events.jsonl"
    stop_event = threading.Event()
    tail_thread = threading.Thread(
        target=_tail_jsonl, args=(jsonl_path, stop_event), daemon=True
    )
    tail_thread.start()

    print(f"[BACKEND] running {binary.name} ...")
    proc = subprocess.Popen(
        [str(binary)],
        cwd=project_dir,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
    finally:
        exit_code = proc.wait()
        stop_event.set()
        tail_thread.join(timeout=5)

    if exit_code != 0:
        raise PhysiCellBackendError(f"{binary.name} exited with code {exit_code}")

    print(f"[BACKEND] done. events: {jsonl_path}")

    return {
        "project_dir": str(project_dir),
        "binary_path": str(binary),
        "exit_code": exit_code,
        "events_jsonl": str(jsonl_path),
    }


# -- Public entry point (legacy kernel-dispatch path) ------------------------

def run(workflow: Union[Dict[str, Any], Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Codegen → make → spawn → tail for `kernel: physicell` workflows.

    Builds a spec by walking the workflow JSON (define_* nodes). Kept for
    back-compat; new workflows should prefer the composable pattern with
    `run_physicell_simulation` as a function node.
    """
    workflow_dict = _coerce_to_dict(workflow)
    raw_name = workflow_dict.get("name") or "physicell_workflow"
    name = _sanitize_name(raw_name)

    try:
        spec = spec_from_workflow(workflow_dict)
    except WorkflowSpecError as e:
        raise PhysiCellBackendError(f"Workflow → spec failed: {e}") from e

    output_dir = Path(context.get("output_dir") or f"./results/physicell_{name}").resolve()
    results = run_with_spec(spec, output_dir, name=name)
    context["physicell"] = results
    return context


# -- helpers -----------------------------------------------------------------

def _coerce_to_dict(workflow: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    if isinstance(workflow, dict):
        return workflow
    if hasattr(workflow, "to_dict"):
        return workflow.to_dict()
    raise PhysiCellBackendError(
        f"Cannot interpret {type(workflow).__name__} as a workflow definition"
    )


__all__ = ["run", "run_with_spec", "PhysiCellBackendError", "EVENT_PREFIX"]
