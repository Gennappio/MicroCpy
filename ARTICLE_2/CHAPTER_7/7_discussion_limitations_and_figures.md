# 7. Discussion, Limitations, and Figure Plan

OpenCellComms is built on a simple idea: if AI-generated simulation code is to be
useful to biologists, it must remain visible, structured, and validatable.

The system does not try to replace scientific judgment. It helps organize and
implement that judgment. The biologist still decides what biology matters, what
parameters are plausible, and whether outputs support the hypothesis. OpenCellComms
helps ensure that the resulting code is arranged so those decisions can be
inspected.

## What this solves

OpenCellComms addresses several problems at once.

It gives biologists a GUI-level view of generated models. It gives coding agents a
constrained grammar. It gives developers a predictable folder and plugin structure.
It gives validators a workflow representation they can check. It gives the runtime
a clear execution plan.

Most importantly, it reduces unnecessary correction iterations by moving structural
errors earlier in the process. Missing creation, hidden behaviors, wrong loop
shape, dead nodes, and invalid ownership can be caught before the biologist spends
time interpreting a misleading simulation.

## Limitations

OpenCellComms does not prove that a biological model is correct.

It can validate structure, not truth. A workflow can be well organized and still
use the wrong rate, the wrong threshold, or the wrong biological assumption.

The system also depends on the quality of the authoring protocol. If the model
intake is incomplete, the coding agent may still make poor choices. The point of
the protocol is to expose those choices, not to remove the need for domain
expertise.

Finally, node-based organization can introduce overhead and may not be ideal for
all high-performance simulation settings. The current goal is understandable,
modifiable, research-oriented modeling, not maximum HPC performance.

## Future evaluation

The strongest future evaluation would measure whether OpenCellComms reduces
human-AI correction iterations.

Possible metrics include:

- number of correction turns before first valid workflow JSON;
- number of validator failures per generated model;
- number of run attempts before first successful run;
- number of biology-level corrections after first run;
- time from model description to validated workflow;
- ability of a second biologist to inspect and modify the generated model.

This would separate two questions:

1. Can the coding agent write code?
2. Can the biologist understand and control the generated model?

OpenCellComms is designed around the second question.

## Suggested figures

1. **Biologist-to-simulation pipeline**: biological description -> `MODEL.md` ->
   workflow JSON -> GUI / validator / AI agent / runtime -> Python nodes ->
   simulation.

2. **Script vs OpenCellComms**: monolithic generated Python script versus plugin
   functions, workflow JSON, GUI tabs, validator, and runtime.

3. **Plugin vs workflow**: plugin as reusable function library; workflow as
   experiment arrangement.

4. **Navigable ontology**: World, Agents, Resources, Initialization, Scheduler,
   Processing, Results.

5. **No-orphan rule**: wrong scheduler call with no visible tab versus right
   scheduler call homed under a visible category.

6. **GUI as control surface**: workflow JSON rendered as GUI tabs, with a selected
   node showing parameters, code, LLM explanation, and validation messages.

7. **Node-level LLM loop**: one selected node receives local workflow context, is
   written or explained by the LLM, then returns to validation and GUI review.

8. **Wrong vs right generated behavior**: per-agent behavior looping over all cells
   versus per-agent behavior using `env.agent`.

9. **Use-case comparison**: Sugarscape, TCELL_CORRAL, and MicroC compared by
   agents, resources, couplings, validation focus, and outputs.
