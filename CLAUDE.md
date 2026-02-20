# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
