# Chapter 1 — Executive Summary & Positioning

## 1.1 What this software is (one sentence)

**OpenCellComms (MicroCpy)** is a **multi‑scale biological simulation platform** that couples **cell population dynamics (ABM)**, **microenvironment diffusion (PDE)**, and **intracellular decision logic (gene networks)**—and lets users build and run simulations via a **visual, node‑based workflow designer** that exports a structured **JSON workflow** executed by a Python engine.

## 1.2 Who it’s for

This project is a good fit for:

- **Computational biology / systems biology researchers** exploring hypotheses where *intracellular state*, *cell–cell interactions*, and *diffusing substances* matter together.
- **Teams teaching or prototyping** multi-scale modeling, where speed of iteration and explainability are more important than maximum runtime performance.
- **Users who want reproducible “pipelines for simulations”**, not monolithic scripts—especially when those pipelines need to be reviewed, shared, and extended collaboratively.

It is not trying to be:

- A production monitoring product or an enterprise workflow platform.
- A hyper-optimized HPC framework for million-cell interactive debugging scenarios.

That “research tool” stance is explicit in the observability design philosophy (see `opencellcomms_gui/NODES_OBSERVABILITY.md`).

## 1.3 The core idea: simulations as workflows

Most research simulation code starts as a tight loop:

- initialize state
- for each step:
  - update cell state
  - update environment
  - record outputs

OpenCellComms keeps that loop, but replaces “a pile of custom Python” with a **workflow engine** and a **function registry**:

- A simulation is a JSON workflow describing **what functions run, in what order, with what parameters**.
- The engine executes those functions by passing a shared **context** object across steps.
- The GUI lets users author workflows without editing code and makes it easier to communicate “what the simulation is doing.”

The workflow approach is valuable because it makes the simulation:

- **Inspectable** (you can see the pipeline at a glance),
- **Composable** (subworkflows can be reused),
- **Extensible** (new functions appear in the GUI once registered),
- **Debuggable** (node-level observability can attach to workflow execution).

## 1.4 What makes it different (the differentiators)

### Differentiator A — Multi-scale coupling in a single pipeline

OpenCellComms is not “just an ABM” and not “just a diffusion solver”:

- **Cells** behave, move, divide, and die (ABM).
- **Substances** diffuse and form gradients (FiPy/PDE).
- **Gene networks** influence cell fate and phenotype (Boolean / MaBoSS optional).
- The system is designed to **couple** these dynamics in a stepwise workflow.

### Differentiator B — Visual authoring + code-level extensibility

The GUI is not only a viewer—it is a **workflow composer**:

- Drag nodes representing engine functions.
- Connect nodes to define execution order.
- Edit parameters with type-aware widgets.
- Export the workflow to JSON for CLI runs or sharing.

At the same time, scientists can extend the system by adding new Python functions via a decorator-based registry (see `docs/CREATING_FUNCTIONS.md`).

### Differentiator C — “Scientific observability”

OpenCellComms aims to make simulation runs **debuggable** at the level that matters to researchers:

- What node ran last?
- How long did it take?
- What warnings/errors occurred?
- What changed in the simulation context before/after this node executed?

The project’s observability spec explicitly favors:

- **Maximum debuggability by default** (e.g., snapshot per node),
- **Simple, inspectable artifacts** (flat files such as JSON/JSONL),
- **“Current run only” semantics** (each run overwrites previous observability data; users archive results they care about),
- **A debugging inspector, not a monitoring dashboard**.

This is a deliberate tradeoff: fewer “product features,” more direct support for scientific iteration and understanding.

## 1.5 What you can do with it (example use cases)

### Use case 1 — Tumor spheroid / colony growth in gradients

- Initialize a spheroid (or a grid) of cells.
- Diffuse oxygen/glucose and track depletion zones.
- Observe how phenotypes and fates shift across the gradient.
- Produce plots/heatmaps and time-series summaries.

### Use case 2 — Drug or perturbation studies

- Introduce time-dependent changes to substrate concentrations or reaction rates.
- Evaluate population-level outcomes (viability, phenotype distribution).
- Compare runs via exported CSV checkpoints and plots.

### Use case 3 — Teaching and reproducible methods

- Encode the simulation pipeline as a shareable workflow JSON.
- Make experimental knobs explicit via GUI parameters.
- Let learners modify workflows without editing engine code.

## 1.6 “How it works” at a glance (pseudocode)

This pseudocode is a conceptual view of a typical OpenCellComms run, not a literal implementation:

```text
workflow = load_workflow_json(...)
context  = {}

// Initialization subworkflow
for node in workflow.initialization.execution_order:
    execute(node, context)

// Main run loop (macrosteps / steps / subworkflow calls)
for step in range(number_of_steps):
    for node in workflow.intracellular.execution_order:
        execute(node, context)         // per-cell updates, gene network updates, etc.

    for node in workflow.diffusion.execution_order:
        execute(node, context)         // PDE diffusion, update environment fields

    for node in workflow.intercellular.execution_order:
        execute(node, context)         // migration, division, interactions

    record_outputs(context, step)

// Finalization subworkflow
for node in workflow.finalization.execution_order:
    execute(node, context)
```

Key implementation idea: `execute(node, context)` resolves parameters, calls a registered Python function, and (when observability is enabled) emits node events and context snapshots.

## 1.7 Suggested figures (for this chapter)

- **Figure 1 — “What OpenCellComms is” overview diagram**
  - A simple 3-box diagram: GUI (workflow design) → Engine (workflow execution) → Outputs (plots/CSV/checkpoints).
  - Add callouts: “JSON workflow,” “function registry,” “context,” “observability.”

- **Figure 2 — Screenshot of the workflow canvas (GUI)**
  - Capture the canvas with a small workflow showing the main stages (Initialization / Intracellular / Diffusion / Intercellular / Finalization).
  - If you have node badges/inspector enabled, show them to communicate debuggability.

- **Figure 3 — Example results artifact**
  - Use an existing repo image if you want immediate visuals:
    - `opencellcomms_gui/results/subworkflows/Generate_final_plots/heatmaps/*.png`
    - `opencellcomms_engine/tools/cell_visualizer_results/*.png`

