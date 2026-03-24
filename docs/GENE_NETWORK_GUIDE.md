# Gene Network Architecture Guide

## Overview

Gene networks are stored in `context['gene_networks']` as a dictionary mapping `cell_id → BooleanNetwork`. This context-driven architecture allows gene network operations to be fully controlled by workflow functions and configured from the GUI.

**Key Point**: Gene networks are NOT stored in `cell.state`. The `CellState` dataclass is kept clean and immutable, containing only `gene_states` (Dict[str, bool]) with the current values of each gene.

## Data Structure

### Context Storage

```python
# Gene networks stored in workflow context
context['gene_networks'] = {
    'cell_abc123': BooleanNetwork(...),  # Cell 1's gene network
    'cell_def456': BooleanNetwork(...),  # Cell 2's gene network
    ...
}
```

### CellState (in `src/biology/cell.py`)

```python
@dataclass
class CellState:
    id: str
    position: Tuple
    phenotype: str
    age: float
    division_count: int
    metabolic_state: Dict[str, float]
    gene_states: Dict[str, bool]  # ← Current gene states (values only)
    tq_wait_time: float = 0.0
    # NOTE: gene_network is NOT here - it's in context['gene_networks']
```

### BooleanNetwork (in `src/biology/gene_network.py`)

```python
class BooleanNetwork:
    nodes: Dict[str, NetworkNode]      # All genes in the network
    input_nodes: Set[str]              # Input genes (externally controlled)
    output_nodes: Set[str]             # Output genes (fate: Proliferation, Apoptosis, etc.)
    fixed_nodes: Dict[str, bool]       # Genes fixed to specific values
```

### NetworkNode

```python
@dataclass
class NetworkNode:
    name: str                          # Gene name (e.g., "Oxygen_supply")
    current_state: bool = False        # Current value (True/False)
    next_state: bool = False           # Next value (for synchronous updates)
    update_function: Callable = None   # Boolean logic rule
    inputs: List[str] = []             # Genes this node depends on
    is_input: bool = False             # Is this an input node?
    is_output: bool = False            # Is this an output node?
```

## Helper Functions

The following helper functions are available in `src/workflow/functions/gene_network/get_gene_network_states.py`:

### `get_gene_network(context, cell_id)`

```python
from src.workflow.functions.gene_network.get_gene_network_states import get_gene_network

# Get a cell's gene network from context
cell_gn = get_gene_network(context, cell_id)
```

### `set_gene_network(context, cell_id, gene_network)`

```python
from src.workflow.functions.gene_network.get_gene_network_states import set_gene_network

# Store a gene network in context
set_gene_network(context, cell_id, new_gene_network)
```

### `remove_gene_network(context, cell_id)`

```python
from src.workflow.functions.gene_network.get_gene_network_states import remove_gene_network

# Remove gene network when cell dies
remove_gene_network(context, cell_id)
```

## BooleanNetwork Methods

### 1. `set_input_states(inputs: Dict[str, bool])`

Sets the values of input nodes (which stay FIXED during propagation):

```python
# Get gene network from context first
cell_gn = context['gene_networks'].get(cell_id)
cell_gn.set_input_states({
    'Oxygen_supply': True,
    'Glucose_supply': True,
    'FGFR_stimulus': False
})
```

**Effect**: Updates `node.current_state` for each input node.

### 2. `step(num_steps: int, mode: str) -> Dict[str, bool]`

Propagates the network for N steps. Available modes:
- `"netlogo"`: Random single gene per step (NetLogo-style, default)
- `"synchronous"`: All genes update together each step
- `"asynchronous"`: All genes update in random order each step

```python
cell_gn = context['gene_networks'].get(cell_id)
gene_states = cell_gn.step(500, mode="synchronous")
# Returns: {'Oxygen_supply': True, 'Glucose_supply': True, 'mitoATP': True, ...}
```

**Effect**: Updates all non-input nodes based on their logic rules.

### 3. `get_all_states() -> Dict[str, bool]`

Returns current state of ALL nodes:

```python
cell_gn = context['gene_networks'].get(cell_id)
all_states = cell_gn.get_all_states()
```

### 4. `reset(random_init: bool = False)`

Resets the network:
- Fate nodes (Proliferation, Apoptosis, etc.) → False
- Input nodes → unchanged
- Other nodes → random (if `random_init=True`)

## Typical Workflow

### Step 1: Initialize Gene Networks

```python
# In initialize_gene_networks() workflow function
# Gene networks are stored in context, NOT in cell.state
context['gene_networks'] = {}

for cell_id, cell in cells.items():
    cell_gn = BooleanNetwork(config=config)
    cell_gn.reset(random_init=True)

    # Store in context (NOT cell.state)
    context['gene_networks'][cell_id] = cell_gn

    # Update cell's gene_states dict only
    initial_gene_states = cell_gn.get_all_states()
    cell.state = cell.state.with_updates(gene_states=initial_gene_states)
```

### Step 2: Set Input States

```python
# In set_gene_network_inputs() workflow function
fixed_substances = {
    'Oxygen_supply': True,
    'Glucose_supply': True,
    'FGFR_stimulus': False
}

gene_networks = context.get('gene_networks', {})
for cell_id, cell_gn in gene_networks.items():
    cell_gn.set_input_states(fixed_substances)
```

### Step 3: Propagate Network

```python
# In update_gene_networks() or propagate_gene_networks() workflow function
gene_networks = context.get('gene_networks', {})

for cell_id, cell in cells.items():
    cell_gn = gene_networks.get(cell_id)
    if cell_gn:
        gene_states = cell_gn.step(500, mode="synchronous")
        cell.state = cell.state.with_updates(gene_states=gene_states)
```

## Important Concepts

### Input Nodes (FIXED)
- Set via `set_input_states()`
- **Never updated** during propagation
- Examples: `Oxygen_supply`, `Glucose_supply`, `FGFR_stimulus`

### Output Nodes (FATE)
- Determined by network logic
- Examples: `Proliferation`, `Apoptosis`, `Growth_Arrest`, `Necrosis`

### Context-Based Storage Pattern
```python
# ✅ Correct: Store gene network in context
context['gene_networks'][cell_id] = new_gn

# ✅ Correct: Access gene network from context
cell_gn = context['gene_networks'].get(cell_id)

# ❌ Wrong: Do not store in cell.state
cell.state.gene_network = new_gn  # This field no longer exists!
```

### Each Cell Has Its Own Copy
```python
# Each cell gets a FRESH copy stored in context
context['gene_networks'] = {}
for cell_id in cells.keys():
    context['gene_networks'][cell_id] = BooleanNetwork(config=config)
# Each cell's gene network is INDEPENDENT
```

### Removing Gene Networks (Cell Death)
```python
# When a cell dies, remove its gene network from context
from src.workflow.functions.gene_network.get_gene_network_states import remove_gene_network
remove_gene_network(context, dead_cell_id)
```

## Example: Complete Workflow

```python
# 1. Create cell and context
cell = Cell(position=(50, 75), phenotype="Growth_Arrest")
cell_id = cell.state.id
context = {'gene_networks': {}}

# 2. Create gene network and store in context
cell_gn = BooleanNetwork(config=config)
cell_gn.reset(random_init=True)
context['gene_networks'][cell_id] = cell_gn

# 3. Set input states (FIXED during propagation)
context['gene_networks'][cell_id].set_input_states({
    'Oxygen_supply': True,
    'Glucose_supply': True
})

# 4. Propagate for 500 steps
gene_states = context['gene_networks'][cell_id].step(500, mode="synchronous")

# 5. Update cell state with gene states (values only)
cell.state = cell.state.with_updates(gene_states=gene_states)

# 6. Check fate
fate = gene_states.get('Proliferation', False)
print(f"Cell will proliferate: {fate}")
```

## Available Workflow Functions

### Initialize Gene Networks
- **Function**: `initialize_gene_networks()`
- **Purpose**: Load BND file and create gene networks for all cells
- **Stores**: `context['gene_networks']` dict

### Set Gene Network Inputs
- **Function**: `set_gene_network_inputs()`
- **Purpose**: Set fixed input node values for all cells

### Propagate Gene Networks
- **Function**: `propagate_gene_networks()`
- **Purpose**: Propagate gene networks for specified number of steps
- **Parameters**: `propagation_steps`, `update_mode` (netlogo/synchronous/asynchronous)

### Get Gene Network States
- **Function**: `get_gene_network_states()`
- **Purpose**: Retrieve current gene states from all cells
- **Returns**: Dict mapping cell_id → gene_states
