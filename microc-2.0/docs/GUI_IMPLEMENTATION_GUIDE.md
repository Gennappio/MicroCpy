# GUI Implementation Guide - Complete Overview

## Quick Start

This guide covers the complete GUI implementation for MicroC 2.0 workflow system.

## Architecture Overview

MicroC 2.0 supports **two workflow modes**:

1. **Legacy Mode** - Backward compatible (separate tabs with stage-level steps)
2. **Macrostep Mode** - New flexible canvas (single tab with node-level step_count)

## Implementation Priority

### Phase 1: Legacy Mode Support (REQUIRED)
✅ Ensures backward compatibility with existing workflows

**Tasks:**
- [ ] Add "Steps" input field to Intracellular tab
- [ ] Add "Steps" input field to Microenvironment tab
- [ ] Add "Steps" input field to Intercellular tab
- [ ] Update JSON save/load to include `steps` field in each stage

**Documentation:** `docs/GUI_STEPS_INTEGRATION.md`

### Phase 2: Macrostep Mode (RECOMMENDED)
✅ Provides maximum flexibility for new workflows

**Tasks:**
- [ ] Add "Macrostep" tab between Initialization and Intracellular
- [ ] Implement visual canvas for node arrangement
- [ ] Add node palette (Intracellular, Microenvironment, Intercellular, Custom)
- [ ] Add "Step Count" input for each node
- [ ] Implement execution order list (drag-to-reorder)
- [ ] Update JSON save/load to include macrostep stage

**Documentation:** `docs/GUI_MACROSTEP_INTEGRATION.md`

## Tab Structure

### Current (Legacy Mode Only)
```
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│Initialization│Intracellular│Microenv.    │Intercellular│Finalization │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

### With Macrostep (Recommended)
```
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│Initialization│  Macrostep  │Intracellular│Microenv.    │Intercellular│Finalization │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
                     ▲
                  NEW TAB
```

## JSON Schema Changes

### Legacy Mode (Stage-level steps)

```json
{
  "stages": {
    "intracellular": {
      "enabled": true,
      "steps": 3,          ← Add this field
      "parameters": [...],
      "functions": [...],
      "execution_order": [...]
    }
  }
}
```

### Macrostep Mode (Node-level step_count)

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
          "step_count": 3,    ← Add this field
          "position": {"x": 100, "y": 100},
          "enabled": true,
          "parameters": {}
        }
      ],
      "execution_order": ["intracellular_node", ...]
    }
  }
}
```

## UI Components

### 1. Legacy Mode - Stage Steps Input

**Location:** Top of each stage tab (Intracellular, Microenvironment, Intercellular)

```
┌─────────────────────────────────────┐
│ ☑ Enabled                           │
│ Steps per macro-step: [  3  ] ⓘ    │
│                                     │
│ [Functions and parameters below...] │
└─────────────────────────────────────┘
```

**Properties:**
- Type: Integer (min: 1)
- Default: 1
- Tooltip: "Number of times this stage executes per macro-step"

### 2. Macrostep Mode - Canvas with Nodes

**Location:** Macrostep tab

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
│ │  │Step Count: 3│    │Step Count: 5│    │Step Cnt:1│  │  │
│ │  └─────────────┘    └─────────────┘    └──────────┘  │  │
│ │                                                        │  │
│ │  [+ Add Node ▼]                                       │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Execution Order: [Drag to reorder]                          │
│  ☰ 1. Intracellular (3 steps)                               │
│  ☰ 2. Microenvironment (5 steps)                            │
│  ☰ 3. Intercellular (1 step)                                │
└──────────────────────────────────────────────────────────────┘
```

**Node Properties Panel (when node selected):**
```
┌─────────────────────────────┐
│ Node Properties             │
├─────────────────────────────┤
│ ID: intracellular_node      │
│ Function: standard_intra... │
│                             │
│ ☑ Enabled                   │
│                             │
│ Step Count: [  3  ] ⓘ      │
│                             │
│ Description:                │
│ ┌─────────────────────────┐ │
│ │Intracellular update     │ │
│ └─────────────────────────┘ │
│                             │
│ [Delete Node]               │
└─────────────────────────────┘
```

## Testing

### Test Files

1. **Legacy Mode:**
   - `tests/test_workflow_steps.json` - Stage-level steps (3-5-1)
   - `tests/jayatilake_experiment/jaya_workflow_2d_csv.json` - Production example

2. **Macrostep Mode:**
   - `tests/test_macrostep_workflow.json` - Basic macrostep (3-5-1)
   - `tests/test_macrostep_advanced.json` - Complex execution order

### Validation Checklist

**Legacy Mode:**
- [ ] Load workflow with `steps` field in each stage
- [ ] Modify step values in GUI
- [ ] Save workflow and verify JSON contains correct `steps` values
- [ ] Run workflow and verify console shows correct execution counts

**Macrostep Mode:**
- [ ] Create new macrostep stage
- [ ] Add nodes to canvas
- [ ] Set `step_count` for each node
- [ ] Reorder nodes in execution list
- [ ] Save workflow and verify JSON structure
- [ ] Load workflow and verify nodes appear correctly
- [ ] Run workflow and verify execution order and counts

## Documentation Files

| File | Purpose |
|------|---------|
| `WORKFLOW_ARCHITECTURE_SUMMARY.md` | High-level comparison of modes |
| `WORKFLOW_STEPS.md` | Legacy mode technical details |
| `GUI_STEPS_INTEGRATION.md` | Legacy mode GUI guide |
| `MACROSTEP_STAGE.md` | Macrostep mode technical details |
| `GUI_MACROSTEP_INTEGRATION.md` | Macrostep mode GUI guide (detailed) |
| `GUI_IMPLEMENTATION_GUIDE.md` | This file - complete overview |

## Recommended Libraries

### For Canvas (Macrostep Mode)
- **React Flow** (React) - https://reactflow.dev/
- **JointJS** (vanilla JS) - https://www.jointjs.com/
- **Cytoscape.js** - https://js.cytoscape.org/

### For Drag-and-Drop
- **react-beautiful-dnd** (React)
- **Sortable.js** (vanilla JS)

## Questions?

Contact the MicroCpy team or refer to the detailed documentation files listed above.

