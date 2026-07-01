# The ABM class layer — a simple map

This explains the new `src/abm/` library: what each file does, who owns what, and
how the pieces fit. It answers four questions people keep asking:

1. What is `model.py` for?
2. Which class owns the time?
3. Why are there two `domain.py`?
4. What's in the `biology/` folder?

---

## 1. The big picture

A spatial agent-based model has four kinds of thing, in a 2×2:

| | one of them (individual) | all of them (collective) |
|------------------|--------------------------|--------------------------|
| **agents side**  | `Agent`                  | `Population`             |
| **resources side** | `Resource`             | `Domain`                |

Plus one thing they all share: the **`World`** (the grid/world they live on).
The `World` is the only "smart" class — it knows geometry, neighbours,
distance, occupancy, and how to sample a field. Everybody else asks the `World`.

```
        Domain  ── owns ──>  Resource(s)        Population ── owns ──> Agent(s)
          │                     │                   │                    │
          └────── both sit on ──┴─── the World ─────┴────────────────────┘
```

Files, one line each:

| file | class | what it is |
|------|-------|------------|
| `src/abm/world.py` | `World`, `LatticeWorld` | the world: geometry, neighbours, occupancy, sampling |
| `src/abm/resource.py` | `Resource`, `FieldResource` | a field on the world (e.g. sugar) + its Setup/Step |
| `src/abm/domain.py` | `Domain` | owns the World + all Resources; runs their Steps |
| `src/abm/agent.py` | `Agent` | one individual; asks the World, writes itself |
| `src/abm/population.py` | `Population` | owns all Agents; activation (`ask`) + births/deaths |
| `src/abm/model.py` | *(no class)* | the **builder**: JSON description → wired Domain+Population |

---

## 2. What is `model.py` for?

`model.py` is **not a class**. It is a *factory*: it reads a plain description
(a dict / JSON) and builds the objects for you, wiring behaviours by name. It is
the seam the GUI will target — the GUI produces the description, `build_model`
turns it into a running model. Without it you'd hand-construct every object.

```python
from src.abm import build_model

description = {
    "world": {"type": "lattice", "size_x": 20, "size_y": 20, "tile_size": 1,
              "topology_x": "toroidal", "topology_y": "toroidal"},
    "resources": [{"name": "food", "initial": 1.0, "step": "regrow_food"}],
    "agents":     {"step": "eat_step"},
    "population": {"setup": "scatter", "count": 10},
}

# Behaviour *names* in the description are resolved to functions — either from an
# explicit map (shown here) or from the function registry (what the GUI uses).
domain, population = build_model(description, behaviours={
    "scatter": scatter, "eat_step": eat_step, "regrow_food": regrow_food,
})
```

That's all `model.py` does: description in, `(Domain, Population)` out.

---

## 3. Which class owns the time?

**None of the ABM classes own time.** Time is owned by the engine, not the
library:

- `src/simulation/clock.py` has a `Clock` (the current step number and `dt`).
- The workflow executor advances it and puts it in the shared context.
- A behaviour reads it through `env.step` and `env.dt` — never by holding a clock.

```python
def eat_step(env):
    now = env.step      # current step number, from the engine Clock
    ...
```

**Who decides the *order* of a step?** That's the *scheduler*, and right now it
lives in whoever runs the loop:

```python
for t in range(steps):                       # <- the loop / scheduler
    population.run_agent_step(env)            # ask each agent its Step
    domain.run_step(env)                      # each resource: apply sinks + Step
    population.run_collective_step(env)       # cull the dead, etc.
```

In a demo that loop is the harness; in a real run it is the v2.0 workflow
scheduler. So: **the engine owns the clock; the scheduler owns the order; the
ABM classes just expose `Setup`/`Step` for the scheduler to call.** (If we later
want a single object to own "run N steps in this order", that would be a new
`Scheduler`/`Model` class — it does not exist yet, on purpose.)

---

## 4. Why are there two `domain.py`?

Because two unrelated things were both called "domain". They never clash because
they live in different packages, but the name is confusing:

| file | class | meaning |
|------|-------|---------|
| `src/core/domain.py` | `MeshManager` | the **FiPy diffusion mesh** — the continuous grid the PDE solver uses for substances (oxygen, glucose). Old, unrelated to the ABM layer. |
| `src/abm/domain.py` | `Domain` | the **ABM collective over resources** — owns the World and the resource fields. New. |

Mental model: `core/domain.py` = "the physics mesh"; `abm/domain.py` = "the
world that owns the resources". Different layers. (Worth a rename someday —
e.g. `core/domain.py` → `core/mesh.py` — but it's only cosmetic; imports are
already unambiguous: `src.core.domain` vs `src.abm.domain`.)

---

## 4b. Two kinds of resource: discrete vs continuum

A `Resource` (`src/abm/resource.py`) is non-agent field state on the World. The
platform supports two agent↔resource coupling modes, both first-class:

| | `FieldResource` (discrete) | `DiffusingResource` (continuum) |
|--|--|--|
| example | Sugarscape sugar | MicroC oxygen / glucose / … |
| storage | a plain numpy field on the lattice | a substance inside a shared `MultiSubstanceSimulator` (the FiPy solver), exposed 1:1 as `values()[y, x]` |
| agent coupling | **discrete**: agents `deposit(pos, ±amt)` source/sink terms; `apply_sources()` commits them once per step | **continuum**: reaction rates come from cell metabolism and feed a coupled diffusion-reaction solve |
| the step | a per-resource `run_step` (e.g. growback) | a **collective** `diffuse(reactions)` — one FiPy solve over *all* coupled substances, not per-resource |

`DiffusingResource` *wraps* the existing solver rather than reimplementing it, so
its numerics are identical to the legacy diffusion path by construction. Register
a simulator's substances as resources with
`add_diffusing_resources(domain, world, simulator)`; drive the coupled solve with
the `diffuse_substances` behaviour (`src/workflow/functions/diffusion/`).

**Why the diffusion step is collective, not per-resource.** Coupled
multi-substance diffusion is one solve per tick over all fields together — a
domain-level process, not something any single substance owns. So MicroC uses a
**mix**: each substance is set up by its own per-resource **init** canvas (on the
Resources tab), while the coupled diffusion runs once per step as a collective
World/Domain step. The substances are real resources with real init canvases (each
`*_init` subworkflow runs `setup_substances` for one substance, wired into
`__init_sequence__`); only the shared solve stays collective. The GUI auto-scopes
per-resource *behaviours* to `for_each:{type:resource}`, which is why the coupled
solve is a World step rather than a per-resource behaviour. See
`docs/MICROC_ABM_MIGRATION_PLAN.md` (Stage 6) for the full story.

---

## 5. What's in the `biology/` folder?

The original engine model of cells — the ABM layer **wraps** these, it does not
replace them.

| file | class | what it is |
|------|-------|------------|
| `src/biology/cell.py` | `Cell`, `CellState` | one cell's data (id, position, phenotype, `metabolic_state`) |
| `src/biology/population.py` | `CellPopulation` | the spatial collection of cells + `spatial_grid` (occupancy) + division/death/migration |
| `src/biology/gene_network.py` | `BooleanNetwork` | a per-cell gene regulatory network (used by MicroC) |
| `src/biology/context.py` | `BiologicalContext` + views | the typed `env` API behaviours receive |

How the ABM layer maps onto it (wrap & adapt):

```
ABM            wraps          biology
----           -----          -------
Agent          ─────────────> Cell
Population      ─────────────> CellPopulation   (reuses spatial_grid for occupancy)
env.world etc. ─ added to ───> BiologicalContext
```

So an `Agent` is a thin handle over a `Cell`; a `Population` is a thin manager
over a `CellPopulation`. Nothing in `biology/` was rewritten.

---

## 6. A complete tiny example

A 20×20 toroidal world, one `food` field that regrows, ten agents that eat and
starve. This is the whole shape in ~25 lines.

```python
import numpy as np
from src.abm import build_model
from src.biology.context import BiologicalContext

# --- behaviours (each receives `env`; agent steps use env.agent) -------------
def scatter(env):                                   # Population Setup
    env.population.populate(env.population.params["count"], energy=5.0)

def eat_step(env):                                  # Agent Step (per agent)
    a = env.agent
    got = a.sense("food")           # read the field at my tile (via the World)
    a.consume("food", got)          # deposit a sink; applied in the resource Step
    a.set("energy", a.get("energy") + got - 1.0)    # eat, pay upkeep
    if a.get("energy") < 0:
        a.die()                     # request removal; Population commits it

def regrow_food(env):                               # Resource Step (per field)
    env.resource("food").grow_to(np.full(env.world.shape, 1.0), 0.1)

# --- build + run -------------------------------------------------------------
description = {
    "world": {"type": "lattice", "size_x": 20, "size_y": 20, "tile_size": 1,
              "topology_x": "toroidal", "topology_y": "toroidal"},
    "resources": [{"name": "food", "initial": 1.0, "step": "regrow_food"}],
    "agents":     {"step": "eat_step"},
    "population": {"setup": "scatter", "count": 10},
}
domain, population = build_model(description, behaviours={
    "scatter": scatter, "eat_step": eat_step, "regrow_food": regrow_food})

env = BiologicalContext({"domain": domain, "abm_population": population})
domain.run_setup(env)               # build resources, seed them
population.run_setup(env)           # place the 10 agents

for t in range(3):                  # <- HAND-WRITTEN stand-in for the scheduler
    population.run_agent_step(env)          # ask agents: eat_step
    domain.run_step(env)                    # food: apply sinks, then regrow
    population.run_collective_step(env)     # (no collective step here)
    print(f"step {t}: {population.count()} agents, food {domain.resource('food').total():.0f}")
```

Read it top-to-bottom and every earlier question is visible: `build_model` wires
it (Q1), the `for` loop is the scheduler and `env` carries the clock (Q2),
`Domain` is the ABM one (Q3), and `Population`/`Agent` are wrapping the
`biology/` cells underneath (Q4).

> **That `for` loop is a stand-in.** In a real run you do **not** hand-write it —
> the GUI builds it. See section 7.

---

## 7. How the GUI's nodes become that loop

In the GUI you place each behaviour as a **node** in the Scheduler canvas and
order them. That order is not inferred by any magic — the GUI **serializes it as
an explicit list**, and the executor walks that list. Two fields do the work:

- every subworkflow has an `execution_order`: an ordered list of node ids;
- its controller has a step count (`number_of_steps` / `iterations`).

The special `__scheduler__` subworkflow **is** the main loop: the executor runs
its `execution_order` once per step, for `number_of_steps` steps. So the visual
order you draw becomes the run order, literally:

```
GUI Scheduler canvas              workflow JSON (__scheduler__)        executor
------------------------          ----------------------------        --------
[ask agents]  ──>                 "execution_order": [                 for _ in range(number_of_steps):
[update resources] ──>      ==>      "ask_agents",               ==>       for node in execution_order:
[cull] ──>                           "update_resources",                      run(node, env)
(controller: 200 steps)              "cull" ]
                                  "number_of_steps": 200
```

So the answer to "how does the code know the order?": **it doesn't infer it —
the order is an explicit array the GUI writes and the executor reads.** That is
the whole point of "every step is a visible node": the run order is the node
order, nothing hidden.

**How it actually runs (the executor owns the loop, behaviours are nodes).** The
hand-written `for` above is only for illustration. In the real system every
behaviour is a **node** on a canvas, and the **executor** iterates the
`__scheduler__` subworkflow exactly as for any workflow. The classes here are the
typed API those node-functions call (`env.world`, `env.agent`, `agent.sense(...)`)
— not a runner. One execution capability is new: a `subworkflow_call` with
`for_each: {kind, order}` runs a behaviour subworkflow **once per agent** (the
"ask"), binding `env.agent`. See `docs/ABM_GUI.md` and
`opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json`.

(Earlier transitional experiments — the `FoodWorld` bridge plugin and a single
`run_abm_model` mega-node — were removed; they hid the per-step loop from the
canvas, which defeats the point.)

---

## Things worth tidying (optional)

- **Rename `core/domain.py` → `core/mesh.py`** (its class is `MeshManager`) to
  kill the two-`domain` confusion. Cosmetic; touches a few imports.
- **No `Scheduler`/`Model` object owns "run the loop".** Fine for now (the
  workflow scheduler does it), but if you want the library runnable standalone
  with one call, that's the class to add.
