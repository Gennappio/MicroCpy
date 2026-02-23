# Store Simulation Dimensions Function

## Overview

The `store_simulation_dimensions` function stores the simulation dimensions (2D or 3D) in the workflow context for easy access by other workflow functions.

## Function Details

- **Name**: `store_simulation_dimensions`
- **Display Name**: "Store Simulation Dimensions"
- **Category**: INITIALIZATION
- **Module**: `src.workflow.functions.initialization.store_simulation_dimensions`

## Purpose

This function reads the dimensions from `config.domain.dimensions` (which is set by the "Setup Domain" function) and stores it in `context['dimensions']`. This makes it easy for other workflow functions to check whether the simulation is 2D or 3D without having to access the config object.

## Usage

### In the GUI Workflow

1. Add the "Setup Domain" function first (this sets `config.domain.dimensions`)
2. Add the "Store Simulation Dimensions" function after it
3. The function will automatically read the dimensions and store them in the context

### Parameters

This function has no parameters - it automatically reads from the config.

### Inputs

- `context` (required): Must contain a `config` object with `domain.dimensions` attribute

### Outputs

- `dimensions`: Stores the simulation dimensions (2 or 3) in `context['dimensions']`

## Example Workflow

```
1. Setup Simulation
2. Setup Domain (dimensions=2)
3. Store Simulation Dimensions  ← This function
4. Setup Population
5. ... other functions can now access context['dimensions']
```

## Accessing the Stored Dimensions

Other workflow functions can access the dimensions like this:

```python
def my_custom_function(context: Dict[str, Any], **kwargs) -> bool:
    dimensions = context.get('dimensions')
    
    if dimensions == 2:
        print("Running in 2D mode")
        # 2D-specific logic
    elif dimensions == 3:
        print("Running in 3D mode")
        # 3D-specific logic
    else:
        print("Dimensions not set - run store_simulation_dimensions first")
        return False
    
    return True
```

## Error Handling

The function will return `False` and print an error message if:
- The context doesn't contain a `config` object
- The config doesn't have a `domain.dimensions` attribute
- The dimensions value is not 2 or 3

## Notes

- This function should be called after "Setup Domain" but before any functions that need to know the simulation dimensions
- The dimensions are also available via `config.domain.dimensions`, but storing them in the context makes them easier to access
- This is a non-cloneable function (there's only one way to store dimensions)

