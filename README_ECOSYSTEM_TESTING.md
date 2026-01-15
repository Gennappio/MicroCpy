# Ecosystem Simulation Testing Guide

## 📋 Overview

This guide explains how to test the ecosystem simulation example from the MicroC GUI. The ecosystem simulation is a complete agent-based model demonstrating predator-prey dynamics.

## ✅ What's Been Done

1. **Updated Function Signatures** - All 12 ecosystem functions now accept `context` parameter with `**kwargs`
2. **Verified Command-Line Execution** - Test script confirms all functions work correctly
3. **Set Up GUI Infrastructure** - Backend server and frontend ready to use
4. **Created Documentation** - Multiple guides for different use cases

## 🚀 Quick Start (2 Steps)

### Step 1: Start Backend Server
```bash
cd ABM_GUI/server
pip install -r requirements.txt
python api.py
```

### Step 2: Start Frontend
```bash
cd ABM_GUI
npm install
npm run dev
```

**Browser opens automatically at `http://localhost:5173`**

## 🎯 Using the GUI

1. **Click "Import JSON"** button
2. **Select:** `example_projects/ecosystem_sim/workflows/ecosystem_workflow.json`
3. **Click "Run Simulation"**
4. **Watch logs stream** showing simulation progress
5. **View results** in `results/population_history.csv`

## 📊 What You'll See

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

## 📁 Documentation Files

| File | Purpose |
|------|---------|
| `QUICK_START.md` | 30-second setup guide |
| `ECOSYSTEM_GUI_SETUP.md` | Detailed setup instructions |
| `GUI_TESTING_STEPS.md` | Step-by-step testing guide |
| `COMMANDS_REFERENCE.md` | All commands you need |
| `TESTING_SUMMARY.md` | Complete testing summary |
| `README_ECOSYSTEM_TESTING.md` | This file |

## 🔧 System Architecture

```
┌─────────────────────────────────────────────────────┐
│ Your Browser (http://localhost:5173)                │
│ React GUI - Import/Export Workflows                 │
└────────────────┬────────────────────────────────────┘
                 │ HTTP/SSE
┌────────────────▼────────────────────────────────────┐
│ Flask Backend (http://localhost:5001)               │
│ api.py - Workflow Execution & Log Streaming         │
└────────────────┬────────────────────────────────────┘
                 │ subprocess
┌────────────────▼────────────────────────────────────┐
│ run_microc.py                                       │
│ Workflow Runner & Executor                          │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│ ecosystem_functions.py (12 functions)               │
│ Agent-Based Simulation Logic                        │
└─────────────────────────────────────────────────────┘
```

## 🧪 Testing Checklist

- [ ] Backend server starts on port 5001
- [ ] Frontend starts on port 5173
- [ ] Browser opens automatically
- [ ] Can import ecosystem_workflow.json
- [ ] Workflow displays correctly
- [ ] Can click "Run Simulation"
- [ ] Logs stream in real-time
- [ ] Simulation completes 50 steps
- [ ] Results saved to CSV
- [ ] Summary shows extinction event

## 🎓 What's Being Tested

✅ **Function Signature Compatibility**
- Functions accept `context` parameter
- Support for `**kwargs`
- Backward compatibility

✅ **Workflow Execution**
- Subworkflows execute in order
- Context passed between functions
- Parameters applied correctly

✅ **Agent-Based Simulation**
- Predator-prey dynamics
- Population tracking
- Extinction detection

✅ **GUI Integration**
- Workflow import/export
- Real-time log streaming
- Parameter editing

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 5001 in use | Kill process: `lsof -i :5001 \| grep LISTEN \| awk '{print $2}' \| xargs kill -9` |
| Port 5173 in use | Kill process: `lsof -i :5173 \| grep LISTEN \| awk '{print $2}' \| xargs kill -9` |
| npm not found | Install Node.js 18+ |
| Workflow won't load | Check file path is correct |
| Backend not reachable | Ensure `python api.py` is running |

## 📚 Additional Resources

- **MicroC Documentation:** `microc-2.0/README.md`
- **Workflow System:** `microc-2.0/src/workflow/`
- **GUI Source:** `ABM_GUI/src/`
- **Ecosystem Functions:** `example_projects/ecosystem_sim/functions/`

## 🎯 Next Steps

1. **Follow Quick Start** above
2. **Test the simulation** in the GUI
3. **Modify parameters** to experiment
4. **Export the workflow** to save changes
5. **Run from command line** with run_microc.py

## ✨ Key Features

- 🎨 Visual workflow designer
- 📊 Real-time log streaming
- 💾 JSON import/export
- 🔄 Subworkflow support
- 📈 Population tracking
- 🎯 Parameter editing

---

**Status: ✅ READY FOR TESTING**

Everything is set up and working. Start the servers and open your browser!

