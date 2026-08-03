# 2. OpenCellComms as a Constrained Model-Authoring Environment

OpenCellComms is organized around a practical principle:

> The number of correction iterations is dominated by the number of architectural
> decisions the coding agent must infer.

Informally:

```text
I ~ D
```

where `I` is the number of correction iterations and `D` is the number of implicit
design decisions.

In a conventional AI-assisted workflow, the biologist provides a biological
description and the coding agent must infer the architecture:

```text
Paper or biological description
        |
        v
LLM guesses:
  - scheduler order
  - entity ownership
  - initialization order
  - resources
  - loops
  - outputs
  - folder organization
        |
        v
Generated code
```

Every inferred decision is a possible correction round. The code may be valid
Python, but the model can still be wrong or illegible.

OpenCellComms reduces this decision space by forcing the model through explicit
slots:

```text
Paper or biological description
        |
        v
MODEL.md
        |
        v
Workflow slots:
  - World
  - Agents
  - Resources
  - Initialization
  - Scheduler
  - Processing
  - Results
        |
        v
AI fills constrained slots
        |
        v
Atomic node code
```

The coding agent is no longer asked to invent the architecture. It is asked to
complete a grammar.

## The model ontology

OpenCellComms organizes a model around a small ontology.

The **World** is the spatial and physical substrate. It contains the grid or domain,
topology, and spatial relations.

**Agents** are individual biological entities, such as cells. Agent behaviors run
as per-agent steps through the scheduler. Inside an agent behavior, the function
acts on the single bound agent.

**Resources** are fields, signals, or substances on the world. Oxygen, glucose,
sugar, TNF, and chemokines are examples. Resource behaviors describe how these
fields are initialized, diffused, decayed, consumed, or replenished.

**Initialization** builds the model state once. It creates the world, initializes
resources, creates agents, and prepares any state needed before the first simulation
step.

The **Scheduler** defines the repeated loop. Agent behaviors are called through a
per-agent ask. Resource behaviors update fields. World or reconciliation behaviors
commit shared state changes. Processing nodes may run after the loop.

**Processing and Results** contain post-loop analysis, plots, summaries, and
machine-readable run artifacts.

This ontology is deliberately small. It gives the coding agent enough structure to
place code correctly, while keeping the GUI understandable to biologists.

## The GUI as a biological map

Generated code is not enough. A biologist must be able to see what the model does.
The GUI organizes a model into tabs that match biological questions:

- What is the world?
- Which agents exist?
- Which resources or signals exist?
- What happens during initialization?
- What happens each scheduler step?
- What outputs and summaries are produced?

The GUI is not just decoration. It is the biologist's way to interrogate the
generated model. If a behavior cannot be found in the GUI, then even if it runs, it
is not a good scientific artifact. It is hidden biology.

Suggested figure: **Navigable ontology**. Show the GUI categories World, Agents,
Resources, Initialization, Scheduler, Processing, and Results, with example nodes
under each.
