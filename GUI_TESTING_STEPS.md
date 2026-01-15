# Step-by-Step: Testing Ecosystem Simulation in GUI

## Prerequisites

Make sure you have:
1. ✅ Node.js 18+ installed
2. ✅ Python 3.8+ installed
3. ✅ Dependencies installed

## Setup Instructions

### Terminal 1: Start Backend Server

```bash
cd ABM_GUI/server
pip install -r requirements.txt
python api.py
```

Expected output:
```
============================================================
MicroC Backend Server
============================================================
MicroC path: /path/to/run_microc.py
MicroC exists: True
============================================================
Starting server on http://localhost:5001
============================================================
 * Running on http://127.0.0.1:5001
```

**Keep this terminal open!**

### Terminal 2: Start Frontend Dev Server

```bash
cd ABM_GUI
npm install  # Only first time
npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

The browser should automatically open at `http://localhost:5173/`

## Using the GUI

### Step 1: Import the Ecosystem Workflow

1. Look for **"Import JSON"** button in the top menu
2. Click it
3. Navigate to: `example_projects/ecosystem_sim/workflows/ecosystem_workflow.json`
4. Click "Open"

You should see the workflow load with:
- Main composer showing 3 subworkflow calls
- Initialize, Simulation Step, Output Results subworkflows
- All ecosystem functions visible

### Step 2: Explore the Workflow

- **Click on "main"** tab to see the main composer
- **Click on "initialize"** tab to see initialization functions
- **Click on "simulation_step"** tab to see the simulation loop
- **Click on "output_results"** tab to see output functions

### Step 3: Run the Simulation

1. Look for **"Run Simulation"** or **"Execute"** button
2. Click it
3. Watch the logs stream in real-time showing:
   - Grid creation
   - Agent spawning
   - Simulation steps
   - Population changes
   - Results saved

### Step 4: View Results

After simulation completes:
- Check `results/population_history.csv` for data
- View the summary in the logs
- See extinction events if they occur

## Expected Output

```
[INIT] Created 50x50 grid
[INIT] Spawned 100 prey agents
[INIT] Spawned 20 predator agents
[INIT] Initialized population history tracker
[STEP 0] Predators: 20, Prey: 105
[STEP 1] Predators: 20, Prey: 112
...
[STEP 49] Predators: 0, Prey: 1121
[OUTPUT] Saved population history to results/population_history.csv

==================================================
ECOSYSTEM SIMULATION SUMMARY
==================================================
Total steps: 50
Initial population: 20 predators, 102 prey
Final population: 0 predators, 1121 prey
Peak predators: 20
Peak prey: 1121
⚠️  PREDATOR EXTINCTION occurred!
==================================================
```

## Troubleshooting

### GUI won't load
- Check if `npm run dev` is running
- Try `http://localhost:5173` in browser
- Check browser console (F12) for errors

### "Backend not reachable"
- Ensure `python api.py` is running
- Check port 5001 is not blocked
- Verify CORS is enabled in api.py

### Workflow won't import
- Check file path is correct
- Verify ecosystem_workflow.json exists
- Check browser console for errors

### Simulation won't run
- Ensure backend server is running
- Check ecosystem_functions.py exists
- Verify all paths are correct

## Next Steps

Once working:
1. **Modify parameters** in the main composer
2. **Change predation rates** to see different dynamics
3. **Export modified workflow** as JSON
4. **Run from command line** with run_microc.py

## File Structure

```
MicroCpy/
├── ABM_GUI/
│   ├── server/api.py           ← Backend (port 5001)
│   └── src/App.jsx             ← Frontend (port 5173)
├── example_projects/ecosystem_sim/
│   ├── functions/ecosystem_functions.py
│   └── workflows/ecosystem_workflow.json
└── microc-2.0/run_microc.py    ← Simulation runner
```

## Architecture

```
Your Browser
    ↓ HTTP/SSE (port 5173)
Vite Dev Server (React)
    ↓ HTTP (port 5173)
Flask Backend (api.py, port 5001)
    ↓ subprocess
run_microc.py
    ↓
WorkflowExecutor
    ↓
ecosystem_functions.py
```

