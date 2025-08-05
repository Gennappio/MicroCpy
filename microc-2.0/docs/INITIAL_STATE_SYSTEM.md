# 3D Initial State Generator and Loader System

The MicroC 2.0 Initial State System allows you to save and load complete cell population states, including positions and gene network activation states. This is particularly useful for:

- **Reproducible simulations**: Start multiple runs from identical initial conditions
- **Simulation checkpoints**: Save intermediate states during long simulations
- **Parameter studies**: Use the same initial population to test different parameters
- **Debugging**: Examine exact cell states at specific time points

## Features

### 1. Initial State Generation and Saving
- Uses the same logic as MicroC to initialize cell populations
- Saves complete cell state including:
  - 3D positions (automatically converts 2D to 3D if needed)
  - Gene network activation states (all 107+ genes)
  - Cell phenotypes, ages, division counts
  - Metabolic states
- Efficient HDF5 format for fast I/O and compact storage

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

# Initial state configuration
initial_state:
  mode: "generate"              # "generate" or "load"
  file_path: null               # Path to initial state file (for load mode)
  save_initial_state: true      # Save initial state after generation
```

## Usage Examples

### Example 1: Generate and Save Initial State

```yaml
initial_state:
  mode: "generate"
  save_initial_state: true
```

This will:
1. Generate initial cell population using your custom placement functions
2. Save the initial state to `output_dir/initial_states/initial_state_3D_25x25x25_TIMESTAMP.h5`

### Example 2: Load from Saved Initial State

```yaml
initial_state:
  mode: "load"
  file_path: "output_dir/initial_states/initial_state_3D_25x25x25_20250805_201351.h5"
```

This will:
1. Load the exact cell population from the specified file
2. Skip the normal cell generation process
3. Start simulation with the loaded cells

### Example 3: Periodic Saving During Simulation

```yaml
output:
  save_cellstate_interval: 5   # Save every 5 steps
```

This will save cell states to `output_dir/cell_states/cell_state_stepXXXXXX_3D_25x25x25_TIMESTAMP.h5`

## File Format

The system uses HDF5 format with the following structure:

```
/metadata/
  - timestamp: creation time
  - version: MicroC version
  - cell_count: number of cells
  - step: simulation step
  - domain_info: domain configuration (JSON)

/cells/
  - ids: cell IDs
  - positions: Nx3 array of (x,y,z) coordinates in meters
  - phenotypes: cell phenotypes
  - ages: cell ages
  - division_counts: division counts
  - tq_wait_times: TQ wait times

/gene_states/
  - gene_names: array of gene names
  - states: NxM boolean array (N cells, M genes)

/metabolic_states/
  - metabolite_names: array of metabolite names
  - values: NxK float array (N cells, K metabolites)
```

## API Reference

### InitialStateManager Class

```python
from src.io.initial_state import InitialStateManager

manager = InitialStateManager(config)

# Save cell states
manager.save_initial_state(cells_dict, file_path, step=0)

# Load cell states
cell_data = manager.load_initial_state(file_path)
```

### Integration with CellPopulation

```python
# Initialize population from loaded data
population = CellPopulation(grid_size, gene_network, custom_functions, config)
cells_loaded = population.initialize_cells(cell_data)
```

## Testing

Run the test suite to verify the system:

```bash
python test_initial_state_system.py
```

This will:
1. Generate a 1000-cell initial state using MicroC's logic
2. Save it to HDF5 format
3. Load it back and verify all data is preserved
4. Test periodic saving functionality

## Demo Configuration

See `tests/initial_state_demo_config.yaml` for a complete example configuration that demonstrates all features of the initial state system.

## Benefits

1. **Reproducibility**: Exact same starting conditions for multiple runs
2. **Efficiency**: Skip expensive cell generation for parameter studies
3. **Debugging**: Examine cell states at any simulation step
4. **Flexibility**: Works with both 2D and 3D simulations
5. **Performance**: HDF5 format provides fast I/O for large cell populations
6. **Compatibility**: Automatic validation ensures loaded states match current configuration

## File Naming Convention

- Initial states: `initial_state_3D_25x25x25_YYYYMMDD_HHMMSS.h5`
- Periodic saves: `cell_state_stepXXXXXX_3D_25x25x25_YYYYMMDD_HHMMSS.h5`

Where:
- `3D`: dimension (2D or 3D)
- `25x25x25`: grid size
- `YYYYMMDD_HHMMSS`: timestamp
- `stepXXXXXX`: simulation step (for periodic saves)

## Requirements

- Python packages: `h5py`, `numpy`
- HDF5 library (usually installed with h5py)

The initial state system is fully integrated into MicroC 2.0 and requires no additional setup beyond the configuration parameters.
