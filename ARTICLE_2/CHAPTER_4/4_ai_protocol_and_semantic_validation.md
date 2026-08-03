# 4. Guiding the Coding Agent: Protocol, Nodes, and Semantic Validation

The most important design choice in OpenCellComms is that the coding agent is not
used as an unconstrained programmer. It is used as a constrained model author.

The agent receives a protocol:

```text
Specification
      |
      v
Workflow IR
      |
      v
Preview
      |
      v
Node generation
      |
      v
Validation
      |
      v
Execution
      |
      v
Review
```

The protocol starts by asking for model structure and sources. It records unknowns
instead of silently guessing them. It creates a skeleton workflow for review. Only
after the structure is approved does the coding agent write Python node-functions.

This is different from asking an LLM to write a simulator in one pass. The agent is
not rewarded for producing a large amount of code quickly. It is guided to produce
a small number of model objects that can be inspected before code is generated.

## Model intake

The model intake is the first constraint on the coding agent. The agent records the
biological question, sources, world structure, resources, agent kinds, couplings,
scheduler order, initialization, and expected observables.

Each slot is either answered, sourced, assigned a visible default, or marked as an
unresolved consequential question. Code generation is blocked while important
unknowns remain. This is essential because many AI mistakes come from filling
missing information silently.

The intake becomes `MODEL.md`, which acts as model memory. A later human or agent
can read it to understand what the model is meant to represent.

## One file, one node

The one-file-one-node rule is central to the protocol.

Each atomic biological operation is implemented as one Python function in one file,
and that function appears as one node in the workflow. A node may represent
"consume oxygen", "migrate", "secrete TNF", "diffuse oxygen", "plot world", or
"write run summary".

For the biologist, this makes the model readable. Opening a node shows a small
function with one purpose, rather than a long script containing many processes.

For the coding agent, this reduces the generation task. The agent does not need to
write a whole simulator at once. It writes one biological operation at a time.

For validation, it gives every operation an identity. A function can be checked,
homed, scheduled, observed, and explained individually.

## Role-aware generation

After the workflow structure is approved, the coding agent writes node-functions.
The scaffold depends on the role of the node.

An **Agent Creation** node is collective. It may create agents, wrap existing cells,
place cells, or perform once-only per-cell setup. It does not have a bound
`env.agent`.

An **Agent Step** node is per-agent. It is called by the scheduler with `for_each`,
and it acts on the single bound `env.agent`.

A **Resource** node acts on a field. A **World** node acts on spatial or collective
world state. A **Processing** node writes summaries, plots, or reports.

This role-aware scaffolding is one of the main ways OpenCellComms reduces coding
agent errors. The correct loop shape is built into the starting point.

## Wrong vs right: double iteration

Suppose the biologist asks for tumor cells to migrate up an oxygen gradient.

A generic coding agent might write this inside an agent behavior:

```python
def migrate(env):
    for cell in env.cells:
        ...
```

This is wrong if the function is already called once per agent. The scheduler loops
over agents, and the function loops over all cells again. The result can be much
slower and biologically incorrect, because each cell may be processed many times
per step.

The OpenCellComms scaffold instead guides the agent toward:

```python
def migrate(env):
    agent = env.agent
    if agent is None:
        return True
    ...
```

The scheduler handles the iteration. The function handles one agent. This is easier
to understand, easier to validate, and closer to how biologists describe agent
rules.

## Static semantic validation

Traditional programming tools validate syntax. OpenCellComms validates biological
workflow semantics.

A Python parser can tell whether a function is valid Python. It cannot tell whether
an agent behavior is hidden from the GUI, whether a creation canvas runs per-agent,
or whether a visible biological node is missing from execution order.

Because ownership, scheduling, and GUI binding are represented in the workflow IR,
OpenCellComms can check model structure before the simulation runs.

Representative rules:

| Rule | Prevents |
| --- | --- |
| Every runnable behavior must be homed under a visible GUI category. | Invisible biology that runs but cannot be found by the biologist. |
| `environment.behavior_subworkflows` must be empty. | Behaviors placed under a tab that does not exist. |
| Agent creation must not use `for_each`. | Duplicated or repeated population creation. |
| Agent kinds must not use unsupported leftover per-agent init canvases. | Reintroducing an ambiguous old phase. |
| Agent kinds should have scheduled creation. | Models where agents are never created. |
| Enabled nodes should appear in `execution_order`. | Dead biology: visible nodes that never run. |
| `execution_order` must reference known node IDs. | Run plans that point to deleted nodes. |
| Complex dict/list parameters should use parameter nodes. | GUI-unreadable configuration blobs. |
| Agent behaviors should write only agent state or intents. | Per-agent code directly mutating shared state. |
| Resource behaviors should write only resource state or intents. | Resource code mutating unrelated model state. |
| Call targets must exist. | Broken workflow references. |
| Circular dependencies are rejected or warned. | Infinite or ambiguous execution graphs. |

The no-orphan rule is especially important. Every behavior that can run must also
have a visible home in the GUI. If the scheduler calls a behavior, that behavior
must be listed under a real, clickable category: an agent kind, a resource kind,
the world, or processing. An orphan behavior may execute correctly, but the
biologist has no obvious place to find, inspect, or edit it. It is runnable but
illegible.

The execution-order check prevents another subtle failure: dead biology. A node may
exist on a canvas and have a function body, but if it is not in `execution_order`,
the runtime never calls it. The validator warns when enabled nodes are omitted from
the run order.

## LLM explanation and model interrogation

OpenCellComms can use the LLM not only to write code but also to explain code in
the context of the model. Because each node is small, the LLM can explain one
operation at a time. The biologist can ask what a node does, why it is in the
scheduler, which parameters it uses, or how to modify it.

This is another reason for one-file-one-node organization. A generated explanation
of a small biological operation is useful. A generated explanation of a large
monolithic simulator is much harder to trust.

Suggested figure: **Wrong vs right AI-generated behavior**. Left: per-agent
behavior loops over all cells. Right: per-agent behavior uses `env.agent`.
