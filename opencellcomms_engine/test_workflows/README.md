# Test Workflows for v2.0 Features

This directory contains comprehensive test workflows that validate all v2.0 subworkflow system features.

## Test Workflows

### 1. `test_workflow_comprehensive.json`
**Purpose:** Tests all v2.0 features in a single workflow

**Features Tested:**
- ✅ Subworkflow calls (main → helper_a, main → helper_b, helper_b → helper_a)
- ✅ Step parameter passing (different num_steps for each call)
- ✅ Context mapping (passing data between subworkflows)
- ✅ Results handling (capturing subworkflow outputs)
- ✅ Nested subworkflow calls (helper_b calls helper_a)
- ✅ Composer vs subworkflow distinction
- ✅ Execution order

**Structure:**
```
main (composer, 1 step)
├── helper_a (subworkflow, 3 steps) - called with num_steps=3
├── helper_b (subworkflow, 5 steps) - called with num_steps=5
    └── helper_a (subworkflow) - nested call with num_steps=2
```

**Expected Output:**
```
[MAIN] Starting main composer
[HELPER_A] Intracellular processing (3 steps)
[HELPER_A] Diffusion step (3 steps)
[HELPER_B] Starting helper B (5 steps)
[HELPER_A] Intracellular processing (2 steps) - nested call
[HELPER_A] Diffusion step (2 steps) - nested call
[HELPER_B] Intercellular processing (5 steps)
[HELPER_B] Finalizing helper B (5 steps)
[MAIN] All helpers completed successfully
```

**Run Command:**
```bash
python run_microc.py --workflow test_workflows/test_workflow_comprehensive.json
```

---

### 2. `test_workflow_steps.json`
**Purpose:** Specifically tests that `num_steps` parameter is correctly passed and overrides default

**Features Tested:**
- ✅ Step parameter passing
- ✅ Multiple calls to same subworkflow with different step counts
- ✅ Verification that parameter overrides default num_steps

**Structure:**
```
main (composer, 1 step)
├── worker (subworkflow) - called with num_steps=10 (overrides default 5)
└── worker (subworkflow) - called with num_steps=25 (overrides default 5)
```

**Expected Behavior:**
- First call to `worker`: Should run for **10 steps** (not default 5)
- Second call to `worker`: Should run for **25 steps** (not default 5)
- Each step should execute all 3 nodes in worker (intracellular, diffusion, intercellular)

**Expected Output:**
```
[MAIN] Testing step parameter passing
[WORKER] Processing intracellular (step 1/10)
[WORKER] Running diffusion (step 1/10)
[WORKER] Processing intercellular (step 1/10)
...
[WORKER] Processing intracellular (step 10/10)
[WORKER] Running diffusion (step 10/10)
[WORKER] Processing intercellular (step 10/10)
[MAIN] Worker with 10 steps completed
[WORKER] Processing intracellular (step 1/25)
...
[WORKER] Processing intercellular (step 25/25)
[MAIN] Worker with 25 steps completed - Test successful!
```

**Run Command:**
```bash
python run_microc.py --workflow test_workflows/test_workflow_steps.json
```

---

### 3. `test_workflow_context_mapping.json`
**Purpose:** Tests context mapping and data flow between subworkflows

**Features Tested:**
- ✅ Context mapping (passing variables between subworkflows)
- ✅ Results capture
- ✅ Data pipeline (producer → transformer → consumer)
- ✅ Multiple context variables mapped simultaneously

**Structure:**
```
main (composer, 1 step)
├── producer (subworkflow, 2 steps)
│   └── produces: produced_data
├── transformer (subworkflow, 3 steps)
│   ├── receives: produced_data → input_data
│   └── produces: transformed_data
└── consumer (subworkflow, 1 step)
    └── receives: transformed_data → final_data
                  produced_data → original_data
```

**Context Mapping Chain:**
1. `producer` creates `produced_data`
2. `transformer` receives it as `input_data`, creates `transformed_data`
3. `consumer` receives both `transformed_data` (as `final_data`) and `produced_data` (as `original_data`)

**Expected Output:**
```
[MAIN] Starting context mapping test
[PRODUCER] Generating data (2 steps)
[PRODUCER] Processing data (2 steps)
[TRANSFORMER] Receiving input data (3 steps)
[TRANSFORMER] Transforming data (3 steps)
[TRANSFORMER] Applying transformations (3 steps)
[CONSUMER] Receiving final and original data (1 step)
[CONSUMER] Data consumption complete (1 step)
[MAIN] Context mapping chain completed successfully
```

**Run Command:**
```bash
python run_microc.py --workflow test_workflows/test_workflow_context_mapping.json
```

---

## Running Tests

### Run All Tests
```bash
# Test 1: Comprehensive
python run_microc.py --workflow test_workflows/test_workflow_comprehensive.json

# Test 2: Step Parameters
python run_microc.py --workflow test_workflows/test_workflow_steps.json

# Test 3: Context Mapping
python run_microc.py --workflow test_workflows/test_workflow_context_mapping.json
```

### Run from Specific Entry Point
```bash
# Run helper_b as entry point (instead of main)
python run_microc.py --workflow test_workflows/test_workflow_comprehensive.json --entry-subworkflow helper_b
```

### Run from GUI
1. Open GUI: `cd ABM_GUI && npm start`
2. Load workflow: File → Open → Select test workflow
3. Navigate to desired composer tab
4. Click "Run" button in console panel
5. View results in results panel

---

## Validation Checklist

### ✅ Features to Verify

**Subworkflow System:**
- [ ] Composers can call subworkflows
- [ ] Subworkflows can call other subworkflows (nesting)
- [ ] Execution order is respected
- [ ] Each subworkflow runs in isolation

**Step Parameters:**
- [ ] `num_steps` parameter overrides default
- [ ] Different calls can specify different step counts
- [ ] Step counter increments correctly
- [ ] Logs show correct step numbers

**Context Mapping:**
- [ ] Variables are passed between subworkflows
- [ ] Multiple mappings work simultaneously
- [ ] Nested calls preserve context
- [ ] Context variables are accessible in functions

**Results System:**
- [ ] Results are captured from subworkflows
- [ ] Results are stored in context
- [ ] Results directory structure is correct:
  - `results/composers/main/`
  - `results/subworkflows/helper_a/`
  - `results/subworkflows/helper_b/`
  - etc.

**Entry Point:**
- [ ] Can run from `main` composer
- [ ] Can run from any composer using `--entry-subworkflow`
- [ ] Logs show correct entry point
- [ ] Results saved to correct directory

**Validation:**
- [ ] Cycle detection works (no infinite loops)
- [ ] Invalid targets are rejected
- [ ] Missing subworkflows are detected
- [ ] Execution order conflicts are caught

---

## Expected Results Directory Structure

After running `test_workflow_comprehensive.json`:

```
microc-2.0/results/
├── composers/
│   └── main/
│       └── (any plots/outputs from main)
└── subworkflows/
    ├── helper_a/
    │   └── (any plots/outputs from helper_a)
    └── helper_b/
        └── (any plots/outputs from helper_b)
```

---

## Troubleshooting

### Issue: "Entry subworkflow not found"
**Solution:** Make sure you're using a composer name, not a subworkflow name

### Issue: "Cycle detected"
**Solution:** Check that subworkflows don't call each other in a loop

### Issue: "num_steps not being overridden"
**Solution:** Verify the parameter is in the `parameters` field of the subworkflow_call node

### Issue: "Context variables not available"
**Solution:** Check that `context_mapping` is correctly specified in the subworkflow_call node

---

## Notes

- All test workflows use debug functions that only log messages
- No actual simulation is performed (safe to run)
- Execution is fast (useful for quick validation)
- Can be loaded in GUI for visual inspection
- Can be run from command line for automated testing

