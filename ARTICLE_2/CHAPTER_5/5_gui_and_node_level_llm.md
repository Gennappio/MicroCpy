# 5. The GUI as the Biologist's Control Surface

The graphical interface is not only a convenient way to draw workflows. In
OpenCellComms it is the main control surface through which a biologist can read,
question, and modify an AI-generated model. This distinction is important. The
goal is not to hide code behind a friendly interface. The goal is to expose the
model in a form that matches biological reasoning while still keeping a direct
connection to the executable Python implementation.

For this reason, the GUI is organized around the same ontology used by the
workflow and the runtime: world, agents, resources, initialization, scheduler,
processing, and results. When a biologist opens the model, they should not first
ask where the coding agent placed the code. They should ask a biological question
and find the corresponding part of the model.

```text
Biological question                         GUI location
---------------------------------------------------------------
What is the simulated space?                World
Which cells or individuals exist?           Agents
Which signals, fields, or substances exist? Resources
How is the initial state created?           Initialization
What happens every step?                    Scheduler
What is reconciled after updates?           Processing
What is measured or plotted?                Results
```

This organization turns the GUI into a navigable map of the model. A behavior that
cannot be found in this map is not simply inconvenient. It is scientifically
dangerous, because it means biology is present in the executable model but absent
from the representation used by the person who must validate it.

## From workflow JSON to visible canvases

The GUI is synthesized from the workflow representation. The workflow JSON is the
single source of truth for what nodes exist, how they are categorized, how they are
connected, and how they are scheduled. The GUI does not invent a second model. It
renders the workflow into canvases that are understandable to the biologist.

This has two consequences.

First, the GUI preview can happen before all Python code is written. The system can
show the proposed structure of a model while it is still a plan: agents, resources,
behaviors, initialization steps, scheduler calls, and result nodes. This lets the
biologist validate the architecture before implementation details become costly to
change.

Second, any inconsistency between the workflow and the GUI is a real model
problem. If a node exists in the workflow but has no visible home, the biologist
cannot inspect it. If a node appears in the GUI but is absent from the execution
order, it is visible biology that never runs. These are exactly the kinds of
mistakes that the validator is designed to catch.

## Tabs as biological ownership

The tabs in OpenCellComms are not arbitrary folders. They encode ownership. A
tumor-cell migration rule belongs to the Tumor agent. Oxygen diffusion belongs to
the Oxygen resource. Domain construction belongs to the World. A final population
plot belongs to Results.

This ownership is what makes the model readable. In a conventional script, related
biology can be scattered across helper functions, loops, classes, and plotting
code. A biologist may need to inspect many files to understand where oxygen is
created, diffused, consumed, and plotted. In OpenCellComms, oxygen has a resource
tab. The tab gathers the relevant operations into a place that corresponds to the
biological object.

The same principle applies to agents. Agent creation and agent behavior are kept
separate because they answer different questions. Creation answers how a
population enters the model. Behavior answers what one individual does during a
simulation step. Keeping these phases separate prevents a common AI-generated
mistake: code that creates or initializes populations inside a repeated per-agent
loop.

## The node editor

Each GUI node corresponds to one atomic Python function. Opening a node gives the
biologist and the coding agent a small, local object to inspect. The node has a
name, a category, parameters, a role in the scheduler, and a source file.

This is a deliberate compromise between visual programming and normal programming.
OpenCellComms does not try to make complex ABMs by connecting anonymous visual
blocks with hidden behavior. The Python remains real Python. But the Python is
cut into biological units that can be opened from the GUI.

For a biologist, this means that "consume oxygen" is not a vague phrase hidden in a
large simulation script. It is a node. The node can be opened. Its parameters can
be inspected. Its code can be explained. Its position in the scheduler can be
checked. Its outputs can be connected to results.

For the coding agent, the node editor reduces the scope of each task. Instead of
asking the agent to modify an entire codebase, the system can ask it to write,
inspect, or revise one node at a time.

## The LLM as a node-level assistant

OpenCellComms also uses an LLM at the node level. This is different from the
common pattern of asking a coding agent to generate an entire simulator from a
prompt. The implemented node-level assistant receives the local context of one
node: its biological role, its category, its parameters, the expected scaffold,
and the surrounding workflow information needed to understand how it will be
called.

The LLM can then perform focused tasks:

- write the Python function for a new node;
- inspect an existing node and explain what it does;
- check whether the code matches the node role;
- identify parameters that should be exposed to the GUI;
- suggest a safer or clearer implementation;
- revise the node without rewriting unrelated parts of the model.

This is important scientifically because the LLM is not treated as an oracle that
produces a complete model in one opaque action. It is used as an assistant inside
a constrained authoring protocol. The GUI selects the node. The workflow defines
the node's role. The scaffold defines the expected execution context. The LLM
writes or explains the small piece of code that belongs there.

## Writing a single node

When the LLM writes a node, it is given a much narrower problem than "write an
ABM." For example, for a per-agent Tumor behavior called `consume_oxygen`, the
important context is:

```text
Node name: consume_oxygen
Owner: Agent / Tumor
Role: per-agent behavior
Scheduler context: called once for each Tumor agent
Bound object: env.agent
Resource used: oxygen
Expected effect: reduce local oxygen according to uptake rate
Visible parameters: uptake_rate, hypoxia_threshold
```

This context makes the correct loop shape explicit. The LLM should not loop over
all tumor cells, because the scheduler already performs the per-agent iteration.
The node should use the bound agent and local resource access. This reduces both
performance errors and biological errors.

The same idea applies to a resource node:

```text
Node name: diffuse_oxygen
Owner: Resource / Oxygen
Role: field update
Scheduler context: called once per simulation step
Bound object: oxygen field
Expected effect: diffuse and decay oxygen across the world
Visible parameters: diffusion_rate, decay_rate
```

Here the LLM is guided toward field-level code, not per-cell behavior. The node
role tells the assistant what kind of operation it is writing.

## Inspecting a single node

The node-level LLM is also useful after code generation. A biologist can ask the
system to explain one node in biological language. For example:

```text
Explain what the Tumor / consume_oxygen node does.
Which parameters control it?
When does it run?
Does it change the agent, the oxygen field, or both?
```

Because the node is small, the explanation can be concrete. The LLM can refer to
the node's inputs, parameters, scheduler position, and side effects. This is far
more useful than asking an LLM to summarize thousands of lines of generated code.

This also supports correction. If the explanation says that a node changes the
oxygen field directly but the intended design is to write uptake intents first and
reconcile them later, the mismatch is visible. The user can correct the workflow
or ask the assistant to revise that single node.

## Why this reduces iterations

The GUI and the node-level LLM reduce iterations in different but connected ways.

The GUI reduces structural ambiguity. It shows whether the model has the right
agents, resources, scheduler phases, and outputs before the user spends time
debugging Python.

The node-level LLM reduces implementation ambiguity. It asks the coding agent to
solve one local problem under a known role, instead of allowing it to infer the
whole architecture.

Together, they create a tighter correction loop:

```text
Biologist describes model
        |
        v
Workflow appears in GUI
        |
        v
Biologist corrects structure
        |
        v
LLM writes one node at a time
        |
        v
Validator checks ownership and scheduling
        |
        v
Biologist inspects nodes and outputs
```

The important reduction is not only in the number of prompts. It is in the type of
prompts. The user no longer needs to say "the model is wrong, fix it." They can
say "move this behavior to Tumor," "expose this parameter," "explain this node,"
or "rewrite this node as a per-agent behavior." These are precise corrections, and
precise corrections are what make AI-assisted modeling practical for biologists.

Suggested figure: **GUI as control surface**. Show a workflow JSON in the center,
rendered into GUI tabs. A selected node opens a side panel with parameters, code,
LLM explanation, and validation messages.

Suggested figure: **Node-level LLM loop**. Show one selected node receiving local
context from the workflow, producing or explaining a single Python function, then
returning to validator and GUI review.
