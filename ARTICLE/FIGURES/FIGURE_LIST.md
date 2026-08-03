# Suggested Figures

## Figure 1: Biologist-to-simulation pipeline

Show:

```text
Biologist description -> MODEL.md -> Workflow JSON
Workflow JSON -> GUI / Validator / AI Agent / Runtime
Runtime -> Atomic Python Nodes -> Simulation -> Results
```

Purpose: communicate workflow JSON as the intermediate representation.

## Figure 2: Script vs OpenCellComms

Left side: a monolithic generated Python script with hidden loops.

Right side: plugin functions, workflow JSON, GUI tabs, validator, and runtime.

Purpose: show why generated code alone is not enough.

## Figure 3: Plugin vs workflow

Plugin = reusable functions and behavior canvases.

Workflow = experiment arrangement, parameters, scheduler, and outputs.

Purpose: explain code organization to bioinformaticians.

## Figure 4: Navigable ontology

Show GUI categories:

- World;
- Agents;
- Resources;
- Initialization;
- Scheduler;
- Processing;
- Results.

Purpose: show where a biologist looks for each model component.

## Figure 5: No-orphan rule

Wrong: scheduler calls a behavior that is not listed under any tab.

Right: scheduler calls a behavior homed under an agent/resource/world/processing
category.

Purpose: explain invisible biology.

## Figure 6: Wrong vs right generated behavior

Wrong:

```python
for cell in env.cells:
    ...
```

inside an Agent Step.

Right:

```python
agent = env.agent
...
```

Purpose: show how role-aware scaffolding prevents double iteration.

## Figure 7: Use-case comparison

Table with Sugarscape, TCELL_CORRAL, and MicroC:

- agents;
- resources;
- coupling type;
- validation focus;
- outputs.

Purpose: show breadth of the system.
