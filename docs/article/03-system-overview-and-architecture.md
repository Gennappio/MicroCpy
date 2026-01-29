# Chapter 3 — System Overview & Architecture

## 3.1 High-level architecture (two halves + shared contract)

OpenCellComms is easiest to understand as two products sharing one contract:

- **A simulation engine** (Python): executes a workflow, updates simulation state, and writes outputs.
- **A workflow designer** (React GUI): allows users to compose workflows and run them through a backend API.

The shared contract between them is:

- the **workflow JSON format** (stages/subworkflows, nodes, parameters, execution order)
- a **function registry**: string `function_name` in JSON maps to a registered Python function
- a shared **context** model: functions read and write to a context dictionary during execution

## 3.2 Components in the repository

### 3.2.1 Python simulation engine (`opencellcomms_engine/`)

What it contains (conceptually):

- **Workflow runtime**
  - loading workflow JSON + schema validation
  - resolving node parameters
  - executing nodes in order
  - coordinating stages/subworkflows and step loops
- **Biology models**
  - cell and population state
  - gene network hooks
  - phenotype, metabolism, cell fate logic
- **Microenvironment simulation**
  - diffusion solvers (FiPy-based)
  - multi-substance orchestration
- **I/O and visualization**
  - CSV/VTK/H5 outputs
  - plots and analysis summaries

It is also designed for extensibility: users add new workflow nodes by registering Python functions.

### 3.2.2 Visual designer (`opencellcomms_gui/`)

What it contains (conceptually):

- **React Flow canvas** for node editing
- **function palette** built from a function registry (available node types)
- **parameter editor** for node parameters (type-aware)
- **results explorer** to browse outputs after runs
- **observability UI** (node badges, inspector, logs, context diffs) when enabled

### 3.2.3 Backend API (`opencellcomms_gui/server/`)

The GUI starts runs by talking to a Flask server which:

- validates and writes the workflow JSON
- launches the engine as a subprocess
- streams logs back to the GUI
- arranges results directories with “overwrite semantics” (fresh results each run)

This is intentionally simple: it is designed to support local research workflows, not to be a multi-user cloud service.

## 3.3 Layered architecture and boundaries

OpenCellComms benefits from clear boundaries:

- **GUI layer**: authoring, interaction, visualization, run control
- **API layer**: “run workflow”, stream logs, expose observability artifacts
- **Engine layer**: deterministic execution of workflow nodes
- **Domain layer**: biology and microenvironment models
- **I/O layer**: data products for analysis and visualization

The most important engineering rule in practice is:

> Workflow nodes should be *domain logic* and should not depend on GUI state.

The GUI produces a workflow JSON; the engine consumes it.

## 3.4 Data flow: from workflow design to results

The typical end-to-end flow:

1. User composes a workflow in the GUI.
2. GUI exports JSON and sends it to backend API.
3. Backend writes the workflow file and sets up results directories.
4. Backend launches the engine with `--workflow ...` (optionally `--entry-subworkflow ...`).
5. Engine executes nodes:
   - updates context, population, diffusion fields
   - logs progress
   - produces outputs (CSV, plots, checkpoints, observability artifacts)
6. GUI streams logs during the run and shows results afterward.

## 3.5 The workflow “context” as the runtime glue

The engine passes a shared context object across nodes. This context typically includes:

- simulation configuration (dt, step counters, parameters)
- population state
- diffusion simulator state / substance fields
- gene network models
- results collectors / output paths

This is a practical choice: it gives workflow nodes a consistent way to exchange state without requiring tight coupling between all modules.

The tradeoff is that context can become “a junk drawer” if not governed by conventions. The observability spec recommends key prefixes (e.g. `sim:*`, `node:*`, `user:*`) to help manage this.

## 3.6 Suggested figures (for this chapter)

- **Figure 1 — System architecture diagram**
  - GUI (React) ↔ Backend (Flask) → Engine (Python)
  - Outputs: `results/` (plots/CSVs/checkpoints/observability)

- **Figure 2 — Dataflow sequence**
  - A simple sequence diagram: “Design → Export JSON → Run → Stream logs → Browse results.”

- **Figure 3 — Repo structure screenshot**
  - A tree view focusing on `opencellcomms_engine/`, `opencellcomms_gui/`, and `docs/`.

