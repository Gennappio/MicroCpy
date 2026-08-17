#!/usr/bin/env python3
"""
Flask Backend API for OpenCellComms GUI
Provides endpoints for running simulations and streaming logs in real-time
"""

import os
import sys
import json
import re
import signal
import subprocess
import threading
import queue
import time
import shutil
import ast
import inspect
import tempfile
import tomllib
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS

import agent  # In-GUI Claude coding agent (config + code generation)

app = Flask(__name__)
BACKEND_HOST = os.environ.get("OPENCELLCOMMS_API_HOST", "127.0.0.1")
BACKEND_PORT = 5001
LOCAL_GUI_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
CORS(app, resources={r"/api/*": {"origins": LOCAL_GUI_ORIGINS}})

IS_WINDOWS = sys.platform == 'win32'


def _kill_process_tree(pid, force=False):
    """Kill a process and all its children. Works on Windows, macOS, and Linux."""
    if IS_WINDOWS:
        # taskkill /T kills the entire process tree, /F forces it
        subprocess.run(
            ['taskkill', '/T', '/F', '/PID', str(pid)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    else:
        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.killpg(os.getpgid(pid), sig)
        except (ProcessLookupError, OSError):
            pass

# Global state for simulation process
simulation_process = None
simulation_thread = None
log_queue = queue.Queue()
is_running = False
last_run_status = "idle"
last_exit_code = None

# PID file for cross-refresh / cross-restart recovery
PID_FILE = Path(__file__).parent / ".current_process.pid"

# Base directory for all simulation outputs: <repo-root>/runs/<label>/<subworkflow>/
# One place, shared by GUI and CLI (the engine writes here via --gui-results-dir).
# parents[0]=server, [1]=opencellcomms_gui, [2]=repo root.
RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"
REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_DIR = REPO_ROOT / "opencellcomms_engine"
ENGINE_SOURCE_DIR = ENGINE_DIR / "src"
ADAPTERS_DIR = REPO_ROOT / "opencellcomms_adapters"
EXPORTS_DIR = ENGINE_DIR / "exports"


class PathPolicyError(ValueError):
    """A client-supplied path violates an API filesystem boundary."""


def _resolve_allowed_path(
    raw_path,
    *,
    roots,
    bases=None,
    suffixes=None,
    must_exist=False,
    require_file=False,
    allow_absolute=False,
):
    """Resolve a path and prove that it remains under an allowed root.

    Resolution happens before containment checking, so ``..`` components and
    symlinks cannot escape by string-prefix tricks. Client-facing endpoints
    reject absolute paths; server-owned registry paths may opt in explicitly.
    """
    if raw_path is None or str(raw_path).strip() == "":
        raise PathPolicyError("A non-empty path is required")

    supplied = Path(str(raw_path))
    if supplied.is_absolute() and not allow_absolute:
        raise PathPolicyError("Absolute paths are not accepted")

    resolved_roots = tuple(Path(root).resolve() for root in roots)
    candidate_bases = tuple(Path(base).resolve() for base in (bases or (REPO_ROOT,)))
    candidates = (
        (supplied.resolve(),)
        if supplied.is_absolute()
        else tuple((base / supplied).resolve() for base in candidate_bases)
    )

    target = next(
        (
            candidate
            for candidate in candidates
            if any(candidate == root or candidate.is_relative_to(root) for root in resolved_roots)
        ),
        None,
    )
    if target is None:
        raise PathPolicyError("Path is outside the allowed project roots")

    if suffixes is not None and target.suffix.lower() not in {
        suffix.lower() for suffix in suffixes
    }:
        raise PathPolicyError(
            f"File type {target.suffix or '(none)'} is not allowed"
        )
    if must_exist and not target.exists():
        raise FileNotFoundError(target)
    if require_file and target.exists() and not target.is_file():
        raise PathPolicyError("Path must identify a file")
    return target


def _enabled_code_roots():
    """Engine source plus adapter directories enabled for discovery."""
    roots = [ENGINE_SOURCE_DIR]
    try:
        engine_dir = get_engine_path().parent
        for path in (engine_dir, engine_dir.parent):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        from src.workflow.registry import discover_adapter_names

        roots.extend(ADAPTERS_DIR / name for name in discover_adapter_names(ADAPTERS_DIR))
    except Exception:
        # The engine tree is always safe and remains useful if plugin discovery
        # itself is temporarily broken.
        pass
    return roots


def safe_run_label(value):
    """Return a non-traversing directory name for a user-visible run label."""
    normalized = re.sub(r'[^\w.-]+', '_', str(value or ''), flags=re.UNICODE)
    return normalized.strip('._') or 'default'


def get_engine_path():
    """Get the path to OpenCellComms run_workflow.py"""
    # Server is in opencellcomms_gui/server, engine is in ../opencellcomms_engine
    server_dir = Path(__file__).parent
    engine_path = server_dir.parent.parent / "opencellcomms_engine" / "run_workflow.py"
    return engine_path


def stream_output(process, log_queue):
    """Stream stdout and stderr from subprocess to queue"""
    global is_running, last_run_status, last_exit_code
    def enqueue_output(pipe, queue, prefix):
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    queue.put(f"{prefix}{line}")
                    # Recovery channel: also mirror to the server terminal so logs
                    # are visible even if the GUI SSE stream isn't delivering.
                    sys.stdout.write(f"{prefix}{line}")
                    sys.stdout.flush()
        except Exception as e:
            queue.put(f"[ERROR] Stream error: {e}\n")
        finally:
            pipe.close()

    # Start threads for stdout and stderr.
    # NOTE: the prefix is purely the *channel*, not a severity. Everything the
    # subprocess writes to stderr is tagged "[ERROR]" — including benign Python
    # warnings (e.g. the engine's legacy-signature UserWarnings) and library
    # chatter. A red "[ERROR]" line in the GUI is therefore NOT necessarily a
    # failure; only treat the process exit code / explicit error messages as
    # fatal. (The legacy-signature flood is silenced at source by default; set
    # OCC_WARN_LEGACY_CONTEXT=1 to bring it back.)
    stdout_thread = threading.Thread(
        target=enqueue_output,
        args=(process.stdout, log_queue, "[LOG] ")
    )
    stderr_thread = threading.Thread(
        target=enqueue_output,
        args=(process.stderr, log_queue, "[ERROR] ")
    )
    
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    stdout_thread.start()
    stderr_thread.start()
    
    # Wait for process to complete
    process.wait()
    
    # Signal completion
    if process.returncode == 0:
        log_queue.put("[COMPLETE] Simulation completed successfully\n")
        last_run_status = "completed"
    else:
        log_queue.put(f"[FAILED] Simulation failed with exit code {process.returncode}\n")
        last_run_status = "failed"
    last_exit_code = process.returncode

    is_running = False
    PID_FILE.unlink(missing_ok=True)


def run_simulation_async(workflow_path, entry_subworkflow=None, gui_results_dir=None):
    """Run OpenCellComms workflow in background thread (workflow-only mode)"""
    global simulation_process, is_running, last_run_status, last_exit_code

    try:
        engine_path = get_engine_path()

        if not engine_path.exists():
            log_queue.put(f"[ERROR] OpenCellComms engine not found at: {engine_path}\n")
            is_running = False
            last_run_status = "failed"
            last_exit_code = None
            return

        # Get engine directory (working directory for simulation)
        engine_dir = engine_path.parent

        # Build command - GUI runs workflows only
        if not workflow_path:
            log_queue.put(f"[ERROR] Workflow path must be provided\n")
            is_running = False
            last_run_status = "failed"
            last_exit_code = None
            return

        # === Pass this run's output dir to the engine (it appends the subworkflow).
        # If omitted, the engine auto-derives runs/<workflow-stem>.
        cmd = [
            sys.executable,
            str(engine_path),
            "--workflow",
            workflow_path,
        ]
        if gui_results_dir:
            cmd += ["--gui-results-dir", str(Path(gui_results_dir).absolute())]

        # Add entry_subworkflow parameter if specified (Section 9.2).
        # 'main' is the GUI-synthesized top-level composer — internal plumbing,
        # so we don't surface it in the user-facing log.
        if entry_subworkflow:
            cmd.extend(["--entry-subworkflow", entry_subworkflow])
        else:
            log_queue.put(f"[START] Running workflow-only mode: {workflow_path}\n")

        log_queue.put(f"[INFO] Command: {' '.join(cmd)}\n")
        log_queue.put(f"[INFO] Working directory: {engine_dir}\n")
        log_queue.put("[INFO] Starting OpenCellComms simulation...\n")

        # Start subprocess with correct working directory
        # Create a new process group so we can kill the entire tree
        # Force unbuffered stdout in the engine (and its nested subprocess, which
        # copies os.environ) so log lines stream live instead of arriving in one
        # block-buffered dump when the process exits.
        child_env = os.environ.copy()
        child_env["PYTHONUNBUFFERED"] = "1"
        # Force UTF-8 for the engine's own stdout/stderr too (not just its nested
        # tools). Without this, Windows decodes the pipe as cp1252 and any non-ASCII
        # log line (Greek gene names, °, µ, emoji) raises UnicodeDecodeError here.
        child_env["PYTHONIOENCODING"] = "utf-8"

        popen_kwargs = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(engine_dir),
            env=child_env,
        )
        if IS_WINDOWS:
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs['start_new_session'] = True

        simulation_process = subprocess.Popen(cmd, **popen_kwargs)

        # Persist PID for cross-refresh / cross-restart recovery
        PID_FILE.write_text(str(simulation_process.pid))

        # Stream output
        stream_output(simulation_process, log_queue)
        
    except Exception as e:
        log_queue.put(f"[ERROR] Failed to start simulation: {e}\n")
        is_running = False
        last_run_status = "failed"
        last_exit_code = None


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current simulation status"""
    return jsonify({
        'running': is_running,
        'pid': simulation_process.pid if simulation_process else None,
        'status': last_run_status,
        'exit_code': last_exit_code,
    })


@app.route('/api/run', methods=['POST'])
def run_simulation():
    """Start a new simulation (Section 9.2: supports entry_subworkflow parameter)"""
    global simulation_thread, is_running, last_run_status, last_exit_code

    # Check if the process is actually still alive; reset stale flag if not
    if is_running:
        if simulation_process is not None and simulation_process.poll() is not None:
            # Process has already exited but flag was not cleared
            is_running = False
        else:
            return jsonify({'error': 'Simulation already running'}), 400

    data = request.json
    workflow_data = data.get('workflow')   # Workflow definition is required
    entry_subworkflow = data.get('entry_subworkflow', 'main')  # Default to 'main'
    run_label = data.get('run_label')  # Optional label for planner multi-run

    # Must have a workflow definition
    if not workflow_data:
        return jsonify({'error': 'Workflow is required'}), 400

    # Validate workflow before running
    try:
        # Import workflow schema for validation
        engine_path = get_engine_path()
        engine_dir = engine_path.parent
        sys.path.insert(0, str(engine_dir))

        from src.workflow.schema import WorkflowDefinition

        # Load and validate workflow
        workflow_obj = WorkflowDefinition.from_dict(workflow_data)
        validation_result = workflow_obj.validate()

        if not validation_result['valid']:
            error_messages = validation_result['errors']
            error_text = '\n'.join(error_messages)
            log_queue.put(f"[ERROR] Workflow validation failed:\n{error_text}\n")
            return jsonify({
                'error': 'Workflow validation failed',
                'details': error_messages
            }), 400

        # Log warnings if any
        if validation_result.get('warnings'):
            for warning in validation_result['warnings']:
                log_queue.put(f"[WARNING] {warning}\n")

    except Exception as e:
        import traceback
        error_msg = f'Workflow validation error: {str(e)}'
        log_queue.put(f"[ERROR] {error_msg}\n")
        log_queue.put(f"[ERROR] Traceback:\n{traceback.format_exc()}\n")
        return jsonify({'error': error_msg}), 400

    # Validate entry_subworkflow (Section 9.2)
    if workflow_data.get('version') == '2.0':
        subworkflows = workflow_data.get('subworkflows', {})

        # Check if entry_subworkflow exists
        if entry_subworkflow not in subworkflows:
            error_msg = f'Entry subworkflow "{entry_subworkflow}" not found in workflow'
            log_queue.put(f"[ERROR] {error_msg}\n")
            return jsonify({'error': error_msg}), 400

        # Check if entry_subworkflow is a composer (Section 9.2).
        # Phase 14B: subworkflow_kinds is no longer persisted to JSON (the GUI
        # derives it at load time and strips it on export), so fall back to the
        # same default the engine uses: 'main' is a composer, others are not.
        metadata = workflow_data.get('metadata', {})
        gui_metadata = metadata.get('gui', {})
        subworkflow_kinds = gui_metadata.get('subworkflow_kinds', {})

        entry_kind = subworkflow_kinds.get(
            entry_subworkflow,
            'composer' if entry_subworkflow == 'main' else 'subworkflow'
        )
        if entry_kind != 'composer':
            error_msg = f'Entry subworkflow "{entry_subworkflow}" must be a composer (found: {entry_kind})'
            log_queue.put(f"[ERROR] {error_msg}\n")
            return jsonify({'error': error_msg}), 400

        log_queue.put(f"[INFO] Entry subworkflow: {entry_subworkflow} (composer)\n")

    # Set up this run's output directory: runs/<label>/, overwrite same label.
    # Planner runs pass run_label (WT, KO, ...); standard runs default to the
    # workflow name. Both write into the same top-level runs/ tree.
    try:
        label = run_label or getattr(workflow_obj, 'name', None) or 'default'
        safe_label = safe_run_label(label)
        run_dir = RUNS_DIR / safe_label
        if run_dir.is_symlink():
            raise PathPolicyError("Run directory may not be a symlink")
        run_dir = _resolve_allowed_path(
            run_dir,
            roots=(RUNS_DIR,),
            allow_absolute=True,
        )
        if run_dir.exists():
            shutil.rmtree(run_dir)
            log_queue.put(f"[INFO] Cleared runs/{safe_label} directory\n")
        run_dir.mkdir(parents=True, exist_ok=True)
        log_queue.put(f"[INFO] runs/{safe_label} directory ready\n")

        # Planner multi-run: the GUI sends keep_labels = all current planner tabs.
        # Prune run folders for tabs that were removed/renamed so the Results tab
        # mirrors the planner. Only runs when keep_labels is provided.
        keep_labels = data.get('keep_labels')
        if keep_labels is not None:
            keep = {
                safe_run_label(l)
                for l in keep_labels
            } | {safe_label}
            for item in RUNS_DIR.iterdir():
                if (
                    item.is_dir()
                    and not item.is_symlink()
                    and not item.name.startswith('.')
                    and item.name not in keep
                ):
                    stale_dir = _resolve_allowed_path(
                        item,
                        roots=(RUNS_DIR,),
                        allow_absolute=True,
                    )
                    shutil.rmtree(stale_dir, ignore_errors=True)
                    log_queue.put(f"[INFO] Removed stale results folder '{item.name}'\n")
    except PathPolicyError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        error_msg = f'Failed to setup results directories: {str(e)}'
        log_queue.put(f"[ERROR] {error_msg}\n")
        return jsonify({'error': error_msg}), 500

    # Save workflow to a temp file (planner runs get a per-label temp file so
    # concurrent conditions don't collide).
    temp_label = safe_run_label(run_label) if run_label else ''
    workflow_path = str(Path(tempfile.gettempdir()) / (f"opencellcomms_workflow_{temp_label}.json" if run_label else "opencellcomms_workflow.json"))
    try:
        with open(workflow_path, 'w') as f:
            json.dump(workflow_data, f, indent=2)
    except Exception as e:
        return jsonify({'error': f'Failed to save workflow: {e}'}), 500

    # Clear log queue
    while not log_queue.empty():
        log_queue.get()

    # Hand the engine this run's output dir so GUI and CLI agree on the location.
    gui_results_dir_for_run = str(run_dir)

    # Start simulation in background thread
    is_running = True
    last_run_status = "running"
    last_exit_code = None
    simulation_thread = threading.Thread(
        target=run_simulation_async,
        args=(workflow_path, entry_subworkflow, gui_results_dir_for_run)
    )
    simulation_thread.daemon = True
    simulation_thread.start()

    return jsonify({
        'status': 'started',
        'workflow': workflow_path,
        'entry_subworkflow': entry_subworkflow
    })


@app.route('/api/stop', methods=['POST'])
def stop_simulation():
    """Stop the running simulation"""
    global is_running

    # Gate on process liveness, not is_running flag (survives page refresh)
    if simulation_process is None or simulation_process.poll() is not None:
        return jsonify({'error': 'No simulation running'}), 400

    try:
        _kill_process_tree(simulation_process.pid, force=False)
        simulation_process.wait(timeout=5)
        log_queue.put("[STOP] Simulation stopped by user\n")
        is_running = False
        PID_FILE.unlink(missing_ok=True)
        return jsonify({'status': 'stopped'})
    except subprocess.TimeoutExpired:
        _kill_process_tree(simulation_process.pid, force=True)
        log_queue.put("[STOP] Simulation forcefully killed\n")
        is_running = False
        PID_FILE.unlink(missing_ok=True)
        return jsonify({'status': 'killed'})
    except (ProcessLookupError, OSError):
        # Process already gone
        is_running = False
        PID_FILE.unlink(missing_ok=True)
        return jsonify({'status': 'stopped'})
    except Exception as e:
        return jsonify({'error': f'Failed to stop simulation: {e}'}), 500


@app.route('/api/force-kill', methods=['POST'])
def force_kill():
    """Kill any running process — works even after page refresh or server restart"""
    global is_running
    pid = None

    # Try in-memory process first
    if simulation_process is not None and simulation_process.poll() is None:
        pid = simulation_process.pid
    # Fall back to PID file (survives Flask restarts)
    elif PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
        except ValueError:
            pass

    if pid is None:
        return jsonify({'error': 'No process found'}), 404

    _kill_process_tree(pid, force=True)

    PID_FILE.unlink(missing_ok=True)
    is_running = False
    log_queue.put("[STOP] Process forcefully killed\n")
    return jsonify({'status': 'killed', 'pid': pid})


@app.route('/api/logs', methods=['GET'])
def stream_logs():
    """Stream logs using Server-Sent Events (SSE)"""
    def generate():
        """Generator function for SSE"""
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'message': 'Log stream connected'})}\n\n"
        
        last_heartbeat = time.time()
        
        while True:
            try:
                # Drain up to 50 messages from the queue within a 50 ms window.
                # This caps SSE delivery to ~20 bursts/sec regardless of log volume,
                # preventing the browser from being flooded with individual SSE events.
                batch = []
                deadline = time.time() + 0.05
                while time.time() < deadline and len(batch) < 50:
                    try:
                        batch.append(log_queue.get_nowait())
                    except queue.Empty:
                        break

                if batch:
                    last_heartbeat = time.time()
                    for log_line in batch:
                        log_type = 'info'
                        if log_line.startswith('[ERROR]'):
                            log_type = 'error'
                        elif log_line.startswith('[COMPLETE]'):
                            log_type = 'complete'
                        elif log_line.startswith('[FAILED]'):
                            log_type = 'error'
                        elif log_line.startswith('[STOP]'):
                            log_type = 'warning'
                        yield f"data: {json.dumps({'type': log_type, 'message': log_line})}\n\n"
                else:
                    # Idle: send heartbeat if needed, then sleep to avoid busy-wait
                    if time.time() - last_heartbeat > 15:
                        yield f"data: {json.dumps({'type': 'heartbeat', 'message': ''})}\n\n"
                        last_heartbeat = time.time()
                    time.sleep(0.05)

            except GeneratorExit:
                # Client disconnected
                break
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'engine_path': str(get_engine_path()),
        'engine_exists': get_engine_path().exists()
    })


@app.route('/api/cli-info', methods=['GET'])
def cli_info():
    """
    Return the paths the GUI needs to build 'run from terminal' commands.

    Everything is resolved server-side so the displayed commands stay accurate
    no matter where the project lives (engine dir, python interpreter, and the
    temp file the GUI writes the current workflow to before each run).
    """
    engine_path = get_engine_path()
    return jsonify({
        'python': sys.executable,
        'engine_dir': str(engine_path.parent),
        'run_workflow': engine_path.name,  # run_workflow.py
        # Path the GUI writes the current workflow to on every (unlabeled) run.
        # Must match the path built in run_simulation().
        'gui_temp_workflow': str(Path(tempfile.gettempdir()) / "opencellcomms_workflow.json"),
        # A concrete runs/<label> dir so the 'run from terminal' command reproduces
        # a labeled run (the engine appends the subworkflow name).
        'gui_results_dir': str((RUNS_DIR / 'default').absolute()),
    })


@app.route('/api/registry', methods=['GET'])
def get_registry():
    """
    Get the full function registry from the Python backend.

    Returns:
        {
            'success': true,
            'functions': {
                'function_name': {
                    'name': 'function_name',
                    'display_name': 'Display Name',
                    'description': 'Description',
                    'category': 'INTRACELLULAR',
                    'parameters': [...],
                    'inputs': [...],
                    'outputs': [...],
                    'cloneable': true/false,
                    'module_path': '...',
                    'source_file': '...'
                },
                ...
            },
            'count': 62
        }
    """
    try:
        # Get engine directory
        engine_dir = get_engine_path().parent

        # Add to Python path
        sys.path.insert(0, str(engine_dir))
        # Add parent directory so opencellcomms_adapters can be imported
        sys.path.insert(0, str(engine_dir.parent))

        # Import registry
        from src.workflow.registry import get_default_registry

        # Get the registry
        registry = get_default_registry()

        # Convert to JSON-serializable format
        functions_dict = {
            name: metadata.to_dict()
            for name, metadata in registry.functions.items()
        }

        return jsonify({
            'success': True,
            'functions': functions_dict,
            'count': len(functions_dict)
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': f'Failed to load registry: {e}',
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/plugins', methods=['GET'])
def list_plugins():
    """
    List installed plugins (adapters): manifest metadata + their functions.

    Returns:
        { success, count, plugins: [
            { name, path, has_manifest, manifest: {name, version, description,
              author, engine_version, compatible_kernels}, functions: [...] }
        ] }
    """
    try:
        import tomllib

        engine_dir = get_engine_path().parent
        sys.path.insert(0, str(engine_dir))
        sys.path.insert(0, str(engine_dir.parent))
        from src.workflow.registry import get_default_registry, discover_adapter_names

        adapters_root = engine_dir.parent / 'opencellcomms_adapters'
        names = discover_adapter_names(adapters_root)
        registry = get_default_registry()

        plugins = []
        for name in names:
            manifest_path = adapters_root / name / 'plugin.toml'
            has_manifest = manifest_path.is_file()
            manifest = {}
            if has_manifest:
                try:
                    manifest = tomllib.loads(manifest_path.read_text(encoding='utf-8')).get('plugin', {})
                except Exception as e:
                    manifest = {'_error': f'Failed to parse plugin.toml: {e}'}

            # Functions whose source file lives under this plugin's folder.
            marker = f'opencellcomms_adapters/{name}/'
            functions = sorted(
                fname for fname, md in registry.functions.items()
                if marker in (md.source_file or '').replace('\\', '/')
            )

            plugins.append({
                'name': name,
                'path': f'opencellcomms_adapters/{name}',
                'has_manifest': has_manifest,
                'manifest': manifest,
                'functions': functions,
            })

        return jsonify({'success': True, 'count': len(plugins), 'plugins': plugins})

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': f'Failed to list plugins: {e}',
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/function/source', methods=['GET'])
def get_function_source():
    """
    Get source code for a workflow function.

    Query params:
        - name: Function name (e.g., 'update_metabolism')
        - file: Optional source file path (relative to engine directory)

    Returns:
        {
            'success': true,
            'source': '...',
            'file_path': '...',
            'function_name': '...'
        }
    """
    try:
        function_name = request.args.get('name')
        source_file = request.args.get('file')
        client_supplied_file = bool(source_file)

        if not function_name:
            return jsonify({'error': 'Missing required parameter: name'}), 400

        # Get engine directory
        engine_dir = get_engine_path().parent

        # If source_file is provided, use it; otherwise try to find it from registry
        if not source_file:
            # Try to load from registry
            try:
                sys.path.insert(0, str(engine_dir))
                sys.path.insert(0, str(engine_dir.parent))
                from src.workflow.registry import get_default_registry

                registry = get_default_registry()
                metadata = registry.get(function_name)

                if metadata and metadata.source_file:
                    source_file = metadata.source_file
                else:
                    return jsonify({
                        'error': f'Function "{function_name}" not found in registry or has no source file'
                    }), 404
            except Exception as e:
                return jsonify({'error': f'Failed to load registry: {e}'}), 500

        # Resolve only within engine source or enabled adapter trees. Registry
        # paths are server-owned and may be absolute; client paths may not be.
        try:
            file_path = _resolve_allowed_path(
                source_file,
                roots=_enabled_code_roots(),
                bases=(engine_dir, engine_dir.parent),
                suffixes={'.py'},
                must_exist=True,
                require_file=True,
                allow_absolute=not client_supplied_file,
            )
        except PathPolicyError as e:
            return jsonify({'error': str(e)}), 400
        except FileNotFoundError:
            return jsonify({
                'error': f'Source file not found: {source_file}',
            }), 404

        # Read source code
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            return jsonify({'error': f'Failed to read source file: {e}'}), 500

        return jsonify({
            'success': True,
            'source': source_code,
            'file_path': str(file_path.relative_to(REPO_ROOT)),
            'function_name': function_name
        })

    except Exception as e:
        return jsonify({'error': f'Unexpected error: {e}'}), 500


@app.route('/api/function/save', methods=['POST'])
def save_function_source():
    """
    Save source code for a workflow function.

    Request body:
        {
            'name': 'update_metabolism',
            'source': 'def update_metabolism(...):\n    ...',
            'file': 'src/workflow/functions/intracellular/update_metabolism.py'  # optional
        }

    Returns:
        {
            'success': true,
            'file_path': '...',
            'message': '...'
        }
    """
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        # Accept both field-name variants used across the GUI
        # (CodeViewer sends name/file; ParameterEditor sends function_name/file_path).
        function_name = data.get('name') or data.get('function_name')
        source_code = data.get('source')
        source_file = data.get('file') or data.get('file_path')
        client_supplied_file = bool(source_file)

        if not function_name or not source_code:
            return jsonify({'error': 'Missing required fields: name, source'}), 400

        # Get engine directory
        engine_dir = get_engine_path().parent

        # If source_file is not provided, try to find it from registry
        if not source_file:
            try:
                sys.path.insert(0, str(engine_dir))
                sys.path.insert(0, str(engine_dir.parent))
                from src.workflow.registry import get_default_registry

                registry = get_default_registry()
                metadata = registry.get(function_name)

                if metadata and metadata.source_file:
                    source_file = metadata.source_file
                else:
                    return jsonify({
                        'error': f'Function "{function_name}" not found in registry or has no source file'
                    }), 404
            except Exception as e:
                return jsonify({'error': f'Failed to load registry: {e}'}), 500

        # Resolve file path
        try:
            file_path = _resolve_allowed_path(
                source_file,
                roots=_enabled_code_roots(),
                bases=(engine_dir, engine_dir.parent),
                suffixes={'.py'},
                must_exist=True,
                require_file=True,
                allow_absolute=not client_supplied_file,
            )
        except PathPolicyError as e:
            return jsonify({'error': str(e)}), 400
        except FileNotFoundError:
            return jsonify({
                'error': f'Source file not found: {source_file}. Cannot create new files.',
            }), 404

        # Validate Python syntax before saving
        try:
            compile(source_code, str(file_path), 'exec')
        except SyntaxError as e:
            return jsonify({
                'error': f'Syntax error in Python code: {e}',
                'line': e.lineno,
                'offset': e.offset
            }), 400

        # Create backup of original file
        try:
            backup_path = _resolve_allowed_path(
                file_path.with_suffix('.py.bak'),
                roots=_enabled_code_roots(),
                allow_absolute=True,
            )
        except PathPolicyError as e:
            return jsonify({'error': str(e)}), 400
        try:
            import shutil
            shutil.copy2(file_path, backup_path)
        except Exception as e:
            return jsonify({'error': f'Failed to create backup: {e}'}), 500

        # Write new source code
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(source_code)
        except Exception as e:
            # Restore from backup if write fails
            try:
                shutil.copy2(backup_path, file_path)
            except:
                pass
            return jsonify({'error': f'Failed to write source file: {e}'}), 500

        return jsonify({
            'success': True,
            'file_path': str(file_path.relative_to(REPO_ROOT)),
            'message': f'Successfully saved {function_name}',
            'backup_path': str(backup_path.name)
        })

    except Exception as e:
        return jsonify({'error': f'Unexpected error: {e}'}), 500


@app.route('/api/filesystem/write-file', methods=['POST'])
def write_file():
    """
    Write arbitrary text content to a path inside the project tree.

    Used by the GUI to persist .subworkflow.json files next to their .py
    counterparts. Strictly limited to paths under the engine source tree
    and the adapters directory.

    Request body:
        { "file_path": "<abs or repo-relative>", "content": "<text>" }

    Returns:
        { success, file_path, created, backup_path? }
    """
    try:
        data = request.json or {}
        raw_path = data.get('file_path')
        content = data.get('content')
        if not raw_path or content is None:
            return jsonify({'error': 'file_path and content are required'}), 400

        repo_root = REPO_ROOT
        try:
            target = _resolve_allowed_path(
                raw_path,
                roots=(ADAPTERS_DIR, ENGINE_SOURCE_DIR, EXPORTS_DIR),
                bases=(repo_root,),
                suffixes={'.py', '.json'},
            )
        except PathPolicyError as e:
            return jsonify({'error': str(e)}), 400

        target.parent.mkdir(parents=True, exist_ok=True)

        backup_path = None
        created = not target.exists()
        if not created:
            backup_target = _resolve_allowed_path(
                target.with_suffix(target.suffix + '.bak'),
                roots=(ADAPTERS_DIR, ENGINE_SOURCE_DIR, EXPORTS_DIR),
                allow_absolute=True,
            )
            shutil.copy2(target, backup_target)
            backup_path = str(backup_target)

        target.write_text(content, encoding='utf-8')

        return jsonify({
            'success': True,
            'file_path': str(target.relative_to(repo_root) if target.is_relative_to(repo_root) else target),
            'created': created,
            'backup_path': backup_path,
        })
    except PathPolicyError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Write failed: {e}'}), 500


@app.route('/api/filesystem/save-dialog', methods=['POST'])
def save_dialog():
    """
    Open a native cross-platform Save-As dialog (via tkinter in a subprocess)
    and return the chosen path. Cancellation returns {cancelled: true}.
    """
    try:
        data = request.json or {}
        default_path = data.get('default_path', '')
        repo_root = REPO_ROOT
        requested_initial_dir = data.get('initial_dir')
        if requested_initial_dir:
            try:
                initial_dir = str(_resolve_allowed_path(
                    requested_initial_dir,
                    roots=(ADAPTERS_DIR, ENGINE_SOURCE_DIR, EXPORTS_DIR),
                    bases=(repo_root,),
                    allow_absolute=False,
                ))
            except PathPolicyError as exc:
                return jsonify({'error': str(exc)}), 400
        else:
            initial_dir = str(repo_root)

        if default_path:
            default_path_obj = Path(default_path)
            initial_file = default_path_obj.name
            if default_path_obj.parent and str(default_path_obj.parent) != '.':
                # If a parent directory was given, use it as the initial_dir
                try:
                    p = _resolve_allowed_path(
                        default_path_obj.parent,
                        roots=(ADAPTERS_DIR, ENGINE_SOURCE_DIR, EXPORTS_DIR),
                        bases=(repo_root,),
                    )
                    if p.exists():
                        initial_dir = str(p)
                except PathPolicyError:
                    initial_dir = str(repo_root)
        else:
            initial_file = ''

        # Match the dialog to what's actually being saved. Callers may override
        # explicitly; otherwise infer the extension from default_path's suffix so
        # the OS doesn't nag about a "wrong" extension (e.g. a .json saved under a
        # hardcoded .py default).
        suffix = Path(default_path).suffix if default_path else ''
        ext = data.get('default_extension') or suffix or '.py'
        type_label = {'.json': 'JSON', '.py': 'Python'}.get(ext, (ext.lstrip('.').upper() or 'File'))
        filetypes = data.get('filetypes') or [(type_label, f'*{ext}'), ('All files', '*.*')]
        filetypes = [tuple(ft) for ft in filetypes]
        title = data.get('title') or f'Save {type_label} file'

        # Use a subprocess so tkinter mainloop doesn't interfere with Flask
        script = (
            "import sys, tkinter as tk\n"
            "from tkinter import filedialog\n"
            "root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)\n"
            f"p = filedialog.asksaveasfilename(\n"
            f"    defaultextension={ext!r},\n"
            f"    filetypes={filetypes!r},\n"
            f"    initialdir={initial_dir!r},\n"
            f"    initialfile={initial_file!r},\n"
            f"    title={title!r})\n"
            "root.destroy()\n"
            "sys.stdout.write(p or '')\n"
        )
        try:
            proc = subprocess.run(
                [sys.executable, '-c', script],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=120,
            )
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Save dialog timed out'}), 500

        chosen = (proc.stdout or '').strip()
        if proc.returncode != 0 and not chosen:
            return jsonify({'error': f'Dialog failed: {proc.stderr.strip() or "unknown"}'}), 500
        if not chosen:
            return jsonify({'cancelled': True})

        # The native dialog returns an absolute path. Most of the app expects a
        # repo-relative path (e.g. opencellcomms_adapters/...). Provide both so
        # callers can show the clean relative form when the pick is inside the repo.
        try:
            chosen_path = _resolve_allowed_path(
                chosen,
                roots=(ADAPTERS_DIR, ENGINE_SOURCE_DIR, EXPORTS_DIR),
                suffixes={'.py', '.json'},
                allow_absolute=True,
            )
        except PathPolicyError as e:
            return jsonify({'error': str(e)}), 400
        relative_path = str(chosen_path.relative_to(repo_root))
        return jsonify({'path': str(chosen_path), 'relative_path': relative_path})

    except Exception as e:
        return jsonify({'error': f'Save dialog failed: {e} — type the path manually'}), 500


def _path_to_module_name(file_path, engine_dir):
    """
    Map a filesystem path to its dotted module name based on known roots.
    Returns (module_name, register_path_or_None) or (None, None) if the path
    isn't within a known import root.
    """
    p = Path(file_path).resolve()
    adapters_dir = (engine_dir.parent / 'opencellcomms_adapters').resolve()
    engine_src = (engine_dir / 'src').resolve()

    try:
        rel = p.relative_to(adapters_dir)
        parts = list(rel.parts)
        if not parts:
            return None, None
        parts[-1] = parts[-1].removesuffix('.py')
        adapter_name = parts[0]
        register_path = adapters_dir / adapter_name / 'register.py'
        module_name = 'opencellcomms_adapters.' + '.'.join(parts)
        return module_name, register_path
    except ValueError:
        pass

    try:
        rel = p.relative_to(engine_src)
        parts = list(rel.parts)
        if not parts:
            return None, None
        parts[-1] = parts[-1].removesuffix('.py')
        module_name = 'src.' + '.'.join(parts)
        return module_name, None
    except ValueError:
        pass

    return None, None


def _auto_reload_module(module_name):
    """
    Import or reload a module by name so any @register_function decorators
    re-run immediately. Returns (ok, warning_message_or_None).
    """
    import importlib
    try:
        engine_dir = get_engine_path().parent
        # Ensure both the engine dir (so `src.workflow.*` resolves) and the
        # repo root (so `opencellcomms_adapters.*` resolves) are on sys.path.
        for p in [str(engine_dir.parent), str(engine_dir)]:
            if p not in sys.path:
                sys.path.insert(0, p)

        importlib.invalidate_caches()
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)
        return True, None
    except Exception as e:
        return False, f'Auto-reload failed: {type(e).__name__}: {e}'


@app.route('/api/function/scaffold', methods=['POST'])
def scaffold_behavior_code():
    """
    Idempotently create a Python file for a behavior subworkflow and live-load it
    into the registry (no backend restart required).

    NEW request body (preferred):
        {
            "file_path": "opencellcomms_adapters/jayatilake/functions/agent_behavior/cell_init.py",
            "functions": [{"name": "evaluate_de_inputs", "parameters": [...]}, ...]
        }

    LEGACY request body (still accepted):
        {
            "behavior_name": "differentiation",
            "category": "intracellular",
            "adapter": "jayatilake",   // null for generic engine functions
            "functions": [{"name": "evaluate_de_inputs"}, ...]
        }

    Returns:
        { success, file_path, created, added_functions, skipped_existing,
          module_name, reload_warning? }
    """
    try:
        data = request.json or {}
        functions = data.get('functions', [])
        if not functions:
            return jsonify({'error': 'functions list is required'}), 400

        engine_dir = get_engine_path().parent  # opencellcomms_engine/

        # Resolve file_path: prefer explicit, fall back to legacy fields
        explicit_path = data.get('file_path')
        if explicit_path:
            try:
                file_path = _resolve_allowed_path(
                    explicit_path,
                    roots=(ADAPTERS_DIR, ENGINE_SOURCE_DIR),
                    bases=(REPO_ROOT,),
                    suffixes={'.py'},
                )
            except PathPolicyError as e:
                return jsonify({'error': str(e)}), 400

            module_name, register_path = _path_to_module_name(file_path, engine_dir)
            if module_name is None:
                return jsonify({
                    'error': f'file_path must be within an importable tree '
                             f'(opencellcomms_adapters/ or opencellcomms_engine/src/). '
                             f'Got: {file_path}'
                }), 400

            # Use the parent folder as the role/fallback decorator category.
            # New plugins use role folders such as agent_behavior; older code
            # may still pass registry-category folders such as intracellular.
            category = file_path.parent.name
            behavior_name = file_path.stem
        else:
            behavior_name = data.get('behavior_name', '').strip()
            category = data.get('category', 'intracellular').strip()
            adapter = (data.get('adapter') or '').strip() or None
            if not behavior_name:
                return jsonify({'error': 'either file_path or behavior_name is required'}), 400

            if adapter:
                adapters_dir = engine_dir.parent / 'opencellcomms_adapters'
                file_path = adapters_dir / adapter / 'functions' / category / f'{behavior_name}.py'
            else:
                file_path = engine_dir / 'src' / 'workflow' / 'functions' / category / f'{behavior_name}.py'
            try:
                file_path = _resolve_allowed_path(
                    file_path,
                    roots=(ADAPTERS_DIR, ENGINE_SOURCE_DIR),
                    suffixes={'.py'},
                    allow_absolute=True,
                )
            except PathPolicyError as e:
                return jsonify({'error': str(e)}), 400
            module_name, register_path = _path_to_module_name(file_path, engine_dir)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Derive the legacy registry category constant. The folder name is only
        # a valid FunctionCategory for old .../functions/<category>/ layouts.
        # New role folders (agent_behavior, resource_behavior, etc.) rely on the
        # per-function category sent by the GUI; otherwise fall back to a valid
        # compatibility default so the scaffold always imports.
        VALID_CATEGORIES = {
            'INITIALIZATION', 'INTRACELLULAR', 'DIFFUSION',
            'INTERCELLULAR', 'ENVIRONMENT', 'FINALIZATION', 'UTILITY',
        }
        category_const = category.upper()
        if category_const not in VALID_CATEGORIES:
            category_const = 'INTRACELLULAR'

        # File header template
        header = f'''"""
{behavior_name} — auto-generated behavior scaffold.

Edit the function bodies below to implement the behavior logic.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


'''

        created = False
        if not file_path.exists():
            file_path.write_text(header, encoding='utf-8')
            created = True
        else:
            # Make a backup before modifying
            backup_path = _resolve_allowed_path(
                file_path.with_suffix('.py.bak'),
                roots=(ADAPTERS_DIR, ENGINE_SOURCE_DIR),
                allow_absolute=True,
            )
            shutil.copy2(file_path, backup_path)

        # Read existing function names via ast
        existing_source = file_path.read_text(encoding='utf-8')
        try:
            tree = ast.parse(existing_source)
        except SyntaxError:
            tree = None

        existing_funcs = set()
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    existing_funcs.add(node.name)

        # If we're adding any typed-env functions, ensure the file imports
        # BiologicalContext. The typed signature `env: BiologicalContext`
        # evaluates the annotation at def time, so a missing import would raise
        # NameError when the decorator registers the function.
        wants_typed = any(
            not bool(fn.get('typed_env_exempt')) and (fn.get('name') or '').strip()
            for fn in functions
        )
        BIO_IMPORT = 'from src.biology.context import BiologicalContext'
        if wants_typed and BIO_IMPORT not in existing_source:
            anchor = 'from src.workflow.decorators import register_function'
            if anchor in existing_source:
                existing_source = existing_source.replace(
                    anchor, anchor + '\n' + BIO_IMPORT, 1
                )
            else:
                existing_source = BIO_IMPORT + '\n' + existing_source

        added = []
        skipped = []

        type_to_py = {'INT': 'int', 'FLOAT': 'float', 'BOOL': 'bool', 'STRING': 'str', 'DICT': 'dict'}

        # Role-aware body hints. `category` here is the role folder the function
        # lives in (agent_behavior / resource_behavior / world_behavior / ...), so
        # an agent Step gets the ABM `env` API the class layer advertises rather
        # than the legacy cell-centric hints. All are surfaced on the same
        # `env: BiologicalContext` object.
        _role = (category or '').strip().lower()
        _ABM_HINTS = {
            'agent_create': (
                "    # Creation is COLLECTIVE -- it runs once; env.agent is None here.\n"
                "    # env.population.populate('kind', count, trait=lambda rng: ...) -> create agents\n"
                "    # for cell in env.cells: ...   -> operate on the whole population\n"
            ),
            'agent_behavior': (
                "    # env.agent             -> the current agent (bound per-ask)\n"
                "    # env.agent.neighbors() -> neighbouring agents\n"
                "    # env.agent.sense('sugar')      -> resource value at the agent's tile\n"
                "    # env.resource('sugar')         -> a resource field (.at(pos), .total())\n"
                "    # env.request_move(agent, pos)  -> deferred move intent\n"
                "    # env.request_consume_resource(agent, name, amount) -> deferred uptake\n"
            ),
            'resource_init': (
                "    # Resource setup runs ONCE at init -- seed this field here.\n"
                "    # env.resource(name)    -> this resource field\n"
                "    # field.values()[:] = ...          -> set the initial concentration grid\n"
                "    # field.capacity = ...             -> set a carrying-capacity landscape\n"
                "    # env.world.nx / env.world.ny      -> grid dimensions for the pattern\n"
            ),
            'resource_behavior': (
                "    # env.resource(name)    -> this resource field\n"
                "    # env.current_resource  -> the resource currently being asked\n"
                "    # field.values() / field.total()    -> read the whole field\n"
                "    # field.apply_sources(...)          -> deposit/produce\n"
            ),
            'world': (
                "    # World setup runs ONCE, before agents act -- build the space here.\n"
                "    # env.world       -> the spatial world (bounds, topology, occupancy)\n"
                "    # env.domain      -> the resource domain to attach fields to\n"
                "    # env.population  -> the collective the agents will live in\n"
            ),
            'world_behavior': (
                "    # env.world       -> the spatial world (bounds, neighbors, occupancy)\n"
                "    # env.population  -> the collective (count, census, agents_of_kind)\n"
                "    # env.domain      -> all resources; env.population.census() -> snapshot\n"
            ),
            'processing_behavior': (
                "    # Post-loop reporting: read final state, emit plots/summaries.\n"
                "    # env.population.census()  -> counts by kind/phenotype\n"
                "    # env.domain.resources()   -> each resource field (.name, .total())\n"
                "    # env.record(key, value)   -> persist a metric; env.results -> the dict\n"
                "    # env.plots_dir            -> directory to write figures into\n"
            ),
        }
        _LEGACY_HINTS = (
            '    # requires=["population"]    -> for cell in env.cells: ...\n'
            "    # requires=[\"simulator\"]     -> env.concentration('substance', cell)\n"
            '    # requires=["gene_networks"] -> cell.gene("GeneName").is_on()\n'
        )

        def fmt_default(val, py_type):
            if py_type == 'str':
                return repr(val if val is not None else '')
            if py_type == 'bool':
                return 'True' if val else 'False'
            if py_type == 'dict':
                return '{}'
            if val is None:
                return '0' if py_type == 'int' else '0.0'
            return repr(val)

        for fn in functions:
            fn_name = fn.get('name', '').strip()
            if not fn_name:
                continue
            if fn_name in existing_funcs:
                skipped.append(fn_name)
                continue

            display_name = fn_name.replace('_', ' ').title()
            fn_params = fn.get('parameters') or []
            # Setup functions (population/file loading) keep the raw context dict;
            # everything else uses the typed `env: BiologicalContext` API.
            exempt = bool(fn.get('typed_env_exempt'))

            # Per-function compatibility-category override, falling back to the
            # folder-derived default for old category-folder layouts.
            fn_cat = (fn.get('category') or category).strip().upper()
            if fn_cat not in VALID_CATEGORIES:
                fn_cat = category_const

            # Capability tokens the typed function reads from the kernel.
            fn_requires = [str(r).strip() for r in (fn.get('requires') or []) if str(r).strip()]
            requires_repr = '[' + ', '.join(f'"{r}"' for r in fn_requires) + ']'

            # Build decorator parameters list
            decorator_param_lines = []
            for p in fn_params:
                pname = p.get('name', '').strip()
                ptype = p.get('type', 'FLOAT')
                pdefault = p.get('default')
                if not pname:
                    continue
                py_t = type_to_py.get(ptype, 'float')
                default_repr = fmt_default(pdefault, py_t)
                decorator_param_lines.append(
                    f'        {{"name": "{pname}", "type": "{ptype}", '
                    f'"description": "TODO", "default": {default_repr}}}'
                )
            decorator_params_block = (
                '[\n' + ',\n'.join(decorator_param_lines) + ',\n    ]'
                if decorator_param_lines else '[]'
            )

            # Build signature: typed env (preferred) or raw context (exempt).
            first_arg = '    context: Dict[str, Any] = None,' if exempt else '    env: BiologicalContext,'
            sig_lines = [first_arg]
            for p in fn_params:
                pname = p.get('name', '').strip()
                if not pname:
                    continue
                py_t = type_to_py.get(p.get('type', 'FLOAT'), 'float')
                default_repr = fmt_default(p.get('default'), py_t)
                sig_lines.append(f'    {pname}: {py_t} = {default_repr},')
            sig_lines.append('    **kwargs')
            sig_block = '\n'.join(sig_lines)

            # Decorator tail + body differ by API style.
            if exempt:
                decorator_tail = (
                    '    compatible_kernels=["biophysics"],\n'
                    '    typed_env_exempt=True,'
                )
                body = (
                    f'    """TODO: implement {fn_name}."""\n'
                    f'    if not context:\n'
                    f'        print("[ERROR] [{fn_name}] No context provided")\n'
                    f'        return False\n'
                    f'    # TODO: implement behavior\n'
                    f'    return True\n'
                )
            else:
                decorator_tail = (
                    '    compatible_kernels=["biophysics"],\n'
                    f'    requires={requires_repr},'
                )
                api_hints = _ABM_HINTS.get(_role, _LEGACY_HINTS)
                if _role == 'agent_create':
                    # Collective creation: runs once over the whole population.
                    body = (
                        f'    """TODO: implement {fn_name} (collective creation, runs once)."""\n'
                        f'{api_hints}'
                        f"    # TODO: bring this kind's agents into existence (env.agent is None here)\n"
                        f'    return True\n'
                    )
                elif _role == 'agent_behavior':
                    # Per-agent: runs once per agent via the scheduler's for_each ask.
                    body = (
                        f'    """TODO: implement {fn_name} (runs once per agent)."""\n'
                        f'    agent = env.agent  # the single bound agent; never loop env.cells here\n'
                        f'    if agent is None:\n'
                        f'        return True\n'
                        f'{api_hints}'
                        f'    # TODO: implement per-agent logic\n'
                        f'    return True\n'
                    )
                else:
                    body = (
                        f'    """TODO: implement {fn_name}."""\n'
                        f'    # Available on env: env.config, env.step, env.dt, env.results\n'
                        f'{api_hints}'
                        f'    # TODO: implement behavior\n'
                        f'    return True\n'
                    )

            fn_block = (
                f'\n@register_function(\n'
                f'    display_name="{display_name}",\n'
                f'    description="TODO: describe what {fn_name} does",\n'
                f'    category="{fn_cat}",\n'
                f'    parameters={decorator_params_block},\n'
                f'    inputs=["context"],\n'
                f'    outputs=[],\n'
                f'    cloneable=False,\n'
                f'{decorator_tail}\n'
                f')\n'
                f'def {fn_name}(\n'
                f'{sig_block}\n'
                f') -> bool:\n'
                f'{body}\n'
            )
            existing_source += fn_block
            existing_funcs.add(fn_name)
            added.append(fn_name)

        # Validate syntax before writing
        try:
            compile(existing_source, str(file_path), 'exec')
        except SyntaxError as e:
            return jsonify({'error': f'Syntax error in generated code: {e}', 'line': e.lineno}), 400

        file_path.write_text(existing_source, encoding='utf-8')

        # Persist the import in the adapter's register.py so the function loads
        # on a fresh backend (the engine auto-discovers any adapter that has a
        # register.py). For a brand-new adapter we scaffold the package skeleton
        # — __init__.py files + register.py — so the import actually resolves.
        if added and module_name and module_name.startswith('opencellcomms_adapters.') and register_path:
            register_path = _resolve_allowed_path(
                register_path,
                roots=(ADAPTERS_DIR,),
                suffixes={'.py'},
                allow_absolute=True,
            )
            adapter_dir = register_path.parent

            # Ensure __init__.py from the adapter root down to the function's
            # folder, so the dotted module path is importable.
            d = file_path.parent
            while True:
                init_file = d / '__init__.py'
                init_file = _resolve_allowed_path(
                    init_file,
                    roots=(adapter_dir,),
                    suffixes={'.py'},
                    allow_absolute=True,
                )
                if not init_file.exists():
                    init_file.write_text('', encoding='utf-8')
                if d == adapter_dir:
                    break
                d = d.parent

            # Create register.py with a header if the adapter is new. Track
            # whether it pre-existed so we only back it up when we're modifying
            # a real prior file (no .bak litter for a just-created register.py).
            register_existed = register_path.exists()
            if not register_existed:
                register_path.write_text(
                    f'"""Plugin registry for the {adapter_dir.name} adapter.\n\n'
                    f'Importing this module registers the adapter\'s functions via\n'
                    f'@register_function. The engine discovers and imports it\n'
                    f'automatically from opencellcomms_adapters/.\n"""\n',
                    encoding='utf-8')

                # Brand-new plugin: lay down the full role-based folder skeleton
                # (one folder per authoring role, matching the GUI's v2 kinds),
                # plus behaviors/ and workflows/. This gives the biologist a clear
                # home for each kind of function up front. Existing plugins are
                # left untouched.
                ROLE_FOLDERS = [
                    'agent_create', 'agent_behavior',
                    'resource_init', 'resource_behavior',
                    'world', 'world_behavior',
                    'processing_behavior',
                ]
                functions_root = adapter_dir / 'functions'
                functions_root = _resolve_allowed_path(
                    functions_root,
                    roots=(adapter_dir,),
                    allow_absolute=True,
                )
                functions_root.mkdir(parents=True, exist_ok=True)
                functions_init = _resolve_allowed_path(
                    functions_root / '__init__.py',
                    roots=(adapter_dir,),
                    suffixes={'.py'},
                    allow_absolute=True,
                )
                functions_init.touch()
                for role_folder in ROLE_FOLDERS:
                    role_dir = _resolve_allowed_path(
                        functions_root / role_folder,
                        roots=(adapter_dir,),
                        allow_absolute=True,
                    )
                    role_dir.mkdir(parents=True, exist_ok=True)
                    role_init = _resolve_allowed_path(
                        role_dir / '__init__.py',
                        roots=(adapter_dir,),
                        suffixes={'.py'},
                        allow_absolute=True,
                    )
                    role_init.touch()
                for extra in ('behaviors', 'workflows'):
                    extra_dir = _resolve_allowed_path(
                        adapter_dir / extra,
                        roots=(adapter_dir,),
                        allow_absolute=True,
                    )
                    extra_dir.mkdir(parents=True, exist_ok=True)

            # Seed a plugin manifest so the new plugin has an identity.
            manifest_path = _resolve_allowed_path(
                adapter_dir / 'plugin.toml',
                roots=(adapter_dir,),
                suffixes={'.toml'},
                allow_absolute=True,
            )
            if not manifest_path.exists():
                manifest_path.write_text(
                    '# OpenCellComms plugin manifest. See docs/PLUGINS.md for the schema.\n'
                    '[plugin]\n'
                    f'name = "{adapter_dir.name}"\n'
                    'version = "0.1.0"\n'
                    'description = ""\n'
                    'author = ""\n'
                    'engine_version = ">=0.0.0"\n'
                    'compatible_kernels = ["biophysics"]\n'
                    'enabled = true\n',
                    encoding='utf-8')

            reg_source = register_path.read_text(encoding='utf-8')
            lines_to_add = []
            for fn_name in added:
                import_line = f'from {module_name} import {fn_name}'
                if import_line not in reg_source:
                    lines_to_add.append(import_line)
            if lines_to_add:
                if register_existed:
                    register_backup = _resolve_allowed_path(
                        register_path.with_suffix('.py.bak'),
                        roots=(adapter_dir,),
                        allow_absolute=True,
                    )
                    shutil.copy2(register_path, register_backup)
                register_path.write_text(reg_source.rstrip() + '\n' + '\n'.join(lines_to_add) + '\n',
                                          encoding='utf-8')

        # Auto-reload the module so newly-added functions register immediately —
        # no backend restart required.
        reload_warning = None
        if module_name and added:
            ok, warn = _auto_reload_module(module_name)
            if not ok:
                reload_warning = warn

        rel_path = str(file_path.relative_to(engine_dir.parent))
        return jsonify({
            'success': True,
            'file_path': rel_path,
            'created': created,
            'added_functions': added,
            'skipped_existing': skipped,
            'module_name': module_name,
            'reload_warning': reload_warning,
        })

    except PathPolicyError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {e}'}), 500


@app.route('/api/function/validate', methods=['POST'])
def validate_function_source():
    """
    Validate Python source code without saving.

    Request body:
        {
            'source': 'def update_metabolism(...):\n    ...'
        }

    Returns:
        {
            'valid': true/false,
            'errors': [...]
        }
    """
    try:
        data = request.json

        if not data or 'source' not in data:
            return jsonify({'error': 'Missing required field: source'}), 400

        source_code = data['source']

        # Try to compile the code
        try:
            compile(source_code, '<string>', 'exec')
            return jsonify({
                'valid': True,
                'errors': []
            })
        except SyntaxError as e:
            return jsonify({
                'valid': False,
                'errors': [{
                    'type': 'SyntaxError',
                    'message': str(e.msg),
                    'line': e.lineno,
                    'offset': e.offset,
                    'text': e.text
                }]
            })
        except Exception as e:
            return jsonify({
                'valid': False,
                'errors': [{
                    'type': type(e).__name__,
                    'message': str(e)
                }]
            })

    except Exception as e:
        return jsonify({'error': f'Unexpected error: {e}'}), 500


@app.route('/api/function/upload', methods=['POST'])
def upload_function_file():
    """
    Upload a Python file to replace a workflow function.

    Request: multipart/form-data with:
        - file: Python file to upload
        - function_name: Name of the function (e.g., 'update_metabolism')
        - target_path: Optional target path (e.g., 'src/workflow/functions/intracellular/update_metabolism.py')

    Returns:
        {
            'success': true,
            'file_path': '...',
            'message': '...',
            'backup_path': '...'
        }
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        # Get function name and target path
        function_name = request.form.get('function_name')
        target_path = request.form.get('target_path')

        if not function_name:
            return jsonify({'error': 'Missing required field: function_name'}), 400

        # Read file content
        file_content = file.read().decode('utf-8')

        # Validate Python syntax
        try:
            compile(file_content, file.filename, 'exec')
        except SyntaxError as e:
            return jsonify({
                'error': f'Invalid Python syntax in uploaded file',
                'details': f'Line {e.lineno}: {e.msg}'
            }), 400

        # Determine target file path
        engine_root = get_engine_path().parent

        if target_path:
            try:
                target_file = _resolve_allowed_path(
                    target_path,
                    roots=_enabled_code_roots(),
                    bases=(engine_root, REPO_ROOT),
                    suffixes={'.py'},
                    must_exist=True,
                    require_file=True,
                )
            except PathPolicyError as e:
                return jsonify({'error': str(e)}), 400
            except FileNotFoundError:
                return jsonify({'error': 'Target source file not found'}), 404
        else:
            sys.path.insert(0, str(engine_root))
            sys.path.insert(0, str(REPO_ROOT))
            from src.workflow.registry import get_default_registry
            metadata = get_default_registry().get(function_name)
            if metadata is None or not metadata.source_file:
                return jsonify({'error': f'Function {function_name} not found in registry'}), 404
            try:
                target_file = _resolve_allowed_path(
                    metadata.source_file,
                    roots=_enabled_code_roots(),
                    bases=(engine_root, REPO_ROOT),
                    suffixes={'.py'},
                    must_exist=True,
                    require_file=True,
                    allow_absolute=True,
                )
            except (PathPolicyError, FileNotFoundError) as e:
                return jsonify({'error': f'Invalid registry source path: {e}'}), 400

        # Create backup of existing file
        if target_file.exists():
            backup_dir = _resolve_allowed_path(
                target_file.parent / "backups",
                roots=_enabled_code_roots(),
                allow_absolute=True,
            )
            backup_dir.mkdir(exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{target_file.stem}_backup_{timestamp}{target_file.suffix}"
            backup_path = _resolve_allowed_path(
                backup_dir / backup_filename,
                roots=_enabled_code_roots(),
                suffixes={'.py'},
                allow_absolute=True,
            )

            # Copy existing file to backup
            backup_path.write_text(target_file.read_text())
        else:
            backup_path = None

        # Write uploaded file
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(file_content)

        return jsonify({
            'success': True,
            'file_path': str(target_file.relative_to(REPO_ROOT)),
            'message': f'Successfully uploaded {file.filename} for {function_name}',
            'backup_path': str(backup_path.name) if backup_path else None
        })

    except PathPolicyError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Upload failed: {e}'}), 500


@app.route('/api/results/list', methods=['GET'])
def list_results():
    """
    List all results from the top-level runs/ directory.

    Scans runs/ for images. Each runs/<label>/ becomes a result group; within a
    group, each subworkflow subdirectory becomes a category. Images placed
    directly in a group go into a 'general' category.

    Returns:
        {success: true, results: [{name, timestamp, plots: [{name, path, category}]}]}
    """
    try:
        results_dir = RUNS_DIR

        if not results_dir.exists():
            return jsonify({'success': True, 'results': []})

        IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp'}
        # Viewable artifacts: images plus interactive HTML (the 3D viewer).
        # .js is deliberately NOT listed - plotly.min.js sits beside the
        # HTMLs and is served (see MIME_TYPES) but must not appear as a plot.
        VIEWABLE_EXTENSIONS = IMAGE_EXTENSIONS | {'.html'}

        def scan_for_plots(directory, base_ref):
            """Recursively scan directory for image files, categorizing by subdirectory."""
            plots = []
            if not directory.exists():
                return plots
            if directory.is_symlink():
                return plots
            try:
                directory = _resolve_allowed_path(
                    directory,
                    roots=(RUNS_DIR,),
                    allow_absolute=True,
                )
            except PathPolicyError:
                return plots
            for item in sorted(directory.iterdir()):
                if item.is_symlink():
                    continue
                if item.is_dir():
                    # Subdirectory becomes a category
                    for img_file in sorted(item.rglob('*')):
                        if img_file.is_symlink():
                            continue
                        if img_file.is_file() and img_file.suffix.lower() in VIEWABLE_EXTENSIONS:
                            try:
                                img_file = _resolve_allowed_path(
                                    img_file,
                                    roots=(RUNS_DIR,),
                                    suffixes=VIEWABLE_EXTENSIONS,
                                    must_exist=True,
                                    require_file=True,
                                    allow_absolute=True,
                                )
                            except (PathPolicyError, FileNotFoundError):
                                continue
                            plots.append({
                                'name': img_file.name,
                                'path': str(img_file.relative_to(base_ref)),
                                'category': item.name
                            })
                elif item.is_file() and item.suffix.lower() in VIEWABLE_EXTENSIONS:
                    plots.append({
                        'name': item.name,
                        'path': str(item.relative_to(base_ref)),
                        'category': 'general'
                    })
            return plots

        results = []

        # Check for top-level subdirectories (each becomes a result group)
        has_subdirs = any(
            item.is_dir() and not item.is_symlink()
            for item in results_dir.iterdir()
            if not item.name.startswith('.')
        )

        if has_subdirs:
            for item in sorted(results_dir.iterdir()):
                if item.is_dir() and not item.is_symlink() and not item.name.startswith('.'):
                    plots = scan_for_plots(item, RUNS_DIR)
                    if plots:
                        # Try to extract timestamp from directory name
                        timestamp = item.name if item.name[:8].isdigit() else ''
                        results.append({
                            'name': item.name,
                            'timestamp': timestamp,
                            'plots': plots
                        })

        # Also collect any images directly in runs/
        root_plots = []
        for item in sorted(results_dir.iterdir()):
            if (
                item.is_file()
                and not item.is_symlink()
                and item.suffix.lower() in VIEWABLE_EXTENSIONS
            ):
                root_plots.append({
                    'name': item.name,
                    'path': str(item.relative_to(RUNS_DIR)),
                    'category': 'general'
                })
        if root_plots:
            results.append({
                'name': 'Results',
                'timestamp': '',
                'plots': root_plots
            })

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/results/plot/<path:plot_path>', methods=['GET'])
def get_plot(plot_path):
    """Serve a plot image file with cache-busting headers."""
    try:
        try:
            full_path = _resolve_allowed_path(
                plot_path,
                roots=(RUNS_DIR,),
                bases=(RUNS_DIR,),
                must_exist=True,
                require_file=True,
            )
        except PathPolicyError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except FileNotFoundError:
            return jsonify({'success': False, 'error': 'Plot not found'}), 404

        if not full_path.is_file():
            return jsonify({'success': False, 'error': 'Plot not found'}), 404

        MIME_TYPES = {
            '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.gif': 'image/gif', '.svg': 'image/svg+xml', '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            # 3D viewer artifacts: the HTML itself plus its sibling
            # plotly.min.js (referenced relatively from the iframe URL,
            # resolved through this same sandboxed route)
            '.html': 'text/html', '.js': 'application/javascript'
        }
        mime = MIME_TYPES.get(full_path.suffix.lower())
        if not mime:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400

        # Send file with cache-busting headers to prevent browser caching
        response = send_file(full_path, mimetype=mime)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/library/parse', methods=['POST'])
def parse_library():
    """
    Parse a Python library file and extract function definitions.

    Phase 5: Function Libraries

    Returns:
        {
            'success': True,
            'functions': [
                {
                    'name': 'function_name',
                    'signature': 'def function_name(context, **kwargs)',
                    'docstring': 'Function description',
                    'category': 'utility'  # extracted from decorator or default
                }
            ],
            'library_name': 'filename.py'
        }
    """
    try:
        data = request.json
        library_path = data.get('library_path')

        if not library_path:
            return jsonify({'success': False, 'error': 'No library path provided'}), 400

        try:
            library_file = _resolve_allowed_path(
                library_path,
                roots=_enabled_code_roots(),
                bases=(ENGINE_DIR, REPO_ROOT),
                suffixes={'.py'},
                must_exist=True,
                require_file=True,
            )
        except PathPolicyError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except FileNotFoundError:
            return jsonify({'success': False, 'error': f'Library file not found: {library_path}'}), 404

        # Parse the Python file
        with open(library_file, 'r') as f:
            source_code = f.read()

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return jsonify({'success': False, 'error': f'Syntax error in library: {str(e)}'}), 400

        functions = []

        # Extract function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get function name
                func_name = node.name

                # Skip private functions
                if func_name.startswith('_'):
                    continue

                # Get function signature
                args = [arg.arg for arg in node.args.args]
                signature = f"def {func_name}({', '.join(args)})"

                # Get docstring
                docstring = ast.get_docstring(node) or ''

                # Try to extract category from decorator
                category = 'utility'  # default
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, 'id') and decorator.func.id == 'workflow_function':
                            # Look for category argument
                            for keyword in decorator.keywords:
                                if keyword.arg == 'category':
                                    if isinstance(keyword.value, ast.Constant):
                                        category = keyword.value.value

                functions.append({
                    'name': func_name,
                    'signature': signature,
                    'docstring': docstring.split('\n')[0] if docstring else '',  # First line only
                    'category': category
                })

        return jsonify({
            'success': True,
            'functions': functions,
            'library_name': library_file.name
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# OBSERVABILITY API ENDPOINTS
# ==============================================================================

def get_observability_dir():
    """Get the observability directory path."""
    engine_dir = get_engine_path().parent
    return engine_dir / "results" / "observability"


def _observability_scope_dir(obs_dir, scope_key):
    safe_key = str(scope_key).replace(":", "_")
    context_root = Path(obs_dir) / "context"
    return _resolve_allowed_path(
        safe_key,
        roots=(context_root,),
        bases=(context_root,),
    )


def _observability_json_file(obs_dir, path, *, must_exist=True):
    """Resolve a server-derived snapshot/diff path without following escapes."""
    return _resolve_allowed_path(
        path,
        roots=(obs_dir,),
        suffixes={'.json'},
        must_exist=must_exist,
        require_file=must_exist,
        allow_absolute=True,
    )


@app.route('/api/observability/meta', methods=['GET'])
def get_observability_meta():
    """Get run metadata (startedAt, status)."""
    try:
        obs_dir = get_observability_dir()
        meta_file = obs_dir / "run_meta.json"

        if not meta_file.exists():
            return jsonify({'success': False, 'error': 'No run data available'}), 404

        meta = json.loads(meta_file.read_text())
        return jsonify({
            'success': True,
            'startedAt': meta.get('startedAt'),
            'status': meta.get('status'),
            'endedAt': meta.get('endedAt'),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Incremental cache for /api/observability/nodes. The GUI polls that endpoint,
# and events.jsonl grows without bound during a run — re-parsing the whole file
# on every poll once froze the GUI (six multi-minute requests saturated the
# browser's 6-connections-per-host limit, starving every other /api call).
# Instead, remember the aggregate and only parse bytes appended since last poll.
_node_stats_cache = {'inode': None, 'offset': 0, 'stats': {}}
_node_stats_lock = threading.Lock()


@app.route('/api/observability/nodes', methods=['GET'])
def get_observability_nodes():
    """Get node stats for badges (status, timing, log counts)."""
    try:
        obs_dir = get_observability_dir()
        events_file = obs_dir / "events.jsonl"

        with _node_stats_lock:
            if not events_file.exists():
                _node_stats_cache.update(inode=None, offset=0, stats={})
                return jsonify({'success': True, 'nodes': {}})

            st = events_file.stat()
            if (
                _node_stats_cache['inode'] != st.st_ino
                or st.st_size < _node_stats_cache['offset']
            ):
                # New or truncated file: start aggregation over
                _node_stats_cache.update(inode=st.st_ino, offset=0, stats={})

            node_stats = _node_stats_cache['stats']

            with open(events_file, 'rb') as f:
                f.seek(_node_stats_cache['offset'])
                while True:
                    line = f.readline()
                    if not line:
                        break
                    if not line.endswith(b'\n'):
                        # Partial trailing line (writer mid-append): retry next poll
                        break
                    _node_stats_cache['offset'] = f.tell()
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        node_id = event.get('nodeId')
                        if not node_id:
                            continue

                        if node_id not in node_stats:
                            node_stats[node_id] = {
                                'status': 'idle',
                                'lastStart': None,
                                'lastEnd': None,
                                'lastDurationMs': None,
                                'logCounts': {'info': 0, 'warn': 0, 'error': 0},
                                'writes': 0,
                            }

                        stats = node_stats[node_id]
                        event_type = event.get('event')

                        if event_type == 'node_start':
                            stats['lastStart'] = event.get('ts')
                            stats['status'] = 'running'
                        elif event_type == 'node_end':
                            stats['lastEnd'] = event.get('ts')
                            payload = event.get('payload', {})
                            stats['lastDurationMs'] = payload.get('durationMs')
                            stats['status'] = payload.get('status', 'ok')
                            stats['writes'] = len(payload.get('writtenKeys', []))
                        elif event_type == 'log':
                            level = event.get('level', 'INFO').lower()
                            if level in stats['logCounts']:
                                stats['logCounts'][level] += 1
                            elif level == 'warning':
                                stats['logCounts']['warn'] += 1
                    except json.JSONDecodeError:
                        continue

            return jsonify({'success': True, 'nodes': node_stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/observability/events', methods=['GET'])
def get_observability_events():
    """Get paged events (optionally filtered by scope/node)."""
    try:
        obs_dir = get_observability_dir()
        events_file = obs_dir / "events.jsonl"

        scope_key = request.args.get('scopeKey')
        node_id = request.args.get('nodeId')
        cursor = int(request.args.get('cursor', 0))
        limit = min(int(request.args.get('limit', 200)), 2000)

        if not events_file.exists():
            return jsonify({'success': True, 'events': [], 'nextCursor': None})

        events = []
        line_num = 0

        with open(events_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                line_num += 1
                if line_num <= cursor:
                    continue

                try:
                    event = json.loads(line)

                    # Filter by scope if specified
                    if scope_key:
                        event_scope = f"{event.get('subworkflowKind')}:{event.get('subworkflowName')}"
                        if event_scope != scope_key:
                            continue

                    # Filter by node if specified
                    if node_id and event.get('nodeId') != node_id:
                        continue

                    events.append(event)

                    if len(events) >= limit:
                        break
                except json.JSONDecodeError:
                    continue

        next_cursor = line_num if len(events) >= limit else None
        return jsonify({'success': True, 'events': events, 'nextCursor': next_cursor})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/observability/context', methods=['GET'])
def get_observability_context():
    """Get a context snapshot by scope and version."""
    try:
        obs_dir = get_observability_dir()
        scope_key = request.args.get('scopeKey')
        version = request.args.get('version')

        if not scope_key:
            return jsonify({'success': False, 'error': 'scopeKey is required'}), 400

        try:
            scope_dir = _observability_scope_dir(obs_dir, scope_key)
        except PathPolicyError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        if not scope_dir.exists():
            return jsonify({'success': False, 'error': f'No context data for scope: {scope_key}'}), 404

        # If version not specified, get the latest
        if not version:
            snapshot_files = sorted(scope_dir.glob("v*.json"))
            if not snapshot_files:
                return jsonify({'success': False, 'error': 'No snapshots available'}), 404
            try:
                snapshot_file = _observability_json_file(
                    obs_dir, snapshot_files[-1]
                )
            except PathPolicyError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
        else:
            try:
                version_number = int(version)
                if version_number < 0:
                    raise ValueError
                snapshot_file = _observability_json_file(
                    obs_dir,
                    scope_dir / f"v{version_number:06d}.json",
                    must_exist=False,
                )
            except ValueError:
                return jsonify({'success': False, 'error': 'version must be a nonnegative integer'}), 400
            except PathPolicyError as e:
                return jsonify({'success': False, 'error': str(e)}), 400

        if not snapshot_file.exists():
            return jsonify({'success': False, 'error': f'Snapshot version {version} not found'}), 404

        snapshot = json.loads(snapshot_file.read_text())
        return jsonify({'success': True, 'snapshot': snapshot})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/observability/diff', methods=['GET'])
def get_observability_diff():
    """Get a diff between two context versions."""
    try:
        obs_dir = get_observability_dir()
        scope_key = request.args.get('scopeKey')
        from_version = request.args.get('from')
        to_version = request.args.get('to')

        if not scope_key:
            return jsonify({'success': False, 'error': 'scopeKey is required'}), 400
        if not from_version or not to_version:
            return jsonify({'success': False, 'error': 'from and to versions are required'}), 400

        try:
            context_dir = _observability_scope_dir(obs_dir, scope_key)
        except PathPolicyError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        try:
            from_number = int(from_version)
            to_number = int(to_version)
            if from_number < 0 or to_number < 0:
                raise ValueError
            diff_dir = _resolve_allowed_path(
                context_dir / "diff",
                roots=(obs_dir,),
                allow_absolute=True,
            )
        except ValueError:
            return jsonify({'success': False, 'error': 'from and to must be nonnegative integers'}), 400
        except PathPolicyError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        # Try pre-computed diff first
        if diff_dir.exists():
            try:
                diff_file = _observability_json_file(
                    obs_dir,
                    diff_dir / f"v{from_number:06d}_to_v{to_number:06d}.json",
                    must_exist=False,
                )
            except PathPolicyError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
            if diff_file.exists():
                try:
                    diff_file = _observability_json_file(obs_dir, diff_file)
                except PathPolicyError as e:
                    return jsonify({'success': False, 'error': str(e)}), 400
                diff = json.loads(diff_file.read_text())
                return jsonify({'success': True, 'diff': diff})

        # Compute diff on-the-fly from snapshots
        try:
            from_file = _observability_json_file(
                obs_dir,
                context_dir / f"v{from_number:06d}.json",
                must_exist=False,
            )
            to_file = _observability_json_file(
                obs_dir,
                context_dir / f"v{to_number:06d}.json",
                must_exist=False,
            )
        except PathPolicyError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        if not from_file.exists() or not to_file.exists():
            return jsonify({'success': False, 'error': f'Snapshots not found for versions {from_version} and/or {to_version}'}), 404

        from_snapshot = json.loads(from_file.read_text())
        to_snapshot = json.loads(to_file.read_text())

        from_keys = from_snapshot.get('keys', {})
        to_keys = to_snapshot.get('keys', {})

        # Compute diff
        diff = {'added': {}, 'removed': {}, 'changed': {}}

        all_keys = set(from_keys.keys()) | set(to_keys.keys())
        for key in all_keys:
            if key not in from_keys:
                diff['added'][key] = to_keys[key]
            elif key not in to_keys:
                diff['removed'][key] = from_keys[key]
            elif from_keys[key] != to_keys[key]:
                diff['changed'][key] = {'before': from_keys[key], 'after': to_keys[key]}

        return jsonify({'success': True, 'diff': diff})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/observability/artifact', methods=['GET'])
def get_observability_artifact():
    """Get an artifact by path (for large values)."""
    try:
        obs_dir = get_observability_dir()
        artifact_path = request.args.get('path')

        if not artifact_path:
            return jsonify({'success': False, 'error': 'path is required'}), 400

        artifacts_root = obs_dir / "artifacts"
        try:
            full_path = _resolve_allowed_path(
                artifact_path,
                roots=(artifacts_root,),
                bases=(artifacts_root,),
                must_exist=True,
                require_file=True,
            )
        except PathPolicyError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except FileNotFoundError:
            return jsonify({'success': False, 'error': 'Artifact not found'}), 404

        # Return file content based on type
        if full_path.suffix in ['.json']:
            content = json.loads(full_path.read_text())
            return jsonify({'success': True, 'artifact': content})
        elif full_path.suffix in ['.png', '.jpg', '.jpeg', '.gif']:
            return send_file(full_path)
        else:
            # Return as text
            return jsonify({'success': True, 'artifact': full_path.read_text()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/observability/versions', methods=['GET'])
def get_observability_versions():
    """Get list of available context versions for a scope."""
    try:
        obs_dir = get_observability_dir()
        scope_key = request.args.get('scopeKey')

        if not scope_key:
            return jsonify({'success': False, 'error': 'scopeKey is required'}), 400

        try:
            scope_dir = _observability_scope_dir(obs_dir, scope_key)
        except PathPolicyError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        if not scope_dir.exists():
            return jsonify({'success': True, 'versions': []})

        versions = []
        for f in sorted(scope_dir.glob("v*.json")):
            if f.is_symlink():
                continue
            try:
                version_num = int(f.stem[1:])  # Extract number from v000001
                versions.append(version_num)
            except ValueError:
                continue

        return jsonify({'success': True, 'versions': versions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# AI CODING AGENT (Claude) — config + per-node code generation
# ============================================================================

@app.route('/api/agent/config', methods=['GET'])
def get_agent_config():
    """Return whether an API key is configured (masked) and the chosen model."""
    try:
        return jsonify({'success': True, **agent.get_config()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent/config', methods=['POST'])
def set_agent_config():
    """Persist the provider, model, and per-provider API keys to the gitignored .env."""
    try:
        data = request.json or {}
        provider = data.get('provider')
        model = data.get('model')
        anthropic_key = data.get('anthropic_key')
        openrouter_key = data.get('openrouter_key')
        if not any([provider, model, anthropic_key, openrouter_key]):
            return jsonify({'error': 'Nothing to update'}), 400
        agent.set_config(
            provider=provider,
            model=model,
            anthropic_key=anthropic_key,
            openrouter_key=openrouter_key,
        )
        return jsonify({'success': True, **agent.get_config()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent/generate', methods=['POST'])
def agent_generate():
    """Generate the complete updated source file for a node's function from a prompt."""
    try:
        data = request.json or {}
        prompt = (data.get('prompt') or '').strip()
        if not prompt:
            return jsonify({'error': 'Missing required field: prompt'}), 400

        result = agent.generate_function(
            prompt=prompt,
            function_name=data.get('function_name') or '',
            category=data.get('category') or '',
            current_source=data.get('current_source') or '',
            model=data.get('model'),
            provider=data.get('provider'),
        )
        return jsonify({'success': True, **result})
    except agent.AgentNotConfigured as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Generation failed: {e}'}), 500


def run_server():
    """Run the backend (loopback by default; containers override internally)."""
    app.run(
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        debug=False,
        threaded=True,
        use_reloader=False,
    )


if __name__ == '__main__':
    print("=" * 60)
    print("OpenCellComms Backend Server")
    print("=" * 60)
    print(f"Engine path: {get_engine_path()}")
    print(f"Engine exists: {get_engine_path().exists()}")
    print("=" * 60)
    print("Starting server on http://localhost:5001")
    print("=" * 60)

    # use_reloader=False: the Werkzeug auto-reloader restarts the server worker
    # whenever a watched .py file changes. Because simulations run as detached
    # subprocesses (start_new_session=True), a silent reloader restart orphans any
    # in-flight run and can leave a zombie listener on the port (splitting /api/run
    # and /api/logs across processes, so logs vanish). Sims still survive an
    # intentional restart; we just give up hot-reload on backend edits.
    run_server()
