# 3. Workflow IR, Plugin Organization, and the Minimal ABM Library

OpenCellComms separates biological intent, workflow structure, reusable functions,
and runtime objects. This separation is what allows the same model to be generated
by an AI agent, inspected by a biologist, validated by software, and executed by the
runtime.

## Workflow JSON as an intermediate representation

The workflow JSON is the central intermediate representation of OpenCellComms.

It is not merely a configuration file. It is the common language shared by the
biologist, the GUI, the coding agent, the validator, and the runtime.

```text
Biologist description
        |
        v
      MODEL.md
        |
        v
   Workflow JSON
   |      |       |       |
   v      v       v       v
  GUI  Validator AI Agent Runtime
        |
        v
 Atomic Python nodes
        |
        v
   Simulation
```

This is similar in spirit to intermediate representations in other areas of
computing. LLVM IR sits between programming languages and machine code. ONNX sits
between machine-learning frameworks and inference engines. SQL query plans sit
between declarative queries and physical execution. In OpenCellComms, the workflow
IR sits between biological intent and executable simulation code.

`MODEL.md` is the biological specification of record. It records what the model is
intended to represent, what sources were used, what assumptions were made, and what
observables should be checked after a run.

The workflow JSON is the executable structure derived from that specification. It
records the canvases, nodes, scheduler, initialization order, GUI ownership, and
parameters. The same object is rendered by the GUI, checked by the validator,
completed by the coding agent, and executed by the runtime.

## Plugins as model libraries

A plugin is a model library. It contains the functions and subworkflows that belong
to a biological model family.

Conceptually, a plugin answers:

> What biological operations are available for this model?

A plugin may contain functions for placing agents, updating gene networks,
consuming resources, secreting signals, running diffusion, applying reconciliation,
plotting results, or writing summaries.

The plugin structure gives generated code a predictable home. The coding agent does
not scatter files across the repository. It places model-specific functions inside
the plugin for that model. This makes it easier for a biologist or developer to
find all code related to one model family.

## Workflows as experiments

A workflow is not the same thing as a plugin. A workflow is an experiment.

Conceptually, a workflow answers:

> Which available biological operations run, in what order, with what parameters?

The same plugin can support multiple workflows. One workflow may represent a
baseline experiment. Another may disable a behavior, change a parameter, add a
report, or reorder a process. The underlying functions remain reusable.

This separation is important for collaboration. A workflow JSON can be shared as a
scientific artifact that describes the experiment, while the plugin stores the
reusable biological operations.

## Functions, nodes, and binding to the GUI

In OpenCellComms, a Python function becomes useful to the biologist when it is
registered and placed as a node. The node is the visible representation of the
function in the GUI.

The node carries the function name, configurable parameters, position on the
canvas, execution-order connections, and optional contract metadata describing what
it reads and writes.

The workflow connects nodes into subworkflows. For example, a tumor-cell step
canvas may contain "consume oxygen", "check hypoxia", and "emit death intent".

The binding between code, node, workflow, and GUI category is part of correctness.
If the coding agent writes a function but does not place it in a workflow, the
biologist cannot use it. If the agent places it in a workflow but does not home the
behavior to a tab, the model may run but become invisible.

## The minimal ABM library

OpenCellComms includes a small ABM library that provides stable objects for
node-functions:

- **World** represents spatial structure: geometry, topology, neighborhoods,
  occupancy, and spatial queries.
- **Agent** represents one biological individual, such as one cell.
- **Population** owns the agents and handles creation, wrapping, removal, and
  reconciliation.
- **Resource** represents a field or signal on the world, such as sugar, oxygen,
  TNF, glucose, or a chemokine.
- **Domain** owns the world and resources.
- **Intents and reconciliation** separate what agents request from when shared
  state is committed.

The library is intentionally minimal. It is not meant to hide the model in a large
framework. It gives generated functions a common vocabulary.

This prevents each coding agent from inventing its own cell and field abstractions.
A migration function can ask the World for neighbors. A resource function can update
a field. An agent behavior can act on `env.agent`. A creation function can populate
or wrap agents. The model remains organized around biological objects.

Suggested figure: **Plugin vs workflow vs runtime objects**. Show plugin functions
on the left, workflow JSON in the center, GUI/validator/runtime around it, and ABM
objects underneath.
