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
from flask import Flask, request, jsonify, Response
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

        # Build command
        cmd = [
            sys.executable,
            str(microc_path),
            "--sim", config_path
        ]

        if workflow_path:
            cmd.extend(["--workflow", workflow_path])

        log_queue.put(f"[START] Running: {' '.join(cmd)}\n")
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
    config_path = data.get('config_path')
    workflow_data = data.get('workflow')
    
    if not config_path:
        return jsonify({'error': 'config_path is required'}), 400
    
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

