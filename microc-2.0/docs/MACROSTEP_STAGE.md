# Macrostep Stage - Flexible Workflow Execution

## Overview

The **macrostep stage** is a new workflow stage that provides complete flexibility in defining the execution order and frequency of simulation processes. Instead of the fixed sequence (intracellular → microenvironment → intercellular), users can now:

1. **Arrange nodes visually** on a canvas
2. **Set step counts** for each node
3. **Add custom functions** between standard processes
4. **Reorder execution** as needed

## Architecture

### Stage Hierarchy

```
Workflow
├── Initialization (runs once at start)
├── Macrostep (NEW - runs each macro-step)
│   ├── Node: Intracellular (step_count: 3)
│   ├── Node: Microenvironment (step_count: 5)
│   ├── Node: Intercellular (step_count: 1)
│   └── Node: Custom Function (step_count: 2)
└── Finalization (runs once at end)
```

### Legacy vs. Macrostep Mode

**Legacy Mode** (backward compatible):
- Separate tabs: Intracellular, Microenvironment, Intercellular
- Each tab has a `steps` parameter (stage-level)
- Fixed execution order

**Macrostep Mode** (new):
- Single "Macrostep" tab with visual canvas
- Each **node** has a `step_count` parameter (function-level)
- User-defined execution order via `execution_order` array

## JSON Schema

### Macrostep Stage Structure

```json
{
  "stages": {
    "macrostep": {
      "enabled": true,
      "steps": 1,
      "parameters": [],
      "functions": [
        {
          "id": "intracellular_node",
          "function_name": "standard_intracellular_update",
          "description": "Intracellular update",
          "parameters": {},
          "enabled": true,
          "position": {"x": 100, "y": 100},
          "step_count": 3
        },
        {
          "id": "microenvironment_node",
          "function_name": "standard_diffusion_update",
          "description": "Microenvironment update",
          "parameters": {},
          "enabled": true,
          "position": {"x": 300, "y": 100},
          "step_count": 5
        },
        {
          "id": "intercellular_node",
          "function_name": "standard_intercellular_update",
          "description": "Intercellular update",
          "parameters": {},
          "enabled": true,
          "position": {"x": 500, "y": 100},
          "step_count": 1
        }
      ],
      "execution_order": [
        "intracellular_node",
        "microenvironment_node",
        "intercellular_node"
      ]
    }
  }
}
```

### Key Fields

- **`step_count`** (in `WorkflowFunction`): Number of times this specific function executes
- **`execution_order`** (in `WorkflowStage`): Array of function IDs defining execution sequence
- **`position`**: Canvas coordinates for visual layout

## Execution Behavior

With the example above, at each macro-step:

1. **Intracellular** runs **3 times**
2. **Microenvironment** runs **5 times**
3. **Intercellular** runs **1 time**

The order is determined by `execution_order`, not by position on canvas.

## Standard Function Names

For the macrostep canvas, use these function names:

- `standard_intracellular_update` - Intracellular processes
- `standard_diffusion_update` - Microenvironment/diffusion
- `standard_intercellular_update` - Intercellular interactions

## Use Cases

### 1. Multi-scale Simulations
Run fast processes more frequently than slow ones:
```
Intracellular (10x) → Microenvironment (5x) → Intercellular (1x)
```

### 2. Custom Logging
Insert logging between processes:
```
Intracellular → Log State → Microenvironment → Log State → Intercellular
```

### 3. Reordered Execution
Change the standard order:
```
Microenvironment → Intracellular → Intercellular
```

### 4. Iterative Coupling
Alternate between processes:
```
Intracellular → Microenvironment → Intracellular → Microenvironment → Intercellular
```

## Backward Compatibility

- If **macrostep stage exists and is enabled**, it takes precedence
- If **macrostep stage does not exist**, legacy mode is used (separate intracellular/microenvironment/intercellular stages)
- Existing workflows without macrostep continue to work unchanged

## Testing

See `tests/test_macrostep_workflow.json` for a complete example.

Run with:
```bash
python tools/run_sim.py --workflow tests/test_macrostep_workflow.json
```

Expected output:
```
[WORKFLOW] Function 'standard_intracellular_update' will execute 3 times
[WORKFLOW] Function 'standard_diffusion_update' will execute 5 times
```

## Next Steps

See `docs/GUI_MACROSTEP_INTEGRATION.md` for GUI implementation details.

