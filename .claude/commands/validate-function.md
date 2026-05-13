# /validate-function — Validate an OpenCellComms simulation function

You are helping a biologist verify that a function is correctly set up: importable, properly decorated, and registered so the GUI can find it. This catches the most common mistakes that make functions invisible in the workflow designer.

## Step 1 — Identify the function

Ask the user: **Which function do you want to validate?** They can give you:
- A function name (e.g., `mark_necrotic_cells`)
- A file path (e.g., `opencellcomms_adapters/jayatilake/functions/intercellular/mark_necrotic_cells.py`)

If they give a name, search for the file by looking in:
1. `opencellcomms_engine/src/workflow/functions/` (engine functions)
2. `opencellcomms_adapters/*/functions/` (adapter functions)
3. `opencellcomms_engine/src/workflow/standard_functions.py` (legacy functions)

## Step 2 — Check 1: File exists and imports successfully

Read the function file. Then test the import by running:

```bash
cd opencellcomms_engine && python -c "
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from <module_path> import <function_name>
print('OK: Function imports successfully')
"
```

Where `<module_path>` is the dotted module path (e.g., `opencellcomms_adapters.jayatilake.functions.intercellular.mark_necrotic_cells`).

- **[FAIL]** if the file doesn't exist or import fails. Show the full error.
- **[PASS]** if it imports cleanly.

## Step 3 — Check 2: @register_function decorator

Read the function file and find the `@register_function(...)` decorator. Verify:

1. **`category`** is one of: `INITIALIZATION`, `INTRACELLULAR`, `DIFFUSION`, `INTERCELLULAR`, `FINALIZATION`
   - **[FAIL]** if missing or invalid category
2. **`parameters`** list (if present) — each entry has `name`, `type`, and `default`
   - **[WARN]** if entries are missing fields
   - **[WARN]** if type is not one of: `STRING`, `INT`, `FLOAT`, `BOOL`, `FILE`, `DICT`, `LIST`
3. **`inputs`** includes `"context"` (or is `["context"]`)
   - **[WARN]** if using legacy input pattern (e.g., `inputs=["population", "gene_networks"]`)
4. **`compatible_kernels`** is set (e.g., `["biophysics"]`)
   - **[WARN]** if missing

## Step 4 — Check 3: Function signature matches decorator

Compare the function's Python signature against the decorator's `parameters` list:
- Every parameter name in the decorator must appear as a keyword argument in the function signature
- The function must accept `**kwargs`

- **[FAIL]** if a declared parameter is missing from the signature
- **[WARN]** if function has extra parameters not declared in the decorator (may be intentional)

## Step 5 — Check 4: Function is registered

Check that the function is imported in the correct registration file:

**For engine functions** (`opencellcomms_engine/src/workflow/functions/*/`):
1. Read the category's `__init__.py` — check for `from .<function_name> import <function_name>`
2. Read `opencellcomms_engine/src/workflow/registry.py` — check for `import src.workflow.functions.<category>.<function_name>` inside `get_default_registry()`

**For adapter functions** (`opencellcomms_adapters/*/functions/*/`):
1. Read the adapter's `register.py` (e.g., `opencellcomms_adapters/jayatilake/register.py`) — check for the import

- **[FAIL]** if the function is not imported anywhere — it will never appear in the GUI
- Suggest the exact import line to add and which file to add it to

## Step 6 — Check 5: Workflow compatibility (optional)

If the user provides a workflow JSON file (or you can ask: "Do you want me to also check this function against a specific workflow?"):

1. Find all nodes in the workflow that use this function
2. Check parameter node connections (same logic as `/validate-workflow` checks 3-6 but scoped to this function)
3. Report any parameter mismatches

## Step 7 — Present results

Format as a checklist:

```
Validating: mark_necrotic_cells
File: opencellcomms_adapters/jayatilake/functions/intercellular/mark_necrotic_cells.py

[PASS] Import — Function imports successfully
[PASS] Decorator — Valid category (INTERCELLULAR), 1 DICT parameter, inputs=["context"]
[PASS] Signature — All declared parameters present in function signature
[PASS] Registration — Imported in opencellcomms_adapters/jayatilake/register.py
[PASS] Workflow — Parameter nodes connect correctly in v7_microc_workflow.json

Result: Function is valid and ready to use.
```

For failures, always explain:
- What is wrong (plain English)
- How to fix it (with the exact code/line to add)
