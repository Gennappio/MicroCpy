# /add-to-workflow — Add an existing function to a workflow JSON

You are helping a biologist enable a simulation function inside a workflow JSON file. They may not know the JSON format. Your job is to find the right place in the JSON and insert the function node correctly.

## Step 1 — Identify the function to add

Ask the user:
1. **Which function do you want to add?** (e.g., "mark_hypoxic_cells", or describe it in plain English and you will look it up)
2. **Which workflow JSON file?** Default: `opencellcomms_engine/tests/jayatilake_experiment/v7_microc_workflow.json`
3. **Which stage/subworkflow should it run in?** (e.g., "Intercellular", "Intracellular", "Initialization")

If the user describes a function by name that you are not sure exists, scan the registry by reading `src/workflow/registry.py` and looking at the imports to find the actual Python function name.

## Step 2 — Discover registered functions not yet in the workflow

Read the target workflow JSON. Scan the `"nodes"` arrays in all subworkflows to collect function names already present. Then read `registry.py` to see all imported functions. Report any functions not yet in the workflow, grouped by category. This helps the user discover what is available.

## Step 3 — Understand the JSON node structure

A function node in a subworkflow looks like this:

```json
{
  "id": "node_<function_name>",
  "type": "workflowFunctionNode",
  "data": {
    "function": "<function_name>",
    "label": "<Display Name>",
    "enabled": true,
    "parameters": {}
  },
  "position": { "x": 0, "y": 0 }
}
```

**Rules:**
- `"id"` must be unique in the workflow — use `"node_<function_name>"` unless there is already a node with that id (then append `_2`)
- `"enabled": true` makes the function active; use `false` to add it disabled
- `"parameters": {}` means use the decorator defaults; fill in specific values only if the user wants to override them
- `"position"` values do not affect execution — set to `{"x": 0, "y": 0}` and the user can drag it in the GUI
- The node must also appear in the subworkflow's `"edges"` array to be connected in the graph (see below)

**Edge structure (connecting nodes in sequence):**
```json
{
  "id": "edge_<source_id>_<target_id>",
  "source": "<source_node_id>",
  "target": "<target_node_id>"
}
```

To append a function at the end of a subworkflow's chain:
1. Find the last node in that subworkflow's `"nodes"` array
2. Find the edge from that last node to the subworkflow's output handle (if any)
3. Insert the new node and add an edge from the previous last node to the new node

If there is no existing edge chain (flat list of nodes), simply add the node to the `"nodes"` array and add an edge from the previous last function node to the new one. Do not break existing edges.

## Step 4 — Parameters in workflow JSON

If the function has DICT-type parameters, they should be expressed as a `dictParameterNode` in the subworkflow rather than inlined. Ask the user: "Do you want to use the default parameters, or customize any values?"

If they want to customize:
- For simple scalar params: put values directly in `"parameters": { "param_name": value }`
- For DICT params: create a `dictParameterNode` as a sibling node in the subworkflow's `"parameters"` array with the correct `target_param` field

If they want defaults, leave `"parameters": {}`.

## Step 5 — Edit the workflow JSON

After confirming with the user, make the edit:
1. Read the full workflow JSON
2. Find the correct subworkflow by its key name or by searching `"nodes"` arrays for the stage
3. Insert the new node into `"nodes"`
4. Insert the connecting edge into `"edges"`
5. Write the updated JSON back

**Important:** Validate that the JSON remains valid after editing. Do not break existing node connections.

## Step 6 — Confirm success

Tell the user:
- Which subworkflow was updated
- The function's `"id"` in the JSON
- How to verify: `./run.sh` → open the GUI → navigate to the updated subworkflow → the new node should appear in the canvas
- How to run the workflow: `python run_workflow.py --workflow <path_to_workflow.json>` from `opencellcomms_engine/`

## Common mistakes to avoid

- Do NOT set `"enabled": true` for functions that conflict with each other (e.g., do not enable both `update_gene_networks` and `propagate_gene_networks_netlogo` — they do the same job with different algorithms)
- Do NOT inline dict values in `"parameters"` — use `dictParameterNode` siblings
- Do NOT reuse node `"id"` values — check for uniqueness
- If the function requires a substance or gene network that is not set up in initialization, warn the user and suggest the relevant initialization function (e.g., `setup_substances`, `initialize_netlogo_gene_networks`)
