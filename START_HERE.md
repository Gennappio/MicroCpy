# 🎯 START HERE - Ecosystem Simulation Testing

## Welcome! 👋

You have a fully functional ecosystem simulation ready to test. This document will get you started in 2 minutes.

## ⚡ Quick Start (Copy-Paste Ready)

### Terminal 1: Start Backend Server
```bash
cd ABM_GUI/server
pip install -r requirements.txt
python api.py
```

**Expected:** Server starts on `http://localhost:5001`

### Terminal 2: Start Frontend (New Terminal)
```bash
cd ABM_GUI
npm install
npm run dev
```

**Expected:** Browser opens at `http://localhost:5173`

## 🌐 In Your Browser

1. **Browser opens automatically** at `http://localhost:5173`
2. **Click "Import JSON"** button
3. **Select file:** `example_projects/ecosystem_sim/workflows/ecosystem_workflow.json`
4. **Click "Run Simulation"**
5. **Watch logs stream** showing simulation progress

## 📊 What You'll See

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

## ✅ What's Been Done

- ✅ Updated all 12 ecosystem functions
- ✅ Tested from command line (PASSED)
- ✅ Set up GUI backend and frontend
- ✅ Created comprehensive documentation

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[QUICK_START.md](QUICK_START.md)** | 30-second setup |
| **[INDEX.md](INDEX.md)** | Complete index |
| **[COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md)** | All commands |
| **[TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)** | Testing checklist |
| **[GUI_TESTING_STEPS.md](GUI_TESTING_STEPS.md)** | Detailed steps |
| **[FINAL_SUMMARY.md](FINAL_SUMMARY.md)** | Complete summary |

## 🚀 Next Steps

1. **Copy the two commands above**
2. **Open two terminals**
3. **Run command 1 in Terminal 1**
4. **Run command 2 in Terminal 2**
5. **Browser opens automatically**
6. **Follow the 5 steps above**
7. **Watch the simulation run!**

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Port in use | See [COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md) |
| npm not found | Install Node.js 18+ |
| Workflow won't load | Check file path |
| Backend not reachable | Ensure `python api.py` running |

## 💡 Key Points

- **Two terminals needed** - one for backend, one for frontend
- **Browser opens automatically** at http://localhost:5173
- **Keep both terminals open** during testing
- **Results saved** to results/population_history.csv
- **All documentation** in root directory

## 🎓 What You're Testing

✅ Updated function signatures work
✅ Workflow executes 50 simulation steps
✅ Population dynamics are realistic
✅ GUI can import and run workflows
✅ Real-time log streaming works
✅ Results are saved to CSV

## 📁 Key Files

```
ABM_GUI/server/api.py              ← Backend (port 5001)
ABM_GUI/src/App.jsx                ← Frontend (port 5173)
example_projects/ecosystem_sim/    ← Simulation files
test_ecosystem_sim.py              ← CLI test (✅ PASSED)
```

## 🌟 Features

- 🎨 Visual workflow designer
- 📊 Real-time log streaming
- 💾 JSON import/export
- 🔄 Subworkflow support
- 📈 Population tracking
- 🎯 Parameter editing

## ⏱️ Time Estimate

- **Setup:** 2 minutes
- **First run:** 1 minute
- **Total:** 3 minutes to see results

## 🎯 Success Criteria

- [ ] Backend server starts
- [ ] Frontend server starts
- [ ] Browser opens at http://localhost:5173
- [ ] Workflow imports successfully
- [ ] Simulation runs 50 steps
- [ ] Logs stream in real-time
- [ ] Results saved to CSV
- [ ] Extinction event detected

## 📞 Need Help?

1. **Quick setup:** [QUICK_START.md](QUICK_START.md)
2. **All commands:** [COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md)
3. **Detailed steps:** [GUI_TESTING_STEPS.md](GUI_TESTING_STEPS.md)
4. **Troubleshooting:** [COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md)
5. **Complete info:** [FINAL_SUMMARY.md](FINAL_SUMMARY.md)

---

## 🚀 Ready? Let's Go!

**Copy the two commands above and run them now!**

The browser will open automatically, and you'll be testing the ecosystem simulation in seconds.

---

**Status: ✅ READY FOR TESTING**

Everything is set up and working. Just run the commands above!

