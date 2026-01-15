# Testing Checklist

## Pre-Testing Setup

- [ ] Read [QUICK_START.md](QUICK_START.md)
- [ ] Verify Node.js 18+ installed: `node --version`
- [ ] Verify Python 3.8+ installed: `python --version`
- [ ] Verify ports 5001 and 5173 are available

## Starting Services

### Backend Server
- [ ] Open Terminal 1
- [ ] Navigate to `ABM_GUI/server`
- [ ] Run: `pip install -r requirements.txt`
- [ ] Run: `python api.py`
- [ ] Verify output: "Starting server on http://localhost:5001"
- [ ] Keep terminal open

### Frontend Server
- [ ] Open Terminal 2
- [ ] Navigate to `ABM_GUI`
- [ ] Run: `npm install` (first time only)
- [ ] Run: `npm run dev`
- [ ] Verify output: "VITE v5.x.x ready in xxx ms"
- [ ] Browser opens at `http://localhost:5173`

## GUI Testing

### Workflow Import
- [ ] GUI loads at `http://localhost:5173`
- [ ] Click "Import JSON" button
- [ ] Navigate to: `example_projects/ecosystem_sim/workflows/ecosystem_workflow.json`
- [ ] Click "Open"
- [ ] Workflow loads successfully
- [ ] Main composer visible with 3 subworkflows
- [ ] All functions visible in workflow

### Workflow Exploration
- [ ] Click "main" tab - see main composer
- [ ] Click "initialize" tab - see initialization functions
- [ ] Click "simulation_step" tab - see simulation loop
- [ ] Click "output_results" tab - see output functions
- [ ] All tabs load without errors

### Simulation Execution
- [ ] Click "Run Simulation" button
- [ ] Simulation starts executing
- [ ] Logs appear in real-time
- [ ] See "[INIT]" messages for initialization
- [ ] See "[STEP 0-49]" messages for simulation steps
- [ ] See "[OUTPUT]" messages for results

### Log Verification
- [ ] Grid creation logged: "[INIT] Created 50x50 grid"
- [ ] Prey spawned: "[INIT] Spawned 100 prey agents"
- [ ] Predators spawned: "[INIT] Spawned 20 predator agents"
- [ ] Population tracked: "[STEP X] Predators: Y, Prey: Z"
- [ ] Results saved: "[OUTPUT] Saved population history"
- [ ] Summary printed with extinction detection

### Results Verification
- [ ] Simulation completes without errors
- [ ] Final log shows summary statistics
- [ ] CSV file created: `results/population_history.csv`
- [ ] CSV contains population data
- [ ] Extinction event detected (predators = 0)

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

## Advanced Testing (Optional)

### Parameter Modification
- [ ] Click on parameter nodes in main composer
- [ ] Modify grid size (e.g., 60x60)
- [ ] Modify initial prey count (e.g., 150)
- [ ] Modify initial predator count (e.g., 30)
- [ ] Run simulation with new parameters
- [ ] Verify results change accordingly

### Workflow Export
- [ ] Click "Export JSON" button
- [ ] Save workflow with new name
- [ ] Verify JSON file created
- [ ] Verify file contains workflow definition

### Command-Line Testing
- [ ] Export modified workflow
- [ ] Run: `python microc-2.0/run_microc.py --workflow exported.json`
- [ ] Verify simulation runs from command line
- [ ] Verify results match GUI execution

## Troubleshooting Checks

### If Backend Won't Start
- [ ] Check port 5001: `lsof -i :5001`
- [ ] Kill process if needed
- [ ] Verify Python 3.8+
- [ ] Verify requirements.txt installed
- [ ] Check api.py exists

### If Frontend Won't Start
- [ ] Check port 5173: `lsof -i :5173`
- [ ] Kill process if needed
- [ ] Verify Node.js 18+
- [ ] Verify npm installed
- [ ] Run: `npm install` again

### If Workflow Won't Load
- [ ] Check file path is correct
- [ ] Verify ecosystem_workflow.json exists
- [ ] Check browser console (F12) for errors
- [ ] Verify backend is running

### If Simulation Won't Run
- [ ] Verify backend server is running
- [ ] Check ecosystem_functions.py exists
- [ ] Verify all function files accessible
- [ ] Check browser console for errors

## Final Verification

- [ ] All 50 simulation steps complete
- [ ] Population dynamics are realistic
- [ ] Extinction event detected
- [ ] CSV file created with data
- [ ] Summary printed correctly
- [ ] No errors in browser console
- [ ] No errors in terminal output

## Sign-Off

- [ ] All checks passed
- [ ] Ecosystem simulation working correctly
- [ ] GUI fully functional
- [ ] Ready for production use

---

## Notes

- Keep both terminals open during testing
- Check browser console (F12) for any errors
- Verify file paths are correct
- Ensure both servers are running
- Results saved to `results/population_history.csv`

## Support

If any check fails:
1. See [COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md) for troubleshooting
2. Check [GUI_TESTING_STEPS.md](GUI_TESTING_STEPS.md) for detailed steps
3. Review [TESTING_SUMMARY.md](TESTING_SUMMARY.md) for what was done

---

**Date Tested:** _______________
**Tester Name:** _______________
**Status:** _______________

