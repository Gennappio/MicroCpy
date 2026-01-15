# Commands Reference

## Copy-Paste Ready Commands

### Setup & Run Everything

**All-in-one setup (run these in order):**

```bash
# Terminal 1: Backend Server
cd ABM_GUI/server
pip install -r requirements.txt
python api.py
```

```bash
# Terminal 2: Frontend (in new terminal)
cd ABM_GUI
npm install
npm run dev
```

Then open browser to: `http://localhost:5173`

---

## Individual Commands

### Backend Server

```bash
# Navigate to server directory
cd ABM_GUI/server

# Install dependencies (first time only)
pip install -r requirements.txt

# Start the server
python api.py

# Expected output:
# Starting server on http://localhost:5001
# * Running on http://127.0.0.1:5001
```

### Frontend Development Server

```bash
# Navigate to GUI directory
cd ABM_GUI

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Expected output:
# VITE v5.x.x ready in xxx ms
# ➜ Local: http://localhost:5173/
```

### Build for Production

```bash
# Build the frontend
cd ABM_GUI
npm run build

# Preview production build
npm run preview
```

### Run Simulation from Command Line

```bash
# After exporting workflow from GUI
cd microc-2.0
python run_microc.py --workflow ../exported_workflow.json
```

---

## Troubleshooting Commands

### Check if ports are in use

```bash
# Check port 5001 (backend)
lsof -i :5001

# Check port 5173 (frontend)
lsof -i :5173
```

### Kill processes on ports

```bash
# Kill process on port 5001
lsof -i :5001 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Kill process on port 5173
lsof -i :5173 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Check Python version

```bash
python --version
# Should be 3.8 or higher
```

### Check Node.js version

```bash
node --version
npm --version
# Should be Node 18+ and npm 9+
```

### Test command-line simulation

```bash
# Run the test script
python test_ecosystem_sim.py

# Expected output:
# ✓ Loaded: Predator-Prey Ecosystem Simulation
# ✓ Executor created successfully
# [INIT] Created 50x50 grid
# [INIT] Spawned 100 prey agents
# ...
# ✓ Simulation completed 50 steps
```

---

## File Paths

### Ecosystem Simulation Files

```bash
# Workflow definition
example_projects/ecosystem_sim/workflows/ecosystem_workflow.json

# Functions
example_projects/ecosystem_sim/functions/ecosystem_functions.py

# Test script
test_ecosystem_sim.py

# Results
results/population_history.csv
```

### GUI Files

```bash
# Backend server
ABM_GUI/server/api.py

# Frontend
ABM_GUI/src/App.jsx

# Configuration
ABM_GUI/package.json
ABM_GUI/vite.config.js
```

### MicroC Files

```bash
# Main runner
microc-2.0/run_microc.py

# Workflow executor
microc-2.0/src/workflow/executor.py

# Workflow loader
microc-2.0/src/workflow/loader.py
```

---

## Environment Variables (Optional)

```bash
# Set custom backend port
export FLASK_PORT=5001

# Set custom frontend port
export VITE_PORT=5173

# Enable debug mode
export FLASK_DEBUG=1
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start backend | `cd ABM_GUI/server && python api.py` |
| Start frontend | `cd ABM_GUI && npm run dev` |
| Test CLI | `python test_ecosystem_sim.py` |
| Build GUI | `cd ABM_GUI && npm run build` |
| Check backend | `curl http://localhost:5001/api/health` |
| View logs | Check browser console (F12) |

---

## Browser URLs

| Service | URL |
|---------|-----|
| Frontend GUI | `http://localhost:5173` |
| Backend API | `http://localhost:5001` |
| Health Check | `http://localhost:5001/api/health` |

---

## Next Steps

1. Run the two terminal commands above
2. Open `http://localhost:5173` in browser
3. Click "Import JSON"
4. Select `example_projects/ecosystem_sim/workflows/ecosystem_workflow.json`
5. Click "Run Simulation"
6. Watch the logs!

---

**All commands are ready to copy-paste. Just follow the order above!**

