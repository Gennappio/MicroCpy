# MicroC 2.0 - Multi-Scale Biological Simulation

A Python-based cellular simulation system modeling gene regulatory networks and substance diffusion.

## Quick Start

### 1. Generate Initial Cell Population
```bash
python run_microc.py --generate-csv --pattern spheroid --count 50 \
  --genes tests/jayatilake_experiment/jaya_microc.bnd \
  --output initial_cells.csv
```

### 2. Run Simulation
```bash
python run_microc.py --sim tests/jayatilake_experiment/jayatilake_experiment_config.yaml
```

### 3. Generate Visualizations
```bash
python run_microc.py --plot-csv --cells-dir results/csv_cells \
  --plot-output plots --snapshots
```

## Master Runner Commands

### Cell Generation
- `--generate-csv`: Create initial cell population
- `--pattern`: Cell arrangement (spheroid, random, grid)
- `--count`: Number of cells
- `--genes`: Gene network file (.bnd format)
- `--output`: Output CSV file

### Simulation
- `--sim`: Run simulation with config file
- Config files define domain, substances, and parameters

### Visualization
- `--plot-csv`: Generate plots from CSV results
- `--cells-dir`: Directory with cell state files
- `--plot-output`: Output directory for plots
- `--snapshots`: Generate snapshot plots
- `--animation`: Create time-lapse animation
- `--statistics`: Plot population statistics

## Examples

**2D Tumor Growth Simulation:**
```bash
# Generate spheroid
python run_microc.py --generate-csv --pattern spheroid --count 100 \
  --genes tests/jayatilake_experiment/jaya_microc.bnd --output tumor.csv

# Run simulation
python run_microc.py --sim tests/jayatilake_experiment/jayatilake_experiment_2d_csv_config.yaml

# Visualize results
python run_microc.py --plot-csv --cells-dir results/csv_cells \
  --plot-output tumor_plots --snapshots --statistics
```

**3D Simulation:**
```bash
python run_microc.py --sim tests/jayatilake_experiment/jayatilake_experiment_config.yaml
```

## File Structure
```
microc-2.0/
├── run_microc.py          # Master Runner
├── src/                   # Core simulation code
├── tools/                 # Utilities (CSV export, plotting)
├── tests/                 # Example configurations
│   ├── jayatilake_experiment/  # Main tumor model
│   └── csv_export_test/        # 2D CSV workflow
└── README.md
```

## Requirements
- Python 3.8+
- FiPy, NumPy, Matplotlib, PyYAML

## Help
```bash
python run_microc.py --help
```
