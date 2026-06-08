# /new-function — Scaffold a new OpenCellComms simulation function

You are helping a biologist add a new biological rule to the OpenCellComms simulation. They may not know Python, decorators, or the project architecture. Your job is to gather their intent in plain English and produce a complete, correctly placed, working function.

## Step 1 — Ask three questions (ask all at once in a single message)

Ask the user:

1. **What biological event does this function model?**
   Give examples: "kill cells if oxygen drops below a threshold", "activate a gene when glucose is low", "count how many cells have died this step", "make cells divide when the proliferation gene is ON"

2. **When in the simulation should it run?**
   - **Initialization** — once at the start (set up initial conditions)
   - **Intracellular** — every step, inside each cell (gene updates, metabolism)
   - **Intercellular** — every step, between cells (division, death, migration)
   - **Diffusion** — every step, chemical gradients (rarely needed — diffusion is usually handled automatically)
   - **Finalization** — once at the end (plots, exports, summaries)

3. **What parameters should a scientist be able to configure from the GUI?**
   Give examples: "oxygen threshold (default 0.022)", "glucose threshold (default 0.23)", "require both conditions (yes/no)", "output file name"
   If they don't know, suggest sensible defaults based on the biological event described.

## Step 2 — Map their answers to code

Once you have answers:

### Choose the category
| Stage answer | `category` in decorator |
|---|---|
| Initialization | `"INITIALIZATION"` |
| Intracellular | `"INTRACELLULAR"` |
| Intercellular | `"INTERCELLULAR"` |
| Diffusion | `"DIFFUSION"` |
| Finalization | `"FINALIZATION"` |

### Identify what the function needs (typed `env: BiologicalContext` API)
Biological functions take a typed `env`, **not** the raw `context` dict. Use this reference:
- Loop over cells → `for cell in env.cells:`
- Cell position → `x, y = cell.position[0], cell.position[1]` (add `z = cell.position[2]` for 3D)
- Substance concentration at a cell → `env.concentration('substance_name', cell)`
- Mark cell phenotype → `cell.mark_necrotic()` / `cell.mark_apoptotic()` / `cell.mark_proliferating()` / `cell.mark_growth_arrested()` / `cell.mark_quiescent()`
- Read a gene → `gene = cell.gene('GeneName')` then `gene.is_on()` / `gene.turn_on()` / `gene.turn_off()`
- Cell gene-state snapshot → `cell.gene_states` (dict)
- Current step / time step → `env.step` / `env.dt`
- Config object → `env.config`
- Store a result → `env.results.store('key', value)`; record a GUI change → `env.results.record_change('category', {...})`
- Escape hatch (rare) → `env.raw_context` — the underlying dict; "you are leaving the typed zone"

### Declare what the kernel must provide (`requires`)
List the capability tokens the function reads, so a mismatched kernel fails loudly at load time:
- iterates `env.cells` → `"population"`
- reads `env.concentration(...)` → `"simulator"`
- reads/writes cell gene networks → `"gene_networks"`

### Derive a snake_case function name from the biological description
Examples: `mark_hypoxic_cells`, `apply_glucose_gene_input`, `count_dead_cells`, `trigger_proliferation_from_gene`

## Step 3 — Generate the Python file

Generate the complete file. Use this exact structure (from `_TEMPLATE.py`):

```python
"""
<FunctionDisplayName> - <one-line biological description>

<2–3 sentence explanation of what this rule models biologically and when it should be used.>
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


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
    compatible_kernels=["biophysics"],
    requires=[<capability tokens, e.g. "population", "simulator">],
)
def <function_name>(
    env: BiologicalContext,
    <param_name>: <type> = <default>,
    **kwargs
) -> bool:
    """
    <Function description>
    """
    count = 0
    for cell in env.cells:
        # <biological logic, e.g.:>
        # if env.concentration('oxygen', cell) < <param_name>:
        #     cell.mark_necrotic()
        count += 1

    print(f"[<FUNCTION_NAME>] Processed {count} cells")
    return True
```

**Important rules:**
- Type the first argument as `env: BiologicalContext` and declare `requires=[...]` with the capability tokens the function reads. The typed views fail loudly if the kernel doesn't provide them, so you do **not** need manual `None`-checks for population/simulator.
- `compatible_kernels=["biophysics"]` is always required
- Mutate phenotypes through methods (`cell.mark_necrotic()`), never by assigning strings
- Return `True` on success, `False` on error
- If the parameter set is complex (3+ related params), use a single `"type": "DICT"` parameter instead of many separate parameters
- Add a print statement at the end: `print(f"[<FUNCTION_NAME>] Processed {count} cells")` if iterating over cells
- **Rare exception:** if the function is *not* a biological behaviour — it creates the population, loads cells from a file, or sets up config (no typed setter exists) — keep `context: Dict[str, Any]` and add `typed_env_exempt=True` to the decorator instead of using `env`.

## Step 4 — Place the file and register it

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

## Step 5 — Optionally add to a workflow JSON

If the user wants to add the function to a specific workflow JSON right away, ask:
- "Which workflow JSON file should I add this to?" (default: `opencellcomms_adapters/jayatilake/workflows/v7_microc_workflow.json`)
- "Which subworkflow stage?" (name of the subworkflow, e.g., "Intracellular", "Intercellular")

Then read the workflow JSON, find the correct subworkflow's `"nodes"` array, and insert the new node. Use `/add-to-workflow` logic for the insertion.
