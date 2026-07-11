# How OpenCellComms Helps a Coding Agent Build Correct ABM Workflows

This document explains the design goal behind the current workflow system:

> A biologist should be able to describe the model they want to test, and a coding
> agent should be able to turn that description into a correctly structured,
> runnable ABM workflow with as few correction rounds as possible.

The software does this by turning the ambiguous parts of ABM authoring into explicit
structure, role-aware scaffolding, canonical examples, and hard validation. The
coding agent is still responsible for understanding the biology, but the system
removes many of the mechanical mistakes that usually cause repeated iterations.

## The Problem It Solves

When a biologist describes an ABM, the hard part is often not writing a Python
function. The hard part is placing each biological action in the correct execution
role.

Common coding-agent mistakes are:

- creating agent behavior functions before the agents exist;
- putting collective population creation inside a per-agent loop;
- writing `for cell in env.cells` inside a function that already runs once per agent;
- writing an `env.agent` function on a collective creation canvas, where `env.agent`
  is `None`;
- homing a resource behavior under World instead of Resources;
- copying a stale pre-migration workflow that encodes the old structure;
- adding a node to the GUI without wiring it into `execution_order`, so it exists but
  never runs.

OpenCellComms reduces iterations by making those choices explicit and by rejecting
the invalid combinations before the biologist has to debug a broken simulation.

## The Main Idea

OpenCellComms treats an ABM as a structured workflow, not as one large script.

The workflow has named canvases that match the biological ontology:

| Concept | Authored As | Execution Meaning |
| --- | --- | --- |
| World | World canvas | Builds and owns spatial structure and initialization orchestration |
| Agent kind | Agent metadata plus canvases | Defines entities that act in the model |
| Agent creation | `create_subworkflow` | Runs once, collectively: placement, populate, and any once-only per-cell setup |
| Agent step | `behavior_subworkflows` | Runs once per agent each scheduler tick |
| Resource kind | Resource metadata plus canvases | Defines fields on the world |
| Resource init | resource `init_subworkflow` | Seeds or configures a field |
| Resource step | resource `behavior_subworkflows` | Runs as the resource behavior chosen by the model |
| Scheduler | `__scheduler__` | Orders the repeated per-step phases |
| Initialization | `__init_sequence__` | Orders setup before the scheduler loop |

This structure gives the coding agent a constrained target. It does not need to
invent an architecture for each model; it must fill in the slots.

## The Authoring Flow

The intended flow for a new model is:

1. The biologist describes the model, usually by referencing a paper, an existing
   implementation, or a nearby plugin.
2. The coding agent extracts the model slots: world geometry, agent kinds, resources,
   initialization, per-agent rules, resource dynamics, outputs, and stopping or
   scheduler behavior.
3. The agent maps each slot to the correct canvas and function role.
4. The agent writes atomic node-functions, one biological action per function.
5. The agent wires those functions into subworkflows and orchestration canvases.
6. The GUI and CLI validators reject structural mistakes.
7. Canonical workflows and tests provide examples and regression protection.

The key point is that validation happens at the workflow-structure level, not only
at Python syntax level.

## Model Intake: From Biology to Slots

The `/occ_new-model` workflow is designed to slow the coding agent down at the
right moment: before it writes code.

It asks for the nearest existing plugin and source material, then turns the biology
into a model preview organized by GUI tabs:

- World;
- Resources;
- Agents;
- Scheduler;
- Initialization;
- Results.

This matters because "diff from the nearest model" is usually more reliable than
"build from scratch." A biologist can say, for example, "this is like TCELL_CORRAL,
but with a different chemokine and an extra macrophage state." The agent then starts
from the canonical workflow family and changes the relevant slots instead of
guessing the entire workflow topology.

The instructions explicitly tell agents to copy only canonical workflows:

- `opencellcomms_adapters/MicroC/workflows/microc.json`;
- `opencellcomms_adapters/TCELL_CORRAL/workflows/tcell_corral.json`;
- `opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json`;
- other current canonical workflows that pass validation.

Skip-marked workflows (`metadata.validation.skip: true`) are treated as archived
fixtures or stress tests, not examples to imitate. This prevents a coding agent from
copying old pre-migration structure.

## The Central ABM Rule: Collective Creation vs Per-Agent Work

The most important distinction is whether a function runs collectively or once per
agent.

Agent creation is collective:

- it lives in `create_subworkflow`;
- it is authored in the World tab (the Creation canvas), ordered in Init;
- it runs once;
- it has no `for_each`;
- `env.agent` is `None`;
- it may loop over cells or call `env.population.populate(...)`;
- it is where agents are brought into existence.

Any once-only per-cell setup (building each cell's network, clamping nodes) is done
collectively inside creation (`for cell in env.cells:`), not as a separate per-agent
pass. There is no per-agent init phase.

Per-agent step is the only per-agent phase:

- it lives in `behavior_subworkflows`;
- the scheduler calls it with `for_each`;
- it runs once per agent per tick;
- it acts on the single bound `env.agent`.

This separation catches the classic double-iteration bug:

```python
# Wrong shape for a per-agent function:
def update(env):
    for cell in env.cells:
        ...
```

If this function is already called once per agent, the internal loop multiplies the
work by the number of agents and changes the model.

The correct per-agent shape is:

```python
def update(env):
    agent = env.agent
    if agent is None:
        return True
    ...
```

The correct collective creation shape is:

```python
def create_agents(env):
    env.population.populate("tumor_cell", count=100, trait=lambda rng: {...})
    return True
```

Every agent kind's setup is collective: a `create_subworkflow` (placement, populate,
and any once-only per-cell setup) plus per-step behaviors. There is no
`init_subworkflow` — per-cell setup that used to live there is done inside creation
with a cell loop.

## GUI Structure: The Agent Cannot Put Things Anywhere

The GUI mirrors the same ontology:

- Agents tab: agent kinds and their per-agent step behaviors only (every agent node
  runs per-agent);
- Resources tab: resource fields and their init/step behavior;
- World tab: world setup, each agent kind's collective creation canvas (runs once),
  and collective/world-level setup or behavior;
- Initialization tab: ordering of setup calls;
- Scheduler tab: ordering of repeated step calls;
- Overview tab: assembled view and validation feedback.

This reduces agent iterations because the UI model is not just visual; it becomes
workflow metadata. The engine and validators read that metadata and derive execution
behavior from it.

For example, a call to an agent step behavior in the scheduler is not just a box on
a canvas. It carries the ownership needed to derive `for_each`, so the executor
knows to run that subworkflow once per agent of that kind.

## Role-Aware Function Scaffolding

When the coding agent creates a function, the scaffold is role-aware. The selected
function role changes the body shape and expectations.

Examples:

- `agent_create`: collective creation, `env.agent is None`, may populate or loop over
  all cells;
- `agent_init`: per-agent setup, uses `env.agent`, must not loop over all cells;
- `agent_behavior`: per-agent step, uses `env.agent`, must not loop over all cells;
- resource roles: use `env.resource(name)` and field APIs;
- world roles: use `env.world`, `env.domain`, or collective context.

This matters for coding agents because the first generated function is often copied
and modified. If the first scaffold has the wrong loop shape, every later function
inherits the mistake. The role-aware scaffold makes the first draft structurally
correct.

The generic template also documents the collective/per-agent split so manual
authors and coding agents see the same rule even outside the GUI.

## The Typed `env` API

Node-functions do not manipulate raw global dictionaries directly. They receive
`env: BiologicalContext`, which exposes stable biological objects:

- `env.world`;
- `env.domain`;
- `env.population`;
- `env.agents`;
- `env.agent`;
- `env.resource(name)`;
- `env.cells`;
- result and configuration helpers.

This makes generated code more predictable. Instead of each coding agent inventing
its own context access pattern, functions use the same API. That reduces
integration failures and makes model code easier for a biologist to inspect.

The ABM class layer provides the stable objects behind that API:

- `World` / `LatticeWorld`: geometry, topology, neighborhoods, occupancy, sampling;
- `Domain`: owns the World and Resources;
- `Resource`: field state on the World;
- `Population`: collective over agents, creation, culling, reconciliation;
- `Agent`: one individual, with per-agent state and methods.

The classes hold state and provide operations. The workflow still owns the model's
scientific behavior through nodes.

## Execution: The Engine Owns Time

The engine executes the workflow in a simple shape:

1. `main` calls the initialization sequence once.
2. The initialization sequence creates the world, resources, and agents in order.
3. `main` calls the scheduler for the configured number of steps.
4. The scheduler executes its ordered calls each tick.
5. Calls with `for_each` are expanded by the executor into per-entity asks.

This means generated workflows do not need hidden Python loops around the entire
model. The coding agent creates nodes and wires them into orchestration canvases;
the executor owns time and iteration.

For per-agent calls, the executor binds the current agent into context so each inner
node sees a single `env.agent`. For collective calls, no agent is bound.

## Execution Edges and `execution_order`

A workflow can contain a node that never runs if it is not wired into
`execution_order`. That is a subtle failure mode for coding agents and GUI authors:
the model looks complete, but an intended function is skipped.

The GUI now uses a canonical execution-edge shape for order-carrying edges:

```text
func-out -> func-in
```

The export path rebuilds `execution_order` from reachable execution edges. Palette
actions that add calls to Initialization or Scheduler also create execution edges,
so button-added calls survive export. Removal logic stitches only execution edges,
not parameter edges, so parameter wiring cannot corrupt the run order.

The CLI validator also warns when a subworkflow has enabled nodes that are omitted
from a non-empty `execution_order`.

## Validation: Invalid ABM Structure Is Rejected Early

The system uses both GUI validation and CLI validation.

The CLI validator is:

```text
opencellcomms_engine/scripts/validate_workflow.py
```

It catches workflow-level mistakes that schema validation alone cannot catch.

Hard errors include:

- a `create_subworkflow` scheduled with `for_each`;
- an agent kind that declares a per-agent `init_subworkflow` (that phase was removed);
- behavior subworkflows homed to no tab in ABM workflows;
- resource or agent ownership mismatches;
- unknown or invalid structural references.

Warnings include:

- agent kinds exist but no creation is scheduled anywhere;
- enabled nodes exist but are omitted from `execution_order`.

The GUI mirrors the creation-structure checks and blocks export on hard errors. This
matters because it stops the invalid workflow before it becomes the biologist's
debugging problem.

## Canonical Examples Prevent Drift

Coding agents are strongly influenced by examples. The repository therefore
separates current canonical workflows from archived or generated fixtures.

Canonical examples show the correct current structure:

- MicroC: create-only tumor cell setup where the collective pass is the right model;
- SUGARSCAPE: discrete resources plus agent behavior;
- TCELL_CORRAL: collective creation that places cells and builds each cell's MaBoSS
  network in one pass;
- PhysiBoSS and related workflows when they pass the current validator.

Skip-marked workflows are allowed to remain in the repository for history, negative
tests, or GUI stress coverage, but they are explicitly not examples to copy. This
keeps the coding agent's training context aligned with the current architecture.

## Why This Reduces Iterations

The system reduces coding-agent iterations in five ways.

First, it constrains the target. The coding agent is not asked to design an ABM
runtime. It is asked to fill a known workflow grammar.

Second, it gives names to ambiguous biological roles. "Create cells", "initialize
each cell", and "step each cell" are different canvases with different execution
semantics.

Third, it generates code in the right shape for the selected role. A creation node
starts as collective code; a per-agent node starts as `env.agent` code.

Fourth, it validates the workflow at the same level where coding agents usually make
mistakes: execution order, ownership, `for_each`, and creation-before-init.

Fifth, it keeps examples clean. The agent is told which workflows are canonical and
which workflows are archived.

The intended result is that a biologist's correction loop is about biology:

- "this rule should depend on oxygen, not glucose";
- "activation should happen before migration";
- "the chemokine should decay at this rate";
- "this phenotype transition is missing."

It should not be about workflow plumbing:

- "the agents were never created";
- "the init ran before creation";
- "this step ran once globally instead of once per cell";
- "this node exists but never ran";
- "you copied an old workflow."

## What the Coding Agent Must Still Do

The software does not remove scientific judgment. The coding agent still has to:

- read the source paper or reference implementation;
- identify the model entities and state variables;
- decide which biological events are atomic functions;
- preserve update order and stochastic assumptions;
- expose meaningful parameters;
- write tests or smoke runs for the generated model;
- report assumptions back to the biologist.

The software reduces structural mistakes. It does not prove that the biological
model is scientifically correct.

## The Expected Contract

A correctly generated ABM workflow should satisfy this contract:

1. Every agent kind that needs agents created has a collective creation path.
2. Creation runs once, collectively (no `for_each`), including any per-cell setup.
3. Per-agent step uses `for_each`.
4. Per-agent functions operate on `env.agent`, not on all cells.
5. Collective functions use `env.population`, `env.cells`, `env.world`, or
   `env.domain`, not `env.agent` as if one were bound.
6. Resources are homed under Resources unless the behavior is genuinely a coupled
   World/Domain operation.
7. Scheduler and init calls are wired into execution order.
8. The workflow validates with zero hard errors.
9. The model is based on canonical examples or explicitly documented deviations.
10. The biologist can inspect the workflow by tabs and see the model they described.

When these conditions hold, the coding agent has a much narrower space of possible
mistakes, and the biologist spends fewer iterations correcting software structure.

