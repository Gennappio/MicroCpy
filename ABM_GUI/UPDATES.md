# ABM_GUI Updates - Enhanced Features

## Summary of Changes

This document describes the enhancements made to the ABM_GUI to address three key requirements:

1. **Import JSON loads ALL stages** (not just the current view)
2. **Directed arrows** for node connections
3. **Function file parameter** for each component

---

## 1. Import JSON Loads All Stages ✅

### Problem
Previously, importing a workflow JSON would only load the currently visible stage.

### Solution
Modified `workflowStore.js` to iterate through **all 5 stages** when loading a workflow:

```javascript
// Load workflow from JSON - LOADS ALL STAGES
loadWorkflow: (workflowJson) => {
  const newStageNodes = {
    initialization: [],
    intracellular: [],
    diffusion: [],
    intercellular: [],
    finalization: [],
  };
  
  // Convert workflow functions to React Flow nodes for ALL stages
  Object.keys(newStageNodes).forEach((stageName) => {
    const stage = stages[stageName];
    if (!stage) return;
    // ... process all stages
  });
}
```

### Result
- ✅ Importing `jaya_workflow.json` now loads all 11 functions across all 5 stages
- ✅ Users can switch between stage tabs and see all loaded functions
- ✅ No data loss when importing workflows

---

## 2. Directed Arrows for Connections ✅

### Problem
Node connections were simple lines without direction indicators.

### Solution
Added `markerEnd` property to all edges with arrowhead styling:

**In `workflowStore.js` (loadWorkflow):**
```javascript
edges.push({
  id: `e-${source}-${target}`,
  source: source,
  target: target,
  type: 'smoothstep',
  animated: true,
  markerEnd: {
    type: 'arrowclosed',
    width: 20,
    height: 20,
  },
  style: {
    strokeWidth: 2,
  },
});
```

**In `WorkflowCanvas.jsx` (onConnect):**
```javascript
const onConnect = useCallback(
  (params) =>
    setEdges((eds) =>
      addEdge(
        {
          ...params,
          type: 'smoothstep',
          animated: true,
          markerEnd: {
            type: 'arrowclosed',
            width: 20,
            height: 20,
          },
          style: {
            strokeWidth: 2,
          },
        },
        eds
      )
    ),
  [setEdges]
);
```

### Result
- ✅ All connections now show directional arrows
- ✅ Execution order is visually clear
- ✅ Arrows are animated and styled consistently

---

## 3. Function File Parameter ✅

### Problem
Functions didn't specify which Python file contains their implementation.

### Solution

#### A. Added `function_file` parameter to all functions in registry

**In `functionRegistry.js`:**
```javascript
initialize_cell_placement: {
  name: 'initialize_cell_placement',
  displayName: 'Initialize Cell Placement',
  category: FunctionCategory.INITIALIZATION,
  parameters: [
    {
      name: 'function_file',
      type: 'string',
      description: 'Path to Python file containing this function',
      default: 'tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py',
      required: true,
    },
    // ... other parameters
  ],
}
```

This was added to **all 14 functions** in the registry.

#### B. Updated workflow store to handle function_file

**In `workflowStore.js`:**
- Load: Extract `function_file` from JSON
- Export: Include `function_file` in exported JSON

```javascript
// Loading
data: {
  functionFile: func.function_file || func.parameters?.function_file || '',
  // ...
}

// Exporting
functions.map((node) => ({
  function_file: node.data.functionFile || node.data.parameters?.function_file || '',
  // ...
}))
```

#### C. Updated node component to display function file

**In `WorkflowFunctionNode.jsx`:**
```javascript
const filePath = functionFile || parameters?.function_file || '';
const fileName = filePath ? filePath.split('/').pop() : '';

{fileName && (
  <div className="node-file-path" title={filePath}>
    <FileCode size={12} />
    <span>{fileName}</span>
  </div>
)}
```

**In `WorkflowFunctionNode.css`:**
```css
.node-file-path {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 9px;
  color: #6b7280;
  background: #fef3c7;
  padding: 3px 6px;
  border-radius: 3px;
  margin-top: 4px;
  font-family: monospace;
  border: 1px solid #fbbf24;
}
```

#### D. Updated workflow JSON format

**In `jaya_workflow.json`:**
```json
{
  "id": "init_placement_1",
  "function_name": "initialize_cell_placement",
  "function_file": "tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py",
  "parameters": {
    "function_file": "tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py",
    "initial_cell_count": 50,
    "placement_pattern": "spheroid"
  }
}
```

### Result
- ✅ Every function node displays its Python file
- ✅ File path is shown as a badge with icon
- ✅ Hovering shows full path
- ✅ Parameter editor includes function_file field
- ✅ JSON export includes function_file

---

## Files Modified

### Frontend (ABM_GUI)
1. **`src/store/workflowStore.js`**
   - Load all stages on import
   - Add arrow markers to edges
   - Handle function_file in load/export

2. **`src/components/WorkflowCanvas.jsx`**
   - Add arrow markers to new connections
   - Extract function_file when dropping nodes

3. **`src/components/WorkflowFunctionNode.jsx`**
   - Display function file badge
   - Extract filename from path
   - Show FileCode icon

4. **`src/components/WorkflowFunctionNode.css`**
   - Style function file badge
   - Yellow background for visibility

5. **`src/data/functionRegistry.js`**
   - Add function_file parameter to all 14 functions
   - Set default path for Jayatilake functions

### Backend (microc-2.0)
6. **`tests/jayatilake_experiment/jaya_workflow.json`**
   - Add function_file to all 11 function instances
   - Include in both top-level and parameters

---

## Testing

### Test 1: Import All Stages
1. Open GUI at `http://localhost:3000`
2. Click "Import JSON"
3. Select `example_workflow.json`
4. Switch between all 5 stage tabs
5. ✅ Verify all functions are loaded:
   - Initialization: 2 functions
   - Intracellular: 6 functions
   - Diffusion: 0 functions
   - Intercellular: 2 functions
   - Finalization: 1 function

### Test 2: Directed Arrows
1. View any stage with multiple functions
2. ✅ Verify arrows point from source to target
3. Create new connection by dragging
4. ✅ Verify new connection has arrow

### Test 3: Function File Display
1. View any function node
2. ✅ Verify yellow badge shows filename
3. Hover over badge
4. ✅ Verify tooltip shows full path
5. Double-click node to edit
6. ✅ Verify function_file parameter is editable

### Test 4: Export with Function File
1. Load example workflow
2. Export to JSON
3. Open exported file
4. ✅ Verify all functions have `function_file` field
5. ✅ Verify function_file is in parameters

---

## Visual Changes

### Before
- Connections: Simple lines
- Nodes: No file information
- Import: Only current stage loaded

### After
- Connections: **Directed arrows** with animation
- Nodes: **Yellow badge** showing Python filename
- Import: **All 5 stages** loaded simultaneously

---

## JSON Format Changes

### Old Format
```json
{
  "id": "metabolism_1",
  "function_name": "calculate_cell_metabolism",
  "parameters": {
    "oxygen_vmax": 1.0e-16
  }
}
```

### New Format
```json
{
  "id": "metabolism_1",
  "function_name": "calculate_cell_metabolism",
  "function_file": "tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py",
  "parameters": {
    "function_file": "tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py",
    "oxygen_vmax": 1.0e-16
  }
}
```

---

## Backward Compatibility

The changes are **backward compatible**:
- Old JSON files without `function_file` will still load
- Missing `function_file` defaults to empty string
- Nodes without file info display normally (just no badge)

---

## Future Enhancements

Potential improvements:
1. **File browser** for selecting function files
2. **Validation** to check if file exists
3. **Syntax highlighting** for Python file preview
4. **Auto-detection** of functions in Python files
5. **Multiple files** per workflow support

---

## Summary

All three requirements have been successfully implemented:

✅ **Import loads all stages** - No more manual stage-by-stage loading  
✅ **Directed arrows** - Clear visual execution flow  
✅ **Function file parameter** - Every function points to its Python implementation  

The GUI is now more powerful and provides better visibility into the workflow structure!

