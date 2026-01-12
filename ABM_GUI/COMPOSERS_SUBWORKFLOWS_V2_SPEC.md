# Composers + Sub-workflows (Workflow v2) — Canonical Spec (GUI + Runtime Contract)

**Status:** ✅ **IMPLEMENTATION COMPLETE** (All 5 phases finished)

## Implementation Status

- [x] Phase 1: Core Infrastructure (COMPLETE)
- [x] Phase 2: Visual Representation (COMPLETE)
- [x] Phase 3: Call Hierarchy Enforcement (COMPLETE)
- [x] Phase 4: Results System (COMPLETE)
- [x] Phase 5: Context Mapping (COMPLETE)

**ALL PHASES COMPLETE** ✅

---

This document is intentionally **extremely detailed**. It captures:
- All decisions made in the thread
- Rationale for those decisions (alternatives considered)
- Concrete data contracts (JSON shapes, UI behaviors, validation rules)
- Action plan for implementation (but no implementation in this phase)

---

## Table of Contents
1. Background & Why This Change Exists
2. Hard Product Decisions (Non-negotiables)
3. Vocabulary and Mental Model
4. Workflow v2 JSON Contract (Authoritative)
5. GUI State Model (React Flow nodes/edges → JSON)
6. Composer vs Sub-workflow Classification
7. Call Rules & Validation (Hard Constraints)
8. UI/UX Specification
9. Execution / Run Model (Composers only)
10. Results System (Overwrite, Nested, Active-Tab Viewer)
11. Function Libraries (Global, Conflict Resolution)
12. Path Handling (Relative on Export)
13. Error Handling & User-Facing Messages
14. Removal of Legacy (v1/stages) and Compatibility Policy
15. Known Current Code Gaps (as of now)
16. Implementation Plan (Phased)
17. Acceptance Criteria (Detailed)
18. Future Ideas Discussed (Not committed)

---

## 1) Background & Why This Change Exists

### 1.1 The project goal
We want a single “correct” workflow system moving forward that supports:
- Modular building blocks (sub-workflows)
- Orchestration graphs (composers)
- Clean separation in UI (users immediately understand what is runnable and what is reusable)
- Predictable outputs/results in the GUI
- Extensible function palette via imported Python libraries

### 1.2 Critical finding in current codebase (root cause)
The current GUI store contains **both** legacy stages (v1) and subworkflows (v2), but:
- v2 loading exists (`_loadWorkflowV2`)
- **export currently exports only v1 `workflow.stages`**

Meaning: **load v2 → edit → export loses subworkflow data**.

This is why this spec explicitly treats v2 as the only supported system.

---

## 2) Hard Product Decisions (Non-negotiables)

These are direct from the user’s decisions in this thread.

### 2.1 No backward compatibility
- We do **not** support running/loading/exporting old workflow versions.
- If a file is not v2-compatible, it is rejected (see §14).

Rationale:
- Avoid complexity and dual-mode behavior.
- Remove ambiguity and “migration forever” burden.

### 2.2 Two top-level tabs, never mixed
There are two main tabs:
1. **Composers**
2. **Sub-workflows**

Rules:
- Creating a new composer happens only inside the Composers main tab.
- Creating a new sub-workflow happens only inside the Sub-workflows main tab.
- Composer tabs and sub-workflow tabs are never displayed together.

Rationale:
- Zero ambiguity, no “choose type” dialogs.
- UI teaches the model implicitly.

### 2.3 Callability hierarchy
Sub-workflows are always callable by other sub-workflows.
Composers are callable by composers.
Composers are **never callable** by sub-workflows.

Rationale:
- Keeps orchestration as a privileged layer.
- Avoids “business logic hidden inside orchestration graphs”.

### 2.4 Results
- Nested directory structure.
- No timestamps (`20260112_...`) in GUI output paths.
- GUI results folders are overwritten each run.
- Users explicitly save elsewhere in their custom code if they want permanent archival.

Rationale:
- Users should not see images from other experiments or other composers.
- GUI is a working view, not an experiment tracking system.

### 2.5 Function libraries
- Function libraries are **global** for the workflow project (not per subworkflow).
- Palette import is initiated from the **palette toolbar**.
- Naming conflicts prompt overwrite vs variant creation.

Rationale:
- One library import benefits all subgraphs.
- Conflict handling must be explicit because it can affect existing nodes.

### 2.6 Export paths for libraries
- Library paths must be written **relative to the workflow file location**.

Rationale:
- Enables portability across machines.

---

## 3) Vocabulary and Mental Model

### 3.1 “Workflow” (ambiguous term)
In conversation, “workflow” was used for both composers and sub-workflows because their graph structures are similar.

In implementation/spec:
- We use **SubWorkflow** as the JSON structure name.
- We use **Kind** as the GUI classification: `composer` vs `subworkflow`.

### 3.2 Sub-workflow (compute)
A sub-workflow is a reusable graph that primarily contains:
- Function nodes
- Parameter nodes
- Optional calls to other sub-workflows

Sub-workflows:
- Are callable by sub-workflows and composers.
- Are not runnable from the GUI directly.

### 3.3 Composer (orchestration)
A composer is a top-level orchestration graph.
Composers:
- Are runnable from the GUI.
- Can call other composers and sub-workflows.
- Are callable only by other composers.

---

## 4) Workflow v2 JSON Contract (Authoritative)

### 4.1 File-level contract
Minimum required top-level fields:
- `version: "2.0"`
- `name: string`
- `description: string`
- `metadata: object` (free-form; we will store GUI-specific metadata here)
- `subworkflows: { [name: string]: SubWorkflow }`

Strict policy:
- If `version !== "2.0"`, GUI rejects the file.

### 4.2 SubWorkflow JSON shape (based on MicroC schema)
Each `subworkflows[name]` is a SubWorkflow object:
- `description: string`
- `enabled: boolean`
- `deletable: boolean`
- `controller: ControllerNode`
- `functions: WorkflowFunction[]`
- `subworkflow_calls: SubWorkflowCall[]`
- `parameters: ParameterNode[]`
- `execution_order: string[]` (ordered node IDs; may reference functions and/or call nodes)
- `input_parameters: InputParameter[]` (optional)

Notes:
- `execution_order` is the canonical execution sequence for that subworkflow.
- `controller` is the entry point.

### 4.3 ControllerNode JSON shape
- `id: string`
- `type: "controller"` (MicroC schema)
- `label: string`
- `position: {x:number, y:number}`
- `number_of_steps: number`

GUI note:
- In React Flow the controller node type currently used is `initNode`.
- Export must map GUI controller to schema controller.

### 4.4 WorkflowFunction JSON shape
- `id: string`
- `function_name: string`
- `function_file?: string` (optional)
- `parameters: object`
- `enabled: boolean`
- `position: {x:number, y:number}`
- `description: string`
- `custom_name: string`
- `parameter_nodes: string[]`
- `step_count: number`

Critical reasoning:
- MicroC already supports loading a function by `function_file` per node.
- This naturally supports palette variants.

### 4.5 SubWorkflowCall JSON shape
- `id: string`
- `type: "subworkflow_call"`
- `subworkflow_name: string`
- `iterations: number`
- `parameters: object`
- `enabled: boolean`
- `position: {x:number, y:number}`
- `description: string`
- `parameter_nodes: string[]`
- `context_mapping: { [from:string]: string }`

### 4.6 ParameterNode JSON shape
- `id: string`
- `label: string`
- `parameters: object`
- `position: {x:number, y:number}`

### 4.7 GUI-specific metadata contract
We store GUI-only details under `metadata.gui`.

#### 4.7.1 Subworkflow kind classification
`metadata.gui.subworkflow_kinds`:
```json
{
  "main": "composer",
  "initialize_cells": "subworkflow"
}
```

Rules:
- Every subworkflow name in `subworkflows` must have an entry.
- Allowed values: `"composer" | "subworkflow"`.

Rationale (why metadata):
- MicroC runtime ignores unknown metadata fields and round-trips them.
- Avoids modifying the SubWorkflow schema for a GUI concern.

#### 4.7.2 Function libraries list (workflow-global)
`metadata.gui.function_libraries` (or `metadata.function_libraries`, pick one and keep consistent):
```json
[
  "./libs/custom_functions.py",
  "./libs/analysis.py"
]
```

Rules:
- Paths are stored relative to the workflow JSON file location (see §12).
- Applies globally to palette and runtime resolution.

Important note:
- MicroC currently supports per-node `function_file` loading. Global library preloading is a planned enhancement.

---

## 5) GUI State Model (React Flow nodes/edges → JSON)

### 5.1 Canvas partitioning
The GUI maintains a separate canvas per subworkflow name:
- `stageNodes[subworkflowName] = ReactFlowNode[]`
- `stageEdges[subworkflowName] = ReactFlowEdge[]`

Even though the store names them `stageNodes/stageEdges`, they are the per-subworkflow graphs in v2.

### 5.2 Node types in the canvas
Current node types used in the GUI:
- `initNode` (controller)
- `workflowFunction`
- `subworkflowCall`
- `parameterNode`

Mapping to JSON:
- `initNode` → `controller`
- `workflowFunction` → WorkflowFunction
- `subworkflowCall` → SubWorkflowCall
- `parameterNode` → ParameterNode

### 5.3 Edge semantics
Two conceptual edge types:
1) **Execution edges**: represent execution sequence.
   - GUI uses handles like `func-out` → `func-in`
   - In v2 loader, execution edges are synthesized from `execution_order`
2) **Parameter edges**: link parameter nodes to function/call nodes.
   - In v2 loader, these are synthesized from `parameter_nodes` arrays

Export rule:
- Execution edges do not need to be explicitly stored as edges; `execution_order` is canonical.
- Parameter edges are stored indirectly via `parameter_nodes` arrays.

### 5.4 Execution order generation (reasoning)
We have two valid strategies:
- **Strategy A (graph-based):** traverse execution edges from controller and infer `execution_order`.
- **Strategy B (order-based):** treat `execution_order` in JSON as canonical and store it directly.

Current v2 loader already uses Strategy B (it builds edges from `execution_order`).
Therefore export should also treat `execution_order` as canonical and export it.

If the user edits edges directly, export must rebuild `execution_order` deterministically.
Preferred deterministic rule:
- Start from controller node
- Follow `func-out`→`func-in` edges
- Linearize into a sequence (if multiple outgoing edges: define stable ordering rule or reject)

This spec requires: **the UI must enforce a single linear execution chain** per subworkflow.
(If branching is allowed later, the schema would need a different model.)

---

## 6) Composer vs Sub-workflow Classification

### 6.1 How kinds are created (no disambiguation)
- Creating inside **Composers** tab → create a new subworkflow entry with kind `composer`.
- Creating inside **Sub-workflows** tab → create a new subworkflow entry with kind `subworkflow`.

No UI dialogs asking to choose type.

### 6.2 Where kinds are stored
- Stored in `workflow.metadata.gui.subworkflow_kinds`.

### 6.3 Import behavior if kinds metadata is missing
We do not support old versions, but v2 files may still lack GUI metadata.
To keep UX simple (no dialogs) and avoid hard failure on otherwise valid v2:

Default inference rule (simple + deterministic):
- If a subworkflow name is exactly `main`: kind = `composer`
- All other subworkflows: kind = `subworkflow`

The GUI should then write back the explicit map on next export.

---

## 7) Call Rules & Validation (Hard Constraints)

### 7.1 The rule
Let `kind(caller)` and `kind(target)` be derived from metadata.

Allowed:
- composer → composer
- composer → subworkflow
- subworkflow → subworkflow

Forbidden:
- subworkflow → composer

### 7.2 Enforcement moments
Enforce at three times:
1. **At edit-time** (best UX):
   - Prevent selecting a composer in a call node when editing inside a sub-workflow.
   - Or prevent dropping a composer-call palette item into a sub-workflow.
2. **At export-time** (safety net):
   - Validate all SubWorkflowCall targets against kinds.
3. **At run-time** (final gate):
   - Server rejects run request if illegal calls exist.

### 7.3 Validation coverage
Validation should include:
- Subworkflow name validity (`^[a-zA-Z][a-zA-Z0-9_]*$`)
- Call target existence (target must exist in `subworkflows`)
- Kind rule (subworkflow cannot call composer)
- Cycle detection
  - MicroC already has general cycle detection across subworkflows.
  - We still validate in GUI to provide immediate feedback.
- execution_order references must exist (ids must exist in functions/calls)

---

## 8) UI/UX Specification

### 8.1 Top-level navigation
Two main tabs:
- **Composers**
- **Sub-workflows**

Switching the main tab:
- Changes the list of subgraphs shown
- Changes the open editor tab set (composer tabs vs sub-workflow tabs)
- Changes palette sections (see §11)
- Changes Run controls visibility

### 8.2 Tab lists and editor tabs
Within each main tab:
- Left: list of subgraphs of that kind
- Center: editor tabs (one per open subgraph)

Rule: A composer tab and a sub-workflow tab are never in the same tab strip.

### 8.3 Create / rename / delete

#### Create
- “+ New Composer” exists only in Composers main tab.
- “+ New Sub-workflow” exists only in Sub-workflows main tab.

New item defaults:
- has a controller node
- enabled=true
- deletable:
  - `main` composer is not deletable
  - other items deletable=true

#### Rename
- Must update:
  - `workflow.subworkflows` key
  - `metadata.gui.subworkflow_kinds`
  - Any SubWorkflowCall `subworkflow_name` references
  - Any UI tab labels

#### Delete
- Only if `deletable=true`.
- Must also delete its React Flow nodes/edges state.

### 8.4 Editing subworkflow call nodes
When editing a call node inside:
- Composer context: user can choose any target
- Sub-workflow context: user can choose only sub-workflow targets (no composers shown)

### 8.5 Run controls
- Run controls exist only in Composers main tab.
- Running is per active composer tab.

---

## 9) Execution / Run Model (Composers only)

### 9.1 What “Run” means
Pressing Run on composer `C` should execute the workflow with `C` as the entry point.

This implies runtime support for selecting an entry subworkflow.

### 9.2 Server API contract (proposed)
`POST /api/run`
Request body:
- `workflow: <full v2 workflow JSON>`
- `entry_subworkflow: <composer_name>`

Rules:
- `entry_subworkflow` must exist.
- `metadata.gui.subworkflow_kinds[entry_subworkflow]` must be `composer`.

### 9.3 Runtime contract
Runtime must:
- Load workflow JSON
- Validate
- Start execution from `entry_subworkflow`

### 9.4 Logs
- GUI consumes streaming logs via SSE `/api/logs`.
- Optional: call stack logs can be grouped by subworkflow name.

---

## 10) Results System (Overwrite, Nested, Active-Tab Viewer)

### 10.1 Directory layout
Root results directory is stable (no timestamp subdir created by GUI runs).

Nested structure:
- `results/composers/<name>/...`
- `results/subworkflows/<name>/...`

Within each subfolder, functions may create additional categories:
- `debug/`
- `analysis/`
- etc.

### 10.2 Overwrite semantics
At the start of each GUI run:
- Clear (delete contents of) `results/composers/*` and `results/subworkflows/*` OR clear only the folders relevant to this workflow.

Reasoning:
- Without clearing, stale files from a prior run can remain if a file is not regenerated.
- The user explicitly asked not to see pictures from other experiments.

### 10.3 Context keys (runtime)
During execution of a node within subworkflow `S` of kind `K`:
- `context['subworkflow_name'] = S`
- `context['subworkflow_kind'] = K` (composer/subworkflow)
- `context['results_dir'] = <Path('results')>`
- `context['subworkflow_results_dir'] = <Path('results/<K_plural>/<S>')>`

This enables any function to save images to its own namespace.

### 10.4 Results viewer behavior
The GUI results panel always shows results for:
- the **currently active editor tab** only.

Implication:
- After running a composer, the user can click into a sub-workflow tab and see images produced inside that sub-workflow (because runtime wrote into `results/subworkflows/<that_name>`).

---

## 11) Function Libraries (Workflow-global, Conflict Resolution)

### 11.1 What a “library” is
A library is a Python file that defines one or more workflow functions.

Two usage modes:
1) **Per-node function_file** (already supported by MicroC executor)
2) **Workflow-global library registration** (planned): makes functions show in palette and optionally allows resolution without per-node function_file.

### 11.2 Library import UX (palette toolbar)
From the palette toolbar:
- “Import Function Library…”
- User selects a `.py` file
- GUI registers it into workflow metadata list

### 11.3 Conflict resolution (exact behavior)
When importing a library that defines function `F` and the palette already has a function named `F`:

GUI must prompt with 3 actions:
1) **Overwrite existing**
   - All nodes that reference `F` with no explicit `function_file` will now resolve to the new implementation.
   - This affects all subworkflows using that function.
2) **Create new variant**
   - Palette adds a new entry displayed as: `F (<library_filename.py>)`
   - Dragging this entry creates nodes with:
     - `function_name = F`
     - `function_file = <that library path>`
   - Existing nodes remain unchanged.
3) **Skip**
   - Function `F` from that library is not added.

Reasoning:
- Overwrite supports global changes.
- Variant supports coexistence.

### 11.4 Palette grouping
Palette should show:
- Built-in / default functions
- Imported library functions grouped by library file

Variant display rule:
- If a palette entry uses `function_file`, append `(<basename>)` in label.

---

## 12) Path Handling (Relative on Export)

### 12.1 Export rule
When exporting workflow JSON to a file path `W`:
- All library paths stored in metadata must be made **relative** to `W.parent`.

Example:
- workflow saved to: `/proj/workflows/my.json`
- library located at: `/proj/libs/custom.py`
- store as: `../libs/custom.py`

### 12.2 Import rule
When loading workflow JSON from file path `W`:
- Resolve library paths relative to `W.parent` when:
  - building the palette
  - running the workflow

### 12.3 Per-node function_file paths
If nodes store `function_file`:
- If path is relative, it is interpreted relative to `workflow_file` directory first.
MicroC already attempts this resolution strategy.

---

## 13) Error Handling & User-Facing Messages

### 13.1 File loading errors
- If version != 2.0: “Unsupported workflow version. Only v2.0 is supported.”
- If JSON invalid: show parse error.

### 13.2 Validation errors (before export/run)
- Illegal call (subworkflow → composer):
  “Sub-workflow '<A>' cannot call composer '<B>'. Only composers can call composers.”
- Missing target:
  “Call node '<id>' references missing sub-workflow '<name>'.”
- Cycle detected:
  “Circular dependency detected: A → B → C → A.”

### 13.3 Library conflicts
Dialog text must clearly warn overwrite impact:
“Overwriting 'write_checkpoint' will affect all nodes using 'write_checkpoint' across all sub-workflows.”

---

## 14) Removal of Legacy (v1/stages) and Compatibility Policy

### 14.1 Policy
- We will remove v1 stage support from GUI and server.
- We will not provide a migration flow in the GUI.

### 14.2 Documentation impact
Existing docs that mention v1 migration must be updated/removed.

---

## 15) Known Current Code Gaps (as of now)

1) GUI export currently exports `workflow.stages` and ignores `workflow.subworkflows`.
2) Store contains v1 and v2 logic simultaneously.
3) Server run endpoint does not accept an entry subworkflow parameter (runs workflow file only).
4) v2 loader currently does not populate `context_mapping` into call nodes (schema supports it).
5) Results folder contract (nested/no timestamp/overwrite) is not enforced end-to-end yet.

---

## 16) Implementation Plan (Phased)

**Phase 0 (this document):** finalize spec (no code).

**Phase 1: v2-only foundation**
- Remove v1/stages support
- Make load/export strictly v2
- Ensure round-trip correctness

**Phase 2: Two-main-tab UI split**
- Composers main tab (list + editor tabs + Run)
- Sub-workflows main tab (list + editor tabs)

**Phase 3: Call rule enforcement**
- Restrict call targets in editor
- Validate on export/run

**Phase 4: Results system**
- Implement nested results dirs
- Implement overwrite semantics
- Results viewer: active-tab-only

**Phase 5: Function libraries**
- Palette toolbar import
- Conflict resolution dialog
- Relative-path export/import

---

## 17) Acceptance Criteria (Detailed)

### 17.1 v2-only behavior
- Loading a v1 workflow fails with a clear error.
- Export always produces v2 JSON with `subworkflows`.

### 17.2 UI separation
- In Composers main tab: only composer list/tabs are visible.
- In Sub-workflows main tab: only sub-workflow list/tabs are visible.

### 17.3 Call constraints
- A sub-workflow cannot be configured to call a composer.
- Any attempt is blocked in UI and rejected on run.

### 17.4 Results
- Running composer X overwrites `results/composers/X`.
- Running again does not show stale artifacts.
- Selecting a tab shows only that tab’s results folder.

### 17.5 Libraries
- Imported library paths round-trip relative to workflow file.
- Name conflicts prompt overwrite vs variant.
- Variant palette items create nodes with `function_file` set.

---

## 18) Future Ideas Discussed (Not committed)

These were discussed earlier but are NOT part of the committed spec unless explicitly re-approved:
- Export/import single composer/sub-workflow as standalone module files (`.composer` / `.workflow`).
- Dependency checks for exports (warn if referenced subworkflows are missing).
- Rich results explorer (history, timestamped runs, experiment management).


