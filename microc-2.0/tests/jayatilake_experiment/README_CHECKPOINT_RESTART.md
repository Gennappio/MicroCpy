# Checkpoint and Restart Guide

## Overview

MicroC 2.0 supports **checkpoint-based simulation restart**. You can save the complete simulation state at any time step and restart from that checkpoint later.

## Checkpoint Format

Checkpoint files are unified CSV files containing:
- **Section 1: CELLS** - Cell positions, phenotypes, ages, generations, and all gene states
- **Section 2: SUBSTANCES** - Concentration fields for all substances at each grid point

Example checkpoint file: `checkpoint_step_000002.csv`

## How to Use Checkpoints

### 1. Run Initial Simulation

Run a simulation that generates checkpoint files:

```bash
python run_microc.py --sim tests/jayatilake_experiment/jayatilake_experiment_2d_csv_config.yaml
```

This creates checkpoint files in:
```
tests/jayatilake_experiment/results/csv_checkpoints/
├── checkpoint_step_000000.csv
├── checkpoint_step_000001.csv
├── checkpoint_step_000002.csv
├── checkpoint_step_000003.csv
└── checkpoint_step_000004.csv
```

### 2. Restart from Checkpoint

To restart from a checkpoint, simply point the `initial_state.file_path` to a checkpoint file:

```yaml
# restart_from_checkpoint_config.yaml
initial_state:
  file_path: "results/csv_checkpoints/checkpoint_step_000002.csv"
```

Then run:

```bash
python run_microc.py --sim tests/jayatilake_experiment/restart_from_checkpoint_config.yaml
```

### 3. What Gets Preserved

When restarting from a checkpoint, the following are preserved:
- ✅ Cell positions (x, y coordinates)
- ✅ Cell phenotypes (Proliferation, Growth_Arrest, etc.)
- ✅ Cell ages (time since cell creation)
- ✅ Cell generations (number of divisions)
- ✅ Gene network states (all 106 gene nodes)
- ❌ Substance concentrations (reset to initial values from YAML)

**Note**: Substance concentrations are currently NOT restored from checkpoints. The simulation restarts with fresh substance fields initialized from the YAML configuration.

## Example Workflow

### Scenario: Long simulation with interruptions

1. **Run first 100 steps**:
   ```yaml
   simulation:
     total_time: 10.0  # 100 steps at dt=0.1
   ```

2. **Checkpoint created**: `checkpoint_step_000100.csv`

3. **Continue from step 100**:
   ```yaml
   initial_state:
     file_path: "results/csv_checkpoints/checkpoint_step_000100.csv"
   
   simulation:
     total_time: 10.0  # Another 100 steps
   ```

4. **Result**: Simulation continues with cells in their exact state from step 100

## Checkpoint File Format

### Section 1: CELLS

```csv
cell_id,x,y,phenotype,age,generation,gene_AKT,gene_AP1,...
cell_000000,11.0,12.0,Growth_Arrest,0.3,0,true,true,...
cell_000001,12.0,11.0,Growth_Arrest,0.3,0,true,true,...
```

### Section 2: SUBSTANCES

```csv
grid_x,grid_y,x_position_um,y_position_um,Glucose_mM,H_mM,Lactate_mM,Oxygen_mM,pH_mM
0,0,10.0,10.0,4.999978,4.21e-05,1.000701,0.069876,7.4
0,1,10.0,30.0,4.999934,4.63e-05,1.002102,0.069629,7.4
```

## Compatibility

- ✅ Checkpoint files can be used as initial state files
- ✅ Simple CSV files (without substances) still work as before
- ✅ Auto-detection of file format (checkpoint vs simple CSV)
- ✅ Backward compatible with existing initial state files

## Limitations

1. **Substance concentrations not restored**: Currently, substance fields are reset to YAML initial values when restarting
2. **2D only**: Checkpoint restart is only supported for 2D simulations
3. **Same grid size required**: The restarted simulation must use the same grid dimensions as the original

## Future Enhancements

Planned improvements:
- [ ] Restore substance concentrations from checkpoints
- [ ] Support for 3D checkpoint restart
- [ ] Automatic time offset (continue from checkpoint time)
- [ ] Checkpoint compression for large simulations

