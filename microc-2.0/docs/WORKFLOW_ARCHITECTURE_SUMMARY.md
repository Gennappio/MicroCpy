# Workflow Architecture Summary

## Overview

MicroC 2.0 now supports two workflow execution modes:

1. **Legacy Mode** - Backward compatible with existing workflows
2. **Macrostep Mode** - New flexible canvas-based execution (RECOMMENDED)

## Comparison

| Feature | Legacy Mode | Macrostep Mode |
|---------|-------------|----------------|
| **Tabs** | Separate (Intracellular, Microenvironment, Intercellular) | Single "Macrostep" tab |
| **Execution Order** | Fixed (Intra → Micro → Inter) | User-defined via canvas |
| **Step Control** | Stage-level (`steps` parameter) | Node-level (`step_count` parameter) |
| **Custom Functions** | Limited | Full support between any nodes |
| **Visual Editor** | Form-based | Canvas with drag-and-drop nodes |
| **Flexibility** | Low | High |

## Legacy Mode (Backward Compatible)

### Structure

```
Workflow
├── Initialization
├── Intracellular (steps: 3)
├── Microenvironment (steps: 5)
├── Intercellular (steps: 1)
└── Finalization
```

### JSON Example

```json
{
  "stages": {
    "intracellular": {
      "enabled": true,
      "steps": 3,
      "functions": [...]
    },
    "microenvironment": {
      "enabled": true,
      "steps": 5,
      "functions": [...]
    },
    "intercellular": {
      "enabled": true,
      "steps": 1,
      "functions": [...]
    }
  }
}
```

### Behavior

- Each stage executes all its functions `steps` times
- Fixed order: Intracellular → Microenvironment → Intercellular
- Controlled by orchestrator timing

## Macrostep Mode (New)

### Structure

```
Workflow
├── Initialization
├── Macrostep
│   ├── Node: Intracellular (step_count: 3)
│   ├── Node: Microenvironment (step_count: 5)
│   └── Node: Intercellular (step_count: 1)
└── Finalization
```

### JSON Example

```json
{
  "stages": {
    "macrostep": {
      "enabled": true,
      "steps": 1,
      "functions": [
        {
          "id": "intracellular_node",
          "function_name": "standard_intracellular_update",
          "step_count": 3,
          "position": {"x": 100, "y": 100}
        },
        {
          "id": "microenvironment_node",
          "function_name": "standard_diffusion_update",
          "step_count": 5,
          "position": {"x": 300, "y": 100}
        },
        {
          "id": "intercellular_node",
          "function_name": "standard_intercellular_update",
          "step_count": 1,
          "position": {"x": 500, "y": 100}
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

### Behavior

- Each **node** (function) executes `step_count` times
- Order defined by `execution_order` array
- Can insert custom functions anywhere
- Can reorder standard processes

## Mode Selection

The simulation engine automatically detects which mode to use:

```python
if macrostep_stage exists and is enabled:
    use macrostep mode
else:
    use legacy mode (separate stages)
```

## Migration Path

### Option 1: Keep Legacy Mode
- No changes needed
- Existing workflows continue to work
- Limited flexibility

### Option 2: Convert to Macrostep
- Create macrostep stage
- Add nodes for each process
- Set `step_count` on each node
- Define `execution_order`
- Disable legacy stages (optional)

## Standard Function Names

For macrostep nodes, use these function names:

| Process | Function Name |
|---------|---------------|
| Intracellular | `standard_intracellular_update` |
| Microenvironment | `standard_diffusion_update` |
| Intercellular | `standard_intercellular_update` |

## Examples

- **Legacy Mode**: `tests/test_workflow_steps.json`
- **Macrostep Mode**: `tests/test_macrostep_workflow.json`
- **Production (2D CSV)**: `tests/jayatilake_experiment/jaya_workflow_2d_csv.json` (legacy)

## Documentation

- **Technical Details**: `docs/MACROSTEP_STAGE.md`
- **GUI Implementation**: `docs/GUI_MACROSTEP_INTEGRATION.md`
- **Legacy Steps Feature**: `docs/WORKFLOW_STEPS.md`

## Recommendations

### For New Workflows
✅ Use **Macrostep Mode** for maximum flexibility

### For Existing Workflows
✅ Keep **Legacy Mode** unless you need:
- Custom execution order
- Functions between standard processes
- Different step counts for different processes

### For GUI Development
✅ Implement both modes:
1. Legacy tabs (for backward compatibility)
2. Macrostep canvas (for new workflows)

