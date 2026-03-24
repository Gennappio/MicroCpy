# Gene Regulatory Network Update

## Purpose

This document describes how Boolean gene regulatory networks (GRNs) are represented, initialized, and updated in OpenCellComms. Each cell carries its own `BooleanNetwork` instance. Every simulation step, the network receives microenvironmental signals as inputs and propagates state changes through its topology, eventually producing fate outputs (Apoptosis, Proliferation, Growth_Arrest, Necrosis) that drive phenotype assignments.

---

## Network Model Overview

OpenCellComms implements **synchronous and asynchronous Boolean networks** loaded from `.bnd` (Boolean network definition) files. The primary production mode is a **NetLogo-faithful graph-walking update** that replicates the sequential random-node selection used in the reference NetLogo ABM.

### Network Topology

A network is a directed graph of `NetworkNode` objects. Each node has:

| Attribute | Type | Meaning |
|-----------|------|---------|
| `name` | `str` | Unique node identifier |
| `current_state` | `bool` | Value at the current simulation step |
| `next_state` | `bool` | Computed value for the next step |
| `update_function` | `BooleanExpression` | Compiled callable: `f(node_states_dict) → bool` |
| `inputs` | `Set[str]` | Names of nodes this function reads |
| `outputs` | `Set[str]` | Names of nodes downstream (added at init) |
| `is_input` | `bool` | True for externally-driven input nodes |

Input nodes (`is_input = True`) are not updated by the network's own logic. Their state is set by external drivers (substance concentrations, experimental stimuli).

Fate/output nodes (`Apoptosis`, `Proliferation`, `Growth_Arrest`, `Necrosis`) are treated specially: they fire once and immediately reset to `False` (transient trigger semantics matching NetLogo).

### Class Hierarchy

```
BooleanNetwork
└── HierarchicalBooleanNetwork   ← production class
```

`BooleanNetwork` provides core functionality: BND file parsing, three update modes, node state access.

`HierarchicalBooleanNetwork` adds fate counting across propagation steps and stores a priority-ordered fate hierarchy list. It is the class instantiated per cell in MicroCpy.

---

## BND File Format

A `.bnd` file defines the network topology:

```
Node Node1 {
    logic = (A | B) & !C;
    inputs = A, B, C;
    rate_up = ...;
    rate_down = ...;
}
```

`BooleanNetwork` parses this at construction time. The `logic` expression is compiled into a Python callable via `BooleanExpression`. At each update step, for every non-input node:

```python
new_state = node.update_function(current_states_dict)
```

where `current_states_dict` maps all node names to their current boolean values.

---

## Context Storage Pattern

Gene networks live in `context['gene_networks']`, a flat dict keyed by `cell_id`:

```python
context['gene_networks'] = {
    cell_id: HierarchicalBooleanNetwork,
    ...
}
```

Cell state (immutable `CellState`) stores only the flat gene values snapshot used for metabolism, phenotype queries, and persistence:

```python
cell.state.gene_states = {node_name: bool, ...}
```

Helper functions provide safe access:

```python
from biology.gene_network import get_gene_network, set_gene_network, remove_gene_network

gn = get_gene_network(context, cell_id)          # → HierarchicalBooleanNetwork or None
set_gene_network(context, cell_id, gn)
remove_gene_network(context, cell_id)
```

---

## Initialization: `initialize_netlogo_gene_networks`

**File:** `src/workflow/functions/gene_network/initialize_netlogo_gene_networks.py`

This single function replaces the older two-step combination of `initialize_hierarchical_gene_networks` + `set_gene_network_inputs`. It creates fully-ready networks per cell, matching the benchmark NetLogo model's initialization sequence.

### Steps (per cell)

1. **Load network from BND file** — `HierarchicalBooleanNetwork(config, fate_hierarchy)` parses the topology once and creates independent node objects per instance.

2. **Reset node states**
   - Fate nodes (`Apoptosis`, `Proliferation`, `Growth_Arrest`, `Necrosis`) → `False`
   - Other non-input nodes → random `True/False` (if `random_initialization=True`) or `False`
   - Input nodes → left untouched (set next)

3. **Build output links** — The reverse adjacency map (`node.outputs: Set[str]`) is computed from the `inputs` lists of all nodes. This is required for graph walking. The flag `_output_links_built = True` is set to prevent redundant rebuilds.

4. **Initialize per-cell random thresholds** — Two persistent uniform random values:
   - `_cell_ran1 ∈ [0, 1)` — used for MCT1I probabilistic activation
   - `_cell_ran2 ∈ [0, 1)` — used for GLUT1I probabilistic activation

   These are fixed for the lifetime of the cell (frozen identity), so two cells in the same microenvironment respond differently to the same inhibitor concentration.

5. **Initialize graph walking state**
   - `_last_node` → random input node name (graph walking entry point)
   - `_fate = None` (no fate assigned yet)

6. **Apply input states** — Deterministic ON/OFF for standard inputs (Oxygen_supply, Glucose_supply, etc.). Probabilistic Hill activation for MCT1I and GLUT1I:
   ```
   probability = 0.85 × (1 − 1 / (1 + (concentration / 1.0)^1.0))
   active = (probability > cell_random_value)
   ```

7. **Store in context** — `context['gene_networks'][cell_id] = cell_gn`

8. **Sync cell state** — `cell.state = cell.state.with_updates(gene_states=initial_gene_states)`

A reference network (`context['reference_gene_network']`) is also created for inspection without modifying any cell's network.

### Parameters (GUI-configurable)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bnd_file` | `STRING` | `"gene_network.bnd"` | Path to the BND topology file |
| `random_initialization` | `BOOL` | `True` | Random vs. all-False initial states |
| `input_states` | `DICT` | See function | Boolean on/off for each input node |
| `concentrations` | `DICT` | `{MCT1I: 0.0, GLUT1I: 0.0}` | Inhibitor concentrations for Hill activation |

---

## Three Update Modes

`BooleanNetwork` supports three update semantics, selected via the `update_mode` argument to `step()`:

### 1. Synchronous

All non-input nodes evaluate their update function simultaneously using the current states, then all flip at once:

```python
for node in non_input_nodes:
    node.next_state = node.update_function(current_states)
for node in non_input_nodes:
    node.current_state = node.next_state
```

This is deterministic and order-independent. It is biologically equivalent to assuming all reactions happen at the same timescale.

### 2. NetLogo (default single-gene random)

One randomly chosen non-input node is updated per step. This replicates the default `go` tick in the NetLogo reference model:

```python
node = random.choice(non_input_nodes)
node.current_state = node.update_function(current_states)
```

This is stochastic and slow to converge but matches the statistical behavior of the original NetLogo model when run for many steps.

### 3. Asynchronous

All non-input nodes are updated in a random order, each reading the most recent states of previously-updated nodes:

```python
shuffled = random.sample(non_input_nodes, len(non_input_nodes))
for node in shuffled:
    node.current_state = node.update_function(current_states_live)
    current_states_live[node.name] = node.current_state
```

This is stochastic but converges faster than the single-gene mode.

---

## NetLogo-Faithful Graph Walking: `propagate_gene_networks_netlogo`

**File:** `src/workflow/functions/gene_network/propagate_gene_networks_netlogo.py`

This is the production propagation function used in v7 workflows. It replicates the `-DOWNSTREAM-CHANGE-590` procedure from the reference NetLogo model at the level of individual cells across a full macrostep.

### Outer Loop Structure

```
for each propagation step (default 500):
    refresh input nodes from context['gene_network_inputs']  (optional)
    for each cell in population:
        _netlogo_downstream_change(cell_gn)
```

The step-outer / cell-inner loop matches NetLogo's `ask turtles [ -DOWNSTREAM-CHANGE-590 ]` called from the outer `repeat` loop. This ensures every cell runs exactly once per propagation step, in a consistent order.

### `_netlogo_downstream_change(gn)` — Core Algorithm

This function replicates the graph walking at the level of a single cell's network:

```
1. evaluate = _netlogo_influence_link_end(gn._last_node, gn)
   → find the "most-changed" downstream neighbor of last_node

2. if evaluate is None:
       gn._last_node = random input node
       return

3. new_val = update_function(evaluate, current_states)

4. if new_val != gn.nodes[evaluate].current_state:
       gn.nodes[evaluate].current_state = new_val
       if evaluate is a fate node:
           gn._fate = evaluate
           gn.nodes[evaluate].current_state = False  ← transient: reset immediately

5. gn._last_node = evaluate
```

Key properties:
- **Graph walking**: traversal continues from `_last_node`, not from a fresh random start each step. This creates memory: the walk tends to stay in the region of the graph where change is occurring.
- **Fate node reversion**: when a fate node fires, it is immediately reset to `False`. This is transient-trigger semantics: the fate is recorded in `_fate`, not persisted in the node state.
- **No synchrony**: only one node changes per cell per step.

### `_netlogo_influence_link_end(from_node, gn)` — Neighbor Selection

Given a source node, selects which downstream neighbor to evaluate next:

```
candidates = gn.nodes[from_node].outputs   (set of downstream node names)

if no candidates:
    return None

for each candidate:
    proposed_val = update_function(candidate, current_states)
    priority = abs(proposed_val - current_state)  # 1 if would change, 0 if not

pick the candidate with highest priority
(tie-break: random, matching NetLogo's `max-one-of ... with-max [...]`)
```

The walk strongly prefers nodes that would change state — a self-organizing focus on the active frontier of the network.

### Input Refresh

At the start of each propagation step, if `context['gene_network_inputs']` is set, those boolean values are written into every cell's network input nodes:

```python
for cell_id, gn in gene_networks.items():
    for node_name, state in input_states.items():
        if node_name in gn.nodes:
            gn.nodes[node_name].current_state = state
```

This allows the microenvironment-to-gene bridge (associations) to update inputs before propagation without being tightly coupled to the propagation function itself.

### After Propagation: State Sync

After all propagation steps, the final node states are written back to `cell.state.gene_states`:

```python
cell.state = cell.state.with_updates(
    gene_states={name: node.current_state for name, node in gn.nodes.items()}
)
```

This snapshot is used by downstream functions (metabolism, phenotype marking) which read from `cell.state` rather than `context['gene_networks']`.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `propagation_steps` | `500` | Number of graph walking steps per macrostep |
| `refresh_inputs_each_step` | `False` | Re-apply `context['gene_network_inputs']` every step |
| `update_gene_states` | `True` | Write final states back to `cell.state.gene_states` |

---

## Input Bridge: `apply_associations_to_inputs`

**File:** `src/workflow/functions/gene_network/apply_associations_to_inputs.py`

This function translates microenvironmental substance concentrations into boolean gene input states. It runs in the macrostep loop, **before** `propagate_gene_networks_netlogo`, bridging the diffusion layer and the intracellular layer.

### Spatial Mode (with simulator)

When a substance simulator is present, each cell gets its own input states based on the concentration at its grid position:

```
for each cell:
    grid_pos = physical_to_grid(cell.position)
    for each (substance → gene_input) in associations:
        local_conc = substance_concentrations[substance][grid_pos]
        threshold  = thresholds[gene_input]
        gene_input_state = (local_conc > threshold)
    write to context['gene_networks'][cell_id].nodes[gene_input].current_state
```

This creates spatially heterogeneous gene input states: cells in hypoxic regions get `Oxygen_supply = False` while oxygenated cells get `True`.

Position conversion uses the same grid mapping as the diffusion solver:

```python
phys_x = cell_x * cell_size_um           # cell grid units → micrometers
grid_x = int(phys_x / grid_spacing_x)    # micrometers → diffusion grid index
```

### Fallback Mode (no simulator)

Without a simulator, a flat concentration value from `context['substances']` is applied uniformly to all cells. This is used in standalone gene network tests or simple (non-spatial) workflows.

### Associations Configuration

Associations are loaded from `context['associations']` or `config.associations`. Example:

```python
associations = {
    'Oxygen':  'Oxygen_supply',
    'Glucose': 'Glucose_supply',
    'Lactate': 'Proton_level',
}
thresholds = {
    'Oxygen_supply':  0.05,   # mM
    'Glucose_supply': 0.1,    # mM
    'Proton_level':   5.0,    # mM
}
```

### Backward Compatibility

The function writes to both storage patterns:
- **New pattern**: `context['gene_networks'][cell_id].nodes[name].current_state`
- **Old pattern**: `cell.state.gene_network.nodes[name].current_state` (if `cell.state.gene_network` exists)

---

## Full Data Flow (per Macrostep)

```
Diffusion layer (run_diffusion_solver)
    │
    │  substance_concentrations[substance][grid_pos]
    ▼
apply_associations_to_inputs
    │  compares local concentrations to thresholds
    │  writes boolean states to gene_networks[cell_id].nodes[input_name].current_state
    ▼
propagate_gene_networks_netlogo
    │  500 × graph-walking steps per cell
    │  fate nodes fire (transient) → gn._fate set
    │  final states written to cell.state.gene_states
    ▼
mark_necrotic / mark_apoptotic / mark_growth_arrest / mark_proliferating
    │  read cell.state.gene_states['Necrosis'], etc.
    │  set cell.state.phenotype
    ▼
cell_division / remove_apoptotic
    │  act on phenotype
    ▼
(next macrostep)
```

---

## Daughter Cell Inheritance

When a cell divides, the daughter cell must receive an initialized gene network. The initialization parameters are stored in `context['gene_network_init_params']` (set by `initialize_netlogo_gene_networks`) so the division function can call the same initialization logic with the same BND file and input states.

Each daughter cell gets:
- A fresh `HierarchicalBooleanNetwork` from the same BND file
- Its own `_cell_ran1`, `_cell_ran2` (new random values — each daughter is a new individual)
- Its own `_last_node` and `_fate = None`
- The same initial input states as the parent

---

## Update Mode Comparison

| Mode | Nodes updated per step | Stochastic | Convergence | Use case |
|------|------------------------|------------|-------------|----------|
| `synchronous` | All | No | Fastest | Deterministic runs, testing |
| `netlogo` (graph walking) | 1 (graph-directed) | Yes | Slow | NetLogo replication, production |
| `asynchronous` | All (random order) | Yes | Moderate | Alternative stochastic mode |

The graph-walking mode is slower per step than synchronous but produces statistically faithful behavior matching the reference NetLogo model because it replicates the exact sequential random node selection and the directed walk along the active frontier of the network.

---

## Key Files

| File | Role |
|------|------|
| `src/biology/gene_network.py` | `BooleanNetwork`, `HierarchicalBooleanNetwork`, `NetworkNode`, `BooleanExpression` |
| `src/workflow/functions/gene_network/initialize_netlogo_gene_networks.py` | Per-cell network creation, probabilistic input activation, output link building |
| `src/workflow/functions/gene_network/propagate_gene_networks_netlogo.py` | Graph walking propagation matching NetLogo `-DOWNSTREAM-CHANGE-590` |
| `src/workflow/functions/gene_network/apply_associations_to_inputs.py` | Microenvironment → gene input bridge (spatial and flat modes) |
| `src/workflow/functions/gene_network/initialize_gene_networks.py` | Older non-NetLogo initializer (kept for compatibility) |
| `src/workflow/functions/gene_network/propagate_gene_networks.py` | Older synchronous propagator (kept for compatibility) |

---

## Reference: NetLogo Correspondence

| NetLogo construct | MicroCpy equivalent |
|-------------------|---------------------|
| `my-last-node` | `gn._last_node` |
| `my-fate` | `gn._fate` |
| `my-cell-ran1` | `gn._cell_ran1` |
| `my-cell-ran2` | `gn._cell_ran2` |
| `-DOWNSTREAM-CHANGE-590` | `_netlogo_downstream_change(gn)` |
| `influence-link-end` | `_netlogo_influence_link_end(from_node, gn)` |
| `ask turtles [ repeat 500 [...] ]` | `for step in range(propagation_steps): for cell_id, gn in ...` |
| Fate node firing + reversion | `gn._fate = evaluate; gn.nodes[evaluate].current_state = False` |
| Hill function for MCT1I/GLUT1I | `0.85 * (1 - 1/(1 + (conc/threshold)))` |
