# Behavior Library Manual

This manual defines how OpenCellComms behavior libraries should be authored,
classified, exported, and reviewed in the GUI.

The current system is in warning mode: contracts are displayed and validated,
but the executor does not yet block invalid behavior. Treat the rules below as
the target architecture.

## Core Model

The workflow is organized by process role, not only by object type.

Objects still exist:

- Agents
- Resources
- Space
- World or environment state

But a behavior belongs to one process role:

- Initialization
- Agent behavior
- Resource behavior
- Coupling
- Reconciliation
- Reporting

The GUI still has familiar places such as Agents, Resources, Environment, and
Processing, but each canvas now declares a contract phase. The phase is the
source of truth for what belongs on that canvas.

## Process Roles

| Role | Use for | Should write | Should not do |
| --- | --- | --- | --- |
| Initialization | Create space, resources, agents, model config | Initial collections and config | Runtime decisions |
| Agent behavior | Agent-local decisions and internal state | `agent.self`, intents | Directly mutate resources or cull other agents |
| Resource behavior | Resource-local dynamics | `resource.self`, intents | Inspect or control agents directly |
| Coupling | Cross-object interaction | Coupled state or intents | Hide structural commits |
| Reconciliation | Mechanical commits | Agent/resource/space collections | Domain decisions |
| Reporting | Plots, exports, census | Nothing in model state | Mutate simulation state |

Coupling is the home for interactions such as:

- Agent-resource sensing
- Cell-field response
- Agent-agent interaction
- Diffusion coupled to cells
- Signaling and mechanics

Reconciliation is the home for structural changes such as:

- Move agents
- Consume resources
- Add agents
- Remove agents
- Apply queued resource deltas

## Contract Schema

Every behavior canvas and every library function may declare a contract:

```json
{
  "phase": "coupling",
  "owner": { "type": "agent", "kind": "tumor_cell" },
  "participants": [
    { "type": "agent", "kind": "tumor_cell" },
    { "type": "resource", "kind": "oxygen" }
  ],
  "reads": ["agent.collection", "resource.fields"],
  "writes": ["agent.self.gene_states"],
  "emits": ["intent.consume_resource"],
  "consumes": []
}
```

All fields except `phase` are optional, but authors should fill them when the
behavior is stable.

Common access tokens:

- `agent.self`
- `agent.collection`
- `agent.self.gene_states`
- `agent.self.phenotype`
- `resource.self`
- `resource.collection`
- `resource.fields`
- `resource.<kind>.local`
- `space.self`
- `space.neighborhood`
- `simulation.config`
- `simulation.results`
- `gene_networks`
- `associations`
- `intent.*`

## Intent API

Intent helpers separate a local decision from the shared-state commit.

Agent behavior can request an action:

```python
env.request_consume_resource("sugar", position=target, store_as="sugar")
```

This records an intent. It does not mutate the sugar field immediately.

Later, reconciliation commits it:

```python
apply_reconciliation(env)
```

Available helpers:

```python
env.request_move(target=(x, y))
env.request_remove_agent(reason="starved")
env.request_add_agent(kind="cell", position=(x, y), state={})
env.request_resource_delta("oxygen", amount=-0.1, position=(x, y))
env.request_consume_resource("sugar", position=(x, y), store_as="sugar")
```

Use intents when a behavior wants to change shared world structure or shared
resources. Direct writes to `agent.self` are still acceptable inside agent
behavior.

## Writing Registered Functions

Library functions should declare a contract in `@register_function` when
possible:

```python
@register_function(
    display_name="Eat Sugar",
    description="Agent consumes sugar on its selected tile",
    category="INTERCELLULAR",
    inputs=["context"],
    outputs=[],
    contract={
        "phase": "coupling",
        "participants": [
            {"type": "agent", "kind": "forager"},
            {"type": "resource", "kind": "sugar"}
        ],
        "reads": ["agent.self", "resource.sugar.local"],
        "writes": [],
        "emits": ["intent.consume_resource"]
    },
)
def eat_sugar(env, **kwargs):
    target = env.agent.get("_pending_position", env.agent.position)
    env.request_consume_resource("sugar", position=target, store_as="sugar")
    return True
```

If a function has no explicit contract, the GUI infers one from legacy category
metadata. Inferred contracts are weaker and should be replaced by explicit
contracts in library code.

## GUI Rules

The Library panel shows the active canvas role and filters functions:

- `Match`: hides explicit phase mismatches.
- `Warnings`: shows functions with explicit or inferred phase concerns.
- `All`: shows every loaded function.

Function nodes display their phase. The inspector shows:

- Canvas role
- Subworkflow contract
- Function contract
- Reads, writes, emits, consumes
- Owner and participants

When creating an Environment behavior, choose the process role:

- Coupling
- Reconciliation
- Reporting

This is intentional. Environment is not a free "global rules" area. It is a
host for explicit cross-object process roles.

## Export Rules

When a workflow or behavior is exported, contracts are exported with it:

- `subworkflows[*].contract`
- `subworkflows[*].functions[*].contract`
- standalone `.subworkflow.json` behavior contracts

A behavior library should keep the workflow file and exported behavior files in
sync. If a behavior is shared across projects, export the `.subworkflow.json`
file so its contract travels with it.

## Examples

Sugarscape:

- `forager_step`: agent behavior
- `move_to_best_sugar`: coupling, emits `intent.move`
- `eat_sugar`: coupling, emits `intent.consume_resource`
- `metabolize`: agent behavior, emits `intent.remove_agent`
- `sugar_growback`: resource behavior
- `world_step`: reconciliation, consumes `intent.*`
- `final_snapshot`: reporting

MicroC:

- `diffusion_step`: coupling between cells, fields, and space
- `gene_update`: coupling between fields and gene networks
- `fate_update`: coupling or agent behavior depending on node
- `division`: reconciliation because it changes population membership
- `iteration_plots`: reporting
- `final_summary`: reporting

## Review Checklist

Before accepting a behavior library:

- Each behavior canvas has a contract.
- Each exported behavior file carries the same contract.
- Agent behaviors do not directly mutate resources or other agents.
- Resource behaviors do not inspect or control agents.
- Couplings declare at least two participants.
- Reconciliation is mechanical and consumes intents where possible.
- Reporting functions are read-only.
- Newly shared functions have explicit contracts in the decorator.

## Current Limitations

The architecture is not fully strict yet.

- Validation is warning-only.
- Some legacy functions still mutate shared state directly.
- Some registry entries still rely on inferred contracts.
- MicroC is annotated but not yet rewritten to intent/reconciliation mechanics.

The next enforcement step is to make executor warnings stricter, then block
invalid writes once the main libraries are migrated.
