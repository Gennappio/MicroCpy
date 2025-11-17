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


def run_simulation_async(config_path, workflow_path):
    """Run MicroC simulation in background thread"""
    global simulation_process, is_running

    try:
        microc_path = get_microc_path()

        if not microc_path.exists():
            log_queue.put(f"[ERROR] MicroC not found at: {microc_path}\n")
            is_running = False
            return

        # Get microc-2.0 directory (working directory for simulation)
        microc_dir = microc_path.parent

        # Build command - use either --workflow or --sim (mutually exclusive)
        cmd = [
            sys.executable,
            str(microc_path)
        ]

        if workflow_path:
            # Workflow mode - complete user control
            cmd.extend(["--workflow", workflow_path])
            log_queue.put(f"[START] Running workflow mode: {workflow_path}\n")
        elif config_path:
            # Default pipeline mode - hardcoded behavior
            cmd.extend(["--sim", config_path])
            log_queue.put(f"[START] Running default pipeline: {config_path}\n")
        else:
            log_queue.put(f"[ERROR] Either config_path or workflow_path must be provided\n")
            is_running = False
            return

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
    """Start a new simulation"""
    global simulation_thread, is_running

    if is_running:
        return jsonify({'error': 'Simulation already running'}), 400

    data = request.json
    config_path = data.get('config_path')  # Optional - only for --sim mode
    workflow_data = data.get('workflow')   # Optional - only for --workflow mode

    # Must have either config_path or workflow
    if not config_path and not workflow_data:
        return jsonify({'error': 'Either config_path or workflow is required'}), 400

    # Save workflow to temporary file if provided
    workflow_path = None
    if workflow_data:
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
        args=(config_path, workflow_path)
    )
    simulation_thread.daemon = True
    simulation_thread.start()

    return jsonify({
        'status': 'started',
        'config': config_path,
        'workflow': workflow_path
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
    """List all simulation result folders with their plots."""
    try:
        server_dir = Path(__file__).parent
        results_dir = server_dir.parent.parent / "microc-2.0" / "results"

        if not results_dir.exists():
            return jsonify({'success': True, 'results': []})

        results = []

        # Iterate through all result folders
        for result_folder in sorted(results_dir.iterdir(), reverse=True):
            if not result_folder.is_dir():
                continue

            # Skip if it's a nested folder (like jayatilake_experiment)
            # We'll handle those separately
            plots_dir = result_folder / "plots"

            if plots_dir.exists():
                result_info = {
                    'name': result_folder.name,
                    'path': str(result_folder.relative_to(results_dir.parent)),
                    'timestamp': result_folder.name,
                    'plots': []
                }

                # Scan for plot categories
                for category_dir in plots_dir.iterdir():
                    if category_dir.is_dir():
                        category_plots = []
                        for plot_file in sorted(category_dir.glob('*.png')):
                            category_plots.append({
                                'name': plot_file.name,
                                'path': str(plot_file.relative_to(results_dir.parent)),
                                'category': category_dir.name
                            })

                        if category_plots:
                            result_info['plots'].extend(category_plots)

                if result_info['plots']:
                    results.append(result_info)

        return jsonify({'success': True, 'results': results})

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


if __name__ == '__main__':
    print("=" * 60)
    print("MicroC Backend Server")
    print("=" * 60)
    print(f"MicroC path: {get_microc_path()}")
    print(f"MicroC exists: {get_microc_path().exists()}")
    print("=" * 60)
    print("Starting server on http://localhost:5000")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)

