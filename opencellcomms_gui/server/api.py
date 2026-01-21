#!/usr/bin/env python3
"""
Flask Backend API for OpenCellComms GUI
Provides endpoints for running simulations and streaming logs in real-time
"""

import os
import sys
import json
import subprocess
import threading
import queue
import time
import shutil
import ast
import inspect
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Global state for simulation process
simulation_process = None
simulation_thread = None
log_queue = queue.Queue()
is_running = False


def get_engine_path():
    """Get the path to OpenCellComms run_workflow.py"""
    # Server is in opencellcomms_gui/server, engine is in ../opencellcomms_engine
    server_dir = Path(__file__).parent
    engine_path = server_dir.parent.parent / "opencellcomms_engine" / "run_workflow.py"
    return engine_path


def setup_results_directories(workflow_data, gui_dir):
    """
    Setup nested results directory structure according to v2.0 spec.

    Creates:
    - results/composers/<name>/ for each composer
    - results/subworkflows/<name>/ for each subworkflow

    Clears ALL existing results to implement overwrite semantics.

    Args:
        workflow_data: Workflow JSON dict
        gui_dir: Path to ABM_GUI directory (results are stored in GUI folder)
    """
    results_dir = gui_dir / "results"

    # Get subworkflow kinds from metadata
    subworkflow_kinds = workflow_data.get('metadata', {}).get('gui', {}).get('subworkflow_kinds', {})

    # Clear the entire results directory (fresh start for each run)
    if results_dir.exists():
        shutil.rmtree(results_dir)
        log_queue.put("[INFO] Cleared existing results directory\n")

    # Create base directories
    composers_dir = results_dir / "composers"
    subworkflows_dir = results_dir / "subworkflows"
    composers_dir.mkdir(parents=True, exist_ok=True)
    subworkflows_dir.mkdir(parents=True, exist_ok=True)

    # Create directories for each subworkflow based on its kind
    for subworkflow_name, subworkflow_data in workflow_data.get('subworkflows', {}).items():
        kind = subworkflow_kinds.get(subworkflow_name,
                                     'composer' if subworkflow_name == 'main' else 'subworkflow')

        if kind == 'composer':
            subworkflow_dir = composers_dir / subworkflow_name
        else:
            subworkflow_dir = subworkflows_dir / subworkflow_name

        subworkflow_dir.mkdir(parents=True, exist_ok=True)
        log_queue.put(f"[INFO] Created results directory: {subworkflow_dir.relative_to(gui_dir)}\n")

    log_queue.put(f"[INFO] Results directory structure ready\n")


def stream_output(process, log_queue):
    """Stream stdout and stderr from subprocess to queue"""
    def enqueue_output(pipe, queue, prefix):
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    queue.put(f"{prefix}{line}")
        except Exception as e:
            queue.put(f"[ERROR] Stream error: {e}\n")
        finally:
            pipe.close()

    # Start threads for stdout and stderr
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
    else:
        log_queue.put(f"[FAILED] Simulation failed with exit code {process.returncode}\n")
    
    global is_running
    is_running = False


def run_simulation_async(workflow_path, entry_subworkflow=None):
    """Run OpenCellComms workflow in background thread (workflow-only mode)"""
    global simulation_process, is_running

    try:
        engine_path = get_engine_path()

        if not engine_path.exists():
            log_queue.put(f"[ERROR] OpenCellComms engine not found at: {engine_path}\n")
            is_running = False
            return

        # Get engine directory (working directory for simulation)
        engine_dir = engine_path.parent

        # Build command - GUI runs workflows only
        if not workflow_path:
            log_queue.put(f"[ERROR] Workflow path must be provided\n")
            is_running = False
            return

        cmd = [
            sys.executable,
            str(engine_path),
            "--workflow",
            workflow_path,
        ]

        # Add entry_subworkflow parameter if specified (Section 9.2)
        if entry_subworkflow:
            cmd.extend(["--entry-subworkflow", entry_subworkflow])
            log_queue.put(f"[START] Running workflow from entry point: {entry_subworkflow}\n")
        else:
            log_queue.put(f"[START] Running workflow-only mode: {workflow_path}\n")

        log_queue.put(f"[INFO] Command: {' '.join(cmd)}\n")
        log_queue.put(f"[INFO] Working directory: {engine_dir}\n")
        log_queue.put("[INFO] Starting OpenCellComms simulation...\n")

        # Start subprocess with correct working directory
        simulation_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=str(engine_dir)  # Set working directory to opencellcomms_engine
        )
        
        # Stream output
        stream_output(simulation_process, log_queue)
        
    except Exception as e:
        log_queue.put(f"[ERROR] Failed to start simulation: {e}\n")
        is_running = False


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current simulation status"""
    return jsonify({
        'running': is_running,
        'pid': simulation_process.pid if simulation_process else None
    })


@app.route('/api/run', methods=['POST'])
def run_simulation():
    """Start a new simulation (Section 9.2: supports entry_subworkflow parameter)"""
    global simulation_thread, is_running

    if is_running:
        return jsonify({'error': 'Simulation already running'}), 400

    data = request.json
    workflow_data = data.get('workflow')   # Workflow definition is required
    entry_subworkflow = data.get('entry_subworkflow', 'main')  # Default to 'main'

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

        # Check if entry_subworkflow is a composer (Section 9.2)
        metadata = workflow_data.get('metadata', {})
        gui_metadata = metadata.get('gui', {})
        subworkflow_kinds = gui_metadata.get('subworkflow_kinds', {})

        if subworkflow_kinds.get(entry_subworkflow) != 'composer':
            error_msg = f'Entry subworkflow "{entry_subworkflow}" must be a composer (found: {subworkflow_kinds.get(entry_subworkflow)})'
            log_queue.put(f"[ERROR] {error_msg}\n")
            return jsonify({'error': error_msg}), 400

        log_queue.put(f"[INFO] Entry subworkflow: {entry_subworkflow} (composer)\n")

    # Setup nested results directory structure (v2.0 spec)
    # Results are stored in opencellcomms_gui/results/, not opencellcomms_engine/results/
    try:
        gui_dir = Path(__file__).parent.parent  # opencellcomms_gui directory
        setup_results_directories(workflow_data, gui_dir)
    except Exception as e:
        error_msg = f'Failed to setup results directories: {str(e)}'
        log_queue.put(f"[ERROR] {error_msg}\n")
        return jsonify({'error': error_msg}), 500

    # Save workflow to temporary file
    workflow_path = "/tmp/opencellcomms_workflow.json"
    try:
        with open(workflow_path, 'w') as f:
            json.dump(workflow_data, f, indent=2)
    except Exception as e:
        return jsonify({'error': f'Failed to save workflow: {e}'}), 500

    # Clear log queue
    while not log_queue.empty():
        log_queue.get()

    # Start simulation in background thread
    is_running = True
    simulation_thread = threading.Thread(
        target=run_simulation_async,
        args=(workflow_path, entry_subworkflow)  # Pass entry_subworkflow
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
    global simulation_process, is_running
    
    if not is_running or not simulation_process:
        return jsonify({'error': 'No simulation running'}), 400
    
    try:
        simulation_process.terminate()
        simulation_process.wait(timeout=5)
        log_queue.put("[STOP] Simulation stopped by user\n")
        is_running = False
        return jsonify({'status': 'stopped'})
    except subprocess.TimeoutExpired:
        simulation_process.kill()
        log_queue.put("[STOP] Simulation forcefully killed\n")
        is_running = False
        return jsonify({'status': 'killed'})
    except Exception as e:
        return jsonify({'error': f'Failed to stop simulation: {e}'}), 500


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
                # Try to get log from queue (non-blocking with timeout)
                try:
                    log_line = log_queue.get(timeout=1)
                    
                    # Parse log type
                    log_type = 'info'
                    if log_line.startswith('[ERROR]'):
                        log_type = 'error'
                    elif log_line.startswith('[COMPLETE]'):
                        log_type = 'complete'
                    elif log_line.startswith('[FAILED]'):
                        log_type = 'error'
                    elif log_line.startswith('[STOP]'):
                        log_type = 'warning'
                    
                    # Send log as SSE
                    yield f"data: {json.dumps({'type': log_type, 'message': log_line})}\n\n"
                    
                except queue.Empty:
                    # Send heartbeat every 15 seconds to keep connection alive
                    if time.time() - last_heartbeat > 15:
                        yield f"data: {json.dumps({'type': 'heartbeat', 'message': ''})}\n\n"
                        last_heartbeat = time.time()
                    
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

        # Import registry
        from src.workflow.registry import get_default_registry

        # Get the registry
        registry = get_default_registry()

        # Convert to JSON-serializable format
        functions_dict = {}
        for name, metadata in registry.functions.items():
            functions_dict[name] = {
                'name': metadata.name,
                'display_name': metadata.display_name,
                'description': metadata.description,
                'category': metadata.category.value,  # Convert enum to string
                'parameters': [
                    {
                        'name': p.name,
                        'type': p.type.value,  # Convert enum to string
                        'description': p.description,
                        'default': p.default,
                        'required': p.required,
                        'min_value': p.min_value,
                        'max_value': p.max_value,
                        'options': p.options
                    }
                    for p in metadata.parameters
                ],
                'inputs': metadata.inputs,
                'outputs': metadata.outputs,
                'cloneable': metadata.cloneable,
                'module_path': metadata.module_path,
                'source_file': metadata.source_file
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

        if not function_name:
            return jsonify({'error': 'Missing required parameter: name'}), 400

        # Get engine directory
        engine_dir = get_engine_path().parent

        # If source_file is provided, use it; otherwise try to find it from registry
        if not source_file:
            # Try to load from registry
            try:
                sys.path.insert(0, str(engine_dir))
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
        file_path = engine_dir / source_file

        if not file_path.exists():
            return jsonify({
                'error': f'Source file not found: {source_file}',
                'file_path': str(file_path)
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
            'file_path': str(source_file),
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

        function_name = data.get('name')
        source_code = data.get('source')
        source_file = data.get('file')

        if not function_name or not source_code:
            return jsonify({'error': 'Missing required fields: name, source'}), 400

        # Get engine directory
        engine_dir = get_engine_path().parent

        # If source_file is not provided, try to find it from registry
        if not source_file:
            try:
                sys.path.insert(0, str(engine_dir))
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
        file_path = engine_dir / source_file

        # Validate that file exists (don't create new files)
        if not file_path.exists():
            return jsonify({
                'error': f'Source file not found: {source_file}. Cannot create new files.',
                'file_path': str(file_path)
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
        backup_path = file_path.with_suffix('.py.bak')
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
            'file_path': str(source_file),
            'message': f'Successfully saved {function_name}',
            'backup_path': str(backup_path.name)
        })

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
            # Use provided target path
            target_file = engine_root / target_path
        else:
            # Try to find the function in registry
            registry_path = engine_root / "src" / "workflow" / "registry.py"

            if not registry_path.exists():
                return jsonify({'error': 'Registry file not found'}), 404

            # Parse registry to find source_file
            import re
            registry_content = registry_path.read_text()

            # Look for function metadata with source_file
            pattern = rf"'{function_name}'.*?source_file\s*=\s*['\"]([^'\"]+)['\"]"
            match = re.search(pattern, registry_content, re.DOTALL)

            if not match:
                return jsonify({'error': f'Function {function_name} not found in registry'}), 404

            source_file_path = match.group(1)
            target_file = engine_root / source_file_path

        # Create backup of existing file
        if target_file.exists():
            backup_dir = target_file.parent / "backups"
            backup_dir.mkdir(exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{target_file.stem}_backup_{timestamp}{target_file.suffix}"
            backup_path = backup_dir / backup_filename

            # Copy existing file to backup
            backup_path.write_text(target_file.read_text())
        else:
            backup_path = None

        # Write uploaded file
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(file_content)

        return jsonify({
            'success': True,
            'file_path': str(target_file.relative_to(engine_root)),
            'message': f'Successfully uploaded {file.filename} for {function_name}',
            'backup_path': str(backup_path.name) if backup_path else None
        })

    except Exception as e:
        return jsonify({'error': f'Upload failed: {e}'}), 500


@app.route('/api/results/list', methods=['GET'])
def list_results():
    """
    List results for a specific subworkflow (v2.0 nested structure).

    Query params:
        subworkflow_name: Name of the subworkflow
        subworkflow_kind: 'composer' or 'subworkflow'
        include_all: If 'true', include results from all subworkflows (default for composers)
    """
    try:
        # Results are stored in opencellcomms_gui/results/, not opencellcomms_engine/results/
        gui_dir = Path(__file__).parent.parent  # opencellcomms_gui directory
        results_dir = gui_dir / "results"

        # Get query parameters
        subworkflow_name = request.args.get('subworkflow_name', 'main')
        subworkflow_kind = request.args.get('subworkflow_kind', 'composer')
        include_all = request.args.get('include_all', 'true' if subworkflow_kind == 'composer' else 'false')

        if not results_dir.exists():
            return jsonify({'success': True, 'plots': []})

        plots = []

        def scan_directory(directory, category_prefix=""):
            """Scan a directory for image files."""
            found = []
            if not directory.exists():
                return found
            for item in directory.iterdir():
                if item.is_dir():
                    # Scan subdirectory
                    for plot_file in sorted(item.glob('*.png')):
                        cat = f"{category_prefix}{item.name}" if category_prefix else item.name
                        found.append({
                            'name': plot_file.name,
                            'path': str(plot_file.relative_to(gui_dir)),
                            'category': cat
                        })
                elif item.suffix.lower() == '.png':
                    # Direct PNG file
                    cat = category_prefix.rstrip('/') if category_prefix else 'default'
                    found.append({
                        'name': item.name,
                        'path': str(item.relative_to(gui_dir)),
                        'category': cat
                    })
            return found

        if include_all == 'true':
            # Scan all results directories (composers and subworkflows)
            for kind_dir in ['composers', 'subworkflows']:
                kind_path = results_dir / kind_dir
                if kind_path.exists():
                    for sw_dir in kind_path.iterdir():
                        if sw_dir.is_dir():
                            prefix = f"{kind_dir}/{sw_dir.name}/"
                            plots.extend(scan_directory(sw_dir, prefix))

            # Also scan root results directory for legacy images
            plots.extend(scan_directory(results_dir, "root/"))
        else:
            # Only scan the specific subworkflow directory
            kind_plural = 'composers' if subworkflow_kind == 'composer' else 'subworkflows'
            subworkflow_dir = results_dir / kind_plural / subworkflow_name
            plots.extend(scan_directory(subworkflow_dir))

        # Sort plots by category and name
        plots.sort(key=lambda p: (p['category'], p['name']))

        return jsonify({
            'success': True,
            'plots': plots,
            'subworkflow_name': subworkflow_name,
            'subworkflow_kind': subworkflow_kind
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/results/plot/<path:plot_path>', methods=['GET'])
def get_plot(plot_path):
    """Serve a plot image file."""
    try:
        # Results are stored in ABM_GUI/results/, paths are relative to ABM_GUI
        gui_dir = Path(__file__).parent.parent  # ABM_GUI directory
        full_path = gui_dir / plot_path

        if not full_path.exists():
            return jsonify({'success': False, 'error': 'Plot not found'}), 404

        if not full_path.suffix == '.png':
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400

        return send_file(full_path, mimetype='image/png')

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

        library_file = Path(library_path)

        if not library_file.exists():
            return jsonify({'success': False, 'error': f'Library file not found: {library_path}'}), 404

        if library_file.suffix != '.py':
            return jsonify({'success': False, 'error': 'Library must be a .py file'}), 400

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


@app.route('/api/observability/nodes', methods=['GET'])
def get_observability_nodes():
    """Get node stats for badges (status, timing, log counts)."""
    try:
        obs_dir = get_observability_dir()
        events_file = obs_dir / "events.jsonl"

        if not events_file.exists():
            return jsonify({'success': True, 'nodes': {}})

        # Parse events and aggregate by node
        node_stats = {}

        with open(events_file, 'r') as f:
            for line in f:
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

        # Convert scope key to safe directory name
        safe_key = scope_key.replace(":", "_")
        scope_dir = obs_dir / "context" / safe_key

        if not scope_dir.exists():
            return jsonify({'success': False, 'error': f'No context data for scope: {scope_key}'}), 404

        # If version not specified, get the latest
        if not version:
            snapshot_files = sorted(scope_dir.glob("v*.json"))
            if not snapshot_files:
                return jsonify({'success': False, 'error': 'No snapshots available'}), 404
            snapshot_file = snapshot_files[-1]
        else:
            snapshot_file = scope_dir / f"v{int(version):06d}.json"

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

        # Convert scope key to safe directory name
        safe_key = scope_key.replace(":", "_")
        context_dir = obs_dir / "context" / safe_key
        diff_dir = context_dir / "diff"

        # Try pre-computed diff first
        if diff_dir.exists():
            diff_file = diff_dir / f"v{int(from_version):06d}_to_v{int(to_version):06d}.json"
            if diff_file.exists():
                diff = json.loads(diff_file.read_text())
                return jsonify({'success': True, 'diff': diff})

        # Compute diff on-the-fly from snapshots
        from_file = context_dir / f"v{int(from_version):06d}.json"
        to_file = context_dir / f"v{int(to_version):06d}.json"

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

        # Security: ensure path doesn't escape observability directory
        full_path = (obs_dir / "artifacts" / artifact_path).resolve()
        if not str(full_path).startswith(str(obs_dir.resolve())):
            return jsonify({'success': False, 'error': 'Invalid path'}), 400

        if not full_path.exists():
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

        # Convert scope key to safe directory name
        safe_key = scope_key.replace(":", "_")
        scope_dir = obs_dir / "context" / safe_key

        if not scope_dir.exists():
            return jsonify({'success': True, 'versions': []})

        versions = []
        for f in sorted(scope_dir.glob("v*.json")):
            try:
                version_num = int(f.stem[1:])  # Extract number from v000001
                versions.append(version_num)
            except ValueError:
                continue

        return jsonify({'success': True, 'versions': versions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("OpenCellComms Backend Server")
    print("=" * 60)
    print(f"Engine path: {get_engine_path()}")
    print(f"Engine exists: {get_engine_path().exists()}")
    print("=" * 60)
    print("Starting server on http://localhost:5001")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)

