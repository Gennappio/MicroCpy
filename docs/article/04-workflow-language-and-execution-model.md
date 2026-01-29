# Chapter 4 — Workflow Language & Execution Model

## 4.1 The workflow file as a scientific “protocol”

In experimental science, a protocol specifies:

- what actions to take,
- in what order,
- with what settings,
- and what to record.

OpenCellComms treats a workflow JSON similarly: a workflow is a **protocol for a simulation run**.

This is not just a technical file format; it is a communication tool:

- it can be shared with collaborators,
- discussed in meetings,
- version-controlled,
- and compared across experiments.

## 4.2 Two workflow versions: v1 stage-based and v2 subworkflow-based

The repo documents two workflow formats in `docs/WORKFLOW_STRUCTURE.md`:

### Version 1.0 — stage-based

- Organizes execution into named stages:
  - `initialization`, `intracellular`, `diffusion`, `intercellular`, `finalization`
  - plus an optional `macrostep` stage acting as an outer controller
- Each stage contains:
  - a list of function nodes
  - an explicit `execution_order` list
  - stage-level parameters

This format is approachable and makes the multi-scale structure explicit.

### Version 2.0 — subworkflow-based (“composer”)

- Generalizes the pipeline into nested subworkflows:
  - A “main” composer subworkflow orchestrates calls to other subworkflows
  - Subworkflow calls can repeat (iterations) and pass parameters
- This enables:
  - hierarchical composition,
  - reuse of subworkflows,
  - more flexible execution structures than the fixed stage template.

If your article needs one mental model, you can describe v2 as:

> v2 is a general workflow graph where “stages” are a common special case.

## 4.3 Node types (what a workflow is made of)

The workflow format supports multiple node-like entities:

- **Function node**: calls a registered Python function with parameters.
- **Controller node**: sets loop iterations / “number of steps” in a composer.
- **Subworkflow call node**: invokes another subworkflow, possibly multiple times.
- **Parameter nodes** (GUI concept): visually define and connect parameter values to functions.

Even if your article focuses on the science, it’s worth clarifying that these are not “arbitrary code blocks.” They are structured node types with clear semantics.

## 4.4 Execution order is a first-class citizen

A critical detail: workflows include explicit `execution_order` arrays.

Why this matters:

- It prevents “incidental” ordering from list positions or UI coordinates.
- It makes the pipeline reproducible.
- It makes order changes show up clearly in diffs and code reviews.

In multi-scale coupling, ordering *is part of the model*.

## 4.5 The function registry: mapping JSON to Python

Workflow nodes reference functions by name, and the engine resolves them through a registry.

OpenCellComms uses a decorator pattern (see `docs/CREATING_FUNCTIONS.md`):

- Developers write a Python function with a signature like:
  - `def my_function(context: Dict[str, Any], **kwargs) -> None`
- They annotate it with `@register_function(...)` including:
  - display name, description, category, and parameter metadata

Key effect:

- The same metadata enables:
  - correct execution in the engine,
  - and a rich UI representation (palette, parameter editor, tooltips) in the GUI.

## 4.6 Context passing: how nodes communicate

OpenCellComms nodes communicate via a shared context dictionary.

Typical node behavior:

- read needed objects from context
- validate assumptions (e.g. population exists)
- compute updates
- write results back to context or mutate referenced objects

This is simple and flexible, but it requires discipline:

- agreed-upon context keys,
- clear contracts for what each node reads/writes,
- and observability tooling to understand deltas.

## 4.7 Observability hooks at the workflow layer

The observability design (see `opencellcomms_gui/NODES_OBSERVABILITY.md`) treats node execution as an event stream:

- `node_start` / `node_end`
- structured logs attached to nodes
- context snapshots before/after nodes
- diffs between context versions

This is powerful because it makes “why did this happen?” traceable to a specific node and a specific context delta.

## 4.8 Suggested figures (for this chapter)

- **Figure 1 — Workflow JSON excerpt**
  - Show a minimal example with `execution_order` and 2–3 nodes.
  - Include a caption: “the workflow is the protocol.”

- **Figure 2 — v1 vs v2 conceptual diagram**
  - v1: fixed five stages
  - v2: composer calling subworkflows

- **Figure 3 — Node types legend**
  - Icons/boxes for Function / Controller / SubworkflowCall / ParameterNode.

