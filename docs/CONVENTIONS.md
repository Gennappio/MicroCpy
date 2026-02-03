# MicroCpy Coding Conventions

## General Principles

1. **Dual-Stack Synchronization**: When adding features, changes typically need to be made in both Python (engine) and JavaScript (GUI).
2. **v2.0 Only**: Only workflow version 2.0 is supported. No backward compatibility with v1.x.
3. **Modular Design**: Keep files focused on single responsibilities.

## Python Conventions (opencellcomms_engine/)

### File Organization

```python
# Standard import order
import standard_library
import third_party
from opencellcomms import local_imports

# Type hints encouraged
def function(param: str) -> dict:
    """Docstring with Args, Returns, Raises."""
    pass
```

### Workflow Functions

Location: `src/opencellcomms/workflow/functions/`

```python
# Each function module follows this pattern:
from ..decorators import workflow_function

@workflow_function(
    name="my_function",
    description="What it does",
    category="simulation"
)
def my_function(ctx: WorkflowContext, **kwargs) -> dict:
    """
    Execute my function.
    
    Args:
        ctx: Workflow context with cell population, microenvironment, etc.
        my_param: Description of parameter
        
    Returns:
        dict with results or empty dict
    """
    # Access context
    population = ctx.get("population")
    
    # Do work...
    
    # Return results (optional)
    return {"cells_processed": count}
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Functions | snake_case | `add_cells`, `run_simulation` |
| Classes | PascalCase | `CellPopulation`, `WorkflowExecutor` |
| Constants | UPPER_SNAKE | `DEFAULT_RADIUS`, `MAX_ITERATIONS` |
| Private | _underscore | `_internal_method` |

## JavaScript Conventions (opencellcomms_gui/)

### File Organization

```javascript
// Components: PascalCase.jsx
// Utilities: camelCase.js
// Stores: camelCase.js
```

### React Components

```jsx
// Functional components with hooks
import React, { useState, useEffect } from 'react';
import useWorkflowStore from '../store/workflowStore';

const MyComponent = ({ prop1, prop2 }) => {
  // Zustand store hooks first
  const { action } = useWorkflowStore();
  
  // Local state
  const [value, setValue] = useState(null);
  
  // Effects
  useEffect(() => {
    // ...
  }, [dependencies]);
  
  // Event handlers
  const handleClick = () => {
    // ...
  };
  
  return (
    <div>
      {/* JSX */}
    </div>
  );
};

export default MyComponent;
```

### Zustand Store Patterns

```javascript
// Slices follow this pattern
export const createMySlice = (set, get) => ({
  // State
  myState: initialValue,
  
  // Actions (use arrow functions)
  myAction: (param) => {
    set((state) => ({
      myState: newValue
    }));
  },
  
  // Async actions
  myAsyncAction: async (param) => {
    const result = await fetchSomething();
    set({ myState: result });
  },
  
  // Getters (use get())
  getMyData: () => {
    return get().myState;
  },
});
```

### Node Types

All custom nodes follow this pattern:

```jsx
// In components/nodes/MyNode.jsx
const MyNode = ({ id, data }) => {
  return (
    <div className="node-container">
      <Handle type="target" position={Position.Top} id="func-in" />
      {/* Node content */}
      <Handle type="source" position={Position.Bottom} id="func-out" />
    </div>
  );
};
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Components | PascalCase | `WorkflowCanvas`, `ParameterEditor` |
| Functions | camelCase | `handleClick`, `parseWorkflow` |
| Constants | UPPER_SNAKE | `API_BASE_URL` |
| Store actions | camelCase | `setStageNodes`, `addFunction` |

## API Conventions

### REST Endpoints

```
GET    /api/functions          # List available functions
POST   /api/workflow/run       # Execute workflow
GET    /api/results/{id}       # Get results
POST   /api/workflow/validate  # Validate workflow
```

### Response Format

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

## Git Conventions

- **Commits**: Short imperative ("Add feature" not "Added feature")
- **Branches**: `feature/`, `fix/`, `refactor/` prefixes
- **PR titles**: Match commit convention

