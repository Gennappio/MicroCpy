# MicroC Repository Organization

This document describes the new organized structure of the MicroC repository.

## 🎯 Goals Achieved

1. **Moved non-essential files to `debug/` folder**
2. **Moved `run_sim.py` to `tools/` folder**
3. **Created `run_microc.py` master runner**
4. **Each tool creates its own output folder**
5. **Removed confusing output directories**

## 📁 New Directory Structure

```
microc-2.0/
├── debug/                          # Non-essential Python files
│   ├── analyze_*.py               # Analysis scripts
│   ├── debug_*.py                 # Debug scripts
│   ├── test_*.py                  # Test scripts
│   ├── calc_*.py                  # Calculation scripts
│   └── ...                        # Other debug/development files
├── tools/                          # Main tools
│   ├── run_sim.py                 # Main simulation runner
│   ├── cell_state_visualizer.py   # Cell visualization
│   ├── cell_state_analyzer.py     # Cell analysis
│   ├── quick_inspect.py           # Quick H5 inspection
│   └── cell_visualizer_results/   # Visualizer output folder
├── benchmarks/                     # Benchmark tools
│   ├── standalone_steadystate_fipy_3D_h5_reader.py
│   └── fipy_h5_simulation_results/ # FiPy simulation output
├── run_microc.py                   # Master runner script
└── ...                            # Core MicroC files
```

## 🚀 Master Runner: `run_microc.py`

The new master runner provides a unified interface to all MicroC tools:

### Usage Examples

```bash
# Run main simulation
python run_microc.py --sim tests/jayatilake_experiment/jayatilake_experiment_config.yaml

# Analyze cell states from H5 file
python run_microc.py --analyze initial_state_3D_S.h5

# Visualize cell states
python run_microc.py --visualize initial_state_3D_S.h5

# Quick inspect H5 file
python run_microc.py --inspect initial_state_3D_S.h5

# Run FiPy standalone simulation
python run_microc.py --fipy initial_state_3D_S.h5

# Run all visualization tools
python run_microc.py --all-viz initial_state_3D_S.h5
```

### Available Flags

- `--sim CONFIG`: Run main MicroC simulation
- `--analyze H5_FILE`: Run cell state analyzer
- `--visualize H5_FILE`: Run cell state visualizer
- `--inspect H5_FILE`: Quick inspect H5 file
- `--demo`: Run visualization demo
- `--fipy H5_FILE`: Run FiPy H5 reader simulation
- `--all-viz H5_FILE`: Run all visualization tools

## 📂 Output Folder Organization

Each tool now creates its own clearly named output folder:

### Tools Output Folders
- **Cell Visualizer**: `tools/cell_visualizer_results/`
- **FiPy H5 Reader**: `benchmarks/fipy_h5_simulation_results/`
- **Main Simulation**: Uses existing `plots/` and `results/` structure

### Removed Confusing Directories
- ❌ `comparison_plots/`
- ❌ `comparison_results/`
- ❌ `demo_output/`
- ❌ `demo_visualizations/`
- ❌ `h5_simulation_results/` (root level)
- ❌ `simple_visualizations/`
- ❌ `visualizations/` (root level)

## 🔧 Technical Changes

### Unicode Compatibility
- Fixed Unicode character encoding issues for Windows compatibility
- Replaced emoji characters with ASCII equivalents:
  - `❌` → `[!]`
  - `✅` → `[+]`
  - `💾` → `[SAVE]`
  - `🚀` → `[RUN]`
  - `μ` → `u`

### Output Directory Logic
- Each tool creates output in its own folder using `Path(__file__).parent`
- No more scattered output files across the repository
- Clear naming convention: `{tool_name}_results/`

## 📋 Migration Notes

### For Users
- Use `python run_microc.py --help` to see all available options
- Old direct tool calls still work: `python tools/cell_state_visualizer.py file.h5`
- Output files are now in predictable, tool-specific folders

### For Developers
- Debug/development files are in `debug/` folder
- Core tools remain in `tools/` folder
- Each tool manages its own output directory
- Unicode characters replaced for Windows compatibility

## 🎉 Benefits

1. **Cleaner Repository**: Non-essential files moved to `debug/`
2. **Unified Interface**: Single `run_microc.py` entry point
3. **Clear Output**: Each tool has its own output folder
4. **Better Organization**: Logical separation of tools and results
5. **Windows Compatible**: Fixed Unicode encoding issues
6. **Maintainable**: Clear structure for future development

## 🔍 Quick Start

```bash
# See all available options
python run_microc.py --help

# Run a quick visualization
python run_microc.py --visualize initial_state_3D_S.h5

# Run FiPy simulation
python run_microc.py --fipy initial_state_3D_S.h5
```

The repository is now much more organized and user-friendly!
