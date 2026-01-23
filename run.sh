#!/bin/bash
# OpenCellComms Launch Script for macOS/Linux
# Starts both the backend server and frontend development server

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              OpenCellComms Launcher                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "[!] No virtual environment found. Please run ./install.sh first."
    exit 1
fi

echo "[✓] Virtual environment activated"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "[!] Shutting down..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo "[✓] Shutdown complete"
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start Flask backend server
echo "[...] Starting backend server..."
cd opencellcomms_gui/server
python api.py > /dev/null 2>&1 &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
sleep 2

# Check if backend started successfully
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo "[✓] Backend server started (PID: $BACKEND_PID)"
else
    echo "[✗] Failed to start backend server"
    exit 1
fi

# Start React frontend
echo "[...] Starting frontend server..."
cd opencellcomms_gui
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 3

# Check if frontend started successfully
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "[✓] Frontend server started (PID: $FRONTEND_PID)"
else
    echo "[✗] Failed to start frontend server"
    cleanup
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              OpenCellComms is Running!                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:5001"
echo ""
echo "  Press Ctrl+C to stop all servers"
echo ""

# Wait for processes
wait $FRONTEND_PID $BACKEND_PID 2>/dev/null || true

