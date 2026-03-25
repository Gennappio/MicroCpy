# Technical Details — OpenCellComms

This document is a **deep technical description** of the software in this repository, written so that another LLM (or engineer) can understand:

- what the system does,
- how it is structured,
- how the runtime works end-to-end,
- how workflows are represented and executed,
- how extensibility works,
- where outputs go,
- and how to debug/observe a run.

> In this document, **OpenCellComms** refers to the overall platform, **engine** refers to `opencellcomms_engine/`, and **GUI** refers to `opencellcomms_gui/`.

## 1) What the software does (problem statement)

OpenCellComms is a **multi-scale biological simulation platform** combining:

- **Cell populations (ABM)**: per-cell state, division, migration, death, phenotype changes
- **Microenvironment diffusion (PDE)**: chemical gradients solved via **FiPy**
- **Intracellular decision logic**: Boolean gene networks (optional **MaBoSS/pyMaBoSS** integration)

The distinctive engineering idea is that simulations are defined as **workflows**:

- a structured workflow JSON file describes:
  - what functions run,
  - in what order,
  - with which parameters,
  - organized by stage/subworkflow.
- the engine executes this workflow using a shared **context** object that carries state.

The system includes a **visual workflow designer** (GUI) that can build/edit workflows without writing code.

## 2) Repository structure (major components)

At repo root (`OpenCellComms/`):

- `opencellcomms_engine/`: Python simulation engine, workflow runtime, models, solvers, tools, tests
- `opencellcomms_gui/`: React GUI (workflow designer) + Flask server used to run the engine from the GUI
- `docs/`: documentation (installation, usage, workflow format, custom functions, etc.)
- `install.sh` / `install.bat`: one-click setup scripts
- `run.sh` / `run.bat`: one-click launch scripts (GUI + backend)

### 2.1 Engine structure (`opencellcomms_engine/`)

Key entry points:

- `run_workflow.py`: **master CLI** / runner that can:
  - run simulations in “config-only” mode (`--sim ...`)
  - run workflow-only mode (`--workflow ...`)
  - run “workflow + config setup” mode (`--sim ... --workflow ...`)
  - generate 2D CSV initial cell layouts (`--generate-csv ...`)
  - plot CSV results (`--plot-csv ...`)

Core source code lives in `opencellcomms_engine/src/`:

- `src/workflow/`: workflow format, registry, executor, loader, schema, standard functions
- `src/workflow/functions/`: the built-in function library, organized by category
- `src/workflow/observability/`: node-level observability: events, snapshots, tracked context
- `src/biology/`: core biology entities (cell, population, gene network)
- `src/simulation/`: diffusion and simulation orchestration
- `src/io/`: I/O helpers (initial state, domain loaders)
- `src/visualization/`: plotting, export, analysis tooling
- `src/config/`: YAML config and templates

### 2.2 GUI structure (`opencellcomms_gui/`)

- `src/`: React app
  - node components (workflow nodes, inspector, results explorer, etc.)
  - state store (`Zustand`)
  - validation/layout utilities
- `server/api.py`: Flask backend
  - validates workflows
  - creates/clears results directories (overwrite semantics)
  - launches engine as a subprocess
  - streams stdout/stderr to the frontend in real-time
- `server/workflows/`: example workflow JSON files (including MaBoSS demo)
- `results/`: example output artifacts (heatmaps, checkpoints, etc.) — currently present in repo

## 3) Workflow concept and file formats

Workflows are JSON files that define:

- the list of node “functions” available to run,
- execution ordering,
- parameters and parameter nodes (for GUI wiring),
- stages/subworkflows depending on version.

See `docs/WORKFLOW_STRUCTURE.md` for the authoritative description.

### 3.1 Workflow v1.0: stage-based

The v1 format uses explicit stages:

- `initialization`
- `macrostep` (outer loop controller)
- `intracellular`
- `diffusion`
- `intercellular`
- `finalization`

Each stage includes:

- `enabled`
- `steps` (how many times to run the stage per invocation)
- `functions`: array of function nodes
- `execution_order`: array of node IDs defining the exact order

**Example**: `opencellcomms_gui/server/workflows/jaya_workflow_2d_csv_macrostep.json` is a v1.0 workflow designed so “all parameters are configurable from the GUI.”

### 3.2 Workflow v2.0: subworkflow/composer-based

The v2 format generalizes into named subworkflows, with:

- a `main` composer that contains a controller and a sequence of:
  - function nodes
  - subworkflow call nodes
- subworkflows may be invoked multiple times (`iterations`)
and can map/override context/parameters.

The GUI stores subworkflow “kinds” in metadata (`composer` vs `subworkflow`) and the engine uses that to place outputs into different results folders (see “results layout”).

### 3.3 Node types and their semantics

Across formats, the “units of execution” include:

- **Workflow function nodes**
  - refer to a `function_name` that must exist in the engine registry
  - carry a parameters object and/or references to parameter nodes
  - can be enabled/disabled
- **Subworkflow call nodes** (v2)
  - invoke another subworkflow by name, optionally with iterations
- **Controller** (v2)
  - holds step count / loop control at the composer level
- **Parameter nodes** (GUI concept)
  - act as reusable parameter sources that can connect to function nodes

## 4) Workflow execution model (engine runtime)

### 4.1 Primary runtime class: `WorkflowExecutor`

The core executor is `opencellcomms_engine/src/workflow/executor.py` (`WorkflowExecutor`).

High-level responsibilities:

- validate workflow (`workflow.validate()`)
- maintain a registry mapping `function_name` → Python callable (`FunctionRegistry`)
- execute node sequences in the `execution_order`
- manage subworkflow calls and call stack
- optionally enable observability (events/snapshots)
- set up consistent filesystem paths into the shared context

#### Context path initialization (Clean Architecture)

`WorkflowExecutor.setup_context_paths()` centralizes filesystem path behavior and puts path keys into `context`, including:

- `engine_root`, `project_root`
- `workflow_file`, `workflow_dir`
- `resolve_path`: helper to resolve relative file paths using multiple strategies
- GUI integration flags:
  - `running_from_gui`
  - `gui_root`
  - `gui_results_dir`
- output paths:
  - `output_dir`
  - `plots_dir`
  - `data_dir`

This is a “clean architecture” decision: workflow node functions should not compute paths ad hoc.

#### Path resolution strategy

`create_path_resolver()` tries (in order):

1. absolute existing paths
2. paths relative to the workflow JSON directory
3. paths relative to engine root
4. common subdirectories (`tests/`, `tests/maboss_example/`)
5. GUI workflows directory (`opencellcomms_gui/server/workflows/`), including `maboss_example/`

This exists because workflows frequently refer to files (BND/CFG/CSV/YAML), and those files may live in different locations depending on whether runs happen from GUI or CLI.

### 4.2 The shared `context` object

All workflow functions are called with:

- `context: Dict[str, Any]`
- plus function parameters as keyword args

The `context` carries simulation state and runtime utilities. Typical keys (from docs and conventions):

- simulation objects: `population`, `simulator`, `gene_network`, `config`
- time: `dt`, `step`, `macrostep`
- output: `output_dir`, `plots_dir`, `data_dir`
- GUI integration: `running_from_gui`, `gui_results_dir`
- user-defined and node-defined keys

Because it is shared, context conventions matter. The observability spec recommends prefixes like:

- `sim:*` (global simulation state)
- `node:*` (node-local values)
- `user:*` (user-defined values)

### 4.3 Function registry and dynamic loading

The engine has:

- a default registry (`get_default_registry()`)
- a decorator-based registration mechanism (`@register_function(...)`, see `docs/CREATING_FUNCTIONS.md`)

Function nodes refer to `function_name` strings; the executor resolves them through:

- registry lookups
- caching in `self.function_cache`
- optional dynamic import from file (for custom modules/files)

### 4.4 Execution ordering and loops

For v1 workflows:

- `macrostep.steps` typically controls the number of simulation steps
- within each macrostep iteration, the executor triggers enabled stage execution orders

For v2 workflows:

- the `main` composer defines:
  - controller `number_of_steps`
  - an `execution_order` of function nodes and subworkflow calls
- subworkflow calls can repeat via `iterations`
- the executor tracks a call stack to prevent runaway recursion (`max_call_depth`)

## 5) Built-in function library (what nodes do)

Built-in node functions live under:

`opencellcomms_engine/src/workflow/functions/`

They are grouped into categories that correspond to GUI palette sections and conceptual timing:

- `initialization/`:
  - `setup_simulation`, `setup_domain`, `setup_environment`
  - `setup_population`, `load_cells_from_csv`, `load_cells_from_vtk`
  - `add_substance`, `setup_substances`, `finalize_substances`
  - `setup_gene_network`, `setup_maboss`, associations setup
  - `setup_output`, custom parameter setup
- `intracellular/`:
  - `update_metabolism`, `update_gene_networks`, `run_maboss_step`, `update_phenotypes`, death checks
- `diffusion/`:
  - diffusion solver calls and environment field updates (depends on configuration)
- `intercellular/`:
  - `update_cell_migration`, `update_cell_division`, removal of dead/apoptotic/necrotic cells
- `finalization/`:
  - save data, save MaBoSS results, print summary, generate final plots
- `debug/`:
  - debug dummy functions (useful for observability testing)

> Practical detail: workflows often expose nearly all function parameters via GUI “parameter nodes” so workflows are self-contained without requiring YAML configs.

## 6) Simulation domain details (biology + diffusion subsystems)

### 6.1 Biology subsystem (`src/biology/`)

Conceptually, it includes:

- `cell`: per-agent state (position, phenotype, age, gene states, etc.)
- `population`: collection of cells and helpers for updates
- `gene_network`: representation and update logic for GRNs and/or MaBoSS integration

Cell-level logic is primarily implemented in workflow node functions, not hidden inside an opaque engine loop.

### 6.2 Diffusion subsystem (`src/simulation/`)

The diffusion system uses FiPy (as stated in repository docs) and handles:

- one or more substances with diffusion coefficients and boundary conditions
- PDE solve loops per step
- interactions with cells (consumption/production) via source/sink terms

Multi-substance support is implemented by a simulator/orchestrator pattern (see files in `src/simulation/`).

## 7) GUI runtime and backend API

### 7.1 GUI responsibilities

The GUI (`opencellcomms_gui/src/`) is responsible for:

- authoring workflows visually (nodes/edges)
- providing parameter editing widgets
- import/export JSON workflows
- initiating runs and viewing logs
- displaying results and (optionally) observability insights

### 7.2 Backend API responsibilities (`opencellcomms_gui/server/api.py`)

The Flask server:

- receives workflow JSON from the GUI
- validates it (engine schema)
- writes it to disk (temporary workflow file)
- sets up results directories and clears old ones (overwrite semantics)
- launches the engine as a subprocess:
  - invokes `opencellcomms_engine/run_workflow.py` with:
    - `--workflow <path>`
    - `--gui-results-dir <absolute path to opencellcomms_gui/results>`
    - optional `--entry-subworkflow <name>`
- streams stdout/stderr through threads into a queue for the GUI to consume

The server is intentionally local and simple: it does not aim to be a multi-user service.

## 8) Results layout and overwrite semantics

### 8.1 Two modes: GUI vs CLI outputs

The engine uses `WorkflowExecutor.setup_context_paths()` to define output locations.

**GUI mode**:

- GUI passes `--gui-results-dir <.../opencellcomms_gui/results>`
- outputs go under GUI results directory, and are split by v2 “kind”:
  - `results/composers/<name>/...`
  - `results/subworkflows/<name>/...`

**CLI mode**:

- outputs go under engine results:
  - `opencellcomms_engine/results/composers/<name>/...`
  - `opencellcomms_engine/results/subworkflows/<name>/...`
  - plus subfolders `plots/` and `data/` depending on context keys

### 8.2 Overwrite semantics

The GUI server clears the results directory at the start of each run (see `setup_results_directories()` in `opencellcomms_gui/server/api.py`).

This aligns with the “scientific tool” philosophy described in `opencellcomms_gui/NODES_OBSERVABILITY.md`:

- only the current run’s artifacts are kept unless the user archives them manually.

## 9) Observability system (node-level debugging)

### 9.1 What observability is in this repo

Observability is designed to provide **node-level introspection**:

- per-node status and timing
- per-node logs
- context snapshots and diffs
- tracing through subworkflow calls

The design spec is documented in detail in:

- `opencellcomms_gui/NODES_OBSERVABILITY.md`

The engine contains implementation support in:

- `opencellcomms_engine/src/workflow/observability/`
  - `event_emitter.py`
  - `context_snapshot.py`
  - `tracked_context.py`
  - `validated_context.py`

### 9.2 Engine integration points

In `WorkflowExecutor.__init__()`:

- observability can be enabled/disabled via `observability_enabled`
- if enabled, it initializes:
  - a `NodeEventEmitter` (writes events, e.g. `events.jsonl`)
  - a `ContextSnapshotManager` (writes context versions and diffs)

In GUI terms, this supports:

- node badges (status/timing/log counts)
- inspector panels showing context diffs and logs for a node

### 9.3 TrackedContext + ValidatedContext

The design includes two complementary ideas:

- **TrackedContext**: logs which keys are read/written (so the system can report “this node wrote X keys”)
- **ValidatedContext**: optional enforcement of “write policies”:
  - strict/warn/off behavior for context writes

This helps keep the context from becoming ungoverned and makes debugging possible at scale.

## 10) Extensibility: adding custom workflow nodes

The primary extension mechanism is: **add a workflow function**.

See `docs/CREATING_FUNCTIONS.md` for step-by-step instructions.

Summary of the mechanism:

- Write a Python function that accepts `context` and parameters.
- Decorate it with `@register_function(...)` providing:
  - display name, description, category
  - parameter metadata (type, default, min/max/options)
- Ensure it is import-discovered:
  - placed under `src/workflow/functions/<category>/`
  - imported in the appropriate `__init__.py`
  - imported/registered via `src/workflow/registry.py` (depending on how auto-discovery is configured)

Once registered, it appears in the GUI palette and can be used in workflows.

## 11) Example workflows and demos

Important example assets:

- `opencellcomms_gui/server/workflows/jaya_workflow_2d_csv_macrostep.json`
  - v1 workflow exposing many parameters through parameter nodes (GUI-first)
- `opencellcomms_gui/server/workflows/maboss_workflow.json`
  - minimal MaBoSS demo workflow (stochastic Boolean network updates)
- `opencellcomms_gui/server/workflows/maboss_example/*`
  - includes `cell_fate_config.yaml`, `.bnd`, `.cfg`, and initial cells CSV

The MaBoSS demo is useful because it is small enough to understand end-to-end:

- initialization loads config, sets up MaBoSS, loads initial cells
- macrostep runs an intracellular sub-step
- finalization saves results and plots

## 12) Tooling: generators and post-processing

The engine CLI supports “side tasks” via `run_workflow.py`:

- `--generate-csv`: generate initial cell placement files for 2D sims
- `--plot-csv`: produce plots from CSV outputs without rerunning simulation

Additionally, `opencellcomms_engine/tools/` contains scripts for:

- CSV export/plotting
- VTK export and visualization demos
- cell state analyzers and visualizers
- H5 generation and inspection

Some tools already have example outputs committed (images + interactive HTML).

## 13) Testing and benchmarks

- `opencellcomms_engine/tests/` contains tests for:
  - workflow system behavior
  - decorator registration
  - experiment demos (e.g., jayatilake and maboss examples)
- `opencellcomms_engine/benchmarks/` contains benchmarking assets and scripts.

The project expects runs to be validated by executing workflows and comparing produced artifacts (plots/checkpoints) rather than only unit tests.

## 14) Known “sharp edges” / engineering risks

These are not necessarily bugs; they are areas where a new contributor should be careful:

- **Legacy naming references** (MicroC, BioComposer) in some places can confuse newcomers.
- **Path handling** is complex because workflows can reference many file types; the executor’s path resolver is designed to reduce friction, but file layout still matters.
- **Context sprawl** is a real risk; the observability + validated context system exists to mitigate it, but conventions must be followed.
- **Overwrite semantics** are deliberate but can surprise users; reproducibility requires explicit archiving practices.
- **Performance**: multi-scale coupling is expensive; diffusion solves and output frequency are typical bottlenecks.

## 15) Quick start for another LLM (what to read first)

If an LLM needs to answer questions or implement changes, the most informative sequence is:

1. `README.md` (repo overview)
2. `docs/USAGE.md` (how runs are invoked; outputs)
3. `docs/WORKFLOW_STRUCTURE.md` (workflow schema and semantics)
4. `docs/CREATING_FUNCTIONS.md` (extensibility contract)
5. Engine runtime:
   - `opencellcomms_engine/src/workflow/executor.py`
   - `opencellcomms_engine/src/workflow/registry.py`
   - `opencellcomms_engine/src/workflow/schema.py`
6. GUI backend runner:
   - `opencellcomms_gui/server/api.py`
7. Observability spec + implementation:
   - `opencellcomms_gui/NODES_OBSERVABILITY.md`
   - `opencellcomms_engine/src/workflow/observability/*`

