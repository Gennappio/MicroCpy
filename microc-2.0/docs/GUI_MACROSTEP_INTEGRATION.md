# GUI Integration Guide: Macrostep Stage

## Overview

The **Macrostep** stage is a new tab in the workflow editor that allows users to visually configure the execution order and frequency of simulation processes using a **node-based canvas**.

## UI Layout

### Tab Structure

```
Tabs:
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│Initialization│  Macrostep  │Intracellular│Microenv.    │Intercellular│
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
                     ▲
                  NEW TAB
```

### Macrostep Tab Layout

```
┌──────────────────────────────────────────────────────────────┐
│ Macrostep Configuration                                      │
├──────────────────────────────────────────────────────────────┤
│ ☑ Enabled                                                    │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │                    CANVAS AREA                         │  │
│ │                                                        │  │
│ │  ┌─────────────┐    ┌─────────────┐    ┌──────────┐  │  │
│ │  │Intracellular│───▶│Microenviron.│───▶│Intercell.│  │  │
│ │  │  Steps: 3   │    │  Steps: 5   │    │ Steps: 1 │  │  │
│ │  └─────────────┘    └─────────────┘    └──────────┘  │  │
│ │                                                        │  │
│ │  [+ Add Node ▼]                                       │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Execution Order: [Drag to reorder]                          │
│  1. Intracellular (3 steps)                                 │
│  2. Microenvironment (5 steps)                              │
│  3. Intercellular (1 step)                                  │
└──────────────────────────────────────────────────────────────┘
```

## Node Types

### 1. Standard Process Nodes

Pre-defined nodes that users can add to the canvas:

| Node Name | Function Name | Default Steps | Description |
|-----------|---------------|---------------|-------------|
| **Intracellular** | `standard_intracellular_update` | 1 | Gene networks, metabolism |
| **Microenvironment** | `standard_diffusion_update` | 1 | Diffusion, substance transport |
| **Intercellular** | `standard_intercellular_update` | 1 | Cell division, death, interactions |

### 2. Custom Function Nodes

Users can add custom functions from:
- Registered standard functions
- Custom Python files

## Node Properties

Each node on the canvas has:

### Visual Properties
- **Position**: `{x: number, y: number}` - Canvas coordinates
- **Size**: Fixed or auto-sized based on content
- **Connections**: Visual arrows showing execution order

### Configuration Properties
- **ID**: Unique identifier (auto-generated)
- **Function Name**: Which function to execute
- **Description**: User-editable label
- **Enabled**: Checkbox to enable/disable
- **Step Count**: Integer input (minimum: 1)

### Node UI

```
┌─────────────────────────┐
│ ☑ Intracellular         │
├─────────────────────────┤
│ Steps: [  3  ]          │
│                         │
│ [⚙ Configure]          │
└─────────────────────────┘
```

## Implementation Requirements

### 1. Add "Macrostep" Tab

- Insert between "Initialization" and "Intracellular" tabs
- Tab should be visible by default for new workflows
- For existing workflows without macrostep, show tab but disabled

### 2. Canvas Component

**Features needed:**
- Drag-and-drop nodes
- Connect nodes with arrows (visual only - order is from execution_order list)
- Pan and zoom
- Grid snapping (optional)

**Recommended libraries:**
- React Flow (React)
- JointJS (vanilla JS)
- Cytoscape.js (graph visualization)

### 3. Node Palette

**"Add Node" dropdown menu:**
```
[+ Add Node ▼]
  ├─ Standard Processes
  │  ├─ Intracellular
  │  ├─ Microenvironment
  │  └─ Intercellular
  ├─ Custom Functions
  │  └─ [Load from file...]
  └─ Utilities
     └─ Log State
```

### 4. Node Configuration Panel

When a node is selected, show properties panel:

```
┌─────────────────────────────┐
│ Node Properties             │
├─────────────────────────────┤
│ ID: intracellular_node      │
│ Function: standard_intra... │
│                             │
│ ☑ Enabled                   │
│                             │
│ Step Count: [  3  ]         │
│ ⓘ Number of times to run    │
│                             │
│ Description:                │
│ ┌─────────────────────────┐ │
│ │Intracellular update     │ │
│ └─────────────────────────┘ │
│                             │
│ [Delete Node]               │
└─────────────────────────────┘
```

### 5. Execution Order List

Below the canvas, show a reorderable list:

```
Execution Order:
┌─────────────────────────────────┐
│ ☰ 1. Intracellular (3 steps)   │
│ ☰ 2. Microenvironment (5 steps)│
│ ☰ 3. Intercellular (1 step)    │
└─────────────────────────────────┘
```

- Drag handles (☰) to reorder
- Updates `execution_order` array in JSON
- Visual connections on canvas update automatically

## JSON Serialization

### Save Workflow

When saving, generate JSON:

```json
{
  "macrostep": {
    "enabled": true,
    "steps": 1,
    "functions": [
      {
        "id": "node_1",
        "function_name": "standard_intracellular_update",
        "description": "Intracellular",
        "enabled": true,
        "position": {"x": 100, "y": 100},
        "step_count": 3,
        "parameters": {}
      }
    ],
    "execution_order": ["node_1", "node_2", "node_3"]
  }
}
```

### Load Workflow

When loading:
1. Read `macrostep.functions` array
2. Create nodes at specified positions
3. Set `step_count` for each node
4. Use `execution_order` to draw connections

## Validation

### Required Checks

- [ ] At least one node in macrostep (if enabled)
- [ ] All nodes in `execution_order` exist in `functions`
- [ ] All `step_count` values >= 1
- [ ] No duplicate node IDs
- [ ] All `function_name` values are valid (registered functions)

### User Warnings

- Warn if macrostep is enabled but empty
- Warn if node is not in execution_order (orphaned node)
- Warn if execution_order contains non-existent node ID

## Migration from Legacy Mode

### Option 1: Auto-Convert

When user enables macrostep tab, offer to convert existing configuration:

```
┌────────────────────────────────────────┐
│ Convert to Macrostep?                  │
├────────────────────────────────────────┤
│ Your workflow uses separate tabs for:  │
│  • Intracellular (3 steps)             │
│  • Microenvironment (5 steps)          │
│  • Intercellular (1 step)              │
│                                        │
│ Convert to macrostep canvas?           │
│                                        │
│ [Convert]  [Keep Separate]             │
└────────────────────────────────────────┘
```

### Option 2: Manual Setup

User manually adds nodes to macrostep canvas and disables legacy tabs.

## Testing Checklist

- [ ] Create new workflow with macrostep
- [ ] Add intracellular node (step_count: 3)
- [ ] Add microenvironment node (step_count: 5)
- [ ] Add intercellular node (step_count: 1)
- [ ] Reorder nodes in execution list
- [ ] Save workflow to JSON
- [ ] Load workflow from JSON
- [ ] Run workflow and verify console output shows correct step counts
- [ ] Disable macrostep and verify legacy mode still works

## Example Workflow

See `tests/test_macrostep_workflow.json` for a complete example.

## Questions?

See `docs/MACROSTEP_STAGE.md` for technical details.

