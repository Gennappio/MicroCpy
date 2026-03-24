# Gene Network Update Mechanisms Comparison

This document compares the different gene network propagation algorithms available in the system.

## Overview

The system now supports **three different update mechanisms** for gene network propagation:

1. **Random NetLogo (v4)** - Uniform random gene selection
2. **Graph Walking (v5)** - Topology-based signal propagation
3. **Synchronous** - All genes updated simultaneously (available in v4)

## 1. Random NetLogo Update (v4 Workflows)

### Algorithm
```python
for step in range(propagation_steps):
    # Randomly select ANY updatable gene uniformly
    selected_gene = random.choice(updatable_genes)
    
    # Evaluate that gene's boolean expression
    new_state = evaluate_logic(selected_gene, current_states)
    
    # Update ONLY that gene
    selected_gene.state = new_state
```

### Characteristics
- **Uniform random selection**: Each gene has equal probability of being selected
- **No spatial correlation**: Updates don't follow signal propagation chains
- **Fate nodes persist**: Stay ON/OFF based on boolean logic
- **Matches**: `gene_network_standalone.py` benchmark

### Files
- `propagate_and_update_gene_networks.py`
- `v4_brute_gene_network_workflow.json`
- `v4_brute_gene_network_workflow_no_hierarchy.json`

### Results (500 steps, Oxygen=OFF, Glucose=ON, MCT1=ON)
```
Phenotypes:     Growth_Arrest 61-67%, Proliferation 20-24%, Necrosis 5-7%
Fate Nodes:     Apoptosis 15-23%, Proliferation 2-3%, Growth_Arrest 30-40%
Metabolic:      mitoATP 0%, glycoATP 60-76%
```

**Key Feature**: Fate nodes show final boolean states (persistent)

---

## 2. Graph Walking Update (v5 Workflow)

### Algorithm
```python
last_node = random_input_node()

for step in range(propagation_steps):
    # Get current node's outgoing links
    outgoing_links = get_output_nodes(last_node)
    
    # Pick ONE random outgoing link (follow topology)
    target_node = random.choice(outgoing_links)
    
    # Update target node
    new_state = evaluate_logic(target_node, current_states)
    target_node.state = new_state
    
    # If fate node fired...
    if target_node.is_fate and new_state:
        # Reset fate node (transient trigger)
        target_node.state = False
        # Return to random input
        last_node = random_input_node()
    else:
        # Continue walking from target
        last_node = target_node
```

### Characteristics
- **Topology-based**: Follows network dependency chains
- **Spatial correlation**: Updates follow signal propagation
- **Fate nodes are transient**: Reset to OFF after firing
- **Tracks fate firings**: Counts how many times each fate fired
- **Matches**: `gene_network_graph_walking.py` benchmark

### Files
- `propagate_gene_networks_graph_walking.py`
- `v5_brute_gene_network_workflow.json`

### Results (500 steps, Oxygen=OFF, Glucose=ON, MCT1=ON)

**Single Run (workflow):**
```
Phenotypes:     Apoptosis 24-31%, Proliferation 12-16%, Necrosis 5-9%
Fate Nodes:     Apoptosis 0%, Proliferation 0% (transient reset!)
                Growth_Arrest 29-32%, Necrosis 1%
Metabolic:      mitoATP 0%, glycoATP 70-86%
```

**100 Runs Average (benchmark):**
```
Ever Fired:     Apoptosis 22%, Proliferation 21%, Necrosis 32%
Final ON:       ALL 0% (transient behavior)
Metabolic:      mitoATP 0%, glycoATP 70%
```

**Key Feature**: Fate nodes always show 0% in final state (transient triggers), but phenotypes capture which fates fired

---

## 3. Synchronous Update (Available in v4)

### Algorithm
```python
for step in range(propagation_steps):
    # Evaluate ALL genes based on PREVIOUS state
    new_states = {}
    for gene in updatable_genes:
        new_states[gene] = evaluate_logic(gene, current_states)
    
    # Apply ALL updates simultaneously
    for gene, new_state in new_states.items():
        gene.state = new_state
```

### Characteristics
- **Deterministic dynamics**: Same initial state → same trajectory
- **No stochasticity**: All genes updated in parallel
- **Biologically less realistic**: Cells are noisy systems
- **Useful for**: Deterministic analysis, attractor identification

### Files
- `propagate_gene_networks.py` (with `update_mode="synchronous"`)
- Not used in current workflows (random NetLogo is default)

---

## Comparison Table

| Feature | Random NetLogo (v4) | Graph Walking (v5) | Synchronous |
|---------|---------------------|-------------------|-------------|
| **Selection** | Uniform random | Topology-based | All genes |
| **Stochastic** | Yes | Yes | No |
| **Fate Nodes** | Persistent | Transient (reset) | Persistent |
| **Signal Chains** | No | Yes | No |
| **Biological Realism** | High | Very High | Medium |
| **Computational Cost** | Low | Medium | Medium |
| **Reproducibility** | Different runs vary | Different runs vary | Deterministic |

---

## When to Use Each

### Use Random NetLogo (v4) when:
- ✅ You want standard NetLogo-style stochastic simulation
- ✅ You need persistent fate node states
- ✅ You want to match `gene_network_standalone.py` behavior
- ✅ Computational efficiency is important

### Use Graph Walking (v5) when:
- ✅ You want to model signal propagation through network topology
- ✅ You need transient fate nodes (biological triggers)
- ✅ You want to track "which fates ever fired" vs "final state"
- ✅ You want to match `gene_network_graph_walking.py` behavior
- ✅ Spatial/topological correlation matters

### Use Synchronous when:
- ✅ You need deterministic, reproducible simulations
- ✅ You want to find network attractors
- ✅ You're doing mathematical analysis of network dynamics
- ✅ You don't need stochastic effects

---

## Technical Implementation

### Random NetLogo
```python
# Simple: pick random gene
gene = random.choice(updatable_genes)
gene.state = gene.update_function(current_states)
```

### Graph Walking
```python
# Build dependency graph first
_build_output_links(gene_network)

# Follow links
target = random.choice(current_node.outputs)
target.state = target.update_function(current_states)

# Handle fate nodes
if target.is_fate and target.state:
    target.state = False  # Reset
    current_node = random_input()  # Return to input
else:
    current_node = target  # Continue walking
```

### Synchronous
```python
# Evaluate all, then update all
new_states = {g: g.update_function(current_states) for g in genes}
for gene, state in new_states.items():
    gene.state = state
```

---

## Benchmark Scripts

| Script | Mechanism | Purpose |
|--------|-----------|---------|
| `gene_network_standalone.py` | Random NetLogo | Reference implementation, Monte Carlo statistics |
| `gene_network_graph_walking.py` | Graph Walking | Topology-based propagation, transient fates |

---

## Workflow Files

| File | Mechanism | Fate Logic |
|------|-----------|------------|
| `v4_brute_gene_network_workflow.json` | Random NetLogo | Hierarchical |
| `v4_brute_gene_network_workflow_no_hierarchy.json` | Random NetLogo | None |
| `v5_brute_gene_network_workflow.json` | Graph Walking | Hierarchical |

---

## Key Insights

1. **Fate Node Behavior is Algorithm-Dependent**:
   - Random NetLogo: Fate nodes show final boolean state
   - Graph Walking: Fate nodes always 0% (transient), phenotypes capture firings

2. **Both Algorithms are Biologically Valid**:
   - Random: Models stochastic gene expression noise
   - Graph Walking: Models signal propagation through pathways

3. **Results are Comparable but Not Identical**:
   - Different algorithms explore state space differently
   - Both produce biologically reasonable fate distributions
   - Use same algorithm for comparing experiments

4. **Phenotype vs Boolean State**:
   - Phenotype (hierarchical): Which fate "won" during propagation
   - Boolean State: Current ON/OFF state of fate gene
   - In graph walking: phenotype ≠ boolean state (transient reset)

---

## Recommendations

1. **For standard workflows**: Use v4 (Random NetLogo)
   - Well-tested, matches standalone script
   - Clear interpretation: fate node state = fate decision

2. **For signal propagation studies**: Use v5 (Graph Walking)
   - Models topology-dependent dynamics
   - Captures transient signaling events

3. **For comparing with literature**: Check which algorithm was used
   - NetLogo papers typically use random selection
   - Some papers use synchronous for deterministic analysis

4. **For your own analysis**: Pick one and stick with it
   - Don't mix algorithms when comparing experiments
   - Document which algorithm you used

---

## References

- NetLogo Gene Network Models: Random gene selection is standard
- Boolean Network Literature: Synchronous update is common
- Signal Transduction: Graph walking models pathway propagation

---

**Last Updated**: 2026-02-09  
**Author**: OpenCellComms Team
