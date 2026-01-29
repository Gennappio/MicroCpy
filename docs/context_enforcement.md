# Context Enforcement in OpenCellComms (ValidatedContext)

This document explains **context enforcement** in OpenCellComms: why it exists, how it works, and how to use it effectively when authoring workflow functions and workflows.

It is written to be **discursive and practical**: motivations, opportunities, and concrete use cases are included, alongside code snippets from the codebase.

---

## 1) What “context” is (and why it matters)

In OpenCellComms, a simulation run is a workflow: a sequence of nodes (functions) executed in a specific order. The workflow runtime passes a single mutable **`context` dictionary** through this entire execution. Nodes use it to share the objects and state that make the simulation coherent:

- the population and its cells
- the diffusion simulator and substance fields
- configuration and timing values (`dt`, step counters)
- output directories (plots/data/results)
- intermediate results used by downstream nodes

This shared context is powerful because it makes workflows **composable**: a node can produce something (or mutate something) and downstream nodes can consume it.

But this also creates a classic risk:

> In a shared mutable dictionary, one wrong assignment can silently break the entire run.

That is the core motivation for context enforcement.

---

## 2) The problem context enforcement solves

Without enforcement, any node can do:

```python
context["population"] = something_else
```

Even if that assignment is accidental (wrong key, wrong object, wrong time), downstream nodes will now operate on incorrect objects. These failures often manifest as:

- hard-to-debug errors later (“attribute error” in a different node),
- silently wrong results (the most dangerous case),
- inconsistent behavior between runs if node ordering changes.

In a workflow system, this risk increases because:

- many small nodes touch shared state,
- node authors can be different people,
- LLM-assisted coding can introduce key-name mistakes or “helpful” overwrites,
- experimental workflows frequently re-order, duplicate, or disable nodes.

So OpenCellComms enforces a key principle:

> Core simulation bindings in `context` should be **stable**, while the objects they reference can remain **mutable**.

In other words: **mutate the population**, don’t replace the population binding.

---

## 3) The solution: `ValidatedContext` (write policies)

The enforcement mechanism is implemented in:

- `opencellcomms_engine/src/workflow/observability/validated_context.py`

It defines `ValidatedContext`, which extends `TrackedContext` and adds **write policies** for keys.

### 3.1 Policy model: “read_only”, “write_once”, “mutable”

From the code:

```1:15:/Users/gennaroabbruzzese/Documents/BIDSA/MicroCpy3D/MicroCpy/opencellcomms_engine/src/workflow/observability/validated_context.py
Write Policies:
- read_only: Cannot be written after initialization (e.g., dt, step, time)
- write_once: Can be written once, then becomes read-only (e.g., population, simulator)
- mutable: Can be freely overwritten (e.g., user custom keys, results)
```

And the default core keys (protected by policy) include:

```29:50:/Users/gennaroabbruzzese/Documents/BIDSA/MicroCpy3D/MicroCpy/opencellcomms_engine/src/workflow/observability/validated_context.py
DEFAULT_CORE_KEYS: Dict[str, str] = {
    'step': WRITE_POLICY_WRITE_ONCE,
    'dt': WRITE_POLICY_WRITE_ONCE,
    'time': WRITE_POLICY_WRITE_ONCE,
    'current_step': WRITE_POLICY_WRITE_ONCE,
    'population': WRITE_POLICY_WRITE_ONCE,
    'simulator': WRITE_POLICY_WRITE_ONCE,
    'gene_network': WRITE_POLICY_WRITE_ONCE,
    'config': WRITE_POLICY_WRITE_ONCE,
    'mesh_manager': WRITE_POLICY_WRITE_ONCE,
    'helpers': WRITE_POLICY_WRITE_ONCE,

    'substance_concentrations': WRITE_POLICY_MUTABLE,
    'results': WRITE_POLICY_MUTABLE,
    'substances': WRITE_POLICY_MUTABLE,
    'simulation_params': WRITE_POLICY_MUTABLE,
}
```

Interpretation:

- **Write-once keys** protect the binding for core objects and core time values.
- **Mutable keys** are intended for evolving state or results containers.
- **User keys** default to mutable unless registered otherwise.

### 3.2 Locking: enforcement is activated after initialization

`ValidatedContext` has an internal “locked” state:

- before locking, writes are allowed (initialization needs to populate core keys)
- after locking, policies apply (core keys cannot be overwritten/deleted per policy)

```105:115:/Users/gennaroabbruzzese/Documents/BIDSA/MicroCpy3D/MicroCpy/opencellcomms_engine/src/workflow/observability/validated_context.py
def lock_core_keys(self) -> None:
    self._locked = True
    self._initialized_keys = set(self.keys())
```

This is crucial conceptually:

> A simulation run needs a phase where core keys are established, and then a phase where core bindings become stable.

---

## 4) Enforcement levels: strict vs warn vs off

`ValidatedContext` supports three enforcement levels:

- **`strict`**: raise `ContextWriteError` on violations
- **`warn`**: emit a warning but allow the write
- **`off`**: allow all writes

This behavior is implemented in `_validate_write()` (and similarly for delete):

```160:176:/Users/gennaroabbruzzese/Documents/BIDSA/MicroCpy3D/MicroCpy/opencellcomms_engine/src/workflow/observability/validated_context.py
if policy == WRITE_POLICY_READ_ONLY:
    msg = f"Cannot write to read-only context key: '{key}'"
    if self._enforcement == "strict":
        raise ContextWriteError(msg)
    elif self._enforcement == "warn":
        warnings.warn(msg, stacklevel=3)
    return self._enforcement != "strict"

if policy == WRITE_POLICY_WRITE_ONCE:
    if key in self._initialized_keys:
        msg = f"Cannot overwrite write-once context key: '{key}'. The object is mutable, but the key binding is protected."
        if self._enforcement == "strict":
            raise ContextWriteError(msg)
        elif self._enforcement == "warn":
            warnings.warn(msg, stacklevel=3)
        return self._enforcement != "strict"
```

### Practical advice

- Use **`warn`** during rapid exploratory development (you learn what you’re overwriting without stopping runs).
- Use **`strict`** when you want correctness guarantees and fast failure (CI, benchmarks, “publication mode”).
- Use **`off`** only when you are intentionally doing non-standard manipulations of context bindings.

---

## 5) How enforcement is applied during execution

The enforcement wrapper is applied inside the workflow executor when a node runs. In `_execute_function_with_observability()`:

```670:679:/Users/gennaroabbruzzese/Documents/BIDSA/MicroCpy3D/MicroCpy/opencellcomms_engine/src/workflow/executor.py
if self._observability_enabled and OBSERVABILITY_AVAILABLE:
    # Use ValidatedContext for write policy enforcement
    tracked_context = ValidatedContext(context, enforcement=self._context_enforcement)
    # Lock core keys to prevent overwriting (but allow modification of objects)
    tracked_context.lock_core_keys()
    tracked_context.start_tracking()
else:
    tracked_context = context
```

Key points:

- Each node execution uses a **validated, tracked wrapper** around the shared context.
- Core keys are locked before node execution (so “write-once” protection applies).
- The wrapper also starts tracking reads/writes for observability.

### Important nuance (current behavior)

Right now, the enforcement wrapper is **gated by observability**:

- if observability is disabled or unavailable, the executor passes the raw dict without `ValidatedContext`.

This creates an opportunity for future improvement (see section 9):

> Context enforcement could be valuable even when full observability is disabled.

---

## 6) How to write workflow functions that “play well” with enforcement

### 6.1 The key rule: mutate objects, don’t rebind core keys

This is the intent expressed directly in the ValidatedContext docstring:

```4:8:/Users/gennaroabbruzzese/Documents/BIDSA/MicroCpy3D/MicroCpy/opencellcomms_engine/src/workflow/observability/validated_context.py
Core keys (population, simulator, config, etc.) cannot be overwritten once set,
but the objects they reference remain mutable (you can modify population.cells,
but cannot do context['population'] = new_population).
```

Correct patterns:

- read population: `pop = context["population"]`
- mutate population: `pop.state.cells[cell_id] = ...` or `pop.remove_dead_cells()`
- read simulator: `sim = context["simulator"]`
- update solver state through the simulator’s API (not by replacing `context["simulator"]`)

Risky pattern (violates write-once):

- `context["population"] = make_new_population()`

### 6.2 Use mutable keys for evolving data products

If you want to store intermediate results, use keys that are intended to evolve:

- `context["results"]` (default mutable)
- `context["substance_concentrations"]` (default mutable)
- a new key you create, e.g. `context["user:my_metric"] = ...`

Best practice:

- Use a key naming convention so keys remain discoverable:
  - `user:*` for user-defined outputs
  - `node:*` for node-local intermediate values
  - `sim:*` for simulation-wide computed values

### 6.3 Avoid surprising downstream nodes

Context enforcement prevents “hard breaks” (rebinding core keys), but you can still break a simulation by mutating objects in unexpected ways.

Good practice:

- document what your node reads and writes
- keep mutations narrow and explicit
- prefer adding data to `context["results"]` or `context["user:*"]` rather than modifying unrelated core structures

---

## 7) Use cases (why this is useful in real workflows)

### Use case A — Preventing accidental breaks during rapid iteration

When iterating on a node (especially with LLM assistance), it’s common to:

- mistype a key name, or
- “simplify” by replacing an object instead of mutating it.

With enforcement on `warn`, you get immediate feedback that you are overwriting a protected binding without losing the run.

With `strict`, you get fast failure at the first violation—useful for correctness and tests.

### Use case B — Safer node composition across teams

Workflow systems invite modularity: different team members contribute nodes. Context enforcement provides a baseline safety contract:

- “You may not replace the core objects other nodes rely on.”

This reduces integration risk and makes collaborative development more robust.

### Use case C — Subworkflow reuse and re-ordering

As workflows get complex, you will:

- reuse subworkflows,
- call them multiple times,
- change order for hypothesis testing.

In these scenarios, stable core bindings are critical. Enforcement turns some classes of “reorder-related breakage” into early warnings/errors instead of silent incorrect runs.

### Use case D — Reproducible debugging via observability + enforcement

Because the same wrapper (`ValidatedContext`) is also a `TrackedContext`, you can pair:

- “what was read/written” tracking,
- context snapshots/diffs,
- and enforcement warnings/errors,

to get a high-quality debugging story:

- “This node tried to overwrite `population`”
- “It wrote these keys”
- “The diff shows it changed X and Y”

---

## 8) Opportunities (what this enables beyond “preventing mistakes”)

Context enforcement is more than a guardrail; it is an enabling infrastructure piece.

### Opportunity 1 — Formalizing the context contract

Over time, the project can evolve from:

- “some keys are protected”

to:

- “each node declares which keys it reads and writes; the runtime validates it.”

Because reads/writes are already tracked, you have the telemetry needed to build this.

### Opportunity 2 — Workflow linting and static validation

With a known set of core keys and policies, you can build a workflow linter that flags:

- nodes that likely violate expected contracts,
- suspicious overwrites of keys (even if allowed),
- missing initialization steps for required keys.

This would raise the quality of workflows before they run.

### Opportunity 3 — Safer LLM-driven code generation

LLMs are prone to “overwriting to make it work.” Context enforcement gives the system a way to:

- reject unsafe patterns (strict),
- or at least surface them (warn),

which is particularly valuable when using AI to generate or refactor node functions.

### Opportunity 4 — Better performance control (selective enforcement)

In very large runs, overhead matters. The enforcement framework could evolve to:

- enforce only on selected keys,
- enforce only in certain subworkflows,
- enforce only during development runs.

Because the enforcement is a wrapper, it is easy to scope.

### Opportunity 5 — Decouple enforcement from observability

Currently, enforcement is only applied in the branch that enables observability wrappers. A future improvement could be:

- apply `ValidatedContext` even when event emission/snapshotting is off,
so you can keep safety while reducing observability overhead.

---

## 9) Practical “how to use” guidance (recommended defaults)

### 9.1 Recommended modes by phase

- **Local exploratory workflow authoring**: `warn`
  - preserve productivity while surfacing contract violations
- **Team shared workflows / integration**: `strict`
  - fail fast; keep core bindings stable
- **Special experiments (rare)**: `off`
  - only if you truly need to replace core objects intentionally

### 9.2 Where to configure it today

In the current code, `WorkflowExecutor` accepts:

- `context_enforcement: str = "warn"`

and uses it when wrapping context for node execution.

The executor is constructed in `SimulationEngine` as:

```43:51:/Users/gennaroabbruzzese/Documents/BIDSA/MicroCpy3D/MicroCpy/opencellcomms_engine/src/simulation/engine.py
from ..workflow.executor import WorkflowExecutor
self.workflow_executor = WorkflowExecutor(workflow, custom_functions, config)
```

At the moment, this call uses the default enforcement of `"warn"`. If you want strict behavior globally, the integration point is to pass `context_enforcement="strict"` when creating the executor.

---

## 10) Mini examples (what violations look like)

### Example: accidentally rebinding `population`

```python
def bad_node(context, **kwargs):
    # This violates the write-once rule for 'population' after locking:
    context["population"] = {"oops": "not a Population"}
```

Expected outcomes:

- enforcement `warn`: a warning is emitted (run continues, but you are alerted)
- enforcement `strict`: `ContextWriteError` is raised immediately
- enforcement `off`: no warning/error (downstream nodes may fail or silently misbehave)

### Example: correct mutation pattern

```python
def good_node(context, **kwargs):
    pop = context["population"]          # read core binding
    # mutate the object (allowed)
    pop.remove_dead_cells()
```

---

## 11) Summary (the mental model)

Context enforcement implements a clean, workflow-friendly rule:

- **Core bindings are stable** after initialization (protect the “wiring” of the simulation).
- **Core objects are mutable** (the simulation can still evolve).
- **User keys are flexible** (you can record and share new data products freely).

This improves:

- correctness,
- debuggability,
- team collaboration,
- and confidence when workflows become large and modular.

