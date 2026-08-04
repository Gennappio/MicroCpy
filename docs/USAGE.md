# Usage Guide

This guide covers how to use OpenCellComms after installation.

## Quick Start

### Start OpenCellComms

**macOS / Linux:**
```bash
./run.sh
```

**Windows:**
```batch
run.bat
```

This starts:
- **Frontend** at http://localhost:3000 (Visual Workflow Designer)
- **Backend** at http://localhost:5001 (Flask API Server)

Open http://localhost:3000 in your browser to use the GUI.

## Using the GUI (Recommended)

### 1. Design Your Workflow

1. **Select a view** — use Overview, Agents, Resources, World,
   Initialization, Scheduler, Planner, Processing, or Results.

2. **Add Functions** - Drag functions from the left palette onto the canvas

3. **Connect Functions** - Draw connections between function nodes to define execution order

4. **Configure Parameters** - Double-click a function node to edit its parameters

5. **Repeat** - Configure all stages as needed for your simulation

### 2. Run the Simulation

1. Click the **Run** button in the simulation panel
2. Watch the real-time log output
3. View results in the Results panel when complete

### 3. Export/Import Workflows

- **Export**: Click "Export" to save your workflow as JSON
- **Import**: Click "Import" to load a previously saved workflow

## Command Line Usage

For advanced users or automation, you can run simulations directly from the command line.

### Activate Environment First

```bash
# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### Run a Workflow

```bash
cd opencellcomms_engine
occ-run --workflow path/to/workflow.json
```

### Run with Configuration File

```bash
occ-run --sim config.yaml
```

### Command Line Options

```bash
occ-run --help
```

**Main options:**

| Option | Description |
|--------|-------------|
| `--workflow FILE` | Run a workflow JSON file |
| `--sim FILE` | Use a YAML configuration file |
| `--entry-subworkflow NAME` | Entry point subworkflow (default: main) |

### Generate Cell Data

```bash
# Spheroid pattern
python run_workflow.py --generate-csv --pattern spheroid --count 50 --output cells.csv

# Grid pattern
python run_workflow.py --generate-csv --pattern grid --grid_size 5x5 --output grid.csv

# With gene network
python run_workflow.py --generate-csv --pattern spheroid --count 25 \
    --genes tests/jayatilake_experiment/jaya.bnd --output cells_with_genes.csv
```

### Generate Plots from Results

```bash
# Basic snapshots
python run_workflow.py --plot-csv --cells-dir results/csv_cells --plot-output plots --snapshots

# With animation and statistics
python run_workflow.py --plot-csv --cells-dir results/csv_cells \
    --substances-dir results/csv_substances \
    --plot-output plots --snapshots --animation --statistics
```

## Example Workflows

Canonical workflows are located in the enabled adapters, for example:

```
opencellcomms_adapters/MicroC/workflows/microc.json
opencellcomms_adapters/TCELL_CORRAL/workflows/tcell_corral.json
opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json
```

To run an example:

```bash
cd opencellcomms_engine
occ-run --workflow ../opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json
```

## Output Files

Simulation results are saved to:

- **GUI and CLI modes**: the repository-level `runs/<label>/` tree

Output includes:
- **CSV files**: Cell data at each timestep
- **Plots**: Visualization images
- **Logs**: Simulation logs

## Workflow JSON Format

Workflows are saved as JSON files with this structure:

```json
{
  "name": "My Workflow",
  "version": "2.0",
  "subworkflows": {
    "main": {
      "kind": "main",
      "functions": [...],
      "subworkflow_calls": [...],
      "execution_order": [...]
    }
  }
}
```

## Tips

### Performance
- Start with small cell counts for testing
- Reduce the `__scheduler__` call's `iterations` value for development smokes

### Debugging
- Check the terminal/console for detailed error messages
- Use `--verbose` flag for more detailed output

### Development
- GUI changes auto-reload in development mode
- Python changes require restarting the backend server

## Next Steps

- Explore the canonical workflows in the enabled adapter `workflows/` folders
- Read the engine documentation in `opencellcomms_engine/README.md`
- Check `docs/engine/GETTING_STARTED.md` for more examples
