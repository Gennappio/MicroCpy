# GUI Integration Guide: Workflow Stage Steps

## Overview

Each workflow stage (Intracellular, Microenvironment, Intercellular) now supports a `steps` parameter that controls how many times the stage executes per macro-step.

## Required GUI Changes

### 1. Add "Steps" Input Field to Each Stage Tab

For each of the three main stage tabs (Intracellular, Microenvironment, Intercellular), add a numeric input field:

**Field Properties:**
- **Label**: "Steps per macro-step" or simply "Steps"
- **Type**: Integer input (spinner/number field)
- **Default value**: `1`
- **Minimum value**: `1`
- **Maximum value**: (optional) `100` or unlimited
- **Tooltip/Help text**: "Number of times this stage executes per macro-step. Higher values run the stage more frequently for better accuracy or multi-scale simulations."

**Placement:**
- Place near the top of each stage tab, alongside the "Enabled" checkbox
- Suggested layout:

```
┌─────────────────────────────────────────────┐
│ ☑ Enabled                                   │
│ Steps per macro-step: [  1  ] ⓘ            │
│                                             │
│ [Rest of stage configuration below...]     │
└─────────────────────────────────────────────┘
```

### 2. JSON Schema Updates

When saving/loading workflow JSON files, ensure the `steps` field is included in each stage:

**Example JSON structure:**
```json
{
  "stages": {
    "intracellular": {
      "enabled": true,
      "steps": 3,           ← Add this field
      "parameters": [...],
      "functions": [...],
      "execution_order": [...]
    },
    "microenvironment": {
      "enabled": true,
      "steps": 5,           ← Add this field
      "parameters": [...],
      "functions": [...],
      "execution_order": [...]
    },
    "intercellular": {
      "enabled": true,
      "steps": 1,           ← Add this field
      "parameters": [...],
      "functions": [...],
      "execution_order": [...]
    }
  }
}
```

### 3. Backward Compatibility

When loading older workflow JSON files that don't have the `steps` field:
- Default to `steps: 1` for each stage
- The backend already handles this (see `WorkflowStage.from_dict()` in `src/workflow/schema.py`)

### 4. Validation

- Ensure `steps` is always >= 1
- If user enters 0 or negative value, reset to 1 and show warning

### 5. User Guidance

Consider adding:
- **Info icon (ⓘ)** next to the field with tooltip explaining the feature
- **Example presets** or suggestions:
  - "Standard (1-1-1)": All stages run once per macro-step
  - "Multi-scale (3-5-1)": Fast processes run more frequently
  - "High accuracy diffusion (1-10-1)": Diffusion runs 10 times per macro-step

## Implementation Checklist

- [ ] Add "Steps" input field to Intracellular tab
- [ ] Add "Steps" input field to Microenvironment tab
- [ ] Add "Steps" input field to Intercellular tab
- [ ] Update JSON serialization to include `steps` field
- [ ] Update JSON deserialization to read `steps` field (default to 1 if missing)
- [ ] Add validation (minimum value = 1)
- [ ] Add tooltip/help text
- [ ] Test with existing workflow files
- [ ] Test creating new workflow with custom step values
- [ ] Verify backend correctly executes stages multiple times

## Testing

Use the test workflow file: `tests/test_workflow_steps.json`

This workflow has:
- Intracellular: 3 steps
- Microenvironment: 5 steps
- Intercellular: 1 step

Run it and check the console output for:
```
[WORKFLOW] Stage 'intracellular' will execute 3 times
[WORKFLOW] Stage 'microenvironment' will execute 5 times
```

## Questions?

See `docs/WORKFLOW_STEPS.md` for more details on the feature and use cases.

