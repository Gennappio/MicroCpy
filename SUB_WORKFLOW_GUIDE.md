# Sub-workflow Quick Start Guide

## What are Sub-workflows?

Sub-workflows are reusable, composable workflow components that can be called from other workflows. Think of them as functions in programming - you can define a workflow once and call it multiple times with different parameters.

## Key Concepts

### 1. Sub-workflow
A self-contained workflow with:
- **Controller**: Manages iterations (how many times to run)
- **Functions**: Standard workflow functions
- **Sub-workflow Calls**: Calls to other sub-workflows
- **Parameters**: Configuration values
- **Execution Order**: Sequence of execution

### 2. Sub-workflow Call
A node that executes another sub-workflow:
- Can specify number of iterations
- Can pass parameters
- Can map context variables
- Appears as purple node with ⚡ icon

### 3. Call Stack
Shows the current execution hierarchy:
- Which sub-workflow is running
- Current iteration number
- Nesting depth

## Creating Your First Sub-workflow

### Step 1: Create a New Sub-workflow
1. Open the Workflow Designer
2. Click the "+ New Sub-workflow" button in the tabs
3. Enter a name (e.g., "cell_division")
4. Click "Create"

### Step 2: Add Functions
1. Drag functions from the Function Palette
2. Connect them in the desired order
3. Add parameter nodes if needed
4. Configure the controller iterations

### Step 3: Use the Sub-workflow
1. Switch to another sub-workflow (e.g., "main")
2. Find your sub-workflow in the "Sub-workflows" section of the palette
3. Drag it onto the canvas
4. Connect it in the execution flow

## Example: Cell Division Workflow

### Sub-workflow: "check_division"
```
Controller (1 iteration)
  ↓
check_cell_volume
  ↓
calculate_division_probability
```

### Sub-workflow: "perform_division"
```
Controller (1 iteration)
  ↓
divide_cell
  ↓
update_daughter_cells
```

### Main Workflow
```
Controller (100 iterations)
  ↓
Call: check_division (iterations: 1)
  ↓
Call: perform_division (iterations: 1)
  ↓
update_environment
```

## Advanced Features

### Iterations
Set how many times a sub-workflow executes:
- Double-click the sub-workflow call node
- Set "Iterations" field
- Useful for repeated operations

### Parameters
Pass configuration to sub-workflows:
1. Create a parameter node
2. Connect it to the sub-workflow call
3. Parameters are available in the called sub-workflow

### Context Mapping
Share data between sub-workflows:
- Context is automatically passed
- Use context_mapping to rename variables
- Example: Map "cells" to "input_cells"

## Best Practices

### 1. Keep Sub-workflows Focused
- Each sub-workflow should do one thing well
- Easier to understand and reuse
- Example: "initialize_cells" vs "initialize_everything"

### 2. Use Descriptive Names
- Good: "calculate_cell_forces"
- Bad: "func1"

### 3. Document with Descriptions
- Add descriptions to sub-workflows
- Helps others understand purpose
- Visible in the palette

### 4. Avoid Deep Nesting
- Keep call stack shallow (< 5 levels)
- Improves performance and debugging
- Flatten when possible

### 5. Test Incrementally
- Test each sub-workflow independently
- Verify before composing
- Use small iteration counts for testing

## Migrating from v1.0

If you have existing v1.0 workflows:

### Option 1: Automatic Migration
```bash
python scripts/migrate_workflow.py old.json new.json
```

### Option 2: Manual Recreation
1. Create new v2.0 workflow
2. Create sub-workflows for each stage
3. Add functions to appropriate sub-workflows
4. Create main workflow that calls them

## Troubleshooting

### "Circular dependency detected"
- You're trying to call a sub-workflow that calls back to the current one
- Solution: Restructure to avoid cycles

### "Sub-workflow not found"
- The called sub-workflow doesn't exist
- Solution: Check spelling or create the sub-workflow

### "Invalid sub-workflow name"
- Names must start with a letter
- Can only contain letters, numbers, and underscores
- Solution: Rename following the rules

### Call stack too deep
- Too many nested sub-workflow calls
- Solution: Flatten the hierarchy or reduce nesting

## Tips & Tricks

### Reusable Components
Create a library of common sub-workflows:
- "initialize_cells"
- "update_mechanics"
- "save_snapshot"

### Iteration Patterns
- **Once**: iterations = 1 (initialization)
- **Fixed**: iterations = N (repeat N times)
- **Dynamic**: Use controller steps for variable iterations

### Debugging
1. Enable call stack console
2. Watch execution flow
3. Check iteration counts
4. Verify parameter passing

## Visual Guide

### Sub-workflow Call Node (Purple)
```
┌─────────────────────────┐
│ ⚡ my_subworkflow       │
│ Iterations: 5           │
└─────────────────────────┘
```

### Call Stack Console
```
┌─ Call Stack ────────────┐
│ ● main (1/1)            │
│   ● step (5/10)         │
│     ● update (1/1)      │ ← Currently executing
└─────────────────────────┘
```

## Resources

- Example workflows: `examples/test_workflow_v2.json`
- Migration tool: `scripts/migrate_workflow.py`
- Tests: `tests/test_workflow_v2.py`

## Support

For issues or questions:
1. Check validation errors in console
2. Review call stack for execution flow
3. Verify sub-workflow structure
4. Test with minimal example

