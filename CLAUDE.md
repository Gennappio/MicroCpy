# CLAUDE.md
CLAUDE.md
Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

State your assumptions explicitly. If uncertain, ask.
If multiple interpretations exist, present them - don't pick silently.
If a simpler approach exists, say so. Push back when warranted.
If something is unclear, stop. Name what's confusing. Ask.
2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

No features beyond what was asked.
No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.
No error handling for impossible scenarios.
If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:

Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it - don't delete it.
When your changes create orphans:

Remove imports/variables/functions that YOUR changes made unused.
Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.

4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

"Add validation" → "Write tests for invalid inputs, then make them pass"
"Fix the bug" → "Write a test that reproduces it, then make it pass"
"Refactor X" → "Ensure tests pass before and after"
For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.


## Purpose of the software
The software is a multi-scale cellular simulation platform for biological systems. The idea is to easily create workflows for simulating biological systems. The software is designed to be used with the GUI, but can also be used with the command line. The GUI is a visual workflow designer that allows users to create and edit workflows without writing code. The command line interface allows users to run workflows and simulations. The software is designed to be used by biologists and biologist developers. The software is not designed to be used only by software developers but to enhanvce software developers-biologists cooperation. 
The idea is to make agent based models easy to understand, share, run and modify. The main objective is to have a platfomr where verify biological hypotheses.
A scientist must be capable to understand mechanism tested from the GUI. The code must be mostly visible and understandable from the GUI. Once tested, designed and validate, the code can be run by CLI.

## Repository Structure

This repo is the OpenCellComms project. The outer repo (`MicroCpy3D`) tracks it as a git submodule (currently on the `Abstraction` branch). All real work happens here.

## Commands

All commands run from the project root unless otherwise noted.

### Python Engine (`opencellcomms_engine/`)

```bash
# Development install
make install-dev          # pip install -e ".[dev,docs,jupyter,performance,visualization]"

# Testing
make test                 # pytest tests/ -v
make test-fast            # pytest tests/ -v -m "not slow"
make test-unit            # pytest tests/unit/ -v
make test-integration     # pytest tests/integration/ -v
make test-coverage        # pytest tests/ --cov=src --cov-report=html

# Single test
pytest tests/path/to/test_file.py::test_function_name -v

# Linting & formatting
make lint                 # flake8 src/ tests/ && mypy src/
make format               # black src/ tests/ && isort src/ tests/
make format-check         # Check only, no changes

# CLI simulation run
python run_workflow.py --workflow path/to/workflow.json
python run_workflow.py --sim path/to/config.yaml
```

### React GUI (`opencellcomms_gui/`)

```bash
npm run dev               # Dev server on port 3000
npm run build             # Production build to dist/
npm run lint              # ESLint
```

### Full Stack

```bash
./install.sh              # One-time setup: venv + engine + GUI dependencies
./run.sh                  # Start Flask (port 5001) + Vite (port 3000)
```

## Architecture

OpenCellComms is a **multi-scale cellular simulation platform** for biological systems. It has three layers:

### 1. Python Engine (`opencellcomms_engine/src/`)

Simulates biological systems via a **workflow execution model**:
- **`workflow/`** — Reads a workflow JSON, dispatches functions by stage, manages shared `context` dict
- **`biology/`** — `Cell`, `Population`, `BooleanNetwork` classes (agent-based models)
- **`simulation/`** — `Simulator` orchestrator; `DiffusionSolver` (FiPy PDE for chemical gradients)
- **`workflow/functions/`** — Registered Python functions organized by stage: `initialization/`, `intracellular/`, `diffusion/`, `intercellular/`, `finalization/`, `gene_network/`, `output/`
- **`config/`**, **`io/`**, **`visualization/`** — Supporting infrastructure

### 2. React GUI (`opencellcomms_gui/src/`)

Visual drag-and-drop workflow designer built on **React Flow**:
- `WorkflowCanvas.jsx` — Main node-based canvas
- `FunctionPalette.jsx` — Sidebar of available simulation functions
- `WorkflowFunctionNode.jsx` — Individual node component
- `ParameterEditor.jsx` — Node parameter configuration panel
- `store/workflowStore.js` — Zustand state (workflow graph, execution state)
- `data/functionRegistry.js` — Maps GUI nodes to engine functions

### 3. Flask Backend (`opencellcomms_gui/server/api.py`)

Bridges GUI and engine:
- `POST /api/run` — Accepts workflow JSON, spawns `run_workflow.py` subprocess
- `GET /api/logs` — Streams simulation output via Server-Sent Events (SSE)
- `POST /api/stop` — Terminates simulation subprocess
- `GET /api/status`, `GET /api/health` — Status endpoints

## Workflow JSON Format (v2.0)

Workflows are JSON documents with **stages** containing **nodes** (function calls) connected by edges. The v2.0 system supports **subworkflows** — reusable, modular workflow components that can be nested. All functions share a `context` dict that flows through the pipeline.

Execution stages in order: `initialization → intracellular → diffusion → intercellular → finalization`

## Gene Network Pattern

Gene networks are stored in `context['gene_networks']`, **not** in `cell.state`. Each cell has its own `BooleanNetwork` instance. Use the provided helpers:

```python
get_gene_network(context, cell_id)
set_gene_network(context, cell_id, gene_network)
remove_gene_network(context, cell_id)
```

Cell state only stores `gene_states: Dict[str, bool]` (current gene values). Boolean update modes: `"netlogo"` (random single gene), `"synchronous"` (all at once), `"asynchronous"` (all, random order).

## Key References

- `docs/PLUGINS.md` — What a plugin (adapter) is: structure, `plugin.toml` manifest, auto-discovery, name-collision rules
- `docs/BIOLOGICAL_CONTEXT.md` — Typed `env: BiologicalContext` authoring API (recommended for new functions)
- `docs/GENE_NETWORK_GUIDE.md` — Deep dive on gene network architecture
- `opencellcomms_engine/README.md` — Engine overview
- `docs/engine/GETTING_STARTED.md` — Tutorial
- `docs/engine/UPDATE_MECHANISMS_COMPARISON.md` — Boolean update mode tradeoffs

## Workflow JSON & GUI Readability

- **Never inline complex values** (dicts, lists) directly in a function node's `"parameters"`. They render as unreadable flat strings in the GUI.
- **Use `dictParameterNode`** for dict-typed parameters: create a node in the subworkflow's `"parameters"` array with `target_param` pointing to the function parameter name, and link it via `"parameter_nodes"` on the function node. Same for `listParameterNode`.
- **Prefer DICT parameters over many individual BOOL/FLOAT parameters** in `@register_function`. A single `"type": "DICT"` is more flexible and renders as an editable table in the GUI.
- **Design for the GUI first.** A scientist must be able to read and modify parameters visually. If it's not readable in the canvas, it's wrong.

## Every behavior must belong to a navigable category (NO orphans)

This is non-negotiable, and it is the #1 thing that breaks when a workflow JSON is
written or edited by hand instead of through the GUI.

Every behavior subworkflow named anywhere in `metadata.gui` (and every behavior the
`__scheduler__` calls) **must** be listed under a category that maps to a real,
clickable tab in the GUI. The navigable tabs are exactly:
**Overview · Agents · Resources · Space · Initialization · Scheduler · Planner ·
Processing · Results** (`opencellcomms_gui/src/components/MainTabSelector.jsx`).

The homing rule, by where the behavior runs:

- **In-loop behaviors** (called inside `__scheduler__`, run every step) → an
  **owning object**: `agent_kinds[k].behavior_subworkflows` or
  `resource_kinds[k].behavior_subworkflows`. Assign by *primary actor*:
  `agent_behavior` → that agent kind; `resource_behavior` → that resource kind;
  `coupling` / `reconciliation` / in-loop `reporting` → the agent or resource kind
  that primarily drives it. (A coupling like `gene_update` is what the *cell* does
  each step → it is a `tumor_cell` behavior, not a free-floating one.)
- **Post-loop behaviors** (run once after `__scheduler__`, in `main`) →
  `processing.behavior_subworkflows`.

- **NEVER** put a behavior in **`environment.behavior_subworkflows`**. There is **no
  Environment tab** in the current GUI — that category routes to a dead view
  (`App.jsx` still has the `'environment'` case, but `MainTabSelector.jsx` has no
  button to reach it). A behavior placed there is an **orphan**: you can click it
  from the scheduler call-node and see the canvas, but it belongs to no tab, has no
  owner, and a scientist cannot find or edit it. This is exactly the failure mode
  that produced `gene_network_update_test.json`.

If a behavior genuinely cannot be attributed to any object, the **Processing** tab
is the only legitimate catch-all — never Environment, and never a bare
`__scheduler__` call with no category. `environment.init_subworkflow` /
`space.subworkflow` for world *setup* are a separate matter (they surface via the
Initialization / Space tabs); the prohibition here is specifically on **behavior**
subworkflows. The legacy `BEHAVIOR_LIBRARY_MANUAL.md` text that calls Environment
"a host for cross-object process roles" is superseded by this rule.

## The ABM class layer is authored WITH nodes (never replace the canvas)

The class layer (`src/abm/`, `docs/ABM_LAYER.md`, `docs/ABM_GUI.md`) does **not**
change the rule above: **every custom function is a node = a `.py` file**, on a
canvas, with the palette, code generation, planner parameters, and run/observability
popups. The canvas is the product; the class layer is built *through* it, not
instead of it. (A previous attempt that replaced canvases with forms was reverted.)

What the class layer actually adds is small and additive:
- A typed `env` API the node-functions call: `env.space`, `env.agent`,
  `agent.neighbors()`, `agent.sense('sugar')`, `env.resource('sugar')`. The
  classes in `src/abm/` (Space / Resource / Agent / Population / Domain) are that
  API — they are what the nodes call, not a hidden runner. Only the Space mechanics
  and the per-agent iteration live in library code; all behaviours are nodes.
- An entity organization that mostly already exists: **Agents** (kinds with
  Setup/Step canvases) and **Resources** (the same, mirrored), plus **World**
  (the Space `setup_space` node + the init orchestration + a preview) and
  **Scheduler** (the loop). World = init orchestration; Scheduler = loop
  orchestration — symmetric.
- **One file = one node = one atomic function.** A *behaviour* is a **subworkflow
  of atomic nodes** (e.g. a forager Step = `move_to_best_sugar` → `eat_sugar` →
  `metabolize`), shown as one call-node in an orchestration canvas.

**The executor owns the loop** (the `__scheduler__` subworkflow, iterated). One new
capability: the **per-agent "ask"** — a `subworkflow_call` with
`for_each: {kind, order}` runs the called behaviour subworkflow **once per agent**
of that kind, binding the current agent so each inner node sees `env.agent`. Agent
**Setup** (placement) runs once; agent **Step** runs per-agent; resource/collective
behaviours run once.

When building for the class layer: write **atomic node-functions** that use the
typed `env` API, place them on the entity canvases, and order them in the World
(init) and Scheduler (loop) canvases. Do **not** build forms and do **not** collapse
the simulation into one mega-node.

## Adding a new function

Most new functions are **experiment-specific** and belong in a **plugin** (an
`opencellcomms_adapters/<plugin>/` package). See `docs/PLUGINS.md` for the full
model. Use the typed `env: BiologicalContext` template
(`src/workflow/functions/_TEMPLATE.py`).

**Experiment-specific functions** (hardcoded gene names, substance thresholds,
model-specific logic) go in a plugin:

1. Create the file in `opencellcomms_adapters/<plugin>/functions/<category>/`
2. Write the function and decorator (typed `env`, `requires=[...]`, `compatible_kernels`)
3. Import it in `opencellcomms_adapters/<plugin>/register.py`
4. Restart the backend — the plugin is **auto-discovered** (no `registry.py` edit)

The GUI does steps 1–3 for you: **Library → New Function** picks/creates a plugin
and derives the file path; **Export Behavior** writes the files and seeds
`register.py` + `plugin.toml`.

**Generic (reusable) engine functions** — diffusion solvers, IO, kernel setup —
go in the engine:

1. Create a new file in `opencellcomms_engine/src/workflow/functions/<category>/`
2. Write the function and decorator
3. Import it in `opencellcomms_engine/src/workflow/functions/<category>/__init__.py`
   (pulled in via `standard_functions.py` — no `registry.py` edit needed)
4. Restart the backend server
5. **Use the template:** Copy `src/workflow/functions/_TEMPLATE.py` as a starting point.
6. If needed see `docs/CREATING_FUNCTIONS.md`.

---

## Biologist's Guide: Writing Simulation Code

This section is for biologists and non-engineers. You do not need to understand Python architecture to add a new biological rule to a simulation. Use the `/occ_new-function` slash command in Claude Code and answer a few plain-English questions — Claude will generate and place the code for you.

### The `context` dictionary — what's available inside any function

Every function receives a single `context` dict. Here are the keys you will need:

| What you want | Code | Notes |
|---|---|---|
| Loop over all cells | `for cell in context['population'].cells:` | `cell.id`, `cell.position`, `cell.state.phenotype` |
| Cell position (x, y or x, y, z) | `x, y = cell.position[0], cell.position[1]` | 2D sim; add `z = cell.position[2]` for 3D |
| Substance concentration at a cell | `context['simulator'].get_substance_concentration('oxygen', x, y)` | Returns float in simulation units |
| Mark a cell as dying | `cell.state.phenotype = 'apoptotic'` | Also: `'necrotic'`, `'growth_arrested'`, `'proliferating'` |
| Read a gene node state | `context['gene_networks'][cell.id].nodes['GeneName'].current_state` | Returns `True` (ON) or `False` (OFF) |
| Set a gene node state | `context['gene_networks'][cell.id].nodes['GeneName'].current_state = True` | |
| Current simulation step | `context['current_step']` | Integer |
| Time step size (hours) | `context['dt']` | Float |
| Substance→gene input mappings | `context['associations']` | Dict |
| Store results | `context['results']['my_key'] = value` | Persists across steps |

### Biological patterns — copy-paste recipes

**Pattern 1: Environmental trigger → cell death**
```python
# Kill cells when oxygen drops below a threshold
for cell in context['population'].cells:
    x, y = cell.position[0], cell.position[1]
    oxygen = context['simulator'].get_substance_concentration('oxygen', x, y)
    if oxygen < necrosis_threshold:
        cell.state.phenotype = 'necrotic'
```

**Pattern 2: Gene network output → proliferation decision**
```python
# A cell divides only if the 'Proliferation' gene is ON
for cell in context['population'].cells:
    gn = context['gene_networks'].get(cell.id)
    if gn and gn.nodes['Proliferation'].current_state:
        cell.state.phenotype = 'proliferating'
```

**Pattern 3: Substance concentration → boolean gene input**
```python
# Convert analog oxygen level to a binary gene input
for cell in context['population'].cells:
    x, y = cell.position[0], cell.position[1]
    oxygen = context['simulator'].get_substance_concentration('oxygen', x, y)
    gn = context['gene_networks'].get(cell.id)
    if gn and 'Oxygen' in gn.nodes:
        gn.nodes['Oxygen'].current_state = (oxygen > oxygen_threshold)
```

**Pattern 4: Population census**
```python
# Count cells by phenotype and store
counts = {}
for cell in context['population'].cells:
    ph = cell.state.phenotype
    counts[ph] = counts.get(ph, 0) + 1
context['results']['phenotype_counts'] = counts
```

### Biological terms → code concepts

| Biologist says | Code means |
|---|---|
| "cell dies" | `cell.state.phenotype = 'apoptotic'` (programmed) or `'necrotic'` (stress) |
| "cell divides" | `cell.state.phenotype = 'proliferating'` (triggers `update_cell_division`) |
| "cell stops growing" | `cell.state.phenotype = 'growth_arrested'` |
| "oxygen gradient / oxygen at position" | `context['simulator'].get_substance_concentration('oxygen', x, y)` |
| "glucose level" | `context['simulator'].get_substance_concentration('glucose', x, y)` |
| "gene is ON / expressed" | `network.nodes['GeneName'].current_state = True` |
| "gene is OFF / silenced" | `network.nodes['GeneName'].current_state = False` |
| "each cell, every step" | `for cell in context['population'].cells:` inside any intracellular function |
| "substance diffuses" | handled by `run_diffusion_solver_coupled` in the diffusion stage — no code needed |
| "initial condition" | a function in the `initialization` stage (runs once at t=0) |

### Stage selection guide

| When does this rule fire? | Use stage |
|---|---|
| Once at the start of the simulation | `initialization` |
| Every step, inside each cell (gene networks, metabolism) | `intracellular` |
| Every step, between cells (division, death, migration) | `intercellular` |
| Every step, chemical diffusion | `diffusion` |
| At the end of the simulation (plots, export) | `finalization` |

### Full "add a function" recipe (mechanical steps)

```
For EXPERIMENT-SPECIFIC functions (hardcoded names/thresholds) — i.e. a PLUGIN:

1. Create:  opencellcomms_adapters/<plugin>/functions/<category>/<my_function>.py
            Copy _TEMPLATE.py as starting point; fill in decorator fields.
2. Import:  opencellcomms_adapters/<plugin>/register.py
            Add:  from opencellcomms_adapters.<plugin>.functions.<category>.<my_function> import <my_function>
            (For a NEW plugin, also add __init__.py files + a plugin.toml — or
             let the GUI's New Function / Export Behavior do all of this.)
            The engine auto-discovers the plugin; no registry.py edit.

For GENERIC engine functions (diffusion/IO/kernel — reusable across experiments):

1. Create:  opencellcomms_engine/src/workflow/functions/<category>/<my_function>.py
            Copy _TEMPLATE.py as starting point; fill in decorator fields.
2. Register in category:
            opencellcomms_engine/src/workflow/functions/<category>/__init__.py
            Add:  from .<my_function> import <my_function>
                  and add '<my_function>' to __all__
            (Pulled in via standard_functions.py — no registry.py edit.)

Then for both:

4. Enable in workflow JSON:
            In the target workflow JSON, inside the appropriate subworkflow's
            "nodes" array, add a node with "function": "<my_function>", "enabled": true.

5. Restart backend:  ./run.sh   (or Ctrl+C then ./run.sh)
   The function now appears in the GUI function palette.
```
