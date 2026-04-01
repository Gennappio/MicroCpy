# Creating Custom Functions for OpenCellComms

This guide explains how to create custom workflow functions that appear in the GUI and can be used in your simulations.

## Overview

Functions in OpenCellComms are Python functions decorated with `@register_function`. Once registered, they automatically appear in the GUI's function palette and can be dragged onto the workflow canvas.

## Quick Start: Minimal Function

Here's the simplest possible custom function:

```python
from typing import Dict, Any
from src.workflow.decorators import register_function

@register_function(
    display_name="My Custom Function",
    description="A simple example function",
    category="INTRACELLULAR",
)
def my_custom_function(context: Dict[str, Any], **kwargs) -> None:
    """My custom function that does something."""
    population = context.get('population')
    if population is None:
        print("[my_custom_function] No population - skipping")
        return
    
    # Your logic here
    print(f"[my_custom_function] Processing {len(population.state.cells)} cells")
```

## Function Categories

Functions must belong to one of these categories:

| Category | Purpose | When It Runs |
|----------|---------|--------------|
| `INITIALIZATION` | Setup simulation components | Once at start |
| `INTRACELLULAR` | Cell-internal processes | Each timestep |
| `DIFFUSION` | Substance diffusion | Each timestep |
| `INTERCELLULAR` | Cell-cell interactions | Each timestep |
| `FINALIZATION` | Cleanup and output | Once at end |

## The @register_function Decorator

```python
@register_function(
    display_name="Human Readable Name",     # Shown in GUI
    description="What this function does",  # Tooltip in GUI
    category="INTRACELLULAR",               # Which palette section
    parameters=[...],                       # Configurable parameters
    inputs=["context"],                     # Required inputs
    outputs=["result"],                     # What it produces
    cloneable=True                          # Can be duplicated in GUI
)
```

## Adding Parameters

Parameters appear as editable fields in the GUI when you click on a function node:

```python
@register_function(
    display_name="Custom Metabolism",
    description="Metabolism with configurable rates",
    category="INTRACELLULAR",
    parameters=[
        {
            "name": "oxygen_rate",
            "type": "FLOAT",
            "description": "Oxygen consumption rate",
            "default": 1.0,
            "min_value": 0.0,
            "max_value": 10.0
        },
        {
            "name": "enable_logging",
            "type": "BOOL",
            "description": "Enable debug logging",
            "default": False
        },
        {
            "name": "mode",
            "type": "STRING",
            "description": "Operating mode",
            "default": "normal",
            "options": ["normal", "fast", "accurate"]
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def custom_metabolism(
    context: Dict[str, Any],
    oxygen_rate: float = 1.0,
    enable_logging: bool = False,
    mode: str = "normal",
    **kwargs
) -> None:
    """Custom metabolism function."""
    if enable_logging:
        print(f"[custom_metabolism] Rate={oxygen_rate}, Mode={mode}")
    
    # Your implementation here
    pass
```

### Parameter Types

| Type | Python Type | GUI Widget |
|------|-------------|------------|
| `STRING` | `str` | Text input |
| `INT` | `int` | Number input |
| `FLOAT` | `float` | Number input |
| `BOOL` | `bool` | Checkbox |
| `FILE` | `str` | File path input |
| `DICT` | `dict` | Dict parameter node (key-value table in GUI) |
| `LIST` | `list` | List parameter node (item list in GUI) |

### Parameter Options

```python
{
    "name": "param_name",
    "type": "FLOAT",
    "description": "What this does",
    "default": 1.0,           # Default value
    "required": True,         # Is it required?
    "min_value": 0.0,         # Minimum (for numbers)
    "max_value": 100.0,       # Maximum (for numbers)
    "options": ["a", "b"]     # Dropdown choices
}
```

## The Context Object

All functions receive a `context` dictionary containing simulation state:

```python
def my_function(context: Dict[str, Any], **kwargs) -> None:
    # Core simulation objects
    population = context.get('population')      # Cell population
    config = context.get('config')              # Configuration
    simulator = context.get('simulator')        # Diffusion simulator
    gene_networks = context.get('gene_networks', {})  # Gene networks (dict keyed by cell_id)
    
    # Timing information
    dt = context.get('dt', 0.1)                 # Time step
    step = context.get('current_step', 0)        # Current step number
    macrostep = context.get('macrostep', 0)     # Current macrostep
    
    # Results and state
    results = context.get('results', {})        # Collected results
```

## File Organization

Place your functions in the appropriate directory:

```
opencellcomms_engine/src/workflow/functions/
├── initialization/      # Setup functions
├── intracellular/       # Cell-internal functions
├── diffusion/           # Diffusion functions
├── intercellular/       # Cell interaction functions
├── finalization/        # Output functions
└── your_category/       # Custom category (optional)
```

### Step-by-Step: Adding a New Function

1. **Create the file:**
   ```
   opencellcomms_engine/src/workflow/functions/intracellular/my_function.py
   ```

2. **Write the function** (see template below)

3. **Import in `__init__.py`:**
   ```python
   # In opencellcomms_engine/src/workflow/functions/intracellular/__init__.py
   from .my_function import my_function
   ```

4. **Import in registry.py** (for auto-discovery):
   ```python
   # In opencellcomms_engine/src/workflow/registry.py
   import src.workflow.functions.intracellular.my_function
   ```

5. **Restart the backend server** to see your function in the GUI

## Common Mistakes

### ❌ Mistake 1: Mismatch between `inputs` and function signature

This is the **most common error** when creating new workflow functions!

**Wrong:**
```python
@register_function(
    inputs=["population", "gene_networks"],  # ← Declares these as inputs
    ...
)
def my_func(population=None, context=None, ...):  # ❌ Missing gene_networks parameter!
    # This will fail! The executor tries to pass gene_networks as a kwarg,
    # but the function doesn't accept it, so context gets passed incorrectly.
```

**Symptom:** Function receives `context=False` or `context=None` even though context exists.

**Right (Recommended Pattern):**
```python
@register_function(
    inputs=["context"],  # ← Only declare context
    ...
)
def my_func(context=None, ...):  # ✅ Only context in signature
    # Get everything from context manually
    population = context.get('population')
    gene_networks = context.get('gene_networks', {})
```

**Why this is better:**
- Simple and explicit
- No confusion about what comes from where
- Easy to add new context items without changing signature
- Recommended in all modern functions

**Alternative (Legacy Pattern - Not Recommended):**
```python
@register_function(
    inputs=["population", "gene_networks"],  # ← Declare specific inputs
    ...
)
def my_func(
    population=None,        # ✅ MUST have matching parameters
    gene_networks=None,     # ✅ MUST have matching parameters
    context=None,
    ...
):
```

### ❌ Mistake 2: Forgetting to import in `registry.py`

Even with `@register_function`, the module must be imported so the decorator runs!

**Symptom:** "Function 'my_function' not found in custom or standard functions"

**Fix:** Add to `src/workflow/registry.py`:
```python
import src.workflow.functions.my_category.my_new_function  # ← Required!
```

### ❌ Mistake 3: Not checking if context items exist

**Wrong:**
```python
gene_networks = context['gene_networks']  # ❌ Crashes if not in context
```

**Right:**
```python
gene_networks = context.get('gene_networks', {})  # ✅ Safe with default
if not gene_networks:
    print("[ERROR] No gene networks in context")
    return False
```

### ❌ Mistake 4: Trying to access removed fields

**Wrong:**
```python
cell_gn = cell.state.gene_network  # ❌ This field was removed!
```

**Right:**
```python
gene_networks = context.get('gene_networks', {})  # ✅ Access from context
cell_gn = gene_networks.get(cell_id)
```

### ❌ Mistake 5: Forgetting `compatible_kernels`

**Wrong:**
```python
@register_function(
    display_name="...",
    inputs=["context"],
    outputs=[],
    cloneable=False
    # ❌ Missing compatible_kernels!
)
```

**Right:**
```python
@register_function(
    display_name="...",
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]  # ✅ Required!
)
```

### ✅ Validation Tools

To catch these mistakes early:

1. **Automatic validation:** The `@register_function` decorator now validates your function and will raise a clear error if there's a mismatch.

2. **Pre-commit check:** Run the validation script before committing:
   ```bash
   python scripts/validate_functions.py
   ```

3. **Claude Code slash commands:**
   - `/validate-function` — Validate a single function (import, decorator, registration)
   - `/validate-workflow` — Validate a workflow JSON (function registry, parameter node connections, dict target_param)

4. **Use the template:** Copy `src/workflow/functions/_TEMPLATE.py` as a starting point for new functions.

## Complete Function Template

```python
"""
My Custom Function

Description of what this function does and when to use it.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="My Custom Function",
    description="Detailed description for the GUI tooltip",
    category="INTRACELLULAR",  # or INITIALIZATION, DIFFUSION, etc.
    parameters=[
        {
            "name": "threshold",
            "type": "FLOAT",
            "description": "Threshold value for processing",
            "default": 0.5,
            "min_value": 0.0,
            "max_value": 1.0
        },
        {
            "name": "enabled",
            "type": "BOOL",
            "description": "Enable this feature",
            "default": True
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def my_custom_function(
    context: Dict[str, Any],
    threshold: float = 0.5,
    enabled: bool = True,
    **kwargs
) -> None:
    """
    My custom function implementation.
    
    Args:
        context: Workflow execution context
        threshold: Threshold for processing
        enabled: Whether feature is enabled
        **kwargs: Additional parameters (ignored)
    
    Returns:
        None (modifies context/population in-place)
    """
    # =================================================================
    # EXTRACT CONTEXT
    # =================================================================
    population = context.get('population')
    config = context.get('config')
    
    # =================================================================
    # VALIDATE
    # =================================================================
    if population is None:
        print("[my_custom_function] No population - skipping")
        return
    
    if not enabled:
        print("[my_custom_function] Disabled - skipping")
        return
    
    # =================================================================
    # MAIN LOGIC
    # =================================================================
    for cell_id, cell in population.state.cells.items():
        # Process each cell
        # ...
        pass
    
    print(f"[my_custom_function] Processed {len(population.state.cells)} cells")
```

