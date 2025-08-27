# How to Use run_microc.py

## 🎯 Overview

`run_microc.py` is the **master runner** for all MicroC tools and simulations. It provides a unified command-line interface to run different parts of the MicroC system without having to remember individual script locations or arguments.

## 🚀 Quick Start

```bash
# See all available options
python run_microc.py --help

# Run a quick visualization
python run_microc.py --visualize initial_state_3D_S.h5

# Run FiPy simulation
python run_microc.py --fipy initial_state_3D_S.h5
```

## 📋 Available Commands

### 🧬 Main Simulation
```bash
# Run the main MicroC simulation with a config file
python run_microc.py --sim tests/jayatilake_experiment/jayatilake_experiment_config.yaml
```
- **Input**: YAML configuration file
- **Output**: Creates simulation results in standard MicroC output structure
- **Use case**: Run full biological simulations

### 🔬 Cell Analysis Tools

#### Cell State Analyzer
```bash
# Analyze cell states from H5 file
python run_microc.py --analyze initial_state_3D_S.h5
```
- **Input**: H5 cell state file
- **Output**: Statistical analysis of cell states
- **Use case**: Get detailed cell population statistics

#### Cell State Visualizer
```bash
# Create visualizations of cell states
python run_microc.py --visualize initial_state_3D_S.h5
```
- **Input**: H5 cell state file
- **Output**: Plots saved to `tools/cell_visualizer_results/`
- **Use case**: Generate publication-quality cell visualizations

#### Quick Inspector
```bash
# Quick inspection of H5 file contents
python run_microc.py --inspect initial_state_3D_S.h5
```
- **Input**: H5 cell state file
- **Output**: Summary printed to console
- **Use case**: Quick check of file contents and structure

#### H5 File Generator
```bash
# Generate custom H5 files with specified parameters
python run_microc.py --generate --cells 1000 --radius 50 --sparseness 0.3 --radial 0.5
```
- **Input**: Parameters for cell generation
- **Output**: H5 cell state files
- **Use case**: Create synthetic cell populations for testing

### 🧪 Benchmark Tools

#### FiPy H5 Reader Simulation
```bash
# Run standalone FiPy simulation on H5 cell data
python run_microc.py --fipy initial_state_3D_S.h5
```
- **Input**: H5 cell state file
- **Output**: Simulation plots saved to `benchmarks/fipy_h5_simulation_results/`
- **Use case**: Test FiPy physics on saved cell states

### 🎨 Demonstration Tools

#### Visualization Demo
```bash
# Run visualization demonstration
python run_microc.py --demo
```
- **Input**: None (uses built-in demo data)
- **Output**: Demo visualizations
- **Use case**: Test visualization capabilities

### 🔄 Convenience Commands

#### Run All Visualization Tools
```bash
# Run analyzer, visualizer, and inspector on the same file
python run_microc.py --all-viz initial_state_3D_S.h5
```
- **Input**: H5 cell state file
- **Output**: All visualization outputs
- **Use case**: Complete analysis workflow

## 📁 Output Locations

Each tool creates output in its own clearly named folder:

| Tool | Output Location | Contents |
|------|----------------|----------|
| Cell Visualizer | `tools/cell_visualizer_results/` | PNG plots, 3D visualizations |
| FiPy H5 Reader | `benchmarks/fipy_h5_simulation_results/` | Simulation plots |
| Main Simulation | `plots/` and `results/` | Standard MicroC outputs |

## 💡 Usage Examples

### Example 1: Complete Cell Analysis Workflow
```bash
# 1. Quick inspection
python run_microc.py --inspect my_cells.h5

# 2. Detailed analysis
python run_microc.py --analyze my_cells.h5

# 3. Create visualizations
python run_microc.py --visualize my_cells.h5

# 4. Run physics simulation
python run_microc.py --fipy my_cells.h5
```

### Example 2: One-Command Analysis
```bash
# Run all visualization tools at once
python run_microc.py --all-viz my_cells.h5
```

### Example 3: Custom Cell Generation and Analysis
```bash
# 1. Generate custom cell population
python run_microc.py --generate --cells 1000 --radius 50 --sparseness 0.2

# 2. Analyze generated cells
python run_microc.py --all-viz generated_cells_TIMESTAMP.h5

# 3. Run physics simulation on generated cells
python run_microc.py --fipy generated_cells_TIMESTAMP.h5
```

### Example 4: Full Simulation Pipeline
```bash
# 1. Run main simulation
python run_microc.py --sim my_config.yaml

# 2. Analyze results (assuming simulation creates cell_states.h5)
python run_microc.py --all-viz cell_states.h5
```

## 🔧 Technical Details

### Requirements
- Python 3.7+
- All MicroC dependencies installed
- H5 files for analysis tools
- YAML config files for simulations

### Error Handling
- The script reports success/failure for each tool
- Failed tools don't stop execution of other tools
- Exit code 0 = all tools succeeded, 1 = some tools failed

### Parallel Execution
- Tools run sequentially, not in parallel
- Each tool completes before the next starts
- Progress is reported for each tool

## 🐛 Troubleshooting

### Common Issues

#### "File not found" errors
```bash
# Make sure file paths are correct
python run_microc.py --visualize path/to/your/file.h5
```

#### "Tool failed" messages
- Check that all dependencies are installed
- Verify input file format is correct
- Look at the detailed error message printed

#### Unicode/encoding errors
- All Unicode characters have been replaced with ASCII equivalents
- Should work on all Windows systems

### Getting Help
```bash
# See all available options and examples
python run_microc.py --help

# Run without arguments to see help
python run_microc.py
```

## 📊 Output Summary

After running tools, you'll see a summary like:
```
[RUN] Running: python tools/cell_state_visualizer.py initial_state_3D_S.h5
[+] cell_state_visualizer.py completed successfully

Summary: 1/1 tools completed successfully
[SUCCESS] All tools completed successfully!
```

## 🎯 Best Practices

1. **Start with inspection**: Use `--inspect` to check file contents first
2. **Use meaningful names**: Name your H5 files descriptively
3. **Check outputs**: Look in the tool-specific output folders
4. **Batch processing**: Use `--all-viz` for complete analysis
5. **Keep configs organized**: Store YAML configs in the `tests/` folder

## 🔗 Related Files

- **Individual tools**: Located in `tools/` and `benchmarks/` folders
- **Configurations**: Example configs in `tests/` folder
- **Documentation**: See other `.md` files in the repository

The `run_microc.py` script makes MicroC much easier to use by providing a single, consistent interface to all tools!
