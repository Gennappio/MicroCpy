# Jayatilake 2D CSV Workflow

This workflow demonstrates how to run the Jayatilake metabolic symbiosis experiment using a 2D CSV initial state file instead of a 3D VTK file.

## Files

- **`jaya_workflow_2d_csv.json`**: Workflow definition for 2D CSV simulation
- **`jayatilake_experiment_2d_csv_config.yaml`**: Configuration file for 2D simulation
- **`example_2d_cells.csv`**: CSV file with 13 cell positions (9 unique positions, 4 duplicates)

## Workflow Structure

### Initialization Stage
1. **load_config_file**: Loads the YAML configuration file
   - Config: `tests/jayatilake_experiment/jayatilake_experiment_2d_csv_config.yaml`
   - Sets up 2D domain (500x500 μm, 25x25 grid)
   - Configures 5 substances: Oxygen, Glucose, Lactate, H, pH
   
2. **load_cells_from_csv**: Loads cells from CSV file
   - File: `tests/jayatilake_experiment/example_2d_cells.csv`
   - Loads 13 cells from CSV (9 unique positions, 4 duplicates skipped)
   - Each cell has gene network state and phenotype

### Intracellular Stage
- **standard_intracellular_update**: Standard intracellular processes
  - Calls custom metabolism functions
  - Updates gene networks based on environment
  - Updates phenotypes based on gene states
  - Removes dead cells

### Diffusion Stage
- **standard_diffusion_update**: Standard diffusion solver
  - Runs FiPy diffusion solver
  - Uses substance reactions from cells
  - Produces concentration gradients

### Intercellular Stage
- **standard_intercellular_update**: Standard intercellular processes
  - Calls custom division functions
  - Calls custom migration functions

### Finalization Stage
1. **generate_summary_plots**: Generate all plots
   - Heatmaps for all substances
   - Timeseries plots
   - Cell state plots

2. **print_simulation_summary**: Print summary statistics
   - Final cell count
   - Substance concentrations
   - Simulation metrics

## Usage

### Using --sim flag (recommended for now)
```bash
python microc-2.0/run_microc.py --sim microc-2.0/tests/jayatilake_experiment/jayatilake_experiment_2d_csv_config.yaml
```

### Using --workflow flag (when workflow mode is fully implemented)
```bash
python microc-2.0/run_microc.py --workflow microc-2.0/tests/jayatilake_experiment/jaya_workflow_2d_csv.json
```

**Note**: The `--workflow` flag currently only executes initialization and finalization stages. The simulation loop execution needs to be implemented in `run_workflow_mode()` function in `tools/run_sim.py`.

## Expected Results

After running the simulation, you should see:

1. **9 cells loaded** (13 in CSV, but 4 duplicates skipped)
   - Warning message: `[WARNING] Skipped 4 cells with occupied positions`

2. **Concentration gradients** for all substances:
   - **Oxygen**: 0.048-0.050 mM (near cells) vs 0.07 mM (boundaries)
   - **Glucose**: 4.996 mM (near cells) vs 5.0 mM (boundaries)
   - **Lactate**: 1.12 mM (near cells) vs 1.0 mM (boundaries)

3. **Output files** in `results/YYYYMMDD_HHMMSS/`:
   - `csv_cells/cells_step_NNNNNN.csv` - Cell states at each step
   - `csv_substances/SUBSTANCE_field_step_NNNNNN.csv` - Substance fields at each step
   - `plots/heatmaps/SUBSTANCE_heatmap_*.png` - Heatmap plots
   - `log_simulation_status.txt` - Simulation log

## Differences from 3D VTK Workflow

| Feature | 3D VTK Workflow | 2D CSV Workflow |
|---------|----------------|-----------------|
| Initial state file | `cells_200um_domain_domain.vtk` | `example_2d_cells.csv` |
| Loading function | `load_cells_from_vtk` | `load_cells_from_csv` |
| Dimensions | 3D (x, y, z) | 2D (x, y) |
| Domain size | 200x200x200 μm | 500x500 μm |
| Grid size | 10x10x10 | 25x25 |
| Cell count | ~100 cells | 9 cells (13 in CSV, 4 duplicates) |
| Mesh volume | dx*dy*dz (m³) | dx*dy (m² - area only!) |

## Important Notes

### Duplicate Cell Positions
The CSV file `example_2d_cells.csv` contains 13 rows, but 4 of them have duplicate positions:
- Position (11, 12): 2 cells (rows 3 and 10)
- Position (12, 11): 2 cells (rows 4 and 13)
- Position (12, 12): 2 cells (rows 5 and 14)
- Position (12, 13): 2 cells (rows 6 and 15)

The simulation correctly skips duplicates and loads only 9 unique cells. This is expected behavior in a lattice-based model where only one cell can occupy each grid position.

### 2D Mesh Volume Calculation
**CRITICAL**: For 2D simulations, the mesh cell volume is calculated as **AREA only** (`dx * dy`), NOT as volume (`dx * dy * cell_height`). The `twodimensional_adjustment_coefficient` handles the thickness scaling. This was a critical bug that was fixed in commit `66dd2ea`.

### CSV Export
For 2D simulations, both cell states and substance fields are exported to CSV files:
- Cell states: `csv_cells/cells_step_NNNNNN.csv`
- Substance fields: `csv_substances/SUBSTANCE_field_step_NNNNNN.csv`

This allows for easy analysis and plotting of 2D simulation results.

## Troubleshooting

### Issue: Only 9 cells loaded instead of 13
**Solution**: This is expected! The CSV file has 4 duplicate positions. Check the warning message:
```
[WARNING] Skipped 4 cells with occupied positions
```

### Issue: No concentration gradients visible
**Solution**: Check that the mesh cell volume calculation is correct (area only for 2D). This was fixed in commit `66dd2ea`.

### Issue: Workflow doesn't run simulation loop
**Solution**: Use `--sim` flag instead of `--workflow` flag until workflow mode is fully implemented in `run_workflow_mode()`.

## Future Improvements

1. **Complete workflow mode implementation**: Fix `run_workflow_mode()` to actually run the simulation loop
2. **Remove duplicate cells from CSV**: Edit `example_2d_cells.csv` to have 9 unique positions
3. **Add CSV export to workflow**: Add functions to export CSV files during simulation
4. **Add custom plotting functions**: Create workflow functions for custom plots

