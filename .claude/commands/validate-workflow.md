# /validate-workflow — Validate an OpenCellComms workflow JSON

You are helping a biologist verify that their workflow JSON is correctly configured before running a simulation. You will check that all functions exist, parameter nodes connect properly, and there are no common mistakes that cause silent failures in the GUI.

## Step 1 — Identify the workflow file

Ask the user: **Which workflow JSON file should I validate?**

Default: `opencellcomms_adapters/jayatilake/workflows/v7_microc_workflow.json`

## Step 2 — Run the function validation script

Run from the `opencellcomms_engine/` directory:

```bash
cd opencellcomms_engine && python scripts/validate_functions.py
```

This checks that all functions register correctly (including adapter functions) and catches missing `compatible_kernels`, legacy input patterns, and parameter type issues.

If this script reports adapter import failures, flag it immediately — it means adapter functions (like mark_necrotic_cells, mark_apoptotic_cells, etc.) are invisible to the system. The likely fix is adding the parent directory to `sys.path`.

## Step 3 — Collect the function registry

Read `opencellcomms_engine/src/workflow/registry.py` to find all function imports inside `get_default_registry()`. Then read any adapter register files (e.g., `opencellcomms_adapters/jayatilake/register.py`) to find adapter function imports. Build a complete list of registered function names.

## Step 4 — Read the workflow JSON and run checks

Read the workflow JSON file. For each subworkflow, inspect the `"nodes"` array and `"parameters"` array.

### Check 1: Function registry (CRITICAL)

For each function node, check that its `function_name` (or `function` under `data`) exists in the list of registered functions from Step 3.

- **[FAIL]** if a function name is not found in the registry. This means the function will not execute.
- Suggest: check the function file exists, check it has `@register_function`, check it is imported in `registry.py` or `register.py`.

### Check 2: Parameter node references

For each function node that has a `parameter_nodes` array, verify that every ID in that array exists in the subworkflow's `parameters` array.

- **[FAIL]** if a parameter node ID is referenced but does not exist.

### Check 3: dictParameterNode target_param

For each `dictParameterNode` in the subworkflow's `parameters` array:
1. Find which function nodes reference it (via their `parameter_nodes` array)
2. Read that function's `@register_function` decorator to check if it declares a parameter with `"type": "DICT"`
3. If yes, check that the dictParameterNode has a `target_param` field matching the function's DICT parameter name

- **[WARN]** if `target_param` is missing on a dictParameterNode connected to a function expecting a DICT parameter. Without it, the dict entries get expanded as individual kwargs instead of being packaged into one dict, and the function won't receive the parameter it expects.
- Suggest: add `"target_param": "<param_name>"` to the dictParameterNode.

### Check 4: listParameterNode target_param

Same logic as Check 3 but for `listParameterNode` entries connected to functions expecting a LIST parameter.

### Check 5: Duplicate parameter_nodes entries

For each function node, check if the same parameter node ID appears more than once in its `parameter_nodes` array.

- **[WARN]** if duplicates found. This wastes processing and may cause unexpected overwrites.

### Check 6: Parameter name matching

For each function node with connected parameter nodes:
1. Determine what parameter names the nodes will produce at merge time:
   - Regular `parameterNode`: the keys in its `parameters` object
   - `dictParameterNode` with `target_param`: the `target_param` value
   - `dictParameterNode` without `target_param`: the `key` values from its `entries`
   - `listParameterNode`: its `target_param` value (or `"substances"` if missing)
2. Read the function's `@register_function` decorator to get declared parameter names
3. Check that produced names match declared names

- **[WARN]** if parameter names don't match — the function won't receive the values.

## Step 5 — Present results

Format results as a clear checklist. For each check:

```
[PASS] Function registry — All 12 functions found in registry
[FAIL] Parameter node references — "param_foo" referenced by mark_necrotic but not found in Intercellular parameters
[WARN] dictParameterNode target_param — "param_necrosis_params" missing target_param (function expects DICT "necrosis_params")
```

For failures, always include:
- What is wrong (plain English)
- Which file and which node/parameter
- How to fix it

If everything passes: **"Your workflow is valid and ready to run."**

## Common issues this catches

1. **Functions not recognized after refactoring** — sys.path missing, adapter import silently fails
2. **Parameter nodes not connecting in GUI** — missing target_param on dictParameterNode
3. **Function name typo in workflow JSON** — function_name doesn't match any registered function
4. **Dangling parameter references** — parameter_nodes references a node ID that was removed
