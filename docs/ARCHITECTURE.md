# OpenCellComms Architecture

## Overview

OpenCellComms is a multi-scale cell simulation platform with a **dual-stack architecture**:

```
┌─────────────────────────────────────────────────────────────────┐
│                   OpenCellComms Platform                         │
├──────────────────────────┬──────────────────────────────────────┤
│    React GUI (Frontend)  │      Python Engine (Backend)        │
│    opencellcomms_gui/    │      opencellcomms_engine/          │
├──────────────────────────┼──────────────────────────────────────┤
│  • Visual workflow editor│  • Workflow execution               │
│  • Node-based canvas     │  • Cell simulation (PhysiCell-like) │
│  • Parameter editing     │  • PDE solvers (FiPy)               │
│  • Real-time logs        │  • Gene networks (MaBoSS)           │
└──────────────────────────┴──────────────────────────────────────┘
                           │
                    REST API (Flask)
                    Port 5001
```

## Directory Structure

```
OpenCellComms/
├── opencellcomms_engine/     # Python backend
│   └── src/opencellcomms/
│       ├── core/             # Domain models (Cell, Population, etc.)
│       ├── workflow/         # Workflow execution engine
│       │   ├── executor.py   # Main workflow executor
│       │   └── functions/    # 40+ workflow functions
│       ├── simulation/       # Simulation models
│       │   ├── mechanics.py  # Cell mechanics (forces, adhesion)
│       │   └── diffusion.py  # PDE solvers for microenvironment
│       └── genetics/         # Gene regulatory networks
│           └── grn.py        # MaBoSS integration
│
├── opencellcomms_gui/        # React frontend
│   ├── src/
│   │   ├── store/            # Zustand state management
│   │   │   ├── workflowStore.js    # Main store (composed)
│   │   │   ├── pathUtils.js        # Path handling utilities
│   │   │   └── slices/             # Modular store slices
│   │   │       ├── observabilitySlice.js
│   │   │       ├── subworkflowSlice.js
│   │   │       ├── nodeActionsSlice.js
│   │   │       ├── librarySlice.js
│   │   │       ├── workflowIOSlice.js
│   │   │       └── logSlice.js
│   │   ├── components/       # React components
│   │   │   ├── WorkflowCanvas.jsx
│   │   │   ├── nodes/        # Custom node types
│   │   │   └── editors/      # Parameter editors
│   │   └── utils/            # Utility functions
│   └── server/               # Flask backend for GUI
│       └── app.py            # REST API endpoints
│
└── docs/                     # Documentation
    ├── ARCHITECTURE.md       # This file
    ├── CONVENTIONS.md        # Coding conventions
    └── article/              # Technical paper
```

## Key Concepts

### 1. Workflows (v2.0 Format)

Workflows are JSON files that define simulation pipelines:

```json
{
  "version": "2.0",
  "name": "My Simulation",
  "subworkflows": {
    "main": {
      "controller": { ... },
      "functions": [ ... ],
      "subworkflow_calls": [ ... ],
      "execution_order": ["node1", "node2", ...]
    }
  }
}
```

### 2. Subworkflows

Two types of subworkflows:
- **Composers**: High-level orchestration (e.g., `main`)
- **Subworkflows**: Reusable processing blocks (e.g., `process_cells`)

### 3. Node Types

| Node Type | Purpose |
|-----------|---------|
| `initNode` | Controller node (entry point) |
| `workflowFunction` | Execute a workflow function |
| `subworkflowCall` | Call another subworkflow |
| `parameterNode` | Provide parameters |
| `listParameterNode` | Provide list parameters |
| `dictParameterNode` | Provide dictionary parameters |

### 4. Store Architecture (workflowStore.js)

The store is split into focused slices:

| Slice | Responsibility |
|-------|---------------|
| `observabilitySlice` | UI state, node selection, badges |
| `subworkflowSlice` | CRUD for subworkflows |
| `nodeActionsSlice` | Node manipulation |
| `librarySlice` | Function library imports |
| `workflowIOSlice` | Load/save workflows |
| `logSlice` | Simulation logs |

## Communication Flow

```
User Action → React Component → Zustand Store → REST API → Python Engine
     ↑                                                           │
     └───────────── WebSocket/Polling (logs, status) ────────────┘
```

## Key Files for Common Tasks

| Task | Files to Edit |
|------|--------------|
| Add workflow function | `opencellcomms_engine/src/opencellcomms/workflow/functions/` |
| Modify node appearance | `opencellcomms_gui/src/components/nodes/` |
| Change parameter schema | `opencellcomms_engine/src/opencellcomms/workflow/schema.py` |
| Add store action | `opencellcomms_gui/src/store/slices/` |
| Modify cell behavior | `opencellcomms_engine/src/opencellcomms/core/cell.py` |
| Change mechanics | `opencellcomms_engine/src/opencellcomms/simulation/mechanics.py` |

