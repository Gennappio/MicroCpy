# CSV 2D Integration Summary

## Overview

Successfully integrated CSV support for 2D simulations with the same coordinate system as 3D VTK files. This provides a human-readable alternative to VTK for 2D simulations while maintaining consistency with the existing coordinate system.

## Changes Made

### 1. File Renaming
- **Old**: `jayatilake_experiment_custom_functions.py`
- **New**: `jayatilake_experiment_cell_functions.py`
- **Reason**: More descriptive name that reflects the actual functionality

### 2. Enhanced Initial State Loader (`src/io/initial_state.py`)

#### New Features:
- **Auto-detection**: File format detected by extension (`.csv` vs `.vtk`)
- **CSV Support**: Full CSV loader for 2D simulations
- **Unified API**: Same coordinate system for both CSV and VTK

#### New Classes:
- `CSVCellLoader`: Handles CSV file parsing and validation
- Enhanced `InitialStateManager` with CSV support

#### New Methods:
- `load_initial_state()`: Auto-detects format and loads appropriately
- `load_initial_state_from_csv()`: Dedicated CSV loader for 2D simulations

### 3. CSV Format Specification

#### Required Columns:
- `x`: Logical grid X coordinate
- `y`: Logical grid Y coordinate

#### Optional Columns:
- `phenotype`: Cell phenotype (e.g., "Proliferation", "Quiescent")
- `age`: Cell age in simulation time units
- `gene_<name>`: Gene states (e.g., `gene_mitoATP`, `gene_glycoATP`)

#### Metadata Support:
- Comment line with metadata: `# cell_size_um=20.0, description="..."`
- Automatic parsing of key=value pairs

### 4. CSV Generator Tool (`tools/csv_cell_generator.py`)

#### Patterns Supported:
- **Spheroid**: Circular cell placement for tumor spheroids
- **Grid**: Regular grid pattern for systematic studies
- **Random**: Random placement for heterogeneous studies

#### Features:
- Automatic gene state assignment based on pattern
- Phenotype assignment with spatial logic
- Metadata generation
- Command-line interface

### 5. Documentation

#### New Files:
- `docs/CSV_INITIAL_STATE_FORMAT.md`: Complete CSV format specification
- `CSV_2D_INTEGRATION_SUMMARY.md`: This summary document

#### Example Files:
- `tests/jayatilake_experiment/example_2d_cells.csv`: Example CSV file
- `tests/jayatilake_experiment/jayatilake_experiment_2d_csv_config.yaml`: 2D configuration

## Coordinate System Consistency

### Key Principle: Same System for CSV and VTK
1. **Logical Coordinates**: CSV x,y values are logical grid indices (same as VTK)
2. **Physical Coordinates**: Calculated as `logical_position × cell_size_um`
3. **Cell Size**: Always from YAML configuration (`domain.cell_height`)

### Example:
```
CSV: x=10, y=5
YAML: cell_height=20 um
Result: 
  - Logical position: (10, 5)
  - Physical position: (200, 100) um
```

## Usage Examples

### 1. Auto-Detection
```yaml
initial_state:
  file_path: "cells.csv"  # Automatically detects CSV format
```

### 2. Manual CSV Creation
```csv
# cell_size_um=20.0, description="Custom cells"
x,y,phenotype,gene_mitoATP,gene_glycoATP
10,10,Proliferation,true,false
11,10,Proliferation,false,true
```

### 3. Generator Tool
```bash
# Generate spheroid pattern
python tools/csv_cell_generator.py --output cells.csv --pattern spheroid --count 25

# Generate grid pattern
python tools/csv_cell_generator.py --output cells.csv --pattern grid --grid_size 5x5
```

### 4. Loading in Code
```python
from src.io.initial_state import InitialStateManager

manager = InitialStateManager(config)
cell_data, cell_size_um = manager.load_initial_state("cells.csv")
```

## Benefits

### 1. Human-Readable Format
- Easy to create and edit manually
- Clear column headers and data structure
- Metadata in comments

### 2. Consistency with 3D System
- Same logical→physical coordinate mapping
- Same cell size handling (YAML as source of truth)
- Same gene state and phenotype format

### 3. Flexibility
- Optional columns for different use cases
- Extensible metadata system
- Multiple generation patterns

### 4. Validation and Error Handling
- Coordinate bounds checking
- Data type validation
- Graceful handling of invalid data

## Testing

### Validation Tests:
- ✅ CSV loader correctly parses files
- ✅ Coordinate system matches VTK behavior
- ✅ Gene states and phenotypes load correctly
- ✅ Metadata parsing works
- ✅ Integration with InitialStateManager

### Example Test Results:
```
Loaded 13 cells from CSV
Cell size: 20.00 um (from YAML config)
Phenotypes: 2 types (Proliferation, Quiescent)
Gene states: 3 genes (Proliferation, glycoATP, mitoATP)
```

## Migration Guide

### From VTK to CSV (for 2D):
1. Extract logical coordinates from VTK
2. Map gene states to `gene_` columns
3. Add phenotype column
4. Include metadata comment

### From Manual Placement to CSV:
1. Replace hardcoded positions with CSV file
2. Use generator tool for systematic patterns
3. Update configuration to point to CSV file

## Future Enhancements

### Potential Additions:
- Age column support in CSV
- Division count tracking
- Metabolic state initialization
- 3D CSV support (if needed)
- Excel/ODS format support

### Performance Optimizations:
- Streaming parser for large files
- Binary CSV format for very large datasets
- Parallel loading for multiple files

## Conclusion

The CSV integration provides a clean, human-readable alternative to VTK for 2D simulations while maintaining full compatibility with the existing coordinate system and simulation framework. The implementation is robust, well-tested, and ready for production use.
