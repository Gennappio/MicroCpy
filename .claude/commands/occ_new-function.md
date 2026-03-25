# /occ_new-function — Scaffold a new OpenCellComms simulation function

You are helping a biologist add a new biological rule to the OpenCellComms simulation. They may not know Python, decorators, or the project architecture. Your job is to gather their intent in plain English and produce a complete, correctly placed, working function.

## Step 1 — Ask questions (ask all at once in a single message)

Ask the user:

1. **What biological event does this function model?**
   Give examples: "kill cells if oxygen drops below a threshold", "activate a gene when glucose is low", "count how many cells have died this step", "make cells divide when the proliferation gene is ON"

2. **Which workflow will this function be used in?**
   Ask the user to provide a path to the target workflow JSON (e.g., `opencellcomms_adapters/jayatilake/workflows/v7_microc_workflow.json`), or describe their experiment so you can find the right workflow file.

3. **What parameters should a scientist be able to configure from the GUI?**
   Give examples: "oxygen threshold (default 0.022)", "glucose threshold (default 0.23)", "require both conditions (yes/no)", "output file name"
   If they don't know, suggest sensible defaults based on the biological event described.

## Step 2 — Read the workflow and identify placement

Once you have a workflow path:

1. **Read the target workflow JSON** and extract all subworkflow names and their existing function nodes.
2. **Present the subworkflows** to the user in a clear list, showing which functions each one currently contains. For example:
   ```
   This workflow has these subworkflows:
   - Setup_simulation: [setup_domain, setup_time]
   - microenvironment: [run_diffusion_solver_coupled]
   - intracellular: [apply_associations_to_inputs, propagate_gene_networks_netlogo]
   - intercellular: [mark_necrotic, mark_proliferating, cell_division]
   - ...
   ```
3. **Ask**: "Which subworkflow should your function run in?"
4. If the user is unsure, suggest the most appropriate subworkflow based on the biological event they described and the existing workflow structure.

## Step 3 — Map their answers to code

### Choose the category

Inspect what `category` values existing functions in the target subworkflow use (read their source files or decorator), and suggest the same category. Common categories:

| Category | Typical use |
|---|---|
| `"INITIALIZATION"` | Functions that set up initial conditions (run once) |
| `"INTRACELLULAR"` | Per-cell logic each step (gene updates, metabolism) |
| `"INTERCELLULAR"` | Cell-to-cell logic each step (division, death, migration) |
| `"DIFFUSION"` | Chemical gradient solvers |
| `"GENE_NETWORK"` | Gene network operations |
| `"OUTPUT"` | Logging, plotting, data export |
| `"FINALIZATION"` | End-of-simulation summaries |
| `"UTILITY"` | General-purpose helpers |

If the subworkflow contains functions from multiple categories, or none of the above fit, use your judgment or ask the user.

### Identify context keys available

Read the target workflow JSON and the existing functions in the chosen subworkflow to understand what `context` keys are available at that point in execution. Common patterns:

- `context['population']` — cell population (available after population setup)
- `context['simulator']` — diffusion simulator (available after substance setup)
- `context['gene_networks']` — gene network dict keyed by cell ID (available after gene network init)
- `context['associations']` — substance→gene mappings (available after association setup)
- `context['current_step']`, `context['dt']` — simulation time info
- `context['results']` — dict for storing outputs

**Important:** Not all workflows have all of these keys. Check what the workflow's initialization subworkflows actually set up. If unsure, read the initialization functions to see what they write to context.

### Derive a snake_case function name from the biological description
Examples: `mark_hypoxic_cells`, `apply_glucose_gene_input`, `count_dead_cells`, `trigger_proliferation_from_gene`

## Step 4 — Generate the Python file

Generate the complete file. Use this exact structure (from `_TEMPLATE.py`):

```python
"""
<FunctionDisplayName> - <one-line biological description>

<2–3 sentence explanation of what this rule models biologically and when it should be used.>
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="<Human-readable name for the GUI>",
    description="<One sentence description shown in GUI tooltip>",
    category="<CATEGORY>",
    parameters=[
        # One entry per configurable parameter the biologist requested
        {
            "name": "<param_name>",
            "type": "<INT|FLOAT|BOOL|STRING|DICT>",
            "description": "<what this parameter controls>",
            "default": <default_value>,
            # Include min_value/max_value for numeric params
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def <function_name>(
    context: Dict[str, Any] = None,
    <param_name>: <type> = <default>,
    **kwargs
) -> bool:
    """
    <Function description>

    Expects in context:
    - population: cell population
    - <list other required context keys>
    """

    if not context:
        print("[ERROR] [<function_name>] No context provided")
        return False

    population = context.get('population')
    if population is None:
        print("[ERROR] [<function_name>] No population in context")
        return False

    # <biological logic here>

    return True
```

**Important rules:**
- `compatible_kernels=["biophysics"]` is always required
- Always validate `context` and `population` at the top
- Print errors with `[ERROR] [function_name]` format
- Return `True` on success, `False` on error
- If the parameter set is complex (3+ related params), use a single `"type": "DICT"` parameter instead of many separate parameters
- Add a print statement at the end: `print(f"[<FUNCTION_NAME>] Processed {count} cells")` if iterating over cells

## Step 5 — Place the file and register it

After showing the user the generated code and getting their approval (or if they say "go ahead"):

**For generic (reusable) functions:**

1. **Write the file** to:
   `opencellcomms_engine/src/workflow/functions/<category>/<function_name>.py`

2. **Add the import** to the category's `__init__.py`:
   `opencellcomms_engine/src/workflow/functions/<category>/__init__.py`
   Add: `from .<function_name> import <function_name>`
   Add `'<function_name>'` to `__all__`

3. **Add the import** to the registry:
   `opencellcomms_engine/src/workflow/registry.py`
   Inside `get_default_registry()`, after the block of similar category imports, add:
   `import src.workflow.functions.<category>.<function_name>`

**For experiment-specific functions** (hardcoded gene names, thresholds, model-specific logic):

1. **Write the file** to:
   `opencellcomms_adapters/<experiment>/functions/<category>/<function_name>.py`

2. **Add the import** to the adapter's register module:
   `opencellcomms_adapters/<experiment>/register.py`
   Add: `from opencellcomms_adapters.<experiment>.functions.<category>.<function_name> import <function_name>`

4. **Tell the user** the function is ready and give them two next steps:
   - To add it to a workflow: type `/add-to-workflow`
   - To verify registration: run from `opencellcomms_engine/`:
     ```bash
     python -c "from src.workflow.registry import get_default_registry; r = get_default_registry(); print([f.name for f in r.list_all() if '<function_name>' in f.name])"
     ```

## Step 6 — Optionally add to a workflow JSON

If the user wants to add the function to the target workflow JSON right away, use the subworkflow they already chose in Step 2. Read the workflow JSON, find the correct subworkflow's `"nodes"` array, and insert the new node. Use `/add-to-workflow` logic for the insertion.
