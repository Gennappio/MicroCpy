# /occ_add-to-workflow — Add an existing function to an OpenCellComms workflow JSON

You are helping a biologist place an already-registered function onto a behavior
canvas inside a workflow JSON. They may not know the JSON format. Your job is to
find the right canvas and insert the function node correctly, keeping the graph
valid.

## Step 1 — Identify the function and target workflow

Ask the user:
1. **Which function do you want to add?** (e.g. `eat_sugar`, or describe it and
   you will look it up).
2. **Which workflow JSON file?** (e.g.
   `opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json` or
   `opencellcomms_adapters/MicroC/workflows/microc.json`).

If you are unsure a function exists, list the registry (it auto-discovers plugins,
so reading imports won't help). From `opencellcomms_engine/`:
```bash
python -c "from src.workflow.registry import get_default_registry; print(sorted(f.name for f in get_default_registry().list_all()))"
```
(or `GET http://localhost:5001/api/registry` if the backend is running).

## Step 2 — Read the workflow and present the behavior canvases

Read the workflow. Its `subworkflows` are the canvases. Show the user the
**behavior canvases** (skip the synthesized ones `main`, `__space__`,
`__init_sequence__`, `__scheduler__` — those are orchestration, not where you add
behaviors), with each canvas's **contract phase** and current nodes:

```
This workflow has these behavior canvases (phase in parentheses):
- forager_init    (initialization):    [place_foragers, plot_agents]
- forager_step    (agent_behavior):    [move_to_best_sugar, eat_sugar, metabolize]
- sugar_growback  (resource_behavior):  [grow_sugar]
- world_step      (reconciliation):    [apply_reconciliation, census]
- final_snapshot  (reporting):         [plot_world]
```

Ask: **"Which canvas should this function run on?"** Also report registered
functions not yet used anywhere in this workflow (compare the registry list above
against every canvas's `functions[]`), grouped by category — this helps discovery.

**Sanity-check the canvas has a home tab.** Every behavior canvas must be owned by a
category in `metadata.gui` that maps to a navigable tab — an `agent_kinds[k]` /
`resource_kinds[k]` behavior (in-loop) or `processing` (post-loop). If the target
canvas is only listed under `environment.behavior_subworkflows`, it is an **orphan**
(no Environment tab exists; see CLAUDE.md "Every behavior must belong to a navigable
category"). Don't add to an orphan: tell the user it needs re-homing to its owning
agent/resource kind (or Processing) first, and offer to fix the `metadata.gui` lists.

**Check the contract phase matches.** Read the function's `contract.phase` (from
its `@register_function`, or infer from its category). If it disagrees with the
target canvas's phase (e.g. a `reporting` function on an `agent_behavior` canvas),
warn the user — this is exactly what the GUI flags in warn mode. Proceed only if
they confirm.

## Step 3 — The real node structure

A function node lives in `subworkflows.<canvas>.functions[]` and ordering is
controlled by `subworkflows.<canvas>.execution_order` (a list of node ids).
**There is no `edges` array and no `workflowFunctionNode`/`data` wrapper** — that
is the old React-Flow shape, not the saved workflow format. A node looks like:

```json
{
  "id": "<canvas>-<short_name>",
  "function_name": "<function_name>",
  "function_file": "",
  "parameters": {},
  "enabled": true,
  "position": { "x": 400, "y": 0 },
  "description": "<one line>",
  "custom_name": "",
  "step_count": 1,
  "parameter_nodes": [],
  "contract": { "phase": "<canvas phase>", "reads": [], "writes": [], "emits": [] }
}
```

**Rules:**
- `"id"` must be unique within the workflow. Use `"<canvas>-<short_name>"` (e.g.
  `forager-eat`); append `_2` if taken.
- Append the new id to that canvas's `"execution_order"` at the position it should
  run (usually the end). **Order = `execution_order`, not edges.**
- `"enabled": true` activates it; `false` adds it disabled.
- `"position"` is GUI-only; stack ~110px below the last node (`y += 110`) so it is
  visible, or `{ "x": 0, "y": 0 }` and let the user drag it.
- Give the node a `"contract"` whose `phase` matches the canvas. Copy the
  function's declared contract if it has one; otherwise set at least the phase.

## Step 4 — Parameters

- **Defaults:** leave `"parameters": {}` (uses the decorator defaults).
- **Simple scalar overrides:** put values inline, e.g.
  `"parameters": { "vision": 6, "rate": 1.0 }` (the Sugarscape style).
- **DICT / many related params:** do **not** inline a dict — it renders as an
  unreadable flat string in the GUI. Instead add a `dictParameterNode` to the
  canvas's `"parameters"` array with `target_param` set to the function parameter
  name, and reference its id from the node's `"parameter_nodes"` (same for
  `listParameterNode`). See CLAUDE.md "Workflow JSON & GUI Readability".

Ask the user: "Use the default parameters, or customize any values?"

## Step 5 — Edit the workflow JSON

1. Read the full workflow JSON.
2. Find the target canvas under `subworkflows`.
3. Append the node to its `"functions"` array.
4. Append the node id to its `"execution_order"`.
5. Write it back and **validate the JSON parses** (`python -c "import json; json.load(open('<path>'))"`).

**If a standalone behavior file exists** for this canvas
(`opencellcomms_adapters/<plugin>/behaviors/<canvas>.subworkflow.json`), update it
too so the workflow and the exported behavior stay in sync (the manual's Export
Rules). In that file the canvas lives under the top-level `"subworkflow"` key, and
it carries its own `dependencies.functions_required` list — add the function name
there.

## Step 6 — Confirm success

Tell the user:
- Which canvas was updated and the node `"id"`.
- Whether a standalone `behaviors/*.subworkflow.json` was also updated.
- Verify in the GUI: `./run.sh` → open the workflow → the canvas → the new node
  appears at the end of the chain.
- Run it: from `opencellcomms_engine/`,
  `python run_workflow.py --workflow <path_to_workflow.json>`.

## Common mistakes to avoid

- Do **not** emit `"type": "workflowFunctionNode"`, a `"data"` block, or an
  `"edges"` array — wrong format. Use `functions[]` + `execution_order`.
- Do **not** put a behavior on a canvas whose contract phase conflicts (e.g. a
  resource-mutating behavior on an `agent_behavior` canvas) without warning.
- Do **not** inline dict/list values in `"parameters"` — use
  `dictParameterNode`/`listParameterNode` siblings.
- Do **not** reuse a node `"id"`, and do **not** forget to add it to
  `execution_order` (a node absent from `execution_order` never runs).
- If the function needs a resource, substance, space, or gene network that the
  init canvases don't set up, warn the user and point them at the relevant init
  function (or `/occ_new-function`).
