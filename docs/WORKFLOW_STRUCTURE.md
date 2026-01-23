# Workflow File Structure

This document describes the JSON structure of OpenCellComms workflow files.

## Overview

OpenCellComms supports two workflow versions:
- **Version 1.0**: Stage-based (initialization, intracellular, diffusion, intercellular, finalization)
- **Version 2.0**: Subworkflow-based (flexible hierarchical structure with composers)

## Version 1.0 (Stage-Based)

### Basic Structure

```json
{
  "version": "1.0",
  "name": "My Workflow",
  "description": "Description of the workflow",
  "metadata": {
    "author": "Your Name",
    "experiment": "Experiment Name",
    "created": "2026-01-23",
    "notes": "Additional notes"
  },
  "stages": {
    "initialization": { ... },
    "intracellular": { ... },
    "diffusion": { ... },
    "intercellular": { ... },
    "finalization": { ... },
    "macrostep": { ... }
  }
}
```

### Stage Types

| Stage | Purpose | When Executed |
|-------|---------|---------------|
| `initialization` | Setup simulation | Once at start |
| `macrostep` | Main loop controller | Outer loop |
| `intracellular` | Cell-internal processes | Each macrostep |
| `diffusion` | Substance diffusion | Each macrostep |
| `intercellular` | Cell interactions | Each macrostep |
| `finalization` | Output and cleanup | Once at end |

### Stage Definition

```json
"initialization": {
  "enabled": true,
  "steps": 1,
  "description": "Setup simulation components",
  "functions": [
    { ... }
  ],
  "execution_order": ["func_id_1", "func_id_2"],
  "parameters": [
    { ... }
  ]
}
```

### Function Node

```json
{
  "id": "unique_function_id",
  "function_name": "setup_simulation",
  "enabled": true,
  "description": "What this function does",
  "parameters": {
    "param1": "value1",
    "param2": 123
  },
  "position": {
    "x": 100,
    "y": 200
  },
  "parameter_nodes": ["param_node_id_1", "param_node_id_2"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier within the workflow |
| `function_name` | string | Registered function name (Python function) |
| `enabled` | boolean | Whether function executes |
| `description` | string | Tooltip in GUI |
| `parameters` | object | Key-value parameter overrides |
| `position` | object | GUI canvas position (x, y) |
| `parameter_nodes` | array | IDs of connected parameter nodes |

### Parameter Node

Parameter nodes allow values to be visually connected to functions in the GUI:

```json
"parameters": [
  {
    "id": "param_sim_name",
    "label": "Simulation Name",
    "parameters": {
      "name": "My Simulation"
    }
  },
  {
    "id": "param_timestep",
    "label": "Time Step (dt)",
    "parameters": {
      "dt": 0.1
    }
  }
]
```

## Version 2.0 (Subworkflow-Based)

### Basic Structure

```json
{
  "version": "2.0",
  "name": "My Workflow",
  "description": "Description",
  "metadata": {
    "author": "Your Name",
    "created": "2026-01-23",
    "gui": {
      "subworkflow_kinds": {
        "main": "composer",
        "my_subworkflow": "subworkflow"
      }
    }
  },
  "subworkflows": {
    "main": { ... },
    "my_subworkflow": { ... }
  }
}
```

### Subworkflow Definition

```json
"main": {
  "description": "Main entry point",
  "deletable": false,
  "controller": {
    "id": "controller-main",
    "label": "MAIN CONTROLLER",
    "position": {"x": 50, "y": 50},
    "number_of_steps": 1
  },
  "functions": [ ... ],
  "subworkflow_calls": [ ... ],
  "parameters": [],
  "execution_order": ["call_1", "func_1", "call_2"],
  "enabled": true
}
```

### Subworkflow Call

```json
{
  "id": "call_processing",
  "subworkflow_name": "processing_workflow",
  "iterations": 3,
  "enabled": true,
  "description": "Run processing 3 times",
  "parameters": {
    "mode": "fast"
  },
  "context_mapping": {},
  "parameter_nodes": [],
  "position": {"x": 200, "y": 100}
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique call identifier |
| `subworkflow_name` | string | Name of subworkflow to call |
| `iterations` | integer | Number of times to run |
| `enabled` | boolean | Whether call executes |
| `parameters` | object | Parameters passed to subworkflow |
| `context_mapping` | object | Map context values between workflows |
| `position` | object | GUI canvas position |

## Complete v1.0 Example

```json
{
  "version": "1.0",
  "name": "Simple Simulation",
  "description": "Basic cell simulation workflow",
  "metadata": {
    "author": "Your Name",
    "created": "2026-01-23"
  },
  "stages": {
    "initialization": {
      "enabled": true,
      "steps": 1,
      "description": "Setup simulation",
      "functions": [
        {
          "id": "setup_sim",
          "function_name": "setup_simulation",
          "enabled": true,
          "parameters": {"name": "My Sim", "dt": 0.1},
          "position": {"x": 100, "y": 100}
        },
        {
          "id": "setup_pop",
          "function_name": "setup_population",
          "enabled": true,
          "parameters": {"initial_cells": 100},
          "position": {"x": 100, "y": 200}
        }
      ],
      "execution_order": ["setup_sim", "setup_pop"]
    },
    "macrostep": {
      "enabled": true,
      "steps": 100,
      "description": "Main simulation loop",
      "functions": [],
      "execution_order": []
    },
    "intracellular": {
      "enabled": true,
      "steps": 1,
      "functions": [
        {
          "id": "update_meta",
          "function_name": "update_metabolism",
          "enabled": true,
          "parameters": {},
          "position": {"x": 100, "y": 100}
        }
      ],
      "execution_order": ["update_meta"]
    },
    "finalization": {
      "enabled": true,
      "steps": 1,
      "functions": [
        {
          "id": "save_results",
          "function_name": "save_simulation_data",
          "enabled": true,
          "parameters": {},
          "position": {"x": 100, "y": 100}
        }
      ],
      "execution_order": ["save_results"]
    }
  }
}
```

## GUI Position Coordinates

The `position` object controls where nodes appear on the GUI canvas:

```json
"position": {
  "x": 100,   // Horizontal position (pixels from left)
  "y": 200    // Vertical position (pixels from top)
}
```

**Tips:**
- Space nodes ~100-150 pixels apart vertically
- Keep initialization functions at `x: 100`
- Use consistent alignment for readability

## Execution Order

The `execution_order` array determines the sequence of execution:

```json
"execution_order": ["setup_sim", "setup_domain", "setup_pop", "load_cells"]
```

- Order matters - functions run in this exact sequence
- Only enabled functions actually execute
- IDs must match function `id` fields exactly
- For v2.0, can include both function IDs and subworkflow call IDs

