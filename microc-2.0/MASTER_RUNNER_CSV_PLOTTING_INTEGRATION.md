# Master Runner CSV Plotting Integration

## Overview

Successfully integrated **CSV plotting functionality** into the Master Runner (`run_microc.py`), providing a unified interface for all MicroC operations including decoupled visualization.

## ✅ **Implementation Summary**

### **New Master Runner Functionality**
- **`--plot-csv` Flag**: Enables CSV plotting mode for post-simulation visualization
- **Flexible Arguments**: Support for cells, substances, and multiple plot types
- **Path Resolution**: Works from any directory with proper tool path resolution
- **Error Handling**: Validates required arguments and provides helpful error messages
- **Default Behavior**: Automatically defaults to snapshot plots if no plot type specified

### **New Command Line Arguments**

```bash
# CSV Plotting Arguments
--plot-csv              # Enable CSV plotting mode
--cells-dir DIR         # Directory containing CSV cell state files (required)
--substances-dir DIR    # Directory containing CSV substance field files (optional)
--plot-output DIR       # Output directory for generated plots (default: plots)

# Plot Type Selection
--snapshots             # Generate snapshot plots for each time step
--animation             # Generate animation from time series data
--statistics            # Generate population statistics plots
```

## 🚀 **Usage Examples**

### **Basic CSV Plotting**
```bash
# Generate snapshot plots from CSV simulation results
python run_microc.py --plot-csv --cells-dir results/csv_cells --plot-output plots --snapshots
```

### **Comprehensive Plotting**
```bash
# Generate all plot types with substances
python run_microc.py --plot-csv \
  --cells-dir results/csv_cells \
  --substances-dir results/csv_substances \
  --plot-output comprehensive_plots \
  --snapshots --animation --statistics
```

### **Default Behavior**
```bash
# Automatically defaults to snapshots if no plot type specified
python run_microc.py --plot-csv --cells-dir results/csv_cells --plot-output plots
# Output: [INFO] No plot type specified, defaulting to --snapshots
```

### **Error Handling**
```bash
# Missing required argument
python run_microc.py --plot-csv
# Output: [!] Error: --cells-dir is required when using --plot-csv
```

## 🔧 **Technical Implementation**

### **Path Resolution Enhancement**
```python
# Get the directory where this script is located
script_dir = Path(__file__).parent
tools_dir = script_dir / "tools"

# Ensures tools are found regardless of current working directory
```

### **Argument Validation**
```python
# CSV plotting for post-simulation visualization
if args.plot_csv:
    total_count += 1
    
    # Validate required arguments
    if not args.cells_dir:
        print("[!] Error: --cells-dir is required when using --plot-csv")
        print("    Specify the directory containing CSV cell state files")
        return
```

### **Default Plot Type Logic**
```python
# Default to snapshots if no plot type specified
if not any([args.snapshots, args.animation, args.statistics]):
    plot_args.append('--snapshots')
    print("[INFO] No plot type specified, defaulting to --snapshots")
```

## 📊 **Complete Workflow Integration**

### **Full MicroC Workflow via Master Runner**

**1. Generate Initial State:**
```bash
python run_microc.py --generate-csv --pattern spheroid --count 50 \
  --genes tests/jayatilake_experiment/jaya_microc.bnd --output initial_cells.csv
```

**2. Run 2D Simulation:**
```bash
python run_microc.py --sim tests/csv_export_test/csv_export_test_config.yaml
```

**3. Generate Visualizations:**
```bash
python run_microc.py --plot-csv --cells-dir results/csv_export_test/csv_cells \
  --plot-output final_plots --snapshots --statistics
```

### **Benefits of Master Runner Integration**

1. **Unified Interface**: Single command for all MicroC operations
2. **Consistent Path Handling**: Works from any directory
3. **Error Prevention**: Validates arguments before execution
4. **Simplified Workflow**: No need to remember individual tool paths
5. **Help Integration**: All functionality documented in `--help`

## 🧪 **Testing Results**

### **Successful Tests**
- ✅ **Basic Plotting**: Snapshot generation working correctly
- ✅ **Path Resolution**: Works from any directory (root, subdirectories)
- ✅ **Error Handling**: Proper validation of required arguments
- ✅ **Default Behavior**: Automatic fallback to snapshots
- ✅ **Help System**: Complete documentation in `--help` output

### **Test Commands Executed**
```bash
# Test from subdirectory
python ../../run_microc.py --plot-csv --cells-dir results/csv_export_test/csv_cells --plot-output master_runner_plots --snapshots

# Test from root directory  
python run_microc.py --plot-csv --cells-dir tests/csv_export_test/results/csv_export_test/csv_cells --plot-output test_from_root --snapshots

# Test error handling
python run_microc.py --plot-csv
# Output: [!] Error: --cells-dir is required when using --plot-csv

# Test default behavior
python run_microc.py --plot-csv --cells-dir results/csv_export_test/csv_cells --plot-output default_test
# Output: [INFO] No plot type specified, defaulting to --snapshots
```

## 📋 **Updated Help Output**

The Master Runner now provides comprehensive help including CSV plotting:

```bash
python run_microc.py --help
```

**Key sections added:**
- CSV plotting arguments with descriptions
- Usage examples for decoupled plotting
- Clear indication of required vs optional arguments

## 🎯 **Result**

The Master Runner now provides a **complete unified interface** for the entire MicroC workflow:

1. **Initial State Generation**: `--generate-csv` with gene network support
2. **Simulation Execution**: `--sim` for running simulations  
3. **Post-Processing Visualization**: `--plot-csv` for decoupled plotting

**Single Tool, Complete Workflow:**
```bash
# Everything through Master Runner
python run_microc.py --generate-csv --pattern spheroid --count 50 --output cells.csv
python run_microc.py --sim config.yaml
python run_microc.py --plot-csv --cells-dir results/csv_cells --plot-output plots --snapshots
```

This integration makes the CSV export and decoupled plotting system easily accessible through the familiar Master Runner interface, providing a seamless user experience for 2D simulation workflows.

---

**Status**: ✅ **COMPLETE** - Master Runner CSV plotting integration fully implemented and tested
