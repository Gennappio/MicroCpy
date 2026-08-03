# 1. The Problem: AI Can Write Code, but Biologists Need Understandable Models

Agent-based models are attractive in biology because they allow researchers to
describe systems using biological language: cells move, divide, die, secrete
signals, sense fields, and change internal state. This makes ABMs natural for
studying spatial heterogeneity, cell-cell interaction, diffusion, phenotype change,
and emergent tissue-level behavior.

The difficulty is that a biologically meaningful ABM rapidly becomes a complex
software system. A model is not just a list of cell rules. It includes
initialization, spatial structure, fields, agent state, scheduling, outputs,
parameterization, and validation. These parts must be arranged correctly for the
simulation to mean what the biologist thinks it means.

Coding agents change the cost of writing code. They can generate files and
functions quickly, and this is a major opportunity for computational biology.
Models that previously required substantial programming effort can now be drafted
much faster.

However, coding agents do not remove the barrier for biologists. In some ways they
move the barrier. Instead of being blocked by the absence of code, the biologist can
now be overwhelmed by a large amount of generated code. The key problem becomes:

> Can the biologist understand what was generated, inspect the model, modify it,
> validate it, and share it?

Generated code can be syntactically correct while still being scientifically
unreadable. A coding agent may infer scheduler order, decide where resources live,
choose whether a function runs once or once per agent, or create folders and files
without a structure that maps to the biology. When these choices are wrong, the code
may still run, but the model is no longer transparent.

This is especially dangerous because coding agents often infer instead of asking.
In ABM construction, inferred decisions are architectural decisions. They determine
whether agents are created before they behave, whether resource fields are visible
to the biologist, whether a node is executed, and whether a per-agent rule loops
over all cells by mistake.

OpenCellComms is built around the observation that the main bottleneck is not only
writing Python. The bottleneck is producing model code that a biologist can read,
modify, interrogate, validate, and trust.

The goal is therefore not "AI writes the simulator." The goal is:

> A biologist describes a theoretical model, and the system guides the coding agent
> toward a functioning ABM implementation with the fewest correction iterations,
> while preserving a model structure the biologist can inspect.

This requires constraining the coding agent. OpenCellComms does this through a
node-based GUI, a workflow intermediate representation, plugin and workflow
organization, one-file-one-node code structure, a minimal ABM library, semantic
validators, and AI authoring protocols.

Suggested figure: **Before/after coding agents**. Left: biologist -> coding agent ->
large opaque codebase -> many corrections. Right: biologist -> model intake ->
workflow preview -> validated nodes -> simulation.
