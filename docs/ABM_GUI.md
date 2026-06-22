# Authoring an ABM model in the GUI (class layer, node-based)

The class layer is authored **on canvases, as nodes** — the same node↔`.py`,
palette, code generation, and observability as every other workflow. It is built
*through* the node system, not as forms. (One file = one node = one atomic
function; a behaviour is a subworkflow of atomic nodes.)

## The tabs

| Tab | What you author (all canvases) |
|-----|--------------------------------|
| **Agents** | Agent kinds. Each kind has a **Setup** canvas (placement) and **Step** canvas(es) — atomic nodes wired into a behaviour subworkflow. |
| **Resources** | Resource fields (mirror of Agents): a **Setup** canvas (seed) and **Step** canvas(es) (growback/decay). |
| **World** | The `setup_world` node, the **init orchestration** (order the Setups), the thin Domain/Population behaviours, and an initial-conditions **preview**. |
| **Scheduler** | The **loop orchestration** — order the per-step phases (agents → resources → population), iterated by the executor. |

World = init orchestration; Scheduler = loop orchestration. Both call the wrapped
behaviour subworkflows authored in the entity tabs.

## The typed `env` API (what the node-functions call)

Atomic node-functions take `env: BiologicalContext` and use the class layer:

```python
def move_to_best_sugar(env):            # an agent Step node (operates on env.agent)
    a = env.agent
    sp, sugar = env.world, env.resource("sugar")
    best = a.position
    best_s = sugar.at(best)
    for cell in sp.neighbors(a.position, int(a.get("vision", 1)), "axial"):
        if sp.is_free(cell) and sugar.at(cell) > best_s:
            best, best_s = cell, sugar.at(cell)
    if best != a.position:
        a.move_to(best)

def grow_sugar(env):                    # a resource Step node (whole field, once)
    env.resource("sugar").grow_to(env.resource("max_sugar").values(), 1.0)
```

`env.world`, `env.agent`, `env.resource(name)`, `env.population`, `env.domain`,
`agent.neighbors/sense/move_to/consume/die` — the `src/abm` classes are this API.

## Per-agent "ask" (the one new execution capability)

An agent's **Step** is per-agent. In the Scheduler, the "agents phase" is a
`subworkflow_call` marked **`for_each: {kind, order}`**. The executor runs the
called Step subworkflow **once per agent** of that kind (in activation order),
binding `env.agent` so each inner node operates on one agent. Every inner node is
a normal executor-run node → full observability, per agent.

Agent **Setup** (placement) runs once; resource and collective (Population/Domain)
behaviours run once.

## The collective rule

A collective never decides *for* its agents (that kills emergence). So:
- **Population** only places agents and commits their decisions (`cull` the dead,
  census). The rich behaviour is on the agents.
- **Domain** orchestrates resources and may apply *exogenous* world change
  (boundary conditions, perturbations) — the world changing, which agents sense.

## Running

The executor owns the loop: `main` calls the init sequence once, then the
`__scheduler__` subworkflow `steps` times. Each step runs the scheduler's
execution_order (the per-agent ask, the resource steps, the population step). The
existing **Run** button works unchanged. See
`opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json` for the reference
node workflow.
