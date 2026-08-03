# 6. Observation, Interrogation, Sharing, and Use Cases

This chapter folds together the earlier observability chapter and the use-case
chapter. A model is useful only if the biologist can observe, validate,
interrogate, modify, and share it. OpenCellComms therefore treats outputs as part
of the authoring loop. The model should not only run; it should produce evidence
that the run behaved as expected.

This evidence includes plots, summaries, logs, parameter values, machine-readable
run summaries, and the visible workflow itself. The same constraints that make
generation easier also make review easier. Because each function is a node, each
node belongs to a visible part of the model, and workflows describe execution
order, the generated model can be inspected from several directions. The user can
ask what agents exist, what resources exist, what happens during initialization,
what happens at each step, what is measured, and what is saved.

## Observation as part of the authoring loop

In many agent-based models, observation is added only after the simulation logic is
complete. This is risky for AI-assisted authoring because the first version of the
code may run while still hiding important mistakes. For example, the population may
grow for the wrong reason, a field may diffuse after it is consumed rather than
before, or a phenotype transition may happen in the wrong scheduler phase. If the
only output is a final animation or a final table, these errors may remain
invisible until late in the process.

OpenCellComms instead treats observation as part of the model. A result node can
plot population counts. Another can save spatial resource maps. Another can
summarize deaths, divisions, movements, secretion events, or uptake events. These
result nodes are ordinary nodes in the same ontology as the rest of the model. They
can be inspected and changed without entering unrelated simulation code.

This makes the coding agent produce models that are easier to debug biologically.
The agent is not merely asked to "write a simulation." It is guided to create a
simulation that has points of inspection. A wrong model with clear outputs can be
corrected. A wrong model with hidden behavior often forces the user to ask the
coding agent to guess what happened.

## GUI preview before generation

The GUI preview is an early validation step. Before Python functions are finalized,
the skeleton workflow can be opened and inspected. It is a map of the biological
assumptions that the coding agent has extracted from the specification.

The biologist can check:

- which agents exist;
- which resources exist;
- what happens during initialization;
- what happens each scheduler step;
- where outputs are produced;
- whether any obvious behavior is missing;
- whether each behavior is owned by the right biological object.

This preview reduces expensive iterations. It is easier to move a behavior from
one canvas to another before implementation details are written. It is also easier
to correct the coding agent with biological language: "TNF should be a resource,"
"hypoxia death belongs to Tumor," or "this measurement belongs in Results."

The preview matters because many mistakes are architectural rather than syntactic.
The model may contain the correct biological words but put them in the wrong place.
A chemokine might be represented as a world helper instead of as a resource. A
tumor-cell death process might be generated as a processing function instead of as
a tumor behavior. A creation function might be scheduled inside a per-agent loop.
The GUI preview gives the user a chance to catch these mistakes when they are still
workflow mistakes, before they become scattered code.

## Run review after execution

After execution, run summaries and plots let the biologist ask whether the model
behaved as expected. The question is not only "did the simulation finish?" but "did
it produce the behavior expected in `MODEL.md`?"

A model may include plots of population counts, spatial maps of resources,
phenotype distributions, growth curves, interaction summaries, or exported tables.
These outputs are also nodes. They can be inspected, modified, and replaced without
changing the rest of the model.

This matters because many ABM errors are not syntax errors. A model can run and
still be biologically wrong. It can use the wrong time scale, place a behavior
under the wrong owner, update a field too early, or measure the wrong quantity.
OpenCellComms reduces these errors by making the model structure visible before
execution and the model behavior visible after execution.

The review loop is explicit:

```text
Specification
    |
    v
Workflow preview
    |
    v
Node generation
    |
    v
Validation
    |
    v
Run
    |
    v
Results review
    |
    v
Workflow or node correction
```

Correction is directed back to a known layer. If the biology is missing, the
workflow can be changed. If the structure is wrong, the node ownership can be
changed. If the implementation is wrong, a single node file can be regenerated or
edited. The user is not forced to repair a monolithic program.

## Parameters, interrogation, and sharing

OpenCellComms exposes parameters through nodes, rather than hiding them in code.
This allows biologists to adjust rates, thresholds, counts, and other values from
the GUI. Diffusion rates, secretion rates, death thresholds, carrying capacities,
initial population sizes, and scheduler choices can be made visible at the level
where the biologist expects to find them.

This is especially important for biological ABMs, where the first question is
often not "does the code run?" but "what assumptions are encoded?" OpenCellComms is
designed so that important assumptions have visible homes. The resource tab
answers questions about signals and fields. The agent tabs answer questions about
cell behavior. The scheduler answers questions about timing. The processing and
results sections answer questions about reconciliation, measurement, and
interpretation.

Because the model is represented as a workflow, it can be shared and interrogated.
A collaborator can open the workflow and see the model structure. They can inspect
the plugin functions, follow the scheduler, examine parameters, and compare
outputs. The one-file-one-node rule also helps collaboration: a reviewer can
inspect one behavior without reading all behaviors, and a coding agent can
regenerate one node without rewriting the whole project.

The model therefore has three linked representations:

```text
Workflow JSON       describes the model structure and execution order
GUI tabs            expose that structure to the biologist
Node files          implement the atomic operations
```

These three representations are not separate models. They are different views of
the same model. Keeping them synchronized is what allows OpenCellComms to support
both AI-assisted generation and human scientific review.

This is especially important for AI-generated models. Trust does not come from the
fact that the code was generated. Trust comes from the ability to inspect what was
generated, validate it, reproduce the run, and share a structured model rather than
an opaque folder of scripts.

## Use case 1: Sugarscape

Sugarscape is the simplest case study. It demonstrates a minimal ABM with agents
and a discrete resource.

It includes:

- a world or lattice;
- forager agents;
- sugar as a resource;
- resource regrowth;
- per-agent movement and consumption;
- scheduler order;
- simple plots or summaries.

The workflow can be summarized as:

```text
World
  setup lattice

Resource
  sugar
    initialize sugar
    grow back sugar

Agent
  forager
    create foragers
    move
    eat sugar
    metabolize

Scheduler
  ask foragers
  grow sugar
  reconcile
  report
```

Main message: OpenCellComms can express a classic ABM as small visible nodes rather
than as a monolithic script.

## Use case 2: TCELL_CORRAL

TCELL_CORRAL illustrates immune-cell modeling and spatial signaling.

It can demonstrate:

- collective creation of cell populations;
- per-agent T cell behavior;
- supporting cell types;
- chemokine or signal fields;
- intracellular or state updates;
- spatial migration and interaction.

The workflow can be summarized as:

```text
World
  setup spatial domain

Resource
  chemokine
    initialize field
    diffuse / decay

Agents
  t_cell
    create cells
    step behavior
    update state
    migrate / interact

Scheduler
  ask T cells
  update signal
  reconcile
  report
```

Main message: OpenCellComms keeps a multi-agent immune model inspectable by
separating creation, per-agent behavior, resources, scheduler, and outputs.

## Use case 3: MicroC

MicroC illustrates multi-scale coupling.

It can demonstrate:

- tumor or cell population agents;
- diffusing substances such as oxygen and glucose;
- phenotype or fate changes;
- intracellular or gene-network logic;
- plots and summaries of fields and cell states.

The workflow can be summarized as:

```text
World
  setup domain and population

Resources
  oxygen
    initialize
    diffuse
    consume

  glucose
    initialize
    diffuse
    consume

Agents
  tumor_cell
    create cells
    update gene or phenotype state
    respond to field conditions
    divide / die / arrest

Scheduler
  ask tumor cells
  run field updates
  reconcile fate changes
  write summaries
```

Main message: OpenCellComms can connect cell-level ABM behavior, resource fields,
and intracellular state while preserving a visible workflow structure.

Suggested figure: **Use-case comparison table** with Sugarscape, TCELL_CORRAL, and
MicroC by agents, resources, couplings, validation focus, and outputs.
