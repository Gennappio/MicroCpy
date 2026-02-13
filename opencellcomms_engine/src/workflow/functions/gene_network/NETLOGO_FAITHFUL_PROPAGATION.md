# NetLogo-Faithful Gene Network Propagation

## Overview

The `propagate_gene_networks_netlogo.py` function now implements the **EXACT** propagation algorithm from the NetLogo model (`microC_Metabolic_Symbiosis.nlogo3d`), as faithfully replicated in the benchmark script `gene_network_netlogo_probability.py`.

## Key Features

### 1. Graph Walking Algorithm

The propagation follows NetLogo's graph walking approach (not synchronous or asynchronous):

1. **Start**: Begin at `last_node` (initially a random input node)
2. **Select**: Pick ONE random outgoing link from current node
3. **Evaluate**: Compute target node's Boolean rule
4. **Update**: Change target node's state if rule requires it
5. **Route**: Move to next node based on target type:
   - **Fate node (Output-Fate)**: Set cell fate, reset node to OFF, jump to random input
   - **Gene/Input node**: Continue walking from that node

### 2. NetLogo-Faithful Behaviors

#### Fate Node Transience
- Fate nodes ALWAYS reset to `false` after being evaluated
- They act as transient triggers, not permanent states
- NetLogo code: line 1568

#### Fate Reversion
- If a fate node turns OFF and it was the current fate → fate resets to `nobody` (None)
- This allows cells to "escape" from transient fate decisions
- NetLogo code: lines 1563-1564

#### Fate Overwriting
- Last fate to fire wins (not hierarchical)
- No priority ordering between fates
- Current fate can be overwritten at any step

#### Stopping Conditions
- **Reversible mode** (default): Keep updating while `fate != "Necrosis"`
- **Non-reversible mode**: Stop at first fate assignment
- NetLogo code: line 1611

### 3. Probabilistic Input Activation

Two input nodes (GLUT1I and MCT1I) use **stochastic activation** instead of deterministic thresholds:

**Standard input**: `active = (concentration >= threshold)`

**Probabilistic input** (GLUT1I, MCT1I):
```python
# Hill function
probability = 0.85 * (1 - 1 / (1 + (concentration / threshold)^1.0))

# Stochastic activation
active = (probability > cell_random_value)
```

**Cell-specific random values**:
- Each cell gets two persistent random values (0-1) at initialization:
  - `_cell_ran1`: used for MCT1I
  - `_cell_ran2`: used for GLUT1I
- These values persist across all propagation steps for that cell
- This creates **cell-to-cell variability** in response to the same input conditions

**NetLogo implementation**: lines 1014-1020 (initialization), 1298-1321 (activation)

## Implementation Details

### Main Function: `propagate_gene_networks_netlogo()`

**Parameters**:
- `propagation_steps`: Number of graph-walk steps per cell (default: 500)
- `reversible`: True = keep updating until Necrosis, False = stop at first fate (default: True)
- `verbose`: Enable detailed logging (default: False)
- `debug_steps`: Print step-by-step propagation details (default: False)

**Returns**: `True` if successful, `False` otherwise

**Key Steps**:
1. Build output links for graph connectivity (once per cell)
2. Initialize cell-specific random values (`_cell_ran1`, `_cell_ran2`)
3. Initialize graph walking state (`_last_node`, `_fate`)
4. Execute graph walking loop with stopping condition
5. Update cell state with final gene states and phenotype

### Helper Functions

#### `_build_output_links(gene_network)`
Constructs the dependency graph by examining input dependencies. For each node, identifies which other nodes depend on it (outputs).

#### `_get_random_start_node(gene_network)`
Selects a random input node to start/restart graph walking. Replicates NetLogo's `one-of my-nodes with [ kind = "Input" ]`.

#### `_netlogo_downstream_change(gene_network, current_tick, debug)`
Replicates NetLogo's `-DOWNSTREAM-CHANGE-590`. Picks ONE random outgoing link and updates the target node.

**NetLogo code** (lines 1273-1280):
```netlogo
to -DOWNSTREAM-CHANGE-590
   ask one-of my-out-links [ -INFLUENCE-LINK-END-WITH-LOGGING--36 ]
end
```

#### `_netlogo_influence_link_end(gene_network, source_name, target_name, current_tick, debug)`
Replicates NetLogo's `-INFLUENCE-LINK-END-WITH-LOGGING--36`. The core update function that:
1. Saves current fate before update
2. Evaluates target node's Boolean rule
3. Updates target's state
4. Handles fate nodes specially (firing, reversion, reset)
5. Sets next `last_node` based on target type

**NetLogo code** (lines 1487-1591)

## Differences from Previous Implementation

### Before
- Used hierarchical fate logic (fate_hierarchy attribute)
- Simple fate counting (last fate in hierarchy that fired wins)
- No probabilistic inputs
- No cell-specific variability
- No fate reversion mechanism

### After (NetLogo-Faithful)
- Non-hierarchical fate overwriting (last fate to fire wins)
- Transient fate nodes that reset to OFF
- Fate reversion when fate node turns OFF
- Probabilistic activation for GLUT1I and MCT1I
- Cell-specific random thresholds (`_cell_ran1`, `_cell_ran2`)
- Reversible/non-reversible stopping conditions

## Usage Example

```python
from src.workflow.functions.gene_network.propagate_gene_networks_netlogo import propagate_gene_networks_netlogo

# In workflow context
result = propagate_gene_networks_netlogo(
    context=context,
    propagation_steps=500,      # Number of graph-walk steps
    reversible=True,             # Keep updating until Necrosis
    verbose=True,                # Print summary
    debug_steps=False            # Don't print each step
)
```

## Comparison to Benchmark Script

This implementation matches `gene_network_netlogo_probability.py`:

| Feature | Benchmark Script | Workflow Function |
|---------|-----------------|-------------------|
| Graph walking | ✓ | ✓ |
| Fate transience | ✓ | ✓ |
| Fate reversion | ✓ | ✓ |
| Probabilistic inputs | ✓ | ✓ |
| Cell random values | ✓ | ✓ |
| Reversible mode | ✓ | ✓ |
| NetLogo line references | ✓ | ✓ |

## References

- **NetLogo model**: `/Users/gennaroabbruzzese/Documents/BIDSA/jayathilake2022-main/microC_Metabolic_Symbiosis.nlogo3d`
- **Benchmark script**: `opencellcomms_engine/benchmarks/gene_network_netlogo_probability.py`
- **Pipeline documentation**: `docs/netlogo_phenotype_pipeline.md`

## Notes

- **Phenotype decision and cell actions** (division, death) are handled SEPARATELY in other workflow functions
- This function only implements the **propagation** (graph walking) component
- The probabilistic input mechanism requires input concentrations to be provided via the input states
- For deterministic behavior, provide the same random seed across runs
