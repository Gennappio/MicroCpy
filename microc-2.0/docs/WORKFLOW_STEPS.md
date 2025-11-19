# Workflow Stage Steps

## Overview

Each workflow stage (intracellular, microenvironment, intercellular) can now specify how many times it should execute per macro-step using the `steps` parameter.

## Usage

In your workflow JSON file, add a `steps` field to any stage:

```json
{
  "stages": {
    "intracellular": {
      "enabled": true,
      "steps": 3,
      "parameters": [...],
      "functions": [...],
      "execution_order": [...]
    },
    "microenvironment": {
      "enabled": true,
      "steps": 5,
      "parameters": [...],
      "functions": [...],
      "execution_order": [...]
    },
    "intercellular": {
      "enabled": true,
      "steps": 1,
      "parameters": [...],
      "functions": [...],
      "execution_order": [...]
    }
  }
}
```

## Behavior

With the configuration above, at each macro-step:
- **Intracellular** functions will run **3 times**
- **Microenvironment** functions will run **5 times**
- **Intercellular** functions will run **1 time**

## Default Value

If `steps` is not specified, it defaults to `1` (execute once per macro-step).

## Example

See `tests/test_workflow_steps.json` for a complete example.

## Use Cases

This feature is useful for:
- **Multi-scale simulations**: Run fast processes (e.g., intracellular metabolism) more frequently than slow processes (e.g., cell division)
- **Numerical stability**: Run diffusion solver multiple times per macro-step for better accuracy
- **Performance tuning**: Balance computational cost vs. accuracy by adjusting step counts

## GUI Integration

In the GUI, each stage tab should have a **"Steps"** input field where users can set the number of times that stage executes per macro-step.

### Recommended UI Layout

For each stage tab (Intracellular, Microenvironment, Intercellular):

```
┌─────────────────────────────────────┐
│ Stage: Intracellular                │
├─────────────────────────────────────┤
│ Enabled: [✓]                        │
│ Steps per macro-step: [3]           │  ← New input field
│                                     │
│ [Functions and parameters below...] │
└─────────────────────────────────────┘
```

The "Steps" field should:
- Be a numeric input (integer)
- Default to `1`
- Minimum value: `1`
- Have a tooltip: "Number of times this stage executes per macro-step"

