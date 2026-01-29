# Chapter 6 — The Visual Workflow Designer (GUI) & Backend API

## 6.1 Why the GUI exists: lowering friction without hiding the model

The OpenCellComms GUI is built around a simple goal:

> Let users build and edit simulation workflows without writing code, while keeping the underlying workflow explicit and exportable.

This matters for scientific software because:

- some users are not comfortable editing Python,
- teams need a shared visual artifact to discuss the model,
- and “parameterizing the model” is as important as implementing the model.

## 6.2 The main UX loop

The GUI supports a predictable workflow:

1. Select a stage/subworkflow.
2. Drag functions from the palette onto the canvas.
3. Connect them to define execution order.
4. Edit parameters (type-aware).
5. Import/export as JSON.
6. Run, watch logs, inspect results.

This is described in `opencellcomms_gui/README.md` and `docs/USAGE.md`.

## 6.3 Node-based editing (React Flow)

The GUI uses a node-based editor (React Flow) to represent:

- function nodes (engine steps)
- subworkflow calls (composition)
- parameter nodes (shared / connected values)
- group nodes (visual grouping)

In an article, explain the “mental model”:

- Nodes are **operations**
- Edges are **ordering/flow**
- Tabs/subworkflows are **scope**

## 6.4 The function library: keeping UI and engine in sync

The GUI shows a function palette (a library of available nodes). The key engineering idea is:

- the engine has a registered set of functions,
- each function carries metadata (display name, category, parameter schema),
- the GUI uses that metadata to render a palette and editors.

This is a strong “single source of truth” pattern: function definitions double as UI definitions.

## 6.5 The backend API: launching runs and streaming logs

The GUI’s backend server (Flask) exists to:

- run the engine as a subprocess
- stream stdout/stderr lines back to the UI
- manage results directories with clear overwrite semantics

This is intentionally pragmatic:

- no database
- no multi-user authentication layer
- optimized for local research iteration

In the repo, `opencellcomms_gui/server/api.py` shows:

- results directory setup and clearing per run
- engine invocation with `--workflow` and a GUI results directory argument
- log streaming via threads and a queue

## 6.6 Results UX: from raw outputs to something users can trust

The GUI’s results view provides two value propositions:

- quick confirmation that a run “did something” (plots, snapshots)
- a navigable set of output artifacts that can be archived or shared

For scientific workflows, the ability to export results as flat files (CSV/plots/checkpoints) is critical: it keeps analysis portable across environments.

## 6.7 Suggested figures (for this chapter)

- **Figure 1 — GUI screenshot: canvas + palette + parameter editor**
  - Capture a medium complexity workflow so the palette categories and node types are visible.

- **Figure 2 — Run panel screenshot**
  - Show “Run” controls and the live log console while a simulation is executing.

- **Figure 3 — Backend dataflow diagram**
  - GUI → Flask API → Engine subprocess → results/ + log stream back to GUI.

