# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose of the software
The software is a multi-scale cellular simulation platform for biological systems. The idea is to easily create workflows for simulating biological systems. The software is designed to be used with the GUI, but can also be used with the command line. The GUI is a visual workflow designer that allows users to create and edit workflows without writing code. The command line interface allows users to run workflows and simulations. The software is designed to be used by biologists and biologist developers. The software is not designed to be used only by software developers but to enhanvce software developers-biologists cooperation. 
The idea is to make agent based models easy to understand, share, run and modify. The main objective is to have a platfomr where verify biological hypotheses.
A scientist must be capable to understand mechanism tested from the GUI. The code must be mostly visible and understandable from the GUI. Once tested, designed and validate, the code can be run by CLI.

## Repository Structure

This repo contains `MicroCpy/` as a git submodule (currently on the `Abstraction` branch). All real work happens inside `MicroCpy/`. The outer repo (`MicroCpy3D`) just tracks submodule state.

## Commands

All commands run from `MicroCpy/` unless otherwise noted.

### Python Engine (`MicroCpy/opencellcomms_engine/`)

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

### React GUI (`MicroCpy/opencellcomms_gui/`)

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

- `MicroCpy/GENE_NETWORK_GUIDE.md` — Deep dive on gene network architecture
- `MicroCpy/opencellcomms_engine/README.md` — Engine overview
- `MicroCpy/opencellcomms_engine/GETTING_STARTED.md` — Tutorial
- `MicroCpy/opencellcomms_engine/UPDATE_MECHANISMS_COMPARISON.md` — Boolean update mode tradeoffs

## Workflow JSON & GUI Readability

- **Never inline complex values** (dicts, lists) directly in a function node's `"parameters"`. They render as unreadable flat strings in the GUI.
- **Use `dictParameterNode`** for dict-typed parameters: create a node in the subworkflow's `"parameters"` array with `target_param` pointing to the function parameter name, and link it via `"parameter_nodes"` on the function node. Same for `listParameterNode`.
- **Prefer DICT parameters over many individual BOOL/FLOAT parameters** in `@register_function`. A single `"type": "DICT"` is more flexible and renders as an editable table in the GUI.
- **Design for the GUI first.** A scientist must be able to read and modify parameters visually. If it's not readable in the canvas, it's wrong.

## Adding a new function

1. Create a new file in `opencellcomms_engine/src/workflow/functions/<category>/`
2. Write the function and decorator
3. Import the function in `opencellcomms_engine/src/workflow/functions/<category>/__init__.py`
4. Import the module in `opencellcomms_engine/src/workflow/registry.py`
5. Restart the backend server
6. **Use the template:** Copy `src/workflow/functions/_TEMPLATE.py` as a starting point for new functions.
7. if needed look for the CREATING_FUNCTIONS.md in `MicroCpy/docs/CREATING_FUNCTIONS.md`

---

## Biologist's Guide: Writing Simulation Code

This section is for biologists and non-engineers. You do not need to understand Python architecture to add a new biological rule to a simulation. Use the `/new-function` slash command in Claude Code and answer three plain-English questions — Claude will generate and place the code for you.

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
1. Create:  opencellcomms_engine/src/workflow/functions/<category>/<my_function>.py
            Copy _TEMPLATE.py as starting point; fill in decorator fields.

2. Register in category:
            opencellcomms_engine/src/workflow/functions/<category>/__init__.py
            Add:  from .<my_function> import <my_function>
                  and add '<my_function>' to __all__

3. Register in engine:
            opencellcomms_engine/src/workflow/registry.py
            Add:  import src.workflow.functions.<category>.<my_function>
            (inside get_default_registry(), after similar imports)

4. Enable in workflow JSON:
            In the target workflow JSON, inside the appropriate subworkflow's
            "nodes" array, add a node with "function": "<my_function>", "enabled": true.

5. Restart backend:  ./run.sh   (or Ctrl+C then ./run.sh)
   The function now appears in the GUI function palette.
```
