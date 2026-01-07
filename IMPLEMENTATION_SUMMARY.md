# Sub-workflow Implementation Summary

## Overview
Successfully implemented a comprehensive sub-workflow system for MicroCpy, transitioning from a fixed 6-stage workflow (v1.0) to a flexible, composable sub-workflow architecture (v2.0).

## Key Features Implemented

### 1. Backend Schema (schema.py)
- **SubWorkflow class**: Represents a reusable workflow component with:
  - Controller node for iteration control
  - Functions and sub-workflow calls
  - Parameters and execution order
  - Input/output parameter definitions
  - Deletable flag for user-created sub-workflows
  
- **SubWorkflowCall class**: Represents a call to another sub-workflow with:
  - Iteration count support
  - Parameter passing
  - Context mapping
  - Enable/disable functionality

- **WorkflowDefinition v2.0**: Updated to support both v1.0 (stages) and v2.0 (subworkflows) formats

### 2. Validation System
Comprehensive validation including:
- Circular dependency detection
- Naming validation (alphanumeric + underscore, starts with letter)
- Controller node requirements
- Execution order validation
- Parameter node reference validation
- Sub-workflow existence checks

### 3. Workflow Executor (executor.py)
- **Call stack tracking**: Monitors nested sub-workflow execution
- **Iteration support**: Execute sub-workflows multiple times
- **Context passing**: Share data between sub-workflows
- **Backward compatibility**: Supports both v1.0 and v2.0 workflows

### 4. GUI Components

#### WorkflowStore (workflowStore.js)
- Dynamic sub-workflow management (add, delete, rename)
- Support for both v1.0 and v2.0 formats
- Automatic loading and conversion

#### App.jsx
- Dynamic tabs for sub-workflows
- Add new sub-workflow button
- Rename and delete functionality
- Version-aware UI (shows different interfaces for v1.0 vs v2.0)

#### SubWorkflowCallNode Component
- Purple gradient design with flash (⚡) icon
- Displays sub-workflow name and iteration count
- Parameter connection support
- Enable/disable toggle

#### FunctionPalette
- New "Sub-workflows" category
- Drag-and-drop sub-workflow calls
- Dynamically populated from available sub-workflows
- Prevents circular references (can't drag current sub-workflow)

#### CallStackConsole
- Real-time call stack visualization
- Shows nested execution with depth indicators
- Iteration progress display
- Collapsible console with running indicator

### 5. Migration Utility
- **WorkflowMigrator class**: Converts v1.0 to v2.0
- **CLI tool**: `migrate_workflow.py` for batch migration
- Preserves all functions, parameters, and execution order
- Creates main sub-workflow that orchestrates standard stages

### 6. Backward Compatibility
- Loader automatically detects version
- v1.0 workflows continue to work
- Executor handles both formats seamlessly
- GUI adapts based on workflow version

## File Structure

### Backend
```
MicroCpy/microc-2.0/src/workflow/
├── schema.py          # Updated with SubWorkflow and SubWorkflowCall
├── executor.py        # Updated with call stack and sub-workflow execution
├── loader.py          # Fixed validation handling
├── migrate.py         # NEW: Migration utility
└── registry.py        # (unchanged)
```

### Frontend
```
MicroCpy/ABM_GUI/src/
├── store/
│   └── workflowStore.js              # Updated for dynamic sub-workflows
├── components/
│   ├── SubWorkflowCallNode.jsx       # NEW: Purple sub-workflow node
│   ├── SubWorkflowCallNode.css       # NEW: Styling
│   ├── CallStackConsole.jsx          # NEW: Call stack UI
│   ├── CallStackConsole.css          # NEW: Styling
│   ├── FunctionPalette.jsx           # Updated with sub-workflows section
│   └── FunctionPalette.css           # Updated styling
├── App.jsx                            # Updated with dynamic tabs
└── App.css                            # Updated with dialog and tab styles
```

### Testing & Examples
```
MicroCpy/microc-2.0/
├── examples/
│   └── test_workflow_v2.json         # NEW: Example v2.0 workflow
├── tests/
│   └── test_workflow_v2.py           # NEW: Validation tests
└── scripts/
    └── migrate_workflow.py           # NEW: CLI migration tool
```

## Usage Examples

### Creating a Sub-workflow (GUI)
1. Click "+ New Sub-workflow" button in tabs
2. Enter name (e.g., "my_custom_workflow")
3. Add functions and sub-workflow calls from palette
4. Configure controller iterations

### Calling a Sub-workflow
1. Drag sub-workflow from palette (purple with ⚡ icon)
2. Set iteration count in node settings
3. Connect parameter nodes if needed
4. Add to execution order

### Migrating v1.0 to v2.0
```bash
python scripts/migrate_workflow.py old_workflow.json new_workflow.json
```

## Testing Results
All tests pass successfully:
- ✓ Load v2.0 workflow
- ✓ Sub-workflow structure validation
- ✓ Call stack tracking initialization

## Next Steps (Future Enhancements)
1. Add sub-workflow templates library
2. Implement sub-workflow import/export
3. Add visual call stack in GUI during execution
4. Create sub-workflow marketplace/sharing
5. Add sub-workflow performance profiling

## Notes
- Main sub-workflow is required and cannot be deleted
- Sub-workflow names must be unique
- Circular dependencies are automatically detected and prevented
- Call stack depth is unlimited but monitored for performance

