# /occ_new-function — Scaffold a new OpenCellComms simulation function

You are helping a biologist add a new biological rule to an OpenCellComms
simulation. They may not know Python, decorators, or the project architecture.
Your job is to gather their intent in plain English and produce a complete,
correctly placed, working **atomic node-function** — one file, one function, one
job — that they can see and edit on the GUI canvas.

## Step 1 — Ask questions (ask all at once in a single message)

1. **What biological event does this function model?**
   Examples: "move each forager to the most sugar it can see", "kill cells when
   oxygen drops below a threshold", "regrow sugar toward its capacity", "count how
   many agents are alive this step".

2. **Which plugin and which workflow will this be used in?**
   Ask for the plugin (e.g. `SUGARSCAPE`, `MicroC`) or the target workflow JSON
   (e.g. `opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json`). If the
   plugin does not exist yet, tell them to run `/occ_create-plugin` first, or
   offer to do it. New functions almost always belong in a **plugin**.

3. **What parameters should a scientist configure from the GUI?**
   Examples: "vision radius (default 6)", "oxygen threshold (default 0.022)",
   "growback rate (default 1.0)". If they don't know, suggest sensible defaults
   from the event described. Prefer a single `DICT` parameter when there are 3+
   related knobs (renders as an editable table in the GUI).

## Step 2 — Read the workflow and decide where it runs

If you have a workflow path, **read it** and list its behavior subworkflows with
the nodes each currently contains, e.g.:

```
This workflow has these behavior canvases (process role in parentheses):
- forager_init      (initialization):   [place_foragers, plot_agents]
- forager_step      (agent_behavior):   [move_to_best_sugar, eat_sugar, metabolize]
- sugar_growback    (resource_behavior): [grow_sugar]
- world_step        (reconciliation):   [apply_reconciliation, census]
- final_snapshot    (reporting):        [plot_world]
```

Then ask **which canvas this function belongs on**. The canvas's **contract phase**
(see Step 3) is the source of truth for what belongs there. If unsure, suggest the
canvas whose phase matches the biological event.

## Step 3 — Classify the function: process role (contract phase)

Every behavior belongs to **one process role**. This is the most important choice
— it decides the canvas, the contract, and the API the function uses.

| Process role (`phase`) | Use for | Writes | Runs |
|---|---|---|---|
| `initialization` | create space, resources, agents, config | initial collections/config | once |
| `agent_behavior` | one agent's local decision & internal state | `agent.self`, intents | **per agent** |
| `resource_behavior` | one resource's local dynamics | `resource.self`, intents | per resource |
| `coupling` | cross-object interaction (agent↔resource, cell↔field) | coupled state, intents | per agent/once |
| `reconciliation` | mechanical commits of queued intents | agent/resource/space collections | once |
| `reporting` | plots, exports, census | nothing in model state (read-only) | once |

Rules of thumb: agent behaviors must **not** directly mutate resources or other
agents — they **emit intents** instead; reconciliation is the only place that
commits structural changes; reporting is read-only. (See
`docs/BEHAVIOR_LIBRARY_MANUAL.md`.)

The legacy decorator `category` (`INITIALIZATION`, `INTRACELLULAR`, `INTERCELLULAR`,
`DIFFUSION`, `FINALIZATION`, …) is **separate** and only legacy registry metadata —
pick the closest one, but the **contract `phase`** is what matters.

## Step 4 — Identify what the function needs (typed `env: BiologicalContext`)

Biological functions take a typed `env`, **not** the raw `context` dict.

**Per-agent functions** (`agent_behavior` / `coupling`, run once per agent via the
scheduler's `for_each` ask) act on the single bound agent:
- The current agent → `agent = env.agent` (may be `None` — return `True` if so)
- Its position / traits → `agent.position`, `agent.get('vision', 1)`, `agent.set('key', v)`
- The space → `env.space`: `space.neighbors(pos, radius, 'axial')`, `space.is_free(cell)`, `space.distance(a, b)`
- A resource field → `env.resource('sugar')`: `.at(pos)`, `.set(pos, v)`
- **Emit an intent** (don't mutate shared state directly):
  - `env.request_move(target=(x, y))`
  - `env.request_consume_resource('sugar', position=pos, store_as='sugar')`
  - `env.request_resource_delta('oxygen', amount=-0.1, position=pos)`
  - `env.request_remove_agent(reason='starved')`
  - `env.request_add_agent(kind='cell', position=pos, state={})`

**Collective functions** (`initialization` / `resource_behavior` / `reporting`, run
once) act on whole collections:
- Create agents → `env.population.populate(kind, count, trait=lambda rng: ...)`
- Loop cells → `for cell in env.cells:` then `cell.mark_necrotic()` / `cell.mark_apoptotic()` / `cell.mark_proliferating()` / `cell.mark_growth_arrested()` / `cell.mark_quiescent()`
- Concentration at a cell → `env.concentration('oxygen', cell)`
- Read/set a gene → `cell.gene('Name').is_on()` / `.turn_on()` / `.turn_off()`
- Step / dt / config → `env.step` / `env.dt` / `env.config`
- Store a result → `env.results.store('key', value)`
- Escape hatch (rare) → `env.raw_context` ("you are leaving the typed zone")

**Declare `requires`:** capability tokens the function reads (`"population"`,
`"simulator"`, `"gene_networks"`) so a mismatched kernel fails loudly at load.
Per-agent functions that only touch `env.agent`/`env.space`/`env.resource(...)`
often need `requires=[]`.

## Step 5 — Generate the Python file

Derive a snake_case name from the event (`move_to_best_sugar`, `grow_sugar`,
`mark_hypoxic_cells`, `census`). Generate the complete file:

```python
"""<one-line biological description>."""

from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function


@register_function(
    display_name="<Human-readable name for the GUI>",
    description="<One sentence shown in the GUI tooltip>",
    category="<legacy bucket, e.g. INTERCELLULAR>",
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"],          # or ["biophysics"]
    requires=[<tokens, e.g. "population"; often [] for per-agent fns>],
    operates_on=[<resource/kind names this reads, optional, e.g. "sugar">],
    parameters=[
        {"name": "<param>", "type": "<INT|FLOAT|BOOL|STRING|DICT>",
         "description": "<what it controls>", "default": <value>},
    ],
    contract={
        "phase": "<initialization|agent_behavior|resource_behavior|coupling|reconciliation|reporting>",
        # owner OR participants depending on phase:
        "owner": {"type": "agent", "kind": "<kind>"},     # single-object phases
        # "participants": [{"type": "agent", "kind": "<k>"}, {"type": "resource", "kind": "<r>"}],  # coupling
        "reads": [<tokens, e.g. "agent.self", "resource.sugar.local", "space.neighborhood">],
        "writes": [<tokens, e.g. "agent.self">],
        "emits": [<tokens, e.g. "intent.move">],
    },
)
def <function_name>(env: BiologicalContext, <param>: <type> = <default>, **kwargs) -> bool:
    """<Description>."""
    agent = env.agent          # per-agent functions; omit for collective functions
    if agent is None:
        return True
    # <biological logic — emit intents, don't mutate shared state directly>
    return True
```

**Important rules:**
- First arg is `env: BiologicalContext`. Declare `requires=[...]`; typed views fail
  loudly, so **no** manual `None`-checks for population/simulator (but **do** guard
  `env.agent is None` in per-agent functions).
- Mutate phenotypes through methods (`cell.mark_necrotic()`), never string assignment.
- Agent/resource behaviors **emit intents** for shared-state changes; let
  `reconciliation` commit them. Reporting functions are read-only.
- Declare a `contract` matching the chosen process role. In the current **warn
  mode** the executor validates but does not block — still author it correctly.
- Return `True` on success, `False` on error.
- **Rare exception:** if the function is *not* a behaviour — it creates the
  population, loads cells from a file, or sets config with no typed setter — keep
  `context: Dict[str, Any]` and add `typed_env_exempt=True` to the decorator.

## Step 6 — Place the file and register it

After showing the code and getting approval (or "go ahead"):

**In a plugin** (the normal case — experiment-specific logic):

1. Write to
   `opencellcomms_adapters/<plugin>/functions/<model_role>/<function_name>.py`.
   The `<model_role>` folder names the **model object** (`forager`, `sugar`,
   `tumor_cell`, `reporting`) — **not** the legacy category. Create the folder
   (with an empty `__init__.py`) if it doesn't exist.

2. Add the import to `opencellcomms_adapters/<plugin>/register.py`:
   `import opencellcomms_adapters.<plugin>.functions.<model_role>.<function_name>  # noqa: F401`
   (match the existing import style in that file).

3. If the plugin doesn't exist yet, run `/occ_create-plugin` first.

**In the engine** (only for generic, reusable machinery — diffusion/IO/kernel):

1. Write to `opencellcomms_engine/src/workflow/functions/<category>/<function_name>.py`.
2. Add `from .<function_name> import <function_name>` to that category's
   `__init__.py` and add it to `__all__` (pulled in via `standard_functions.py`).

## Step 7 — Confirm and hand off

- Restart the backend (`./run.sh`) — the function appears in the GUI palette.
- Verify registration from `opencellcomms_engine/`:
  ```bash
  python -c "from src.workflow.registry import get_default_registry; print([f.name for f in get_default_registry().list_all() if '<function_name>' in f.name])"
  ```
- Next steps:
  - Add it to a workflow canvas: `/occ_add-to-workflow`
  - Build a fresh workflow from this plugin's behaviors: `/occ_create-workflow`
