# Test_GUI Adapter

A stress-test adapter for the new ABM-shaped GUI. Every function is print-only — no real biology — designed to verify that the GUI handles many agent kinds, mixed scheduler order, planner overrides, and processing pipelines without breaking.

## What it covers

- **3 agent kinds**: `predator`, `prey`, `plankton`
  - Each has an Init canvas (3 functions) and 3 behavior canvases (3 functions each) → 12 functions per kind
- **Environment**: an Init canvas + 3 behaviors (3 functions each) → 12 functions
- **Scheduler**: 12 mixed-order entries (`number_of_steps=10`)
- **Planner**: 5 parameterized runs
- **Processing**: 3 behaviors with 3 functions each

Total: ~57 registered print-only functions across 19 files.

## Running

CLI:
```bash
python opencellcomms_engine/run_workflow.py --workflow opencellcomms_adapters/Test_GUI/workflows/test_gui.json
```

GUI: open the project in the OpenCellComms GUI, then **Import Project** → select `workflows/test_gui.json`. Every tab will populate with the structures described above.

## Regenerating

If you need to change the spec (more kinds, more behaviors, different scheduler order, etc.), edit `_build_test_gui.py` and re-run:
```bash
python opencellcomms_adapters/Test_GUI/_build_test_gui.py
```
