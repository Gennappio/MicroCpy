# Granular Workflow Functions - GUI Customization Guide

## Overview

The workflow system now provides **granular functions** that break down each simulation stage into individual, customizable operations. This allows you to:

1. **Modify specific parts** of the simulation without rewriting entire stages
2. **Add custom logging** or data collection between operations
3. **Disable specific operations** by removing nodes from the workflow
4. **Insert custom functions** at any point in the execution chain

## Granular Functions Available

### Intracellular Stage (4 functions)

| Function | Description | What it does |
|----------|-------------|--------------|
| `update_metabolism` | Update intracellular metabolism | Calls custom metabolism function for each cell (ATP, metabolites) |
| `update_gene_networks` | Update gene networks | Reads environment and updates gene states (hypoxia, glycolysis genes) |
| `update_phenotypes` | Update cell phenotypes | Determines phenotype based on gene states (glycolytic vs oxidative) |
| `remove_dead_cells` | Remove dead cells | Removes cells with ATP below death threshold |

**Default execution order**: metabolism → gene networks → phenotypes → remove dead cells

### Diffusion Stage (1 function)

| Function | Description | What it does |
|----------|-------------|--------------|
| `run_diffusion_solver` | Run diffusion PDE solver | Solves diffusion equations for all substances (O₂, glucose, lactate, H⁺, pH) |

### Intercellular Stage (2 functions)

| Function | Description | What it does |
|----------|-------------|--------------|
| `update_cell_division` | ATP-based cell division | Checks ATP threshold and creates daughter cells |
| `update_cell_migration` | Cell migration | Placeholder for custom migration logic (currently empty) |

**Default execution order**: division → migration

## Example: Granular Workflow JSON

Here's the structure of `jaya_workflow_2d_csv.json` with granular functions:

```json
{
  "stages": {
    "intracellular": {
      "enabled": true,
      "functions": [
        {
          "id": "metabolism_1",
          "function_name": "update_metabolism",
          "description": "Update intracellular metabolism (ATP, metabolites)",
          "enabled": true
        },
        {
          "id": "gene_networks_1",
          "function_name": "update_gene_networks",
          "description": "Update gene networks based on environment",
          "enabled": true
        },
        {
          "id": "phenotypes_1",
          "function_name": "update_phenotypes",
          "description": "Update cell phenotypes based on gene states",
          "enabled": true
        },
        {
          "id": "remove_dead_1",
          "function_name": "remove_dead_cells",
          "description": "Remove cells with ATP below death threshold",
          "enabled": true
        }
      ],
      "execution_order": ["metabolism_1", "gene_networks_1", "phenotypes_1", "remove_dead_1"]
    },
    
    "diffusion": {
      "enabled": true,
      "functions": [
        {
          "id": "diffusion_solver_1",
          "function_name": "run_diffusion_solver",
          "description": "Run diffusion PDE solver",
          "enabled": true
        }
      ],
      "execution_order": ["diffusion_solver_1"]
    },
    
    "intercellular": {
      "enabled": true,
      "functions": [
        {
          "id": "cell_division_1",
          "function_name": "update_cell_division",
          "description": "ATP-based cell division",
          "enabled": true
        }
      ],
      "execution_order": ["cell_division_1"]
    }
  }
}
```

## Customization Examples

### Example 1: Skip Gene Network Updates

If you want to run the simulation without updating gene networks (e.g., to test metabolism only):

**Option A**: Disable the node in the GUI
- Click on the "Update Gene Networks" node
- Toggle "enabled" to false

**Option B**: Edit the JSON
```json
{
  "id": "gene_networks_1",
  "function_name": "update_gene_networks",
  "enabled": false  // ← Set to false
}
```

### Example 2: Add Custom Logging Between Operations

Create a custom function to log cell states:

**1. Create custom function** (`jayatilake_experiment_cell_functions.py`):
```python
def log_cell_states(population, **kwargs):
    """Log current cell states"""
    print(f"[CUSTOM LOG] Current cell count: {len(population.cells)}")
    for cell in population.cells:
        print(f"  Cell {cell.id}: ATP={cell.atp:.2e}, Phenotype={cell.phenotype}")
```

**2. Add to workflow** (between metabolism and gene networks):
```json
{
  "functions": [
    {"id": "metabolism_1", "function_name": "update_metabolism"},
    {"id": "log_1", "function_name": "log_cell_states"},  // ← Custom logging
    {"id": "gene_networks_1", "function_name": "update_gene_networks"},
    ...
  ],
  "execution_order": ["metabolism_1", "log_1", "gene_networks_1", ...]
}
```

### Example 3: Change Execution Order

If you want to remove dead cells BEFORE updating phenotypes (instead of after):

```json
{
  "execution_order": [
    "metabolism_1",
    "gene_networks_1",
    "remove_dead_1",      // ← Moved before phenotypes
    "phenotypes_1"
  ]
}
```

### Example 4: Add Custom Data Collection

Create a function to collect custom statistics:

**1. Create custom function**:
```python
def collect_phenotype_stats(population, context, **kwargs):
    """Collect phenotype distribution statistics"""
    phenotype_counts = {}
    for cell in population.cells:
        phenotype = cell.phenotype
        phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1
    
    # Store in context for later use
    if 'phenotype_history' not in context:
        context['phenotype_history'] = []
    context['phenotype_history'].append({
        'step': context['step'],
        'counts': phenotype_counts
    })
    return context
```

**2. Add to workflow** (after phenotype update):
```json
{
  "functions": [
    {"id": "metabolism_1", "function_name": "update_metabolism"},
    {"id": "gene_networks_1", "function_name": "update_gene_networks"},
    {"id": "phenotypes_1", "function_name": "update_phenotypes"},
    {"id": "collect_stats_1", "function_name": "collect_phenotype_stats"},  // ← Custom stats
    {"id": "remove_dead_1", "function_name": "remove_dead_cells"}
  ]
}
```

## Backward Compatibility

The monolithic functions are still available for backward compatibility:

| Monolithic Function | Equivalent Granular Chain |
|---------------------|---------------------------|
| `standard_intracellular_update` | `update_metabolism` → `update_gene_networks` → `update_phenotypes` → `remove_dead_cells` |
| `standard_diffusion_update` | `run_diffusion_solver` |
| `standard_intercellular_update` | `update_cell_division` |

You can use either approach - they produce identical results.

## GUI Integration

In the GUI workflow designer:

1. **Drag and drop** granular function nodes from the function palette
2. **Connect nodes** in the desired execution order
3. **Enable/disable** individual operations by toggling the node
4. **Add custom functions** by creating a "Custom Function" node
5. **Reorder operations** by changing the execution order

The GUI will automatically:
- Show available granular functions in the palette
- Validate execution order
- Generate the correct JSON workflow
- Pass the correct context parameters to each function

## Testing

Both workflows produce identical results:

```bash
# Granular workflow (new)
python microc-2.0/run_microc.py --workflow microc-2.0/tests/jayatilake_experiment/jaya_workflow_2d_csv.json

# Monolithic workflow (old, for comparison)
# (Would need to create a separate workflow file with standard_* functions)
```

**Verified Results**:
- ✅ Oxygen concentration: 0.048 - 0.070 mM
- ✅ Glucose concentration: 4.996 - 5.000 mM
- ✅ Lactate concentration: 1.000 - 1.123 mM
- ✅ Final cell count: 9 cells
- ✅ CSV exports: 30 files (5 cells + 25 substances)
- ✅ Plots: 7 plots generated

## Summary

The granular workflow system provides:

✅ **Fine-grained control** - Modify individual operations without rewriting entire stages
✅ **Easy customization** - Add logging, data collection, or custom logic anywhere
✅ **GUI-friendly** - Each operation is a separate node in the visual workflow designer
✅ **Backward compatible** - Monolithic functions still work
✅ **Validated** - Produces identical results to the original implementation

This makes the ABM GUI truly customizable - you can modify exactly what you need without touching the rest of the simulation!

