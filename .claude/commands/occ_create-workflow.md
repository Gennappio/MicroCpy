# /occ_create-workflow — Assemble a runnable workflow from a plugin's behaviors

You are helping a biologist turn a plugin's existing behaviors into a complete,
runnable **workflow JSON** in the ABM class-layer format (version 2.0). The
workflow wires the plugin's agent/resource setup and per-step behaviors into the
synthesized scaffold the executor and GUI expect: a Space, an init sequence, a
Scheduler loop, and processing — plus the `metadata.gui` that the canvas reads.

You **assemble from what exists**. You do not write biological functions here
(that is `/occ_new-function`); you arrange already-authored behaviors and flag
anything missing.

> **Readability Contract — mandatory.** Read `docs/READABILITY.md` before
> writing anything, and finish with its Verification checklist. Enforced
> strictly: **R1 — every ABM mechanism is exposed** (biology as nodes,
> constants as GUI parameters, consumed not just defined, announced on the canvas — never hidden inside a dict entry) and **R2 — exactly
> one source of truth** (one law, one implementation; one value, one owning
> GUI location that everything else reads — never a copy). For workflows this
> means in particular: parameter values carried explicitly in parameter
> nodes/tables (visible, not silent code defaults), and planner tab overrides
> kept as sparse diffs of the owning node — never snapshot copies.

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
3. **World** — the `__world__` canvas (`metadata.gui.world.subworkflow`): a tile
   grid (`setup_space`, the NetLogo/Sugarscape world) or a continuous diffusion
   domain (`setup_simulation` + `setup_domain`, the MicroC shape). Both canonical
   workflows name this canvas `__world__`.
4. **Cross-object & processing behaviors** — once-per-step `coupling`,
   `reconciliation`, and in-loop `reporting` canvases (e.g. `world_step`,
   `gene_update`), plus post-loop `reporting` (e.g. `final_snapshot`). **Every one
   of these must be owned by a category** — see the homing rule in Step 4. There is
   **no Environment tab**; never park a behavior in `environment.behavior_subworkflows`.
5. **Number of steps** for the scheduler loop (default 30).
6. **Workflow name** and a one-line description.

## Step 3 — Synthesize the scaffold

Build the `subworkflows` dict. Embed each behavior canvas **inline** (read the
plugin's `behaviors/<name>.subworkflow.json` and copy the object under its
`"subworkflow"` key in as `subworkflows.<name>`; keep its `contract`). Then add the
synthesized orchestration canvases:

- **`__world__`**: for a tile grid, a `setup_space` node (size_x, size_y,
  tile_size, topology, seed) and optionally `plot_space`; for a diffusion domain,
  `setup_simulation` + `setup_domain` (+ population/associations setup).
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

This is how the GUI reconstructs the entity view. **Every behavior subworkflow MUST
be owned by a category that maps to a navigable GUI tab** (Agents / Resources /
Processing) — otherwise it is an orphan: callable from the scheduler but editable in
no tab, invisible to the scientist. This is the rule in CLAUDE.md
("Every behavior must belong to a navigable category"). The homing rule:

- **In-loop behaviors** (called by `__scheduler__`, run every step) → the **owning
  object**: `agent_kinds[k].behavior_subworkflows` or
  `resource_kinds[k].behavior_subworkflows`, assigned by primary actor.
  `agent_behavior` → that agent kind; `resource_behavior` → that resource kind;
  `coupling` / `reconciliation` / in-loop `reporting` → the agent or resource kind
  that primarily drives it (e.g. `world_step` → the principal agent kind whose
  intents it commits; `gene_update` → the cell kind whose genes it updates).
- **Post-loop behaviors** (run once after the loop) → `processing.behavior_subworkflows`.
- **`environment.behavior_subworkflows` MUST be `[]`** — there is no Environment tab
  in the GUI; anything placed there is orphaned.

```json
"gui": {
  "function_libraries": [],
  "agent_kinds": [ { "name": "<kind>", "create_subworkflow": "<kind>_create",
                     "behavior_subworkflows": ["<kind>_step", "world_step"] } ],
  "resource_kinds": [ { "name": "<res>", "init_subworkflow": "<res>_init",
                        "behavior_subworkflows": ["<res>_growback"] } ],
  "world": { "subworkflow": "__world__",
             "behavior_subworkflows": ["world_step"] },   // world setup canvas + lattice-only behaviors
  "init_sequence": { "subworkflow": "__init_sequence__" },
  "scheduler": { "subworkflow": "__scheduler__" },
  "processing": { "behavior_subworkflows": ["final_snapshot"] },
  "main_is_synthesized": true,
  "user_functions": [],
  "contract_enforcement": "warn",
  "planner": { "tabs": [ { "id": "tab-baseline", "name": "baseline",
                           "enabled": true, "parameterOverrides": {} } ] }
}
```

**Use only these `metadata.gui` keys**: `agent_kinds`, `resource_kinds`, `world`,
`scheduler`, `processing`, `init_sequence`, `function_libraries`, `user_functions`,
`main_is_synthesized`, `contract_enforcement`, `planner` (and `subworkflow_kinds`).
The GUI loader (`opencellcomms_gui/src/store/slices/workflowIOSlice.js`,
`ALLOWED_GUI_KEYS`) refuses to open a workflow carrying any other key — `processes`,
`space` and `environment` all trigger "metadata.gui keys the current taxonomy does
not support". The behavior phase is carried by each canvas's `contract`, not by a
`processes` block. The reference workflows `sugarscape.json` / `microc.json` home
every behavior under an owning `agent_kinds` / `resource_kinds` / `world` /
`processing` category (no `environment` block) — mirror them directly. Set the top-level
workflow `"version": "2.0"`,
`"name"`, `"description"`, `"kernel"` (e.g. `"biophysics"`), and
`metadata.author` / `metadata.created`.

## Step 5 — Write, flag gaps, verify

1. Write to `opencellcomms_adapters/<plugin>/workflows/<name>.json` (create the
   `workflows/` folder if needed). Validate it parses:
   `python -c "import json; json.load(open('<path>'))"`. Then run the readability
   linter and fix anything it reports before continuing — from
   `opencellcomms_engine/`, `python scripts/validate_workflow.py <path>` — it must
   exit 0 (no orphan behaviors, no inlined dict/list parameters).
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
- Keep the canvas contracts (each behavior's `phase`) and the scheduler order in
  agreement; do not add a `metadata.gui.processes` block (the GUI rejects it).
- **Never leave a behavior in `environment.behavior_subworkflows`** (no Environment
  tab → orphan). Own every in-loop behavior under an agent/resource kind; send
  post-loop behaviors to `processing`. Every name in `__scheduler__` must trace to
  one of those categories.
- Mark `main`, `__init_sequence__`, `__scheduler__` as `"deletable": false`.
