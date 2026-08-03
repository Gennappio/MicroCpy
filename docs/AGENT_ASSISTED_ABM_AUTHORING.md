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

## Operational Detail: How the AI Authoring Loop Actually Works

This section answers the practical questions that matter for describing the system
as an AI authoring protocol rather than just "we used an LLM."

### 1. How the AI Actually Creates a Model

The coding agent does not start by writing Python. It follows a staged protocol:

```text
Biologist request / paper / reference model
        |
        v
/occ_new-model intake
        |
        |  produces MODEL.md as the spec-of-record
        v
Skeleton workflow JSON
        |
        |  produced by following /occ_create-workflow rules
        v
GUI Overview preview
        |
        |  user approves structure before code exists
        v
/occ_new-function for each atomic node
        |
        v
Workflow validation
        |
        v
Run + /occ_review-run against observables
```

The algorithm is:

```text
Algorithm: agent-assisted ABM creation

Input:
  - biological model description from the user;
  - optional paper, DOI, reference implementation, config, or nearest plugin.

Output:
  - MODEL.md;
  - workflow JSON;
  - atomic Python node-functions;
  - validation and run-review report.

1. Prime from the nearest canonical model.
   Read the nearest plugin's MODEL.md and canonical workflow JSON.
   Do not copy skip-marked archived workflows.

2. Fill the intake checklist.
   For each model slot, mark it as:
     - answered by user;
     - sourced from paper/code/config;
     - chosen default;
     - unresolved consequential question.
   Stop while consequential unresolved questions remain.

3. Write MODEL.md.
   This is the human-readable model intent and provenance record.

4. Create the skeleton workflow JSON.
   The LLM writes the JSON directly into the repository, following the
   /occ_create-workflow protocol. There is no hidden separate model compiler.
   The JSON contains subworkflows, metadata.gui ownership, init sequence,
   scheduler, and empty/stub function nodes.

5. Preview before code.
   The GUI loads the workflow JSON and synthesizes the Overview and tabs from
   subworkflows + metadata.gui. The biologist checks structure while changes are
   cheap.

6. Generate functions.
   For each empty/stub function node, the agent follows /occ_new-function and
   writes one atomic Python function with the role-appropriate body shape.

7. Validate.
   Run workflow validation. Fix structural errors before running.

8. Run and review.
   Execute the workflow and compare run_summary.json and plots to MODEL.md
   observables.
```

Answers to the direct implementation questions:

| Question | Current Answer |
| --- | --- |
| Does the LLM generate workflow JSON directly? | Yes. The LLM writes the workflow JSON file directly, but it is constrained by the `/occ_new-model` and `/occ_create-workflow` authoring protocols. |
| Does it call `/occ_create-workflow`? | Conceptually yes: `/occ_new-model` composes `/occ_create-workflow`. In practice these slash commands are prompt protocols in `.claude/commands/`; the agent follows them and edits files with repository tools. They are not a separate opaque binary compiler. |
| Is GUI preview automatically synthesized from metadata? | Yes. The GUI derives tabs, subworkflow kinds, Overview links, and ownership from `workflow.subworkflows` plus `workflow.metadata.gui`. Runtime `subworkflow_kinds` is computed from that metadata rather than trusted as hand-authored truth. |
| Is there a single source of truth? | For executable workflow structure, yes: the workflow JSON. `MODEL.md` is the biological spec-of-record, Python files are node implementations, and the GUI is a view/editor over the JSON. |

So the source-of-truth stack is:

```text
MODEL.md        = biological intent, provenance, expected observables
workflow JSON   = executable workflow topology and GUI ownership
Python files    = implementation of each atomic node
GUI             = synthesized editor/preview of the workflow JSON
run_summary.json = evidence from an executed run
```

### 2. Validator Rules

There are several validation layers. The most publishable layer is
`opencellcomms_engine/scripts/validate_workflow.py`, because it checks the
GUI-readability and ABM-structure rules that normal JSON schema validation cannot
know.

The current workflow-readability validator applies these rules:

| ID | Severity | Rule | What It Prevents |
| --- | --- | --- | --- |
| WFV-1 | Error | Workflow file must be readable and parseable JSON. | The agent did not produce a usable workflow artifact. |
| WFV-2 | Error | In an ABM workflow, every subworkflow called by `main`, `__init_sequence__`, or `__scheduler__` must be homed under a navigable GUI category. | Callable behavior exists but the biologist cannot find or edit it in the GUI. |
| WFV-3 | Error | `environment.behavior_subworkflows` must be empty. | There is no Environment tab, so behaviors parked there become orphaned. |
| WFV-4 | Error | A registered `DICT` or `LIST` parameter must not be inlined directly in a function node's `parameters`; it must use a `dictParameterNode` or `listParameterNode`. | Complex parameters render as unreadable flat strings in the GUI. |
| WFV-5 | Warning | If a function is unregistered and has an inlined dict/list parameter, warn because its true type cannot be confirmed. | Early skeletons may contain GUI-unfriendly complex parameters. |
| WFV-6 | Error | Agent kinds must not declare a leftover `init_subworkflow`. The current two-canvas model has Creation plus per-agent Step; once-only per-cell setup belongs in Creation. | Reintroducing the old ambiguous per-agent init phase. |
| WFV-7 | Error | An agent `create_subworkflow` must not be scheduled with `for_each`. | Collective population creation would run once per agent, recreating or duplicating setup. |
| WFV-8 | Warning | If agent kinds exist but no `create_subworkflow` is scheduled in Initialization or `main`, warn. | Agents may never be created. The warning allows legitimate collective creation of several kinds inside one creation canvas. |
| WFV-9 | Warning | If `execution_order` is non-empty, every enabled function node and subworkflow-call node in that subworkflow should appear in it. | A visible node exists but never runs. |
| WFV-10 | Skip | A workflow with `metadata.validation.skip: true` is reported as skipped and excluded from totals. | Archived negative examples and stress fixtures do not teach users to ignore warnings. |

The GUI/export validator adds interactive checks before a workflow is saved:

| ID | Severity | Rule | What It Prevents |
| --- | --- | --- | --- |
| GUI-1 | Error | Subworkflow names must start with a letter and contain only letters, numbers, and underscores, except system names like `__scheduler__`. | Names that cannot be safely referenced or displayed. |
| GUI-2 | Error | Every call node must specify a target. | Dangling call nodes. |
| GUI-3 | Error | Every call target must exist in `workflow.subworkflows`. | Broken references. |
| GUI-4 | Error | A generic subworkflow cannot call a composer. Only composers can call composers. | Invalid hierarchy and confusing nested orchestration. |
| GUI-5 | Error | `execution_order` must not reference unknown node IDs. | Exporting a run order that points to deleted or nonexistent nodes. |
| GUI-6 | Error | Circular dependencies are rejected in the GUI validation path. | Infinite or ambiguous call graphs. |
| GUI-7 | Warning | Behavior subworkflows that require contracts should carry contract metadata. | Loss of machine-readable ownership/read/write discipline. |
| GUI-8 | Warning | Contract fields such as `reads`, `writes`, `emits`, and `consumes` must be lists when present. | Contracts that tools cannot parse. |
| GUI-9 | Warning | `contract.owner` must be an object when present. | Malformed ownership metadata. |
| GUI-10 | Warning | `contract.participants` must be a list when present. | Malformed coupling metadata. |
| GUI-11 | Warning | An `agent_behavior` should declare `owner.type = "agent"`. | A behavior is homed as an agent behavior but described as owning something else. |
| GUI-12 | Warning | An `agent_behavior` should write only `agent.self` or `intent.*`. | Agent behaviors directly mutating shared state instead of emitting intents. |
| GUI-13 | Warning | A `resource_behavior` should declare `owner.type = "resource"`. | A resource behavior is described with the wrong owner. |
| GUI-14 | Warning | A `resource_behavior` should write only `resource.self` or `intent.*`. | Resource behavior mutating unrelated state. |
| GUI-15 | Error | Agent kinds with leftover `init_subworkflow` are invalid in the current two-canvas model. | Reintroducing unsupported per-agent init. |
| GUI-16 | Warning | Agent kinds exist but no creation canvas is scheduled. | The model may contain no agents at runtime. |

The engine schema validator adds general workflow integrity checks:

| ID | Severity | Rule | What It Prevents |
| --- | --- | --- | --- |
| SCH-1 | Error | Workflow version must be supported. | Loading unknown workflow formats. |
| SCH-2 | Error | A v2 workflow must contain `main`. | No entry point. |
| SCH-3 | Error | `main` must have a controller node. | No executable entry controller. |
| SCH-4 | Error | `main` must not be deletable. | Users deleting the entry point. |
| SCH-5 | Error | Reserved names such as `init` and `system` cannot be used for normal subworkflows. | Name collisions with system concepts. |
| SCH-6 | Error | Subworkflow names must follow the allowed naming convention. | Invalid references and display names. |
| SCH-7 | Error | Subworkflow names must be 50 characters or fewer. | Unusable or unwieldy identifiers. |
| SCH-8 | Error | Subworkflow names must be unique case-insensitively. | Ambiguous references across platforms. |
| SCH-9 | Error | Every subworkflow must have a controller. | Non-enterable canvases. |
| SCH-10 | Error | Every subworkflow call must target an existing subworkflow. | Broken execution references. |
| SCH-11 | Warning | Direct self-calls are warned. | Possible infinite recursion unless iterations are bounded. |
| SCH-12 | Warning | Circular dependencies are warned by the engine schema path. | Possible infinite or confusing call graphs. |
| SCH-13 | Error | `execution_order` must reference known node IDs. | Run order points to missing nodes. |
| SCH-14 | Error | Node IDs inside a subworkflow must be unique. | Ambiguous node identity. |
| SCH-15 | Error | `iterations` must be an integer >= 1. | Non-executable loop counts. |
| SCH-16 | Warning | `iterations > 1000` is warned. | Accidental very expensive runs. |
| SCH-17 | Warning | Missing subworkflow descriptions are warned. | Poor GUI readability for biologists. |
| SCH-18 | Warning | Contract shape and agent/resource contract semantics are checked, as in the GUI. | Ownership/read/write metadata drift. |

"Resource behavior cannot live under World" is enforced by the ownership model rather
than by one string-matching rule. If a behavior is listed in
`world.behavior_subworkflows`, it is a World behavior. If it is listed under
`resource_kinds[k].behavior_subworkflows`, it is a Resource behavior. Contract
warnings then catch mismatches such as a resource behavior with non-resource owner or
wrong write discipline. The authoring protocol also tells the agent to home fields
under Resources unless the operation is genuinely coupled World/Domain behavior, such
as a multi-substance PDE solve.

### 3. What Prompt the AI Receives

The contribution is not simply "an LLM writes code." The repository defines an AI
authoring protocol through slash-command prompt files:

| Command | Purpose |
| --- | --- |
| `/occ_new-model` | Intake discipline, nearest-model priming, model preview before code, and orchestration of the other commands. |
| `/occ_create-plugin` | Create a new plugin/package when the model family does not exist yet. |
| `/occ_create-workflow` | Assemble a workflow JSON scaffold and `metadata.gui` from known behaviors. |
| `/occ_new-function` | Generate one atomic node-function in the correct role and file location. |
| `/occ_add-to-workflow` | Place an existing function into a workflow canvas. |
| `/occ_review-run` | Run the model and compare outputs to the observables recorded in `MODEL.md`. |

The `/occ_new-model` prompt tells the agent, in effect:

```text
You are helping a biologist go from a paper or existing model to a runnable
OpenCellComms model in as few iterations as possible.

Front-load the specification.
Fill the intake checklist before writing code.
Block code generation while any consequential NEEDS slot remains.
Use the nearest canonical workflow, not archived skip-marked fixtures.
Generate a skeleton workflow JSON first.
Stop for GUI Overview approval before writing Python.
Then generate each atomic node-function.
Validate and review the run against declared observables.
```

The `/occ_new-function` prompt then gives the lower-level function protocol:

```text
First decide where the function runs.
The canvas decides the execution shape.

Creation:
  - collective;
  - runs once;
  - env.agent is None;
  - may populate or loop over cells.

Agent Step:
  - runs once per agent through scheduler for_each;
  - env.agent is bound;
  - must not loop over all cells.

Generate one file, one function, one biological job.
Use env: BiologicalContext.
Declare parameters, requires, and contract.
```

This is stronger than generic AI assistance because the prompt is a reproducible
method. The LLM is being driven through a constrained protocol with stop gates,
source citation, GUI preview, and validation.

### 4. Real Failure Example: Double Iteration in an Agent Behavior

This is the failure that the protocol is designed to prevent.

Suppose the biologist says:

> Tumor cells migrate up an oxygen gradient.

A generic coding agent may write:

```python
def migrate(env, oxygen_name: str = "oxygen", threshold: float = 0.02, **kwargs) -> bool:
    oxygen = env.resource(oxygen_name)
    for cell in env.cells:
        if env.concentration(oxygen_name, cell) > threshold:
            # choose a better nearby position and move this cell
            ...
    return True
```

That code is collective. It loops over all cells. If the function is then placed on
an Agent Step canvas, the scheduler already calls it once per agent:

```text
for each tumor agent:
    run migrate()
        for each cell:
            move/check every cell again
```

The result is wrong:

- complexity becomes roughly `N_agents * N_cells`;
- cells may move or update multiple times per tick;
- stochastic order changes;
- the model can look biologically plausible while being algorithmically wrong.

OpenCellComms steers the coding agent to the correct scaffold because an Agent Step
is role-aware:

```python
def migrate(env, oxygen_name: str = "oxygen", threshold: float = 0.02, **kwargs) -> bool:
    agent = env.agent
    if agent is None:
        return True

    oxygen = env.resource(oxygen_name)
    here = agent.position
    best = here
    best_value = oxygen.at(here)

    for pos in env.world.neighbors(here, radius=1, mode="moore"):
        if env.world.is_free(pos) and oxygen.at(pos) > best_value:
            best = pos
            best_value = oxygen.at(pos)

    if best != here:
        env.request_move(target=best)
    return True
```

Now the scheduler does the iteration, and the function only acts on the bound agent:

```text
for each tumor agent:
    run migrate()
        inspect only this agent and its neighborhood
        emit one move intent
reconciliation commits the moves
```

This is a good figure for the paper:

| Wrong | Right |
| --- | --- |
| Agent Step contains `for cell in env.cells` | Agent Step uses `agent = env.agent` |
| Scheduler loops over agents and function loops over all cells | Scheduler loops; function handles one agent |
| `O(N^2)` accidental work | `O(N)` agent activations plus local neighborhood checks |
| Direct mutation may happen multiple times | Intent emitted once, reconciliation commits |
| Failure discovered after run/debugging | Prevented by role-aware scaffold and prompt protocol |

### 5. How Much It Reduces Iterations

This should be described carefully. The current evidence is primarily structural and
qualitative, not a controlled benchmark.

Before the protocol, the loop often looks like:

```text
Biologist describes model
        |
        v
LLM writes plausible workflow/code
        |
        v
Run fails or behavior is biologically wrong
        |
        v
User explains missing structure
        |
        v
LLM rewrites
        |
        v
Another hidden structure issue appears
```

The failures are not necessarily Python syntax failures. They are semantic workflow
failures:

- agents were never created;
- behavior was not homed to a GUI tab;
- a node existed but was omitted from `execution_order`;
- per-agent code looped over all cells;
- a collective creation ran with `for_each`;
- an archived workflow was copied as if it were canonical.

After the protocol, the loop is intended to become:

```text
Biologist describes model
        |
        v
Intake checklist resolves consequential unknowns
        |
        v
Skeleton workflow JSON + GUI preview
        |
        v
Validator catches structural errors
        |
        v
Node code generated from role-aware scaffolds
        |
        v
Run reviewed against declared observables
```

Qualitatively, this changes the iteration target:

| Before | After |
| --- | --- |
| Corrections are about missing workflow structure. | Corrections are about biological assumptions and parameter values. |
| The user discovers that the agent guessed the wrong architecture. | The user approves architecture before code exists. |
| Errors surface during simulation debugging. | Errors surface during static validation or GUI export. |
| Examples may be copied from stale workflows. | The prompt restricts copying to canonical workflows. |
| The agent has to infer where code belongs. | The role/table tells it where code belongs. |

An honest paper claim would be:

> The protocol is designed to reduce avoidable structural correction rounds. It does
> not guarantee biological correctness, but it moves common ABM authoring errors from
> post-run debugging into pre-run specification, preview, and validation.

If measured later, a simple benchmark would count:

- number of user correction turns before first valid workflow JSON;
- number of validator failures per model;
- number of run attempts before first non-crashing run;
- number of biology-level corrections after first run;
- time from model description to first validated workflow.

Even without a benchmark, the qualitative mechanism is clear: the system reduces
iterations by replacing unconstrained generation with a protocol of constrained
slots, GUI preview, role-aware scaffolds, and static validation.

### Concrete Example: Tumor, Oxygen, Macrophage, TNF

Biologist request:

> I want a model where tumor cells consume oxygen, macrophages secrete TNF, TNF
> diffuses, and tumor cells die under hypoxia.

The authoring protocol turns that into this workflow structure before code is
written:

```text
World
  __world__
    setup lattice
    setup domain/population

Resources
  oxygen
    oxygen_init
      initialize oxygen field
    oxygen_diffuse
      diffuse oxygen
      decay / boundary condition

  tnf
    tnf_init
      initialize TNF field
    tnf_diffuse
      diffuse TNF
      decay TNF

Agents
  tumor_cell
    tumor_cell_create       (authored in World; collective)
      place tumor cells
      wrap into ABM population
    tumor_cell_step         (per-agent, scheduler for_each)
      consume oxygen
      sense hypoxia
      request death if hypoxic

  macrophage
    macrophage_create       (authored in World; collective)
      place macrophages
      wrap into ABM population
    macrophage_step         (per-agent, scheduler for_each)
      migrate
      request TNF secretion

Scheduler
  each tick:
    ask tumor_cell -> tumor_cell_step
    ask macrophage -> macrophage_step
    run oxygen_diffuse
    run tnf_diffuse
    run reconciliation/world_step
    run census/reporting

Processing
  final_report
    write_run_summary
    plot world/resources/phenotypes
```

The corresponding `metadata.gui` homes each behavior to the tab where a biologist
expects to find it:

```json
{
  "agent_kinds": [
    {
      "name": "tumor_cell",
      "create_subworkflow": "tumor_cell_create",
      "behavior_subworkflows": ["tumor_cell_step"]
    },
    {
      "name": "macrophage",
      "create_subworkflow": "macrophage_create",
      "behavior_subworkflows": ["macrophage_step"]
    }
  ],
  "resource_kinds": [
    {
      "name": "oxygen",
      "init_subworkflow": "oxygen_init",
      "behavior_subworkflows": ["oxygen_diffuse"]
    },
    {
      "name": "tnf",
      "init_subworkflow": "tnf_init",
      "behavior_subworkflows": ["tnf_diffuse"]
    }
  ],
  "world": {
    "subworkflow": "__world__",
    "behavior_subworkflows": ["world_step"]
  },
  "init_sequence": { "subworkflow": "__init_sequence__" },
  "scheduler": { "subworkflow": "__scheduler__" },
  "processing": { "behavior_subworkflows": ["final_report"] }
}
```

The validator then checks the generated workflow before the run:

- tumor and macrophage creation canvases are scheduled;
- creation does not use `for_each`;
- no leftover per-agent init canvas exists;
- each scheduler behavior is homed to a GUI tab;
- execution-order chains include the intended nodes;
- complex parameters use parameter nodes where needed;
- resource and agent behavior contracts warn if ownership or writes are wrong.

This is the core contribution: the biologist describes biology, the AI maps it into
a constrained ABM workflow grammar, and validation prevents the most common
structural errors before simulation.
