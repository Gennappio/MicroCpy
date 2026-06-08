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

| Member | Returns | Notes |
|---|---|---|
| `env.cells` | `PopulationView` | iterate / query / add cells |
| `env.environment` | `EnvironmentView` | substance concentration queries |
| `env.results` | `ResultsView` | typed results / change sink |
| `env.concentration(substance, at)` | `float` | shortcut for `env.environment.concentration(...)` |
| `env.concentrations_at(at)` | `Dict[str, float]` | all substances at a cell/position |
| `env.step` | `int` | reads `clock.step`, else `current_step`/`step` |
| `env.dt` | `float` | reads `clock.dt`, else `dt` (default `1.0`) |
| `env.config` | config object | `context['config']` |
| `env.verbose` | `bool` | `context['verbose']` |
| `env.gene_network(cell)` | `BooleanNetwork \| None` | underlying network for direct access (`.step()`, graph walking) |
| `env.set_gene_network(cell, net)` | — | bind a network for a cell id |
| `env.remove_gene_network(cell)` | — | unbind |
| `env.raw_context` | `Dict[str, Any]` | **escape hatch** — the underlying dict |

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

---

## See also

- `docs/CREATING_FUNCTIONS.md` — full function-authoring guide
- `docs/context_enforcement.md` — `ValidatedContext` write policies (the rules
  the raw dict obeys underneath `BiologicalContext`)
- `docs/GENE_NETWORK_GUIDE.md` — gene-network architecture
