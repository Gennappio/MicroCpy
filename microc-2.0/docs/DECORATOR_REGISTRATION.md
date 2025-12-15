# Decorator-Based Function Registration System

## Overview

The MicroCpy workflow system now supports **decorator-based function registration**, allowing you to define and register workflow functions in the same place using Python decorators. This eliminates the need for manual registration in `registry.py` and makes the codebase more maintainable.

## Key Features

- ✅ **Auto-extraction** of function name, module path, and source file
- ✅ **Auto-detection** of input parameters from function signature
- ✅ **Parameter type inference** from default values (FLOAT, INT, BOOL, STRING, LIST, DICT)
- ✅ **Backward compatibility** - existing manual registrations still work
- ✅ **Precedence** - decorator registrations override manual ones if there's a conflict
- ✅ **Full metadata support** - all FunctionMetadata fields are supported

## Basic Usage

### Simple Example

```python
from src.workflow.decorators import register_function

@register_function(
    display_name="Advanced Metabolism",
    description="Sophisticated metabolism model with pH effects",
    category="INTRACELLULAR",
    parameters=[
        {"name": "ph_sensitivity", "type": "FLOAT", "default": 0.1},
        {"name": "temperature_effect", "type": "FLOAT", "default": 1.0}
    ]
)
def advanced_metabolism(context, ph_sensitivity=0.1, temperature_effect=1.0, **kwargs):
    """Function implementation"""
    # Your code here
    return {"oxygen_consumption": -1.0e-16 * temperature_effect}
```

### What Gets Auto-Extracted

The decorator automatically extracts:

1. **Function name**: `advanced_metabolism`
2. **Module path**: `jayatilake_experiment_cell_functions` (from `func.__module__`)
3. **Source file**: `tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py` (from `inspect.getfile()`)
4. **Input parameters**: `["context", "ph_sensitivity", "temperature_effect"]` (from function signature, excluding `**kwargs`)

## Decorator Parameters

### Required Parameters

- **`display_name`** (str): Human-readable name shown in the GUI
- **`description`** (str): Description of what the function does
- **`category`** (str or FunctionCategory): Function category

### Optional Parameters

- **`parameters`** (List[Dict]): Parameter definitions (auto-inferred if not provided)
- **`inputs`** (List[str]): Input parameter names (auto-detected from signature if not provided)
- **`outputs`** (List[str]): Output names (default: `[]`)
- **`cloneable`** (bool): Whether function can be cloned in GUI (default: `False`)

## Parameter Definitions

### Full Parameter Specification

```python
parameters=[
    {
        "name": "atp_threshold",
        "type": "FLOAT",  # FLOAT, INT, BOOL, STRING, LIST, DICT
        "description": "ATP threshold for division",
        "default": 0.8,
        "required": False,  # Optional, inferred from default value
        "min_value": 0.0,   # Optional
        "max_value": 1.0,   # Optional
        "options": None     # Optional, for enum-like parameters
    }
]
```

### Parameter Type Inference

If you don't specify parameter types, they're inferred from default values:

```python
# These parameters will be auto-inferred:
def my_function(context, 
                count=10,           # → INT
                rate=0.5,           # → FLOAT
                enabled=True,       # → BOOL
                name="default",     # → STRING
                items=[],           # → LIST
                config={},          # → DICT
                **kwargs):
    pass
```

## Categories

Available categories (case-insensitive):

- `INITIALIZATION` - Setup and initialization functions
- `INTRACELLULAR` - Cell-level processes
- `DIFFUSION` (or `MICROENVIRONMENT`) - Diffusion and microenvironment
- `INTERCELLULAR` - Cell-cell interactions
- `FINALIZATION` - Cleanup and reporting
- `UTILITY` - Helper functions

## Complete Examples

### Example 1: Intracellular Function

```python
@register_function(
    display_name="Custom Division Check",
    description="Check if cell should divide based on ATP and age",
    category="INTRACELLULAR",
    parameters=[
        {
            "name": "atp_threshold",
            "type": "FLOAT",
            "description": "ATP threshold for division (0-1)",
            "default": 0.8,
            "min_value": 0.0,
            "max_value": 1.0
        },
        {
            "name": "min_cell_age",
            "type": "FLOAT",
            "description": "Minimum cell age for division (hours)",
            "default": 24.0,
            "min_value": 0.0
        }
    ],
    outputs=["can_divide"],
    cloneable=True
)
def custom_division_check(context, atp_threshold=0.8, min_cell_age=24.0, **kwargs):
    cell_state = context.get('cell_state', {})
    atp_rate = cell_state.get('metabolic_state', {}).get('atp_rate', 0.0)
    cell_age = cell_state.get('age', 0.0)
    
    return (atp_rate > atp_threshold) and (cell_age > min_cell_age)
```

### Example 2: Initialization Function

```python
@register_function(
    display_name="Initialize Custom Cells",
    description="Initialize cells with custom placement pattern",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "num_cells",
            "type": "INT",
            "description": "Number of cells to initialize",
            "default": 50,
            "min_value": 1,
            "max_value": 10000
        },
        {
            "name": "placement_pattern",
            "type": "STRING",
            "description": "Cell placement pattern",
            "default": "spheroid",
            "options": ["spheroid", "grid", "random", "cluster"]
        },
        {
            "name": "initial_atp",
            "type": "FLOAT",
            "description": "Initial ATP level",
            "default": 0.5,
            "min_value": 0.0,
            "max_value": 1.0
        }
    ],
    outputs=["population"],
    cloneable=True
)
def initialize_custom_cells(context, num_cells=50, placement_pattern="spheroid",
                           initial_atp=0.5, **kwargs):
    # Implementation
    pass
```

## How It Works

### 1. Decorator Execution

When Python imports a module containing decorated functions, the decorators execute immediately:

```python
# When this module is imported:
import jayatilake_experiment_cell_functions

# The @register_function decorators execute and register functions
# in the global decorator registry
```

### 2. Registry Merging

The `get_default_registry()` function merges manual and decorator registrations:

```python
def get_default_registry() -> FunctionRegistry:
    registry = FunctionRegistry()

    # Add manual registrations
    registry.register(FunctionMetadata(...))

    # Merge with decorator registrations (decorator takes precedence)
    from src.workflow.decorators import get_decorator_registry, merge_registries
    decorator_registry = get_decorator_registry()
    registry = merge_registries(registry, decorator_registry)

    return registry
```

### 3. Function Execution

Decorated functions work exactly like normal functions:

```python
# Call the function normally
result = advanced_metabolism_decorated(
    context={},
    ph_sensitivity=0.2,
    temperature_effect=1.5
)
```

## Migration Guide

### Converting Manual Registrations to Decorators

**Before (Manual Registration in registry.py):**

```python
# In registry.py
registry.register(FunctionMetadata(
    name="calculate_cell_metabolism",
    display_name="Calculate Cell Metabolism",
    description="Calculate substance consumption/production",
    category=FunctionCategory.INTRACELLULAR,
    parameters=[
        ParameterDefinition(
            name="oxygen_vmax",
            type=ParameterType.FLOAT,
            description="Maximum oxygen consumption rate",
            default=1.0e-16
        )
    ],
    inputs=["local_environment", "cell_state", "config"],
    outputs=["substance_reactions"],
    cloneable=True,
    module_path="jayatilake_experiment_cell_functions"
))

# In jayatilake_experiment_cell_functions.py
def calculate_cell_metabolism(local_environment, cell_state, config, oxygen_vmax=1.0e-16):
    # Implementation
    pass
```

**After (Decorator-Based):**

```python
# In jayatilake_experiment_cell_functions.py
from src.workflow.decorators import register_function

@register_function(
    display_name="Calculate Cell Metabolism",
    description="Calculate substance consumption/production",
    category="INTRACELLULAR",
    parameters=[
        {
            "name": "oxygen_vmax",
            "type": "FLOAT",
            "description": "Maximum oxygen consumption rate",
            "default": 1.0e-16
        }
    ],
    outputs=["substance_reactions"],
    cloneable=True
)
def calculate_cell_metabolism(local_environment, cell_state, config, oxygen_vmax=1.0e-16):
    # Implementation
    pass
```

## Best Practices

### 1. Use Decorators for New Functions

For new functions, always use the decorator approach:

```python
@register_function(
    display_name="My New Function",
    description="Does something cool",
    category="INTRACELLULAR"
)
def my_new_function(context, **kwargs):
    pass
```

### 2. Keep Manual Registrations for Stability

Existing manual registrations can stay as-is for backward compatibility. Migrate them gradually.

### 3. Always Include `context` Parameter

Workflow functions should always accept a `context` parameter:

```python
def my_function(context, param1=0.5, **kwargs):
    # Access context data
    population = context.get('population')
    config = context.get('config')
```

### 4. Use `**kwargs` for Forward Compatibility

Always include `**kwargs` to handle additional parameters:

```python
def my_function(context, my_param=1.0, **kwargs):
    # kwargs absorbs any extra parameters
    pass
```

## Testing

Run the decorator registration test:

```bash
cd MicroCpy/microc-2.0
python tests/test_decorator_registration.py
```

Expected output:
```
✅ Decorator module imported successfully
✅ Module imported successfully
   Decorator registry now has 3 functions
✅ Full registry has 63 total functions
✅ advanced_metabolism_decorated found in full registry
✅ Function called successfully
```

## Troubleshooting

### Functions Not Appearing in Registry

**Problem**: Decorated functions don't appear in the registry.

**Solution**: Make sure the module containing decorated functions is imported:

```python
# In src/workflow/standard_functions.py or wherever you initialize
import jayatilake_experiment_cell_functions  # This triggers decorator execution
```

### Import Errors

**Problem**: `ImportError: No module named 'src'`

**Solution**: Ensure the microc-2.0 root is in `sys.path`:

```python
import sys
import os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)
```

### Parameter Type Mismatch

**Problem**: Parameter types are wrong in the GUI.

**Solution**: Explicitly specify parameter types in the decorator:

```python
parameters=[
    {"name": "my_param", "type": "FLOAT", "default": 1.0}  # Explicit type
]
```

## API Reference

### `@register_function()`

Decorator for registering workflow functions.

**Parameters:**
- `display_name` (str, required): Human-readable name
- `description` (str, required): Function description
- `category` (str|FunctionCategory, required): Function category
- `parameters` (List[Dict], optional): Parameter definitions
- `inputs` (List[str], optional): Input parameter names
- `outputs` (List[str], optional): Output names
- `cloneable` (bool, optional): Whether function can be cloned

**Returns:** Decorated function with `_workflow_metadata` attribute

### `get_decorator_registry()`

Get the global decorator-based registry.

**Returns:** `FunctionRegistry` containing all decorator-based registrations

### `merge_registries(manual_registry, decorator_registry)`

Merge manual and decorator-based registries.

**Parameters:**
- `manual_registry` (FunctionRegistry): Registry with manual registrations
- `decorator_registry` (FunctionRegistry): Registry with decorator registrations

**Returns:** Merged `FunctionRegistry` (decorator registrations take precedence)

## Summary

The decorator-based registration system provides:

1. **Cleaner code** - Function definition and registration in one place
2. **Auto-extraction** - Less manual work, fewer errors
3. **Backward compatibility** - Works alongside existing manual registrations
4. **Type safety** - Parameter type inference and validation
5. **Maintainability** - Easier to add, modify, and remove functions

Start using decorators for all new workflow functions!

