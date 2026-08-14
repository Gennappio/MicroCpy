# Planner Tab

## Purpose

The Planner tab is the **multi-run experiment manager** of OpenCellComms.

Its core idea is simple: a scientist often wants to run the same workflow several times with different parameter values — different cell counts, different diffusion coefficients, different gene network rules — and compare the results. Without the Planner, this means manually editing parameter nodes on the canvas, running, then changing them again. With the Planner, each set of parameter values is saved as a named **configuration**, and all enabled configurations execute sequentially with a single click of the Run button.

The Planner tab does not change the workflow structure (stages, nodes, edges). It only overrides parameter values at run time.

---

## Location in the UI

The Planner is one of four main tabs at the top of the application:

| Tab | Icon | Purpose |
|-----|------|---------|
| Composers | Layers | Design the main workflow canvas |
| Sub-workflows | Workflow | Design reusable subworkflow canvases |
| **Planner** | ListChecks | Manage multi-run parameter configurations |
| Results | BarChart3 | Explore simulation outputs |

---

## Layout

```
┌─────────────────────────────────────────────────────────┐
│  [+ New]  [ ● Run 1 × ]  [ ● Run 2 × ]  [ ○ Run 3 × ]  │  ← Tab bar
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Parameters Dashboard                                  │  ← Content area
│   ▼ Composers                                           │
│     ▼ initialization                                    │
│       ▼ Configure Time and Steps                        │
│           dt          [ 0.1  ]                          │
│           macrosteps  [ 10   ]                          │
│     ▼ microenvironment                                  │
│       ▼ Run Diffusion Solver                            │
│           ...                                           │
│   ▼ Sub-workflows                                       │
│     ▼ Init_gene_networks                                │
│       ▼ Init Netlogo GN                                 │
│           ...                                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

The tab bar at the top manages the list of configurations. The content area below shows the **Parameters Dashboard** for whichever configuration tab is currently selected.

---

## Configuration Tabs

### Creating a configuration

Clicking **+ New** creates a new configuration tab named `Run N` (where N is an auto-incrementing counter). A new tab starts **empty**: it stores only the parameter values you edit in it (a sparse diff), and every other parameter follows the canvas base value at run time. Editing a value in the Planner does not touch the canvas; editing the canvas immediately affects every configuration that has not overridden that parameter.

The dashboard shows every parameter node that is connected to a function node via an edge, across all stages and subworkflows. Entries the tab overrides carry an **override** badge (with a **Reset** button that reverts to the canvas value); all other entries display the live canvas value. Editing an overridden value back to exactly the canvas value also removes the override.

> Older workflow files stored a full snapshot of every parameter in each tab. These load fine: entries equal to the canvas base are pruned on load (a no-op at run time), so the tabs collapse to true diffs, and the next save migrates the file.

### Tab controls

Each tab in the tab bar has three interactive elements:

| Control | Appearance | Action |
|---------|-----------|--------|
| Eye toggle | `●` (enabled) / `○` (disabled) | Toggles whether this configuration runs when Run is pressed |
| Tab name | Text label | Click to select; double-click to rename inline (confirm with Enter, cancel with Escape) |
| Delete button | `×` | Removes the configuration permanently |

Disabled configurations are visually distinguished with a strikethrough name and a dimmed style. They are skipped during execution but remain saved.

### Renaming

Double-click any tab name to enter rename mode. An inline text input appears with the current name pre-filled. Pressing Enter or clicking away commits the rename. Pressing Escape cancels without saving.

---

## Parameters Dashboard

The Parameters Dashboard is the content area of each configuration tab. It shows all parameter nodes that are connected to function nodes in the workflow, organized in a three-level collapsible hierarchy:

```
Kind (Composers / Sub-workflows)
  └── Stage name (initialization, macrostep, microenvironment, ...)
        └── Function node name
              └── Parameter node with inline editor
```

Each level can be collapsed or expanded by clicking its header. All levels start expanded.

### Navigation shortcut

Each stage row has a **Go to canvas** button (external link icon). Clicking it switches the main tab to the relevant Composer or Sub-workflow canvas and selects that stage, so you can inspect the node connections without leaving context.

### Parameter node types

Three types of parameter nodes are recognized:

#### Simple parameters (`parameterNode`)

Holds a flat key-value object. Each key is shown as a labeled row with an appropriate inline editor:

| Value type | Editor |
|-----------|--------|
| `boolean` | Checkbox |
| `number` / `float` / `int` | Number input (step=1 for int, any for float) |
| `string` | Text input |

#### List parameters (`listParameterNode`)

Holds an ordered list of values of a single declared type. The editor shows:
- A type badge and item count in the header
- One row per item with an inline value editor and a delete button
- An **Add item** button appending a new blank/zero item at the end

#### Dictionary parameters (`dictParameterNode`)

Holds an ordered list of key-value entries where each entry has its own declared type. The editor shows:
- A type badge and entry count in the header
- A table with columns: Key, Type, Value, Delete
- Supported value types: `string`, `float`, `int`, `bool`, `list`, `dict`
- For `list` values: an inline sub-list editor expands below the row
- For `dict` values: a JSON textarea expands below the row (parsed on-the-fly; invalid JSON is kept as a raw string while typing)
- An **Add entry** button appending a new blank entry

All edits are stored only in the configuration tab's `parameterOverrides` object — the canvas nodes are never modified.

---

## Running Configurations

### With no planner tabs

If the Planner contains no configurations (or all configurations are disabled), pressing Run in the console executes the workflow once using the current canvas parameter values. This is the default backward-compatible behavior.

### With one or more enabled tabs

When at least one configuration is enabled, pressing Run triggers a **sequential planner run**:

1. The console logs `🚀 Starting N planner configuration(s)...`
2. For each enabled configuration, in order:
   a. The full workflow JSON is exported from the canvas
   b. The tab's `parameterOverrides` are patched into the workflow JSON, replacing parameter node data inside each subworkflow's `parameters` array
   c. The patched workflow is sent to the engine via `POST /api/run`
   d. The console logs `▶ [i/N] Running "Run X"...`
   e. The console waits for the SSE stream to report completion or error before starting the next tab
   f. The console logs `✓ "Run X" completed` or `✗ "Run X" finished with errors`
3. The console logs `✓ All planner configurations finished`

If a configuration fails to start (HTTP error from the server), the console logs an error and moves on to the next one without stopping the sequence.

The engine receives each run as an independent execution with its own output directory (timestamped). This means all runs produce separate result folders that can be compared in the Results tab.

---

## How Overrides Are Applied

A tab's `parameterOverrides` is a flat map holding an entry **only for parameters edited in that tab**:

```js
{ [paramNodeId]: paramNodeData, ... }   // sparse: edited entries only
```

When you edit a parameter that has no entry yet, the current canvas value is cloned as the starting point (via `snapshotAllParamNodeData` for that one node) and the entry is stored; editing it back to the canvas value (or clicking **Reset**) removes the entry again.

At run time, `applyOverridesToWorkflow` patches the exported workflow JSON:

```js
for each subworkflow in workflow.subworkflows:
  for each param in subworkflow.parameters:
    if overrides[param.id] exists:
      merge override fields (parameters, items, entries, listType) into param
```

Only the fields that exist in the override are replaced; all other fields of the parameter node are preserved, and parameters with no override entry keep their canvas values. The canvas JSON is never mutated.

---

## State Management

The Planner state is managed in a Zustand slice (`plannerSlice.js`) with the following shape:

```js
{
  plannerTabs: [
    {
      id: string,           // Unique ID (timestamp-based)
      name: string,         // Display name ("Run 1", "Run 2", ...)
      enabled: boolean,     // Whether to include in sequential runs
      parameterOverrides: { // Sparse diff: only parameters edited in this tab
        [paramNodeId]: paramNodeData
      }
    },
    ...
  ],
  activePlannerTabId: string | null
}
```

### Actions

| Action | Description |
|--------|------------|
| `addPlannerTab()` | Create a new empty (no-override) tab, make it active |
| `removePlannerTab(tabId)` | Delete tab; switch active to previous tab if needed |
| `renamePlannerTab(tabId, newName)` | Update tab name |
| `togglePlannerTab(tabId)` | Flip enabled/disabled |
| `setActivePlannerTab(tabId)` | Change the viewed tab |
| `updatePlannerTabParam(tabId, paramNodeId, updater)` | Apply an updater to one param's override (seeds from the canvas value; drops the entry if the result equals the base) |
| `removePlannerTabParam(tabId, paramNodeId)` | Remove one override entry (reset to the canvas value) |
| `setPlannerTabs(tabs)` | Bulk-load tabs (used when importing a saved workflow) |
| `getActivePlannerTabs()` | Return all tabs where `enabled === true` |

### Persistence

Planner tabs are included in the workflow JSON when the workflow is saved (via the workflow IO slice). When a workflow is loaded, override entries equal to the base parameter nodes are pruned (older files stored full snapshots; a pruned entry was a no-op at run time), then `setPlannerTabs` restores the tabs and resets the auto-increment counter to continue after the highest existing `Run N` number. `scripts/validate_workflow.py` errors on override keys that match no parameter node and warns on redundant (base-equal) entries; `scripts/prune_planner_tabs.py` prunes a file in place from the command line.

---

## Empty States

**No configurations created yet:**

> No Planner Configurations
> Click + New to create a parameter configuration. Each configuration stores only the values you change; everything else follows the canvas. Active configurations run sequentially when you press Run.

**A configuration exists but has no connected parameters:**

> No Connected Parameters
> This dashboard shows parameter nodes that are connected to function nodes via edges. To see parameters here:
> 1. Switch to a Composer or Sub-workflow canvas
> 2. Add a parameter node from the palette
> 3. Connect it to a function node's parameter socket

---

## Typical Workflow

1. Design the workflow in the **Composers** and **Sub-workflows** tabs, connecting parameter nodes to function nodes for every value you want to vary.
2. Switch to the **Planner** tab.
3. Click **+ New** to create the first configuration (`Run 1`). It starts with no overrides — it runs exactly the canvas values.
4. Edit the parameter values you want to vary in the dashboard for `Run 1`; each edited entry is marked **override**.
5. Click **+ New** again for `Run 2` and edit its values. Parameters neither tab overrides keep following the canvas.
6. Repeat for as many configurations as needed.
7. Disable configurations you want to skip by clicking their eye toggle.
8. Open the **Run** console and click **Run**. All enabled configurations execute in sequence, each producing its own timestamped output folder.
9. Switch to the **Results** tab to compare outputs across runs.
