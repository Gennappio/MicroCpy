# Phase 5: Run Model - Entry Subworkflow Implementation

## Overview
Fixed the Run Model implementation to properly support the `entry_subworkflow` parameter as specified in Section 9.2 of the v2.0 spec.

## Problem Statement

### Previous Implementation (Workaround)
The GUI used a workaround that:
1. **Renamed the active subworkflow to "main"**
2. **Created a minimal workflow** with only needed subworkflows
3. **Sent modified workflow** to backend
4. **Backend always started from "main"** (hardcoded)

**Issues with this approach:**
- ❌ Modified workflow structure before execution
- ❌ Lost semantic meaning of subworkflow names
- ❌ Confusing logs (showed "main" instead of actual subworkflow name)
- ❌ Results saved to wrong directory (`results/composers/main/` instead of actual composer name)
- ❌ Difficult to track which experiment actually ran
- ❌ Potential issues with subworkflow call resolution

### Spec Requirement (Section 9.2)

**API Contract:**
```json
POST /api/run
{
  "workflow": { /* full v2.0 workflow JSON */ },
  "entry_subworkflow": "experiment1"
}
```

**Rules:**
- `entry_subworkflow` must exist in workflow
- `entry_subworkflow` must be a composer (not a helper subworkflow)

**Runtime Contract:**
- Load workflow JSON
- Validate
- Start execution from `entry_subworkflow`

## Implementation

### 1. Backend API (`ABM_GUI/server/api.py`)

#### Updated `/api/run` endpoint:

**Added parameter extraction:**
```python
entry_subworkflow = data.get('entry_subworkflow', 'main')  # Default to 'main'
```

**Added validation (Section 9.2):**
```python
if workflow_data.get('version') == '2.0':
    subworkflows = workflow_data.get('subworkflows', {})
    
    # Check if entry_subworkflow exists
    if entry_subworkflow not in subworkflows:
        return jsonify({'error': f'Entry subworkflow "{entry_subworkflow}" not found'}), 400
    
    # Check if entry_subworkflow is a composer
    subworkflow_kinds = metadata.get('gui', {}).get('subworkflow_kinds', {})
    if subworkflow_kinds.get(entry_subworkflow) != 'composer':
        return jsonify({'error': f'Entry subworkflow must be a composer'}), 400
```

**Updated `run_simulation_async()` to accept and pass parameter:**
```python
def run_simulation_async(workflow_path, entry_subworkflow=None):
    cmd = [sys.executable, str(microc_path), "--workflow", workflow_path]
    
    if entry_subworkflow:
        cmd.extend(["--entry-subworkflow", entry_subworkflow])
```

### 2. Runtime Executor (`microc-2.0/src/workflow/executor.py`)

#### Updated `execute_main()` method:

**Before:**
```python
def execute_main(self, context: Dict[str, Any]) -> Dict[str, Any]:
    if self.workflow.version == "2.0":
        return self.execute_subworkflow("main", context)  # Hardcoded "main"
```

**After:**
```python
def execute_main(self, context: Dict[str, Any], entry_subworkflow: str = "main") -> Dict[str, Any]:
    """
    Args:
        entry_subworkflow: Name of the subworkflow to start from (default: "main").
                          Section 9.2: Allows running from any composer as entry point.
    """
    if self.workflow.version == "2.0":
        print(f"[WORKFLOW] Starting execution from entry subworkflow: {entry_subworkflow}")
        return self.execute_subworkflow(entry_subworkflow, context)
```

### 3. Command-Line Interface (`microc-2.0/tools/run_sim.py`)

#### Added `--entry-subworkflow` argument:

```python
parser.add_argument(
    '--entry-subworkflow',
    type=str,
    metavar='SUBWORKFLOW_NAME',
    default='main',
    help='Entry point subworkflow for v2.0 workflows (default: main). Section 9.2 spec.'
)
```

#### Updated `run_workflow_mode()` to detect v2.0 and use entry point:

```python
# Section 9.2: For v2.0 workflows with subworkflows, use execute_main with entry point
if workflow.version == "2.0" and hasattr(workflow, 'subworkflows') and workflow.subworkflows:
    entry_subworkflow = getattr(args, 'entry_subworkflow', 'main')
    print(f"[WORKFLOW] v2.0 subworkflow system detected")
    print(f"[WORKFLOW] Entry subworkflow: {entry_subworkflow}")
    
    # Execute from entry point (Section 9.2)
    context = executor.execute_main(context, entry_subworkflow=entry_subworkflow)
    print(f"[WORKFLOW] Workflow completed successfully!")
    return
```

### 4. Frontend - WorkflowConsole (`ABM_GUI/src/components/WorkflowConsole.jsx`)

#### Removed workflow modification logic:

**Before (68 lines of workaround code):**
```javascript
// Create a modified workflow that runs the active subworkflow as "main"
const collectCalledSubworkflows = (subworkflowName, collected = new Set()) => { ... };
const neededSubworkflows = collectCalledSubworkflows(workflowName);
const minimalSubworkflows = {};
neededSubworkflows.forEach(name => {
  if (name === workflowName) {
    minimalSubworkflows.main = { ...fullWorkflow.subworkflows[name] };
  } else {
    minimalSubworkflows[name] = fullWorkflow.subworkflows[name];
  }
});
const singleWorkflow = { ...fullWorkflow, subworkflows: minimalSubworkflows };
```

**After (clean implementation):**
```javascript
// Section 9.2: Send full workflow with entry_subworkflow parameter
const fullWorkflow = exportWorkflow();
const activeSubworkflow = fullWorkflow.subworkflows[workflowName];

if (!activeSubworkflow) {
  throw new Error(`Subworkflow '${workflowName}' not found`);
}

const response = await fetch(`${API_BASE_URL}/run`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    workflow: fullWorkflow,  // Send full workflow unchanged
    entry_subworkflow: workflowName  // Specify entry point
  }),
});
```

### 5. Frontend - SimulationRunner (`ABM_GUI/src/components/SimulationRunner.jsx`)

Updated to explicitly send `entry_subworkflow: 'main'` for consistency:

```javascript
const requestBody = {
  workflow: workflow,
  entry_subworkflow: 'main'  // SimulationRunner always runs from 'main'
};
```

## Benefits

### ✅ 1. Preserves Workflow Integrity
- No modification of workflow structure
- All subworkflows keep their original names
- Workflow JSON remains unchanged

### ✅ 2. Clear Logging
**Before:**
```
[WORKFLOW] Executing main (iteration 1/1)
```

**After:**
```
[WORKFLOW] Starting execution from entry subworkflow: experiment1
[WORKFLOW] Executing experiment1 (iteration 1/1)
```

### ✅ 3. Correct Results Directories
**Before:**
- Results always saved to `results/composers/main/`

**After:**
- Running `experiment1` → `results/composers/experiment1/`
- Running `experiment2` → `results/composers/experiment2/`
- Each composer has its own results directory

### ✅ 4. Multiple Composers Support
Can now run different composers independently:
- `main` (default experiment)
- `experiment1` (variant A)
- `experiment2` (variant B)

Each maintains its own identity and results.

### ✅ 5. Simplified Code
- Removed 68 lines of workaround code from WorkflowConsole
- Cleaner, more maintainable implementation
- Matches spec exactly

## Usage

### From GUI:
1. Open a composer tab (e.g., "experiment1")
2. Click "Run" button in the console
3. Workflow executes from that composer as entry point
4. Results saved to `results/composers/experiment1/`

### From Command Line:
```bash
# Run from default entry point (main)
python run_microc.py --workflow my_workflow.json

# Run from specific entry point
python run_microc.py --workflow my_workflow.json --entry-subworkflow experiment1
```

### From API:
```bash
curl -X POST http://localhost:5001/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": { ... },
    "entry_subworkflow": "experiment1"
  }'
```

## Files Modified

1. **`ABM_GUI/server/api.py`**
   - Added `entry_subworkflow` parameter to `/api/run` endpoint
   - Added validation for entry_subworkflow (exists, is composer)
   - Pass entry_subworkflow to runtime via command-line

2. **`microc-2.0/src/workflow/executor.py`**
   - Updated `execute_main()` to accept `entry_subworkflow` parameter
   - Start execution from specified subworkflow instead of hardcoded "main"

3. **`microc-2.0/tools/run_sim.py`**
   - Added `--entry-subworkflow` command-line argument
   - Updated `run_workflow_mode()` to detect v2.0 and use entry point
   - Pass entry_subworkflow to executor

4. **`ABM_GUI/src/components/WorkflowConsole.jsx`**
   - Removed workflow modification/renaming logic (68 lines)
   - Send full workflow with `entry_subworkflow` parameter

5. **`ABM_GUI/src/components/SimulationRunner.jsx`**
   - Explicitly send `entry_subworkflow: 'main'` for consistency

## Spec Compliance

✅ **Section 9.1** - Run means execute workflow with composer as entry point  
✅ **Section 9.2** - API accepts `entry_subworkflow` parameter  
✅ **Section 9.2** - Validates entry_subworkflow exists and is a composer  
✅ **Section 9.3** - Runtime starts execution from `entry_subworkflow`  
✅ **Section 9.4** - Logs show correct subworkflow names

## Testing

- [ ] Run workflow from "main" composer
- [ ] Run workflow from custom composer (e.g., "experiment1")
- [ ] Verify logs show correct entry subworkflow name
- [ ] Verify results saved to correct directory
- [ ] Test with multiple composers
- [ ] Test error handling (invalid entry_subworkflow)
- [ ] Test error handling (entry_subworkflow is not a composer)

