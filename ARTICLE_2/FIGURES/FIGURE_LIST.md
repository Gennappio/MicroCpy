# Figure List for ARTICLE_2

## Figure 1: Biologist-to-simulation pipeline

```text
Biologist description -> MODEL.md -> Workflow JSON
Workflow JSON -> GUI / Validator / AI Agent / Runtime
Runtime -> Atomic Python Nodes -> Simulation -> Results
```

Purpose: introduce workflow JSON as the intermediate representation.

## Figure 2: Script vs OpenCellComms

Left: generated monolithic script with hidden architecture.

Right: plugin functions, workflow JSON, GUI tabs, semantic validator, runtime.

Purpose: show why generated code alone is insufficient for biologists.

## Figure 3: Plugin vs workflow

Plugin = reusable model operations.

Workflow = experiment arrangement, parameters, scheduler, and outputs.

Purpose: explain code organization.

## Figure 4: Navigable ontology

World, Agents, Resources, Initialization, Scheduler, Processing, Results.

Purpose: show where biologists inspect the model.

## Figure 5: No-orphan rule

Wrong: scheduler calls behavior with no tab.

Right: scheduler calls behavior homed under agent/resource/world/processing.

Purpose: explain invisible biology.

## Figure 6: GUI as control surface

Workflow JSON in the center, rendered into GUI tabs for World, Agents, Resources,
Scheduler, Processing, and Results. A selected node opens a side panel with
parameters, code, LLM explanation, and validation messages.

Purpose: show that the GUI is not decorative; it is the biologist's map for
reading and controlling the generated model.

## Figure 7: Node-level LLM loop

One selected node receives local context from the workflow, category, scheduler
role, parameters, and scaffold. The LLM writes or explains one Python function,
then the node returns to validation and GUI review.

Purpose: show how OpenCellComms uses an LLM as a constrained node assistant rather
than as an unconstrained whole-simulator generator.

## Figure 8: Wrong vs right generated behavior

Wrong: `for cell in env.cells` inside an Agent Step.

Right: `agent = env.agent`.

Purpose: show role-aware code generation.

## Figure 9: Use-case comparison

Sugarscape, TCELL_CORRAL, MicroC by agents, resources, coupling, validation focus,
and outputs.

Purpose: show breadth.
