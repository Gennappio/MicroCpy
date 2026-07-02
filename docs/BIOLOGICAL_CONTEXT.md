# BiologicalContext — the typed authoring layer

`BiologicalContext` is the **recommended way to write workflow functions** in
OpenCellComms. It is a thin, typed wrapper over the raw `context` dictionary that
flows through a simulation run. Instead of reaching into `context['population']`
and assigning `cell.state.phenotype = 'Necrosis'`, you receive an `env` object
with typed views (`env.cells`, `env.environment`, `env.results`) and explicit
mutation methods (`cell.mark_necrotic()`).

The legacy `context: Dict[str, Any]` style still works unchanged — both styles
read and write the **same** underlying dict, so a typed function and a legacy
function can sit side by side in one workflow and see each other's mutations.

Source: `opencellcomms_engine/src/biology/context.py`

---

## 1) Where it comes from (you never construct it)

You do **not** create a `BiologicalContext` yourself. The workflow executor
constructs it for you, automatically, by inspecting your function's signature.

A function **opts in** by declaring its first parameter as `env` annotated
`BiologicalContext`:

```python
from src.biology.context import BiologicalContext

def my_rule(env: BiologicalContext, threshold: float = 0.1):
    ...
```

The mechanism:

1. `_wants_typed_env(func)` in `opencellcomms_engine/src/workflow/executor.py`
   inspects the signature. If the first non-`self` parameter is named `env` and
   annotated `BiologicalContext` (the **string** form is matched too, so
   `from __future__ import annotations` is fine), the function opts in. The
   result is cached per function.
2. When such a node runs, the executor wraps the live context dict:
   ```python
   kwargs['env'] = BiologicalContext(context)
   ```
   This happens at `executor.py` (around lines 584 / 594 / 600 for the plain
   path, and again around line 849 for the observability/change-tracking path).

Because the wrapper holds a reference to the same dict, **every view reads and
writes through that one dict** — mutations propagate to other functions (typed or
legacy) in the same run.

> Trigger summary: get an `env` by *naming and annotating* the first argument.
> Nothing else (no decorator flag, no registration field) is required.

---

## 2) Quick start

```python
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext, Phenotype

@register_function(
    display_name="Necrosis Under Hypoxia",
    description="Mark cells necrotic when local oxygen drops below a threshold",
    category="INTERCELLULAR",
    parameters=[
        {"name": "oxygen_threshold", "type": "FLOAT", "default": 0.1,
         "min_value": 0.0, "max_value": 1.0},
    ],
    inputs=["context"],
    outputs=[],
    compatible_kernels=["biophysics"],
)
def necrosis_under_hypoxia(env: BiologicalContext, oxygen_threshold: float = 0.1):
    killed = 0
    for cell in env.cells:                              # iterate the population
        o2 = env.concentration('oxygen', cell)         # substance @ this cell
        if o2 < oxygen_threshold:
            cell.mark_necrotic()                       # typed phenotype mutation
            killed += 1
    env.results.store('necrotic_this_step', killed)    # typed result sink
```

Compare with the legacy equivalent (still valid):

```python
def necrosis_under_hypoxia(context, oxygen_threshold=0.1, **kwargs):
    pop = context.get('population')
    sim = context.get('simulator')
    for cell in pop.state.cells.values():
        x, y = cell.state.position[0], cell.state.position[1]
        o2 = sim.get_substance_concentration('oxygen', x, y)
        if o2 < oxygen_threshold:
            cell.state = cell.state.with_updates(phenotype='Necrosis')
```

The typed version is shorter, hides coordinate→grid conversion, and makes the
phenotype change explicit and discoverable.

---

## 3) API reference

### `env` — the root (`BiologicalContext`)

**Cell / substance / results views** (the legacy MicroC-style surface):

| Member | Returns | Notes |
|---|---|---|
| `env.cells` | `PopulationView` | iterate / query / add cells |
| `env.environment` | `EnvironmentView` | substance concentration queries |
| `env.results` | `ResultsView` | typed results / change sink |
| `env.concentration(substance, at)` | `float` | shortcut for `env.environment.concentration(...)` |
| `env.concentrations_at(at)` | `Dict[str, float]` | all substances at a cell/position |
| `env.gene_network(cell)` | `BooleanNetwork \| None` | underlying network for direct access (`.step()`, graph walking) |
| `env.set_gene_network(cell, net)` | — | bind a network for a cell id |
| `env.remove_gene_network(cell)` | — | unbind |

**Clock / config:**

| Member | Returns | Notes |
|---|---|---|
| `env.step` | `int` | reads `clock.step`, else `current_step`/`step` |
| `env.dt` | `float` | reads `clock.dt`, else `dt` (default `1.0`) |
| `env.config` | config object | `context['config']` |
| `env.verbose` | `bool` | `context['verbose']` |
| `env.rng` | `numpy.random.Generator` | the single **seeded** run RNG — stochastic behaviours must draw from this (never `np.random.*`) to stay reproducible |

**ABM class layer** (World / Domain / Population / Resource / Agent — see §7):

| Member | Returns | Notes |
|---|---|---|
| `env.world` | `World` | the active spatial world (grid, topology, neighbours, occupancy) |
| `env.domain` | `Domain` | the collective over resources; owns the World |
| `env.population` | `Population` | the ABM population wrapper (distinct from `env.cells`' raw `CellPopulation`) |
| `env.agents` | `List[Agent]` | all ABM agents (empty if no ABM population) |
| `env.agent` | `Agent \| None` | the agent currently being **asked** (set by the per-agent loop) |
| `env.cell` | `CellHandle \| None` | the cell currently being asked in a **legacy** per-cell loop |
| `env.resource(name)` | `Resource` | the named resource field on the Domain |
| `env.resources` | `List[Resource]` | all resource fields on the Domain |
| `env.current_resource` | `Resource \| None` | the resource currently being stepped by a resource behaviour |
| `env.kind` | `str \| None` | the agent kind currently being set up / stepped |
| `env.kind_params` | `Dict` | params (count + traits) of the current kind |

**Intent queue** (deferred model changes; see §8):

| Member | Returns | Notes |
|---|---|---|
| `env.emit_intent(kind, **payload)` | — | append a typed change request for reconciliation |
| `env.request_move(...)`, `env.request_remove_agent(...)`, `env.request_add_agent(...)`, `env.request_resource_delta(...)`, `env.request_consume_resource(...)` | — | typed intent helpers |
| `env.intents` | `Dict[str, List]` | pending intents, grouped by kind |
| `env.clear_intents()` | — | drop all pending intents |

**Observability** (plots + recorded series; see §9):

| Member | Returns | Notes |
|---|---|---|
| `env.record(key, value, step=None)` | — | append a scalar to a named time series |
| `env.records` | `Dict[str, List]` | the recorded series buffer |
| `env.plot_records(keys, filename, ...)` | `Path` | plot recorded series to `plots_dir` |
| `env.plot_timeseries(series, filename, ...)` | `Path` | plot arbitrary named series |
| `env.plot_field(name, filename=None, ...)` | `Path` | render a resource field as a heatmap |
| `env.plots_dir` | `Path` | directory plotting nodes write to |

**Escape hatch:**

| Member | Returns | Notes |
|---|---|---|
| `env.raw_context` | `Dict[str, Any]` | the underlying dict — you are leaving the typed zone |

`cell` arguments accept a `CellHandle`, a raw engine `Cell`, or a cell-id string.

### `env.cells` — `PopulationView`

| Member | Returns | Notes |
|---|---|---|
| `for cell in env.cells` | `CellHandle` | iterates `population.state.cells` |
| `len(env.cells)` | `int` | cell count |
| `env.cells.by_id(cell_id)` | `CellHandle \| None` | |
| `env.cells.by_phenotype(p)` | iterator of `CellHandle` | `p` is `Phenotype` or `str` |
| `env.cells.add(position, phenotype=Phenotype.GROWTH_ARREST)` | `bool` | adds a cell |
| `env.cells.statistics()` | `Dict` | `population.get_population_statistics()` |
| `env.cells.raw` | `CellPopulation \| None` | escape hatch |

### `CellHandle` — one cell

**Read-only properties:** `id`, `position`, `phenotype`, `age`,
`division_count`, `gene_states` (a snapshot dict), and `raw` (the engine `Cell`).

**Phenotype mutations** (use these, not string assignment — each rebuilds
`cell.state` via `with_updates`):
`set_phenotype(p)`, `mark_necrotic()`, `mark_apoptotic()`,
`mark_proliferating()`, `mark_growth_arrested()`, `mark_quiescent()`,
`set_age(hours)`, `set_gene_state_snapshot(dict)`.

**Phenotype queries:** `is_necrotic`, `is_apoptotic`, `is_proliferating`,
`is_growth_arrested`, `is_quiescent`.

**Gene access:** `cell.gene(name)` → `GeneNode | None`; `cell.has_gene(name)` → `bool`.

### `GeneNode` — one gene in a cell's network

`is_on()`, `is_off()`, `turn_on()`, `turn_off()`, `set(bool)`, and `.name`.

### `env.environment` — `EnvironmentView`

| Member | Returns | Notes |
|---|---|---|
| `concentration(substance, at)` | `float` | cell→grid conversion handled; case-insensitive substance fallback (`'oxygen'` vs `'Oxygen'`); `0.0` if unknown/out of range |
| `concentrations_at(at)` | `Dict[str, float]` | all substances at one location |
| `all_substances()` | `List[str]` | substance names |
| `summary()` | `Dict` | `simulator.get_summary_statistics()` |
| `invalidate_cache()` | — | drop the cached concentration snapshot; **call after `simulator.update()`** |
| `raw_simulator` | `ISubstanceSimulator \| None` | escape hatch |

`EnvironmentView` caches the concentration snapshot on first read for speed. If
your function advances the diffusion solver and then re-reads concentrations,
call `env.environment.invalidate_cache()` in between.

### `env.results` — `ResultsView`

`store(key, value)` / `get(key, default=None)` (writes `context['results']`),
and `record_change(category, payload)` / `get_change(category)` (writes
`context['changes']`).

### `Phenotype` enum

`Phenotype.NECROSIS`, `APOPTOSIS`, `PROLIFERATION`, `GROWTH_ARREST`,
`QUIESCENT`. It subclasses `str`, so `cell.phenotype == 'Necrosis'` still
compares correctly during migration — but prefer the `mark_*()` methods.

---

## 3b) The ABM class layer through `env`

Beyond the cell/substance views, `env` surfaces the **ABM object model**
(`opencellcomms_engine/src/abm/`): `World`, `Domain`, `Resource`, `Population`,
`Agent`. These are the objects a spatial agent-based model (Sugarscape-style) is
built from; the model builder (`build_model`) stores them in the context and
`env` hands them to your node-functions. See `docs/ABM_LAYER.md` for the
architecture; this is the `env`-facing API surface.

Two calling conventions decide *which* entity your function acts on:

- **Agent Step** runs **once per agent** (the per-agent "ask"). Inside it,
  `env.agent` is the current `Agent`. Iterate neighbours, move, consume.
- **Resource / collective Step** runs **once**. Use `env.resource(name)` or
  `env.resources`, and `env.current_resource` when a per-resource behaviour is
  bound.

### `env.agent` — one `Agent` (per-agent Step)

| Member | Returns | Notes |
|---|---|---|
| `agent.id` | `str` | underlying cell id |
| `agent.position` | `Position` | integer tile `(ti, tj)` |
| `agent.kind` | `str \| None` | the agent kind (stored in `metabolic_state['_kind']`) |
| `agent.cell` | `Cell` | underlying engine `Cell` (lets legacy per-cell functions run) |
| `agent.get(key, default=None)` / `agent.set(key, value)` | — | per-agent traits (energy, vision, …) |
| `agent.is_alive()` | `bool` | false once `die()` has been requested |
| `agent.world` | `World` | the world this agent lives on |
| `agent.neighbors(radius=1, pattern="moore")` | `List[Agent]` | occupied neighbour tiles → agents |
| `agent.empty_cells(radius=1, pattern="moore")` | `List[Position]` | free neighbour tiles |
| `agent.is_free(pos)` | `bool` | is a tile unoccupied and in-domain |
| `agent.sense(resource)` | `float` | resource field value at this agent's tile |
| `agent.distance_to(other)` | `float` | world distance (honours topology) |
| `agent.move_to(pos)` / `agent.move_toward(target)` | — | relocate self (Population commits occupancy) |
| `agent.consume(resource, amount)` / `agent.produce(resource, amount)` | — | deposit a sink/source term on a field (applied at the resource Step) |
| `agent.die()` | — | **request** removal; the Population culls it later |

`pattern` is `"moore"` (8-neighbour), `"vonneumann"` (4-neighbour diamond), or
`"axial"` (the four straight rays — Sugarscape vision).

### `env.world` — the spatial world (`World` / `LatticeWorld`)

The only "smart" spatial class: geometry, topology, neighbourhood, occupancy,
sampling. Agents and resources delegate every spatial question to it.

| Member | Returns | Notes |
|---|---|---|
| `world.shape` | `(ny, nx)` | numpy field shape for resources over this world |
| `world.nx`, `world.ny`, `world.dimension` | `int` | grid extents (LatticeWorld is 2D only) |
| `world.bounds()` | `(min, max)` | inclusive-min / exclusive-max corners |
| `world.contains(pos)` | `bool` | in-domain and occupiable |
| `world.normalize(pos)` | `Position` | wrap (toroidal) or clamp (bounded) onto a valid tile |
| `world.neighbors(pos, radius=1, pattern="moore")` | `List[Position]` | neighbour tiles, excluding centre |
| `world.distance(a, b)` | `float` | topology-aware distance |
| `world.direction(a, b)` | `(dx, dy)` | unit direction a→b |
| `world.interpolate(values, pos)` | `float` | sample a `(ny, nx)` field at a tile |
| `world.is_free(pos)` | `bool` | unoccupied and in-domain |
| `world.occupants(pos)` | `List[str]` | cell ids on a tile |
| `world.within(pos, radius, pattern="moore")` | `List[str]` | occupant ids in a neighbourhood |
| `world.random_position(rng, empty=False)` | `Position \| None` | a random (optionally empty) tile |
| `world.iter_positions()` | iterator of `Position` | every tile |

### `env.resource(name)` / `env.resources` — fields (`Resource`)

A resource is non-agent field state on the world (sugar, oxygen, a pheromone).
Two flavours: **`FieldResource`** (a plain numpy field; discrete deposit
coupling) and **`DiffusingResource`** (a view onto one substance in the shared
FiPy solver; continuum coupling). Common surface:

| Member | Returns | Notes |
|---|---|---|
| `resource.name` | `str` | field name |
| `resource.at(pos)` | `float` | value at a tile |
| `resource.values()` | `np.ndarray` | the `(ny, nx)` field |
| `resource.total()` / `resource.max()` / `resource.min()` | `float` | field aggregates |
| `resource.deposit(pos, amount)` | — | accumulate a source(+)/sink(−) term (committed at the resource Step) |
| `resource.heatmap(ax=None, cmap="YlOrBr", ...)` | `Axes` | draw the field as a heatmap |

`FieldResource` adds field ops a Step behaviour can call: `set_at(pos, value)`,
`fill(value)`, `map(fn)`, `decay(rate)`, `grow_to(capacity, rate)` (Sugarscape
growback), `clamp_to(capacity)`. `DiffusingResource` adds `diffuse(reactions)` —
one **collective** solve over all coupled substances (driven once per tick by the
`diffuse_substances` behaviour, not per-resource).

### `env.population` / `env.domain` — the collectives

`Population` owns the agents and is the **only** place they appear
(`spawn`/`populate`) or disappear (`cull`); it also owns activation order
(`ask`). `Domain` owns the World and all resources. Node behaviours rarely call
these directly — the executor drives `run_setup` / `run_agent_step` /
`run_step` / `run_collective_step` — but useful read helpers include
`population.count()`, `population.count_by_kind()`, `population.snapshot()`
(positions grouped by kind, for plotting), `population.record_census(step)`, and
`domain.totals()` / `domain.record_totals(step)`.

---

## 3c) Deferred model changes — the intent queue

Inside a per-agent Step an agent should **request** structural change, not commit
it, so all agents decide against the same world state and a reconciliation phase
applies the changes deterministically. `env.emit_intent(kind, **payload)` queues
one; the typed helpers fill in the current agent and position for you:

```python
def forage_step(env):
    a = env.agent
    if a.sense('sugar') > 0:
        env.request_consume_resource('sugar', store_as='energy')   # eat later
    best = a.empty_cells()
    if best:
        env.request_move(target=best[0])                           # move later
    if a.get('energy', 0) <= 0:
        env.request_remove_agent(reason='starved')                 # die later
```

Helpers: `request_move`, `request_remove_agent`, `request_add_agent`,
`request_resource_delta`, `request_consume_resource`. Read the queue with
`env.intents` and drop it with `env.clear_intents()` (the reconciliation node
does this after applying).

---

## 3d) Reproducible randomness — `env.rng`

Stochastic behaviours must draw from `env.rng` (a seeded numpy `Generator`), not
`np.random.*`, or runs won't reproduce:

```python
if env.rng.random() < death_probability:
    env.agent.die()
```

Because the executor builds a fresh `env` per node, `env.rng` resolves to the one
run RNG the executor seeds into the context (falling back to the ABM population's
generator), so every node in a run shares the same stream.

---

## 3e) Observability — recording and plotting

Build a time series without a hand-rolled accumulator, then plot it:

```python
def report_step(env):
    env.record('living_agents', len(env.agents))     # one entry per call
    env.record('total_sugar', env.resource('sugar').total())

def final_plot(env):                                 # finalization stage
    env.plot_records(['living_agents', 'total_sugar'],
                     'population.png', title='Sugarscape', ylabel='count')
    env.plot_field('sugar', 'sugar_field.png')       # heatmap of a resource
```

`env.record(key, value, step=None)` appends `{"step", "value"}` (reads the
current step when omitted); `env.records` is the raw buffer. Plot helpers
(`plot_records`, `plot_timeseries`, `plot_field`) write PNGs to `env.plots_dir`
and return the `Path`. They use a headless matplotlib backend, so they work in a
CLI run.

---

## 4) The fail-loud contract (`KernelContractError`)

Accessing a view whose backing capability is absent raises
`KernelContractError` rather than silently returning empty results (which would
produce wrong science downstream):

- `env.cells` requires `context['population']`
- `env.environment` / `env.concentration(...)` requires `context['simulator']`

If a function depends on these, declare the capability so the runtime can place
it under a kernel that provides it:

```python
@register_function(..., requires=['population'])      # or ['simulator'], etc.
```

The error message names the missing token and the accessor, e.g.
*"env.cells was used but the simulation context provides no 'population'."*

---

## 5) Escape hatches

The typed layer covers the common cases. For anything unusual, drop back to the
raw objects — explicitly:

- `env.raw_context` → the underlying `context` dict
- `env.cells.raw` → the `CellPopulation`
- `cell.raw` → the engine `Cell`
- `agent.cell` → the engine `Cell` behind an ABM `Agent`
- `env.environment.raw_simulator` → the `ISubstanceSimulator`
- `env.gene_network(cell)` → the engine `BooleanNetwork`

Reaching for an escape hatch means you are leaving the typed zone — fine when
needed, but prefer the typed methods so mutations stay discoverable.

---

## 6) Worked examples in the codebase

Copy from real, registered functions:

- `opencellcomms_adapters/common/functions/intercellular/update_cell_division.py`
- `opencellcomms_adapters/common/functions/intracellular/update_metabolism.py`
- `opencellcomms_adapters/common/functions/intercellular/remove_apoptotic_cells.py`
- `opencellcomms_adapters/common/functions/gene_network/*.py`
- Scaffold: `opencellcomms_engine/src/workflow/functions/_TEMPLATE.py`

For the **ABM class layer** (`env.agent`, `env.world`, `env.resource`, intents,
recording), copy from the Sugarscape plugin:

- `opencellcomms_adapters/SUGARSCAPE/functions/` — agent/resource behaviours
- `opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json` — the wired model

---

## See also

- `docs/ABM_LAYER.md` — the `src/abm/` object model (World / Domain / Resource /
  Population / Agent): who owns what and how the pieces fit
- `docs/CREATING_FUNCTIONS.md` — full function-authoring guide
- `docs/context_enforcement.md` — `ValidatedContext` write policies (the rules
  the raw dict obeys underneath `BiologicalContext`)
- `docs/GENE_NETWORK_GUIDE.md` — gene-network architecture
