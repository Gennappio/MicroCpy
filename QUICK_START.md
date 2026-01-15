# 🚀 Quick Start: Ecosystem Simulation GUI

## 30-Second Setup

### Open 2 Terminals

**Terminal 1 - Backend Server:**
```bash
cd ABM_GUI/server && pip install -r requirements.txt && python api.py
```

**Terminal 2 - Frontend:**
```bash
cd ABM_GUI && npm install && npm run dev
```

## 🎯 In Your Browser

1. **Browser opens at:** `http://localhost:5173`

2. **Click "Import JSON"** button

3. **Select file:**
   ```
   example_projects/ecosystem_sim/workflows/ecosystem_workflow.json
   ```

4. **Click "Run Simulation"** button

5. **Watch the logs** - You'll see:
   ```
   [INIT] Created 50x50 grid
   [INIT] Spawned 100 prey agents
   [INIT] Spawned 20 predator agents
   [STEP 0] Predators: 20, Prey: 105
   [STEP 1] Predators: 20, Prey: 112
   ...
   [STEP 49] Predators: 0, Prey: 1121
   ⚠️  PREDATOR EXTINCTION occurred!
   ```

## ✅ What You're Testing

- ✅ Updated function signatures work correctly
- ✅ Workflow executes all 50 simulation steps
- ✅ Population dynamics are realistic
- ✅ GUI can import and run workflows
- ✅ Real-time log streaming works
- ✅ Results are saved to CSV

## 📊 Expected Results

| Metric | Value |
|--------|-------|
| Initial Predators | 20 |
| Initial Prey | 100 |
| Final Predators | 0 |
| Final Prey | 1100+ |
| Simulation Steps | 50 |
| Status | ✅ PASSED |

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 5001 in use | Kill existing process: `lsof -i :5001` |
| Port 5173 in use | Kill existing process: `lsof -i :5173` |
| npm not found | Install Node.js 18+ |
| Backend not reachable | Ensure `python api.py` is running |
| Workflow won't load | Check file path is correct |

## 📁 File Locations

```
MicroCpy/
├── ABM_GUI/server/api.py              ← Backend (port 5001)
├── ABM_GUI/src/App.jsx                ← Frontend (port 5173)
├── example_projects/ecosystem_sim/
│   ├── functions/ecosystem_functions.py
│   └── workflows/ecosystem_workflow.json
└── microc-2.0/run_microc.py           ← Simulation runner
```

## 🎓 What's Happening

```
Browser (React)
    ↓ HTTP
Vite Dev Server (port 5173)
    ↓ HTTP
Flask Backend (port 5001)
    ↓ subprocess
run_microc.py
    ↓
WorkflowExecutor
    ↓
ecosystem_functions.py (12 functions)
    ↓
Agent-based simulation (50 steps)
    ↓
Results + CSV + Summary
```

## 💡 Pro Tips

1. **Modify parameters** in the GUI before running
2. **Export the workflow** after making changes
3. **Run from command line** with: `python microc-2.0/run_microc.py --workflow exported.json`
4. **Check results** in `results/population_history.csv`

## 📚 Full Documentation

- `ECOSYSTEM_GUI_SETUP.md` - Detailed setup guide
- `GUI_TESTING_STEPS.md` - Step-by-step instructions
- `TESTING_SUMMARY.md` - Complete testing summary

---

**Status: ✅ READY TO TEST**

Everything is set up and working. Just run the two commands above and open your browser!

