# Testing Ecosystem Simulation in the GUI

This guide walks you through setting up and running the ecosystem simulation example from the MicroC GUI.

## Quick Start (3 Steps)

### Step 1: Start the Backend Server

```bash
cd ABM_GUI/server
pip install -r requirements.txt
python api.py
```

You should see:
```
 * Running on http://127.0.0.1:5001
```

**Keep this terminal open!**

### Step 2: Start the Frontend (New Terminal)

```bash
cd ABM_GUI
npm install  # Only needed first time
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

The GUI will automatically open in your browser at `http://localhost:5173/`

### Step 3: Load and Run the Ecosystem Workflow

1. **Click "Import JSON"** in the top menu
2. **Select the workflow file:**
   ```
   example_projects/ecosystem_sim/workflows/ecosystem_workflow.json
   ```
3. **The workflow will load** showing:
   - Main composer with 3 subworkflow calls
   - Initialize, Simulation Step, and Output Results subworkflows
   - All the ecosystem functions

4. **Click "Run Simulation"** button
5. **Watch the simulation execute** with real-time logs showing:
   - Grid creation
   - Agent spawning
   - Predation events
   - Population changes
   - Results saved to CSV

## What You'll See

### Workflow Structure
- **Main Composer**: Orchestrates the entire simulation
- **Initialize**: Creates grid and spawns agents
- **Simulation Step**: Runs 50 iterations of movement, predation, reproduction
- **Output Results**: Saves CSV and prints summary

### Live Logs
The GUI will stream logs showing:
```
[INIT] Created 50x50 grid
[INIT] Spawned 100 prey agents
[INIT] Spawned 20 predator agents
[STEP 0] Predators: 20, Prey: 105
[STEP 1] Predators: 20, Prey: 112
...
```

### Results
After completion:
- CSV file saved to `results/population_history.csv`
- Summary printed showing population dynamics
- Extinction events detected

## Troubleshooting

### "Backend server not reachable"
- Ensure `python api.py` is running in ABM_GUI/server
- Check port 5001 is not blocked
- Verify CORS is enabled in api.py

### "Workflow won't load"
- Check the file path is correct
- Verify ecosystem_workflow.json exists
- Check browser console for errors

### "Simulation won't start"
- Ensure backend server is running
- Check that ecosystem_functions.py exists
- Verify all function files are accessible

## File Locations

```
MicroCpy/
├── ABM_GUI/
│   ├── server/
│   │   └── api.py              # Backend server
│   └── src/
│       └── App.jsx             # Frontend
├── example_projects/
│   └── ecosystem_sim/
│       ├── functions/
│       │   └── ecosystem_functions.py
│       └── workflows/
│           └── ecosystem_workflow.json
└── microc-2.0/
    └── run_microc.py           # Simulation runner
```

## Next Steps

Once you have the ecosystem simulation running:

1. **Modify Parameters**: Edit the parameter nodes in the main composer
2. **Adjust Rates**: Change predation rate, reproduction rate, etc.
3. **Export Modified Workflow**: Click "Export JSON" to save your changes
4. **Run from Command Line**: Use the exported workflow with run_microc.py

## Architecture

```
Browser (React GUI)
    ↓ HTTP/SSE
Flask Backend (api.py)
    ↓ subprocess
run_microc.py
    ↓
WorkflowExecutor
    ↓
ecosystem_functions.py
```

The GUI sends the workflow to the backend, which executes it using the MicroC workflow system and streams logs back to the frontend in real-time.

