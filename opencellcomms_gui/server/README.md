# MicroC Backend Server

Flask backend API for running MicroC simulations from the GUI.

## Setup

### 1. Install Dependencies

```bash
cd server
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python api.py
```

The server will start on `http://localhost:5001`

## API Endpoints

### `GET /api/health`
Health check endpoint to verify server and MicroC availability.

**Response:**
```json
{
  "status": "healthy",
  "microc_path": "/path/to/run_microc.py",
  "microc_exists": true
}
```

### `GET /api/status`
Get current simulation status.

**Response:**
```json
{
  "running": false,
  "pid": null
}
```

### `POST /api/run`
Start a new simulation.

**Request Body:**
```json
{
  "config_path": "tests/jayatilake_experiment/jayatilake_experiment_config.yaml",
  "workflow": {
    "name": "My Workflow",
    "version": "1.0",
    "stages": { ... }
  }
}
```

**Response:**
```json
{
  "status": "started",
  "config": "tests/jayatilake_experiment/jayatilake_experiment_config.yaml",
  "workflow": "/tmp/microc_workflow.json"
}
```

### `POST /api/stop`
Stop the running simulation.

**Response:**
```json
{
  "status": "stopped"
}
```

### `GET /api/logs`
Stream logs using Server-Sent Events (SSE).

**Response:** Event stream with JSON messages:
```
data: {"type": "info", "message": "[LOG] Starting simulation...\n"}

data: {"type": "error", "message": "[ERROR] Failed to load config\n"}

data: {"type": "complete", "message": "[COMPLETE] Simulation completed successfully\n"}
```

## Architecture

```
┌─────────────────┐         HTTP/SSE          ┌─────────────────┐
│                 │ ◄────────────────────────► │                 │
│  React Frontend │                            │  Flask Backend  │
│  (Port 3001)    │                            │  (Port 5001)    │
│                 │                            │                 │
└─────────────────┘                            └────────┬────────┘
                                                        │
                                                        │ subprocess
                                                        ▼
                                                ┌─────────────────┐
                                                │                 │
                                                │  run_microc.py  │
                                                │                 │
                                                └─────────────────┘
```

## How It Works

1. **Frontend** sends workflow JSON to `/api/run`
2. **Backend** saves workflow to `/tmp/microc_workflow.json`
3. **Backend** spawns `run_microc.py --sim <config> --workflow <workflow>`
4. **Backend** streams stdout/stderr to log queue
5. **Frontend** connects to `/api/logs` via SSE
6. **Backend** sends log messages as they arrive
7. **Frontend** displays logs in real-time

## Log Types

- `info` - Normal log messages (blue)
- `error` - Error messages (red)
- `warning` - Warning messages (yellow)
- `complete` - Simulation completed successfully (green)
- `heartbeat` - Keep-alive message (ignored by frontend)

## Development

The server runs in debug mode by default, which enables:
- Auto-reload on code changes
- Detailed error messages
- Debug console

For production, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 api:app
```

## Troubleshooting

### "Backend server not reachable"
- Make sure the server is running: `python api.py`
- Check that port 5001 is not in use
- Verify CORS is enabled in `api.py`

### "MicroC not found"
- Check the path in the health check response
- Verify `run_microc.py` exists at `../microc-2.0/run_microc.py`
- Update `get_microc_path()` in `api.py` if needed

### "Simulation failed to start"
- Check the config path is correct
- Verify the workflow JSON is valid
- Check MicroC dependencies are installed
- Look at the error logs in the frontend

### SSE connection drops
- The server sends heartbeat messages every 15 seconds
- If connection drops, frontend auto-reconnects after 5 seconds
- Check browser console for SSE errors

