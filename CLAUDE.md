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

This repository is the OpenCellComms project; treat its root as the working directory.

## Commands

All commands run from the project root unless otherwise noted.

### Python Engine (`opencellcomms_engine/`)

```bash
# Development install
make install-dev          # installs dev tooling plus active diffusion/MaBoSS extras

# Testing
make test                 # pytest tests/ -v
make test-fast            # pytest tests/ -v -m "not slow"
make test-coverage        # pytest tests/ --cov=src --cov-report=html

# Single test
pytest tests/path/to/test_file.py::test_function_name -v

# Linting & formatting
make lint                 # flake8 src/ tests/ && mypy src/
make format               # black src/ tests/ && isort src/ tests/
make format-check         # Check only, no changes

# CLI simulation run
occ-run --workflow path/to/workflow.json
occ-run --sim path/to/config.yaml
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

Workflows are JSON documents with **subworkflows** containing ordered function
nodes and nested subworkflow calls. The GUI's `main` composer sequences
`__init_sequence__`, `__scheduler__`, and processing behaviors. All functions
share a context that is exposed to new biological functions through the typed
`BiologicalContext` API.

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

## Prefer the typed `env: BiologicalContext` over `raw_context`

Where a capability exists on the typed `env` API, use it — do not reach into
`env.raw_context` (or take the raw `context: Dict`) for something that already has a
typed accessor. `env.config`, `env.cells` / `env.agents`, `env.world`,
`env.resource(name)`, `env.concentration(...)`, `env.record(...)`, `env.rng`,
`env.plots_dir` all exist for exactly this. The typed layer owns coordinate
conversion and kernel-gating and reads clearly in the GUI.

- **The tell:** a function typed `env: BiologicalContext` whose body's first move is
  `ctx = env.raw_context` to pull something with an accessor (e.g. `ctx["config"]`
  instead of `env.config`) is a bug. Use the accessor, or be honest it is
  infrastructure and take `context: Dict` with `typed_env_exempt=True`.
- **`raw_context` is a real escape hatch — for genuinely unsupported cases only:** a
  plugin-private context key, or an operation the typed layer can't express (e.g.
  assembling a custom FiPy PDE). "Where possible" is the operative clause.
- **A recurring `raw_context` use is a backlog item for the typed layer, not a
  resting place.** If you keep reaching past `env` for the same capability (a
  substance's decay rate, a field solve), promote it — a config field on the
  substance/resource, or a verb in `src/abm/resource.py` — instead of copying the
  escape hatch into the next plugin.

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
**Overview · Agents · Resources · World · Initialization · Scheduler · Planner ·
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

- **NEVER** park a resource's dynamics in **`world.behavior_subworkflows`**. A
  behavior whose *primary actor* is a named substance/field (diffusion, decay,
  secretion, uptake of e.g. `CCL21`) belongs under that substance's
  **`resource_kinds[k]`** — `init_subworkflow` = the field's registration/Setup,
  `behavior_subworkflows` = its per-tick Step. World *is* a real tab, so a resource
  behavior parked there is **reachable** and passes the no-orphan check above — but
  it is still **mis-homed**: a scientist looking for the CCL21 resource opens
  **Resources**, not **World**. `world.behavior_subworkflows` is only for
  world-level *lattice* mechanics with no owning entity (e.g. move-intent
  `reconciliation`). Two tells you got this wrong: a behavior that reads or writes a
  named substance field sitting under World, and a plugin that has diffusing
  substances but an **empty `resource_kinds`** (the substance is being smuggled in
  as world infrastructure — give it a resource kind). Being collective /
  once-per-step (`no for_each`) does **not** make it World; a resource's Step is
  collective too. `for_each`-ness is *how* a behavior runs, not *who owns it*.

If a behavior genuinely cannot be attributed to any object, the **Processing** tab
is the only legitimate catch-all — never Environment, and never a bare
`__scheduler__` call with no category. `environment.init_subworkflow` /
`world.subworkflow` for world *setup* are a separate matter (they surface via the
Initialization / World tabs); the prohibition here is specifically on **behavior**
subworkflows. The legacy `BEHAVIOR_LIBRARY_MANUAL.md` text that calls Environment
"a host for cross-object process roles" is superseded by this rule.

## The ABM class layer is authored WITH nodes (never replace the canvas)

The class layer (`src/abm/`, `docs/ABM_LAYER.md`, `docs/ABM_GUI.md`) does **not**
change the rule above: **every custom function is a node = a `.py` file**, on a
canvas, with the palette, code generation, planner parameters, and run/observability
popups. The canvas is the product; the class layer is built *through* it, not
instead of it. (A previous attempt that replaced canvases with forms was reverted.)

What the class layer actually adds is small and additive:
- A typed `env` API the node-functions call: `env.world`, `env.agent`,
  `agent.neighbors()`, `agent.sense('sugar')`, `env.resource('sugar')`. The
  classes in `src/abm/` (World / Resource / Agent / Population / Domain) are that
  API — they are what the nodes call, not a hidden runner. Only the World mechanics
  and the per-agent iteration live in library code; all behaviours are nodes.
- An entity organization that mostly already exists: **Agents** (kinds with
  Setup/Step canvases) and **Resources** (the same, mirrored), plus **World**
  (the World `setup_world` node + the init orchestration + a preview) and
  **Scheduler** (the loop). World = init orchestration; Scheduler = loop
  orchestration — symmetric.
- **One file = one node = one atomic function.** A *behaviour* is a **subworkflow
  of atomic nodes** (e.g. a forager Step = `move_to_best_sugar` → `eat_sugar` →
  `metabolize`), shown as one call-node in an orchestration canvas.

**The executor owns the loop** (the `__scheduler__` subworkflow, iterated). One new
capability: the **per-agent "ask"** — a `subworkflow_call` with
`for_each: {kind, order}` runs the called behaviour subworkflow **once per agent**
of that kind, binding the current agent so each inner node sees `env.agent`.

**An agent kind has exactly two canvases; know which runs collectively and which runs
per-agent — don't confuse them just because they live "under the agent kind":**
- **Creation** (`create_subworkflow`, authored in the **World** tab — the collective
  *Creation* canvas; e.g. `tcell_create`) runs **once**, collectively, with **no
  `for_each`**. This is where agents are brought into existence — placement, wrapping
  into the ABM population, **any once-only per-cell setup** (assign each cell's gene
  network, clamp its nodes), and any parse-once shared setup. `env.agent` is `None`;
  work on the whole population (`for cell in env.cells:` or
  `env.population.populate(...)`). You cannot iterate agents before they exist, so
  creation is collective by definition, and it lives in World/Init (ordered in the
  Initialization tab).
- **Per-agent step** (`behavior_subworkflows`, e.g. `tcell_step`) is the **only**
  canvas in the **Agents** tab — it runs **once per agent** each tick via the
  scheduler's `for_each` ask (every agent node runs per-agent). `env.agent`/`env.cell`
  is the bound agent; no cell loop.

There is **no separate per-agent init phase**: once-only per-cell setup is done
collectively in the Creation canvas (`for cell in env.cells:`), not a `for_each` pass.

**The tell:** `for cell in env.cells:` (or `populate`) → a once-run **collective
creation** function (the kind's Creation canvas). `env.agent` / `env.cell` → a
**per-agent Step**. The *canvas* decides how it runs — check which canvas a function
sits on. The two classic mistakes are symmetric: `for_each` on a collective creation
call (re-creates everything once per agent), and an internal `for cell` loop inside a
per-agent Step (double-iterates).

**These structural rules are enforced, not just documented.**
`scripts/validate_workflow.py` (run by the CLI, the pre-commit hook, and the
`/occ_new-*` skills) **hard-errors**: a `create_subworkflow` scheduled with `for_each`
(creation is collective), and an agent kind that declares a per-agent
`init_subworkflow` (that phase was removed — fold its per-cell setup into the Creation
canvas). It **warns** when agent kinds exist but no creation is scheduled anywhere. The
GUI mirrors these on the **Overview** tab and blocks **Export** on the same errors, so a
structurally-invalid ABM is caught before it can run. A kind created collectively
inside *another* kind's creation canvas (it has no `create_subworkflow` of its own,
e.g. TCELL_CORRAL's `dendritic_cell`) is intentionally not errored — that is the warn
case, not a hard failure.

**Copy examples only from canonical workflows** — `MicroC/workflows/microc.json`,
`TCELL_CORRAL/workflows/tcell_corral.json`, `SUGARSCAPE/workflows/sugarscape.json`.
**Never** copy from a workflow carrying `metadata.validation.skip: true` (archived
pre-migration checkpoints / stress fixtures like `gene_network_update_test*`,
`tcell_corral_ccl21/_intracellular/_spatial`, `test_gui`) — they are deliberately
un-migrated and encode the old structure.

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

**There is no custom-functions hook file.** The legacy mechanism (a Python
module loaded by path via `setup_population`'s `custom_functions_module` and
called invisibly by `Cell`/`CellPopulation`/plotters) is **removed** from
workflow authoring: the parameter no longer exists and
`scripts/validate_workflow.py` errors on any workflow that sets it. All model
behavior is registered plugin functions; plot styling is passed explicitly
(e.g. `AutoPlotter(..., cell_color_fn=...)` from the plugin's reporting
function). Archived workflows still carrying the parameter are
`validation.skip` references — never copy from or "fix" them
(see `docs/PLUGINS.md`).

---

## Biologist's Guide: Writing Simulation Code

This section is for biologists and non-engineers. You do not need to understand Python architecture to add a new biological rule to a simulation. Use the `/occ_new-function` slash command in Claude Code and answer a few plain-English questions — Claude will generate and place the code for you.

### The typed `env` — what's available inside a function

New biological functions receive `env: BiologicalContext`. Use these accessors
instead of reaching into the raw context or engine state:

| What you want | Code | Notes |
|---|---|---|
| Loop over all cells | `for cell in env.cells:` | `cell.id`, `cell.position`, `cell.phenotype` |
| Cell position (x, y or x, y, z) | `x, y = cell.position[0], cell.position[1]` | 2D sim; add `z = cell.position[2]` for 3D |
| Substance concentration at a cell | `env.concentration('oxygen', cell)` | Returns float in simulation units |
| Mark a cell as dying | `cell.mark_apoptotic()` | Also `mark_necrotic()`, `mark_growth_arrested()`, `mark_proliferating()` |
| Read a gene node state | `cell.gene('GeneName').is_on()` | Check for `None` when a node is optional |
| Set a gene node state | `cell.gene('GeneName').turn_on()` | Also `turn_off()` and `set(bool)` |
| Current simulation step | `env.step` | Integer |
| Time step size (hours) | `env.dt` | Float |
| Store a result | `env.results.store('my_key', value)` | Persists across steps |

### Biological patterns — copy-paste recipes

**Pattern 1: Environmental trigger → cell death**
```python
# Kill cells when oxygen drops below a threshold
for cell in env.cells:
    oxygen = env.concentration('oxygen', cell)
    if oxygen < necrosis_threshold:
        cell.mark_necrotic()
```

**Pattern 2: Gene network output → proliferation decision**
```python
# A cell divides only if the 'Proliferation' gene is ON
for cell in env.cells:
    proliferation = cell.gene('Proliferation')
    if proliferation and proliferation.is_on():
        cell.mark_proliferating()
```

**Pattern 3: Substance concentration → boolean gene input**
```python
# Convert analog oxygen level to a binary gene input
for cell in env.cells:
    oxygen = env.concentration('oxygen', cell)
    oxygen_gene = cell.gene('Oxygen')
    if oxygen_gene:
        oxygen_gene.set(oxygen > oxygen_threshold)
```

**Pattern 4: Population census**
```python
# Count cells by phenotype and store
counts = {}
for cell in env.cells:
    ph = cell.phenotype
    counts[ph] = counts.get(ph, 0) + 1
env.results.store('phenotype_counts', counts)
```

### Biological terms → code concepts

| Biologist says | Code means |
|---|---|
| "cell dies" | `cell.mark_apoptotic()` (programmed) or `cell.mark_necrotic()` (stress) |
| "cell divides" | `cell.mark_proliferating()` (triggers division) |
| "cell stops growing" | `cell.mark_growth_arrested()` |
| "oxygen gradient / oxygen at a cell" | `env.concentration('oxygen', cell)` |
| "glucose level" | `env.concentration('glucose', cell)` |
| "gene is ON / expressed" | `cell.gene('GeneName').turn_on()` |
| "gene is OFF / silenced" | `cell.gene('GeneName').turn_off()` |
| "each cell, every step" | `env.cell` in a scheduler `for_each` behavior; do not add a second loop |
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
