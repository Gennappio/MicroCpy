# MicroC 2.0 Analysis Tools (VTK-only)

This folder previously contained HDF5 analysis tools. The project has migrated to VTK-only initial-state workflows, and these HDF5 utilities were removed.

- Prior tools (`cell_state_analyzer.py`, `cell_state_visualizer.py`, `quick_inspect.py`) have been deleted.
- Refer to VTK exporters and domain loaders for inspecting and visualizing states.

If you need analysis, consider exporting to CSV/JSON using the available VTK utilities or writing small scripts that read VTK and process to your desired format.

python cell_state_visualizer.py file.h5 --fate-genes --phenotypes

# Interactive 3D plot
python cell_state_visualizer.py file.h5 --interactive-3d

# Generate all visualizations
python cell_state_visualizer.py file.h5 --all-plots

# Temporal analysis across multiple files
python cell_state_visualizer.py "cell_states/*.h5" --temporal

# Show plots instead of saving
python cell_state_visualizer.py file.h5 --show --positions-2d
```

**Command Line Options:**
- `--positions-2d`: 2D cell position plot
- `--positions-3d`: 3D cell position plot
- `--interactive-3d`: Interactive 3D plot (requires plotly)
- `--gene-heatmap`: Gene activation heatmap
- `--phenotypes`: Phenotype distribution plots
- `--fate-genes`: Fate gene analysis
- `--ages`: Cell age distribution
- `--all-plots`: Generate all available plots
- `--temporal`: Temporal evolution analysis
- `--show`: Display plots instead of saving
- `--output-dir DIR`: Specify output directory

## File Format Support

Both tools support the MicroC HDF5 file format with the following structure:

```
/metadata/
  - timestamp, version, cell_count, step, domain_info

/cells/
  - ids, positions, phenotypes, ages, division_counts, tq_wait_times

/gene_states/
  - gene_names, states (boolean matrix)

/metabolic_states/
  - metabolite_names, values (float matrix)
```

## Example Outputs

### Quick Inspector Output
```
📁 initial_state_3D_S.h5
──────────────────────────────────────────────────
📏 Size: 292.3 KB
📊 Groups: metadata, cells, gene_states
🧬 Cells: 1000
⏰ Created: 2025-08-05T21:07:05.123456
📈 Step: 0
🌐 Domain: 3D, 25×25×25
🧬 Genes: 107
📊 Avg activation: 0.234
📍 X range: 2.25e-04 - 2.75e-04
📍 Y range: 2.25e-04 - 2.75e-04
📍 Z range: 2.25e-04 - 2.75e-04
🎭 Phenotypes: Growth_Arrest(1000)
✅ Valid file
```

### Detailed Analyzer Output
```
📊 CELL STATE FILE SUMMARY
============================================================
📁 File: initial_state_3D_S.h5
📏 Size: 292.3 KB

📋 Metadata:
   timestamp: 2025-08-05T21:07:05.123456
   version: MicroC-2.0
   cell_count: 1000
   step: 0
   domain_info: 3D, 25×25×25

🧬 Cell Data:
   Cell count: 1000
   Position dimensions: 3D
   Age range: 0.0 - 240.0
   Division count range: 0 - 0
   Phenotype distribution:
     Growth_Arrest: 1000 (100.0%)

🧬 Gene Network Data:
   Gene count: 107
   States matrix: 1000 cells × 107 genes
   Average activation rate: 0.234
   Most active genes:
     GLUT1: 0.856
     MCT1: 0.823
     Oxygen_supply: 0.789
     Glucose_supply: 0.756
     HIF1A: 0.723
   Least active genes:
     Apoptosis: 0.001
     Necrosis: 0.002
     p53: 0.012
     PTEN: 0.023
     RB1: 0.034
```

## Data Export Formats

### CSV Export
- `*_cells.csv`: Cell properties (ID, position, phenotype, age, etc.)
- `*_gene_states.csv`: Gene activation states (cells × genes matrix)
- `*_metabolic_states.csv`: Metabolic concentrations (cells × metabolites matrix)

### JSON Export
- `*_summary.json`: Complete summary statistics and metadata

## Requirements

**Core Requirements:**
- Python 3.7+
- h5py
- numpy
- pandas (for CSV export)

**Visualization Requirements:**
- matplotlib
- seaborn
- plotly (optional, for interactive plots)

**Installation:**
```bash
# Core requirements
pip install h5py numpy pandas matplotlib seaborn

# Optional for interactive plots
pip install plotly
```

## Installation

No installation required. Just run the scripts directly:

```bash
cd microc-2.0/tools
python cell_state_analyzer.py --help
python quick_inspect.py --help
```

## Examples

### Analyze Initial State
```bash
# Quick overview
python quick_inspect.py ../initial_state_3D_S.h5

# Detailed analysis
python cell_state_analyzer.py ../initial_state_3D_S.h5 --gene-analysis --detailed-cells 3
```

### Compare Multiple Time Points
```bash
# Quick comparison
python quick_inspect.py ../results/jayatilake_experiment/cell_states/*.h5

# Detailed comparison (run separately)
python cell_state_analyzer.py ../results/jayatilake_experiment/cell_states/cell_state_step000001*.h5
python cell_state_analyzer.py ../results/jayatilake_experiment/cell_states/cell_state_step000003*.h5
```

### Export for External Analysis
```bash
# Export to CSV for Excel/R/Python analysis
python cell_state_analyzer.py ../initial_state_3D_S.h5 --export-csv --output-dir ../analysis_data

# Export summary for documentation
python cell_state_analyzer.py ../initial_state_3D_S.h5 --export-json
```

### Visualize Cell States
```bash
# Create comprehensive visualizations
python cell_state_visualizer.py ../initial_state_3D_S.h5 --all-plots

# Create specific visualizations
python cell_state_visualizer.py ../initial_state_3D_S.h5 --positions-3d --fate-genes

# Interactive 3D visualization
python cell_state_visualizer.py ../initial_state_3D_S.h5 --interactive-3d

# Analyze temporal evolution
python cell_state_visualizer.py "../results/*/cell_states/*.h5" --temporal
```

## Tips

1. **Use quick_inspect.py first** to get an overview of your files
2. **Use wildcards** to inspect multiple files at once
3. **Export to CSV** for analysis in Excel, R, or other tools
4. **Use --gene-analysis** to understand cell fate distributions
5. **Check file integrity** by looking for "✅ Valid file" messages

## Troubleshooting

- **File not found**: Check file path and ensure HDF5 file exists
- **Permission errors**: Ensure read access to the file
- **Memory issues**: Large files may require more RAM for detailed analysis
- **Missing dependencies**: Install required packages with `pip install h5py numpy pandas`
