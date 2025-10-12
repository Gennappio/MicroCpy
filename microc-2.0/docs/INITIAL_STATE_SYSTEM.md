# 3D Initial State Generator and Loader System

The MicroC 2.0 Initial State System allows you to save and load complete cell population states, including positions and gene network activation states. This is particularly useful for:

- **Reproducible simulations**: Start multiple runs from identical initial conditions
- **Simulation checkpoints**: Save intermediate states during long simulations
- **Parameter studies**: Use the same initial population to test different parameters
- **Debugging**: Examine exact cell states at specific time points

## Features

### 1. Initial State Generation
- Uses the same logic as MicroC to initialize cell populations
- Initializes complete cell state including:
  - 3D positions (automatically converts 2D to 3D if needed)
  - Gene network activation states (all 107+ genes)
  - Cell phenotypes, ages, division counts
  - Metabolic states
- VTK is the supported format for initial-state domain files

### 2. Initial State Loading
- Load previously saved cell states
- Automatic domain compatibility validation
- Preserves all cell properties and gene states
- Seamless integration with existing simulation workflow

### 3. Periodic Cell State Saving
- Save cell states at configurable intervals during simulation
- Useful for creating simulation checkpoints
- Automatic timestamped filenames

## Configuration

Add these sections to your YAML configuration file:

```yaml
# Output configuration
output:
  save_cellstate_interval: 10   # Save cell states every 10 steps (0 = disabled)

# Initial state configuration (VTK-only)
initial_state:
  file_path: "domain/initial_cells.vtk"
```

## Usage Examples

### Example 1: Load from VTK Initial State

```yaml
initial_state:
  file_path: "domain/initial_cells.vtk"
```

This will:
1. Load the exact cell population from the VTK file
2. Skip the normal cell generation process
3. Start simulation with the loaded cells

### Example 2: Load from VTK Initial State

```yaml
initial_state:
  mode: "load_vtk"
  file_path: "domain/initial_cells.vtk"
```

This will:
1. Load the exact cell population from the VTK file
2. Skip the normal cell generation process
3. Start simulation with the loaded cells

### Example 3: Periodic Saving During Simulation

Use VTK exporters in your custom functions to write periodic snapshots if desired. Built-in HDF5 periodic saves have been removed.

## File Format

Initial state loading uses VTK domain files. See tools/vtk_export.py for the enhanced VTK format that embeds gene states and phenotypes when available.

## API Reference

### InitialStateManager Class

```python
from src.io.initial_state import InitialStateManager

manager = InitialStateManager(config)

# Load from VTK file
cell_data, cell_size_um = manager.load_initial_state_from_vtk("domain/initial_cells.vtk")
```

### Integration with CellPopulation

```python
# Initialize population from loaded data
population = CellPopulation(grid_size, gene_network, custom_functions, config)
cells_loaded = population.initialize_cells(cell_data)
```

## Testing

Write unit tests to validate VTK loading using small synthetic VTK files. Example checks:
- Positions mapped to logical grid as expected
- Phenotype mapping from scalar values to names
- Gene states initialized for all nodes present in VTK metadata
- Fallback to basic loader when metadata is absent

## Demo Configuration

See `tests/initial_state_demo_config.yaml` for a complete example configuration that demonstrates all features of the initial state system.

## Benefits

1. **Reproducibility**: Exact same starting conditions for multiple runs
2. **Efficiency**: Skip expensive cell generation for parameter studies
3. **Debugging**: Examine cell states at any simulation step
4. **Flexibility**: Works with both 2D and 3D simulations

## Notes
- HDF5 saving/loading has been removed in favor of VTK-only initial-state loading.
- If you need persistent snapshots, export via VTK utilities or CSV/JSON from your custom code.

