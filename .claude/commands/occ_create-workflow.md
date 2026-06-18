# /occ_create-workflow — Assemble a runnable workflow from a plugin's behaviors

You are helping a biologist turn a plugin's existing behaviors into a complete,
runnable **workflow JSON** in the ABM class-layer format (version 2.0). The
workflow wires the plugin's agent/resource setup and per-step behaviors into the
synthesized scaffold the executor and GUI expect: a Space, an init sequence, a
Scheduler loop, and processing — plus the `metadata.gui` that the canvas reads.

You **assemble from what exists**. You do not write biological functions here
(that is `/occ_new-function`); you arrange already-authored behaviors and flag
anything missing.

**Use `opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json` as the
canonical structural template** — read it and mirror its shape. A second, simpler
shape (agent + diffusion fields, no tile grid, no resources) is
`opencellcomms_adapters/MicroC/workflows/microc.json`.

## Step 1 — Pick the plugin and discover its behaviors

Ask **which plugin** (e.g. `SUGARSCAPE`, `MicroC`). If it has no behaviors yet,
send them to `/occ_create-plugin` + `/occ_new-function` first.

Then inventory the plugin:
- Read `opencellcomms_adapters/<plugin>/behaviors/*.subworkflow.json` — each is a
  ready canvas carrying a `kind`/`contract.phase` and a `functions[]` list.
- Read `opencellcomms_adapters/<plugin>/functions/<role>/*.py` for functions not
  yet wrapped in a behavior.
- Classify everything by **contract phase**: `initialization`, `agent_behavior`,
  `resource_behavior`, `coupling`, `reconciliation`, `reporting`.

Present the inventory and the proposed mapping for confirmation.

## Step 2 — Confirm the model shape (ask all at once)

1. **Agent kinds** — for each, its **init** canvas (placement, runs once) and its
   **step** canvas(es) (run **per agent**). E.g. `forager` → init `forager_init`,
   step `forager_step`.
2. **Resource kinds** — for each, its **init** canvas and **behavior** canvas(es)
   (e.g. `sugar` → `sugar_init`, `sugar_growback`). Resources are optional.
3. **Space** — tile grid (a `__space__` canvas running `setup_space`, the
   NetLogo/Sugarscape world) or a continuous diffusion domain / none (`space:
   {subworkflow: null}`, the MicroC shape where the domain is built in an
   environment init).
4. **Environment / processing behaviors** — once-per-step `coupling`,
   `reconciliation`, and `reporting` canvases (e.g. `world_step`,
   `final_snapshot`).
5. **Number of steps** for the scheduler loop (default 30).
6. **Workflow name** and a one-line description.

## Step 3 — Synthesize the scaffold

Build the `subworkflows` dict. Embed each behavior canvas **inline** (read the
plugin's `behaviors/<name>.subworkflow.json` and copy the object under its
`"subworkflow"` key in as `subworkflows.<name>`; keep its `contract`). Then add the
synthesized orchestration canvases:

- **`__space__`** (only if tile grid): a `setup_space` node (size_x, size_y,
  tile_size, topology, seed) and optionally `plot_space`. `deletable: false`.
- **`<kind>_init`** canvases: the agent/resource setup behaviors (placement,
  resource creation + seeding). Phase `initialization`.
- **`__init_sequence__`**: `subworkflow_calls` in dependency order — **space →
  resource inits → agent inits** (agents need resources/space to exist first).
  `deletable: false`.
- **`__scheduler__`**: the per-step loop, `number_of_steps` from Step 2,
  `deletable: false`. Its `subworkflow_calls` are, in order:
  - one call per **agent step** behavior with a per-agent ask:
    `"for_each": { "type": "agent", "kind": "<kind>", "order": "random" }`
  - one call per **resource behavior** with
    `"for_each": { "type": "resource", "kind": "<kind>" }`
  - once-per-step **coupling** behaviors (no `for_each`; they iterate internally)
  - a **reconciliation** canvas (e.g. `world_step` running `apply_reconciliation`
    then `census`) — include this whenever any behavior **emits intents**, so the
    queued moves/consumptions/births/removals get committed.
- **`main`**: synthesized, `deletable: false`, three `subworkflow_calls` in
  `execution_order`: `__init_sequence__` (1×) → `__scheduler__` (iterations =
  number of steps) → each processing canvas (1×).

Match the template's node fields exactly: each function node needs
`id, function_name, function_file:"", parameters, enabled:true, position,
description, custom_name:"", step_count:1, parameter_nodes:[], contract`; each
subworkflow needs `description, enabled, deletable, controller, functions,
subworkflow_calls, parameters, execution_order, input_parameters` and (for behavior
canvases) a `contract`.

## Step 4 — Build `metadata.gui`

This is how the GUI reconstructs the entity view. Populate (mirror Sugarscape):

```json
"gui": {
  "function_libraries": [],
  "agent_kinds": [ { "name": "<kind>", "init_subworkflow": "<kind>_init",
                     "behavior_subworkflows": ["<kind>_step"] } ],
  "resource_kinds": [ { "name": "<res>", "init_subworkflow": "<res>_init",
                        "behavior_subworkflows": ["<res>_growback"] } ],
  "space": { "subworkflow": "__space__" },          // or { "subworkflow": null }
  "environment": { "init_subworkflow": null, "behavior_subworkflows": ["world_step"] },
  "init_sequence": { "subworkflow": "__init_sequence__" },
  "scheduler": { "subworkflow": "__scheduler__" },
  "processing": { "behavior_subworkflows": ["final_snapshot"] },
  "main_is_synthesized": true,
  "user_functions": [],
  "contract_enforcement": "warn",
  "processes": {
    "agent_behaviors": ["<kind>_step"], "resource_behaviors": ["<res>_growback"],
    "couplings": [], "reconciliation": ["world_step"], "reporting": ["final_snapshot"]
  },
  "planner": { "tabs": [ { "id": "tab-baseline", "name": "baseline",
                           "enabled": true, "parameterOverrides": {} } ] }
}
```

`processes` classifies every behavior canvas by phase; keep it consistent with the
scheduler order and the contracts. Set the top-level workflow `"version": "2.0"`,
`"name"`, `"description"`, `"kernel"` (e.g. `"biophysics"`), and
`metadata.author` / `metadata.created`.

## Step 5 — Write, flag gaps, verify

1. Write to `opencellcomms_adapters/<plugin>/workflows/<name>.json` (create the
   `workflows/` folder if needed). Validate it parses:
   `python -c "import json; json.load(open('<path>'))"`.
2. **Flag gaps:** if the mapping references a behavior or function that doesn't
   exist (an agent with no step canvas, a behavior emitting intents with no
   reconciliation canvas, a `function_name` not in the registry), say so plainly
   and point to `/occ_new-function` (to author it) or `/occ_add-to-workflow` (to
   place an existing function). Do not invent function names.
3. Tell the user how to run it:
   - GUI: `./run.sh` → open the workflow → the Space / Resources / Agents /
     Scheduler / Processing tabs should be populated.
   - CLI: from `opencellcomms_engine/`,
     `python run_workflow.py --workflow <path_to_workflow.json>`.

## Common mistakes to avoid

- Don't put agent **step** behaviors in `__init_sequence__`, or **init** behaviors
  in `__scheduler__`. Init runs once; step runs every loop.
- Don't forget `for_each` on per-agent/per-resource scheduler calls — without it
  the behavior runs once, not once per agent.
- Order `__init_sequence__` as space → resources → agents (agents read
  resources/space at placement).
- Include a reconciliation canvas whenever behaviors emit intents — otherwise
  moves/eats/births/deaths are queued but never committed.
- Keep `metadata.gui.processes`, the scheduler order, and the canvas contracts in
  agreement.
- Mark `main`, `__space__`, `__init_sequence__`, `__scheduler__` as
  `"deletable": false`.
