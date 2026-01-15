#!/usr/bin/env python3
"""
Flask Backend API for MicroC GUI
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


def get_microc_path():
    """Get the path to MicroC run_microc.py"""
    # Server is in ABM_GUI/server, MicroC is in ../microc-2.0
    server_dir = Path(__file__).parent
    microc_path = server_dir.parent.parent / "microc-2.0" / "run_microc.py"
    return microc_path


def setup_results_directories(workflow_data, microc_dir):
    """
    Setup nested results directory structure according to v2.0 spec.

    Creates:
    - results/composers/<name>/ for each composer
    - results/subworkflows/<name>/ for each subworkflow

    Clears existing results to implement overwrite semantics.

    Args:
        workflow_data: Workflow JSON dict
        microc_dir: Path to microc-2.0 directory
    """
    results_dir = microc_dir / "results"

    # Get subworkflow kinds from metadata
    subworkflow_kinds = workflow_data.get('metadata', {}).get('gui', {}).get('subworkflow_kinds', {})

    # Create base directories
    composers_dir = results_dir / "composers"
    subworkflows_dir = results_dir / "subworkflows"

    # Clear existing results (overwrite semantics)
    if composers_dir.exists():
        shutil.rmtree(composers_dir)
        log_queue.put("[INFO] Cleared existing composer results\n")

    if subworkflows_dir.exists():
        shutil.rmtree(subworkflows_dir)
        log_queue.put("[INFO] Cleared existing subworkflow results\n")

    # Create directories for each subworkflow based on its kind
    for subworkflow_name, subworkflow_data in workflow_data.get('subworkflows', {}).items():
        kind = subworkflow_kinds.get(subworkflow_name,
                                     'composer' if subworkflow_name == 'main' else 'subworkflow')

        if kind == 'composer':
            subworkflow_dir = composers_dir / subworkflow_name
        else:
            subworkflow_dir = subworkflows_dir / subworkflow_name

        subworkflow_dir.mkdir(parents=True, exist_ok=True)
        log_queue.put(f"[INFO] Created results directory: {subworkflow_dir.relative_to(microc_dir)}\n")

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
    """Run MicroC workflow in background thread (workflow-only mode)"""
    global simulation_process, is_running

    try:
        microc_path = get_microc_path()

        if not microc_path.exists():
            log_queue.put(f"[ERROR] MicroC not found at: {microc_path}\n")
            is_running = False
            return

        # Get microc-2.0 directory (working directory for simulation)
        microc_dir = microc_path.parent

        # Build command - GUI runs workflows only
        if not workflow_path:
            log_queue.put(f"[ERROR] Workflow path must be provided\n")
            is_running = False
            return

        cmd = [
            sys.executable,
            str(microc_path),
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
        log_queue.put(f"[INFO] Working directory: {microc_dir}\n")
        log_queue.put("[INFO] Starting MicroC simulation...\n")

        # Start subprocess with correct working directory
        simulation_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=str(microc_dir)  # Set working directory to microc-2.0
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
        microc_path = get_microc_path()
        microc_dir = microc_path.parent
        sys.path.insert(0, str(microc_dir))

        from src.workflow.schema import Workflow

        # Load and validate workflow
        workflow_obj = Workflow.from_dict(workflow_data)
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
        error_msg = f'Workflow validation error: {str(e)}'
        log_queue.put(f"[ERROR] {error_msg}\n")
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
    try:
        setup_results_directories(workflow_data, microc_dir)
    except Exception as e:
        error_msg = f'Failed to setup results directories: {str(e)}'
        log_queue.put(f"[ERROR] {error_msg}\n")
        return jsonify({'error': error_msg}), 500

    # Save workflow to temporary file
    workflow_path = "/tmp/microc_workflow.json"
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
        'microc_path': str(get_microc_path()),
        'microc_exists': get_microc_path().exists()
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
        # Get microc-2.0 directory
        microc_dir = get_microc_path().parent

        # Add to Python path
        sys.path.insert(0, str(microc_dir))

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
        - file: Optional source file path (relative to microc-2.0)

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

        # Get microc-2.0 directory
        microc_dir = get_microc_path().parent

        # If source_file is provided, use it; otherwise try to find it from registry
        if not source_file:
            # Try to load from registry
            try:
                sys.path.insert(0, str(microc_dir))
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
        file_path = microc_dir / source_file

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

        # Get microc-2.0 directory
        microc_dir = get_microc_path().parent

        # If source_file is not provided, try to find it from registry
        if not source_file:
            try:
                sys.path.insert(0, str(microc_dir))
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
        file_path = microc_dir / source_file

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
        microc_root = Path(__file__).parent.parent.parent / "microc-2.0"

        if target_path:
            # Use provided target path
            target_file = microc_root / target_path
        else:
            # Try to find the function in registry
            registry_path = microc_root / "src" / "workflow" / "registry.py"

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
            target_file = microc_root / source_file_path

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
            'file_path': str(target_file.relative_to(microc_root)),
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
    """
    try:
        server_dir = Path(__file__).parent
        results_dir = server_dir.parent.parent / "microc-2.0" / "results"

        # Get query parameters
        subworkflow_name = request.args.get('subworkflow_name', 'main')
        subworkflow_kind = request.args.get('subworkflow_kind', 'composer')

        if not results_dir.exists():
            return jsonify({'success': True, 'plots': []})

        # Determine the subworkflow results directory
        kind_plural = 'composers' if subworkflow_kind == 'composer' else 'subworkflows'
        subworkflow_dir = results_dir / kind_plural / subworkflow_name

        if not subworkflow_dir.exists():
            return jsonify({'success': True, 'plots': []})

        plots = []

        # Scan for all image files in the subworkflow directory
        # Support nested categories (debug/, analysis/, etc.)
        for category_dir in subworkflow_dir.iterdir():
            if category_dir.is_dir():
                # Scan category subdirectory
                for plot_file in sorted(category_dir.glob('*.png')):
                    plots.append({
                        'name': plot_file.name,
                        'path': str(plot_file.relative_to(results_dir.parent)),
                        'category': category_dir.name
                    })
            elif category_dir.suffix == '.png':
                # Direct PNG file in subworkflow directory
                plots.append({
                    'name': category_dir.name,
                    'path': str(category_dir.relative_to(results_dir.parent)),
                    'category': 'default'
                })

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
        server_dir = Path(__file__).parent
        microc_dir = server_dir.parent.parent / "microc-2.0"
        full_path = microc_dir / plot_path

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


# ============================================================================
# Project Management API (Context Management v2)
# ============================================================================

PROJECT_CONFIG_FILENAME = 'project.json'
CONTEXT_REGISTRY_DIR = '.microc'
CONTEXT_REGISTRY_FILENAME = 'context_registry.json'


def get_workspace_root() -> Path:
    """Get the workspace root (parent of ABM_GUI/server)"""
    return Path(__file__).parent.parent.parent


def resolve_project_path(project_root: str) -> Path:
    """Resolve project path - handles both absolute and relative paths"""
    path = Path(project_root)
    if path.is_absolute():
        return path
    # Resolve relative to workspace root
    return get_workspace_root() / path


def get_project_config_path(project_root: str) -> Path:
    """Get the path to project.json (inside .microc/)"""
    return resolve_project_path(project_root) / CONTEXT_REGISTRY_DIR / PROJECT_CONFIG_FILENAME


def get_context_registry_path(project_root: str) -> Path:
    """Get the path to context_registry.json (inside .microc/)"""
    return resolve_project_path(project_root) / CONTEXT_REGISTRY_DIR / CONTEXT_REGISTRY_FILENAME


@app.route('/api/project/create', methods=['POST'])
def create_project():
    """
    Create a new project with project.json and context_registry.json

    Request body:
        {
            'project_root': '/path/to/project',
            'config': { ... project config ... },
            'registry': { ... context registry ... }
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        project_root = data.get('project_root')
        config = data.get('config')
        registry = data.get('registry')

        if not project_root or not config or not registry:
            return jsonify({'error': 'Missing required fields: project_root, config, registry'}), 400

        project_path = Path(project_root)

        # Create project directory if it doesn't exist
        project_path.mkdir(parents=True, exist_ok=True)

        # Create .microc directory
        microc_dir = project_path / CONTEXT_REGISTRY_DIR
        microc_dir.mkdir(exist_ok=True)

        # Write project.json
        config_path = get_project_config_path(project_root)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        # Write context_registry.json
        registry_path = get_context_registry_path(project_root)
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)

        return jsonify({
            'success': True,
            'project_root': str(project_path),
            'config_path': str(config_path),
            'registry_path': str(registry_path)
        })

    except Exception as e:
        return jsonify({'error': f'Failed to create project: {e}'}), 500


@app.route('/api/project/open', methods=['POST'])
def open_project():
    """
    Open an existing project

    Request body:
        {
            'project_root': '/path/to/project'
        }

    Returns:
        {
            'config': { ... },
            'registry': { ... }
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        project_root = data.get('project_root')
        if not project_root:
            return jsonify({'error': 'Missing project_root'}), 400

        config_path = get_project_config_path(project_root)
        registry_path = get_context_registry_path(project_root)

        # Check if project exists
        if not config_path.exists():
            return jsonify({
                'error': 'Project not found',
                'needs_creation': True
            }), 404

        # Load project config
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Load or create context registry
        if registry_path.exists():
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
        else:
            # Create default registry if missing
            registry = {
                'schema_version': 1,
                'project_id': config.get('project_id', ''),
                'revision': 1,
                'keys': []
            }
            # Ensure directory exists
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2)

        return jsonify({
            'success': True,
            'config': config,
            'registry': registry
        })

    except Exception as e:
        return jsonify({'error': f'Failed to open project: {e}'}), 500


@app.route('/api/project/save-config', methods=['POST'])
def save_project_config():
    """
    Save project configuration

    Request body:
        {
            'project_root': '/path/to/project',
            'config': { ... }
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        project_root = data.get('project_root')
        config = data.get('config')

        if not project_root or not config:
            return jsonify({'error': 'Missing required fields'}), 400

        config_path = get_project_config_path(project_root)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': f'Failed to save config: {e}'}), 500


@app.route('/api/project/save-registry', methods=['POST'])
def save_context_registry():
    """
    Save context registry with optimistic concurrency control

    Request body:
        {
            'project_root': '/path/to/project',
            'registry': { ... },
            'expected_revision': 5
        }

    Returns:
        {
            'success': true,
            'new_revision': 6
        }

    Or on conflict:
        {
            'revision_conflict': true,
            'current_revision': 7,
            'error': '...'
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        project_root = data.get('project_root')
        registry = data.get('registry')
        expected_revision = data.get('expected_revision')

        if not project_root or not registry:
            return jsonify({'error': 'Missing required fields'}), 400

        registry_path = get_context_registry_path(project_root)

        # Check current revision for optimistic concurrency
        if registry_path.exists() and expected_revision is not None:
            with open(registry_path, 'r', encoding='utf-8') as f:
                current_registry = json.load(f)

            current_revision = current_registry.get('revision', 1)

            if current_revision != expected_revision:
                return jsonify({
                    'revision_conflict': True,
                    'current_revision': current_revision,
                    'error': 'Registry was modified by another process'
                }), 409

        # Increment revision
        new_revision = registry.get('revision', 1) + 1
        registry['revision'] = new_revision

        # Ensure directory exists
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Write registry
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)

        return jsonify({
            'success': True,
            'new_revision': new_revision
        })

    except Exception as e:
        return jsonify({'error': f'Failed to save registry: {e}'}), 500


@app.route('/api/project/reload-registry', methods=['POST'])
def reload_context_registry():
    """
    Reload context registry from disk

    Request body:
        {
            'project_root': '/path/to/project'
        }

    Returns:
        {
            'registry': { ... }
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        project_root = data.get('project_root')
        if not project_root:
            return jsonify({'error': 'Missing project_root'}), 400

        registry_path = get_context_registry_path(project_root)

        if not registry_path.exists():
            return jsonify({'error': 'Registry not found'}), 404

        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)

        return jsonify({
            'success': True,
            'registry': registry
        })

    except Exception as e:
        return jsonify({'error': f'Failed to reload registry: {e}'}), 500


@app.route('/api/project/exists', methods=['GET'])
def check_project_exists():
    """
    Check if a project exists at the given path

    Query params:
        project_root: Path to check
    """
    try:
        project_root = request.args.get('project_root')
        if not project_root:
            return jsonify({'error': 'Missing project_root'}), 400

        config_path = get_project_config_path(project_root)

        return jsonify({
            'exists': config_path.exists(),
            'project_root': project_root
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("MicroC Backend Server")
    print("=" * 60)
    print(f"MicroC path: {get_microc_path()}")
    print(f"MicroC exists: {get_microc_path().exists()}")
    print("=" * 60)
    print("Starting server on http://localhost:5001")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)

