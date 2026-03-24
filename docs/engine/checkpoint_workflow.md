# Checkpoint Read/Write Workflow

This document explains how to use checkpoints in MicroCpy workflows to save and load cell populations.

## Overview

Checkpoints allow you to:
- **Save** the current population state (positions, gene states, phenotypes, ages)
- **Load** a previously saved population to continue or repeat simulations
- **Share** initial conditions between different experiments

## File Formats

### VTK Format (Recommended)
- **Supports**: 2D and 3D simulations
- **Includes**: Cell positions, gene network states, phenotypes, ages, generations
- **File extension**: `.vtk`
- **Use case**: All simulations, especially 3D

### CSV Format (Legacy)
- **Supports**: 2D simulations only
- **Includes**: Cell positions, gene network states, phenotypes
- **File extension**: `.csv`
- **Use case**: Simple 2D simulations, human-readable format

## Workflow Functions

### 1. `read_checkpoint`
**Category**: INITIALIZATION  
**Purpose**: Load cells from a checkpoint file

**Parameters**:
- `file_path`: Path to checkpoint file (VTK or CSV)

**Example**:
```json
{
  "function_name": "read_checkpoint",
  "parameters": {},
  "parameter_nodes": ["param_checkpoint_file"]
}
```

**Parameter node**:
```json
{
  "id": "param_checkpoint_file",
  "name": "file_path",
  "type": "STRING",
  "value": "opencellcomms_engine/tests/jayatilake_experiment/checkpoint_1000_cells_3d.vtk"
}
```

**Requirements**:
1. Must run **after** `setup_population` (which creates the population object)
2. Must run **after** `setup_domain` (which defines the domain size)
3. Checkpoint file must exist

**Execution order**:
```
setup_simulation → setup_domain → setup_population → read_checkpoint
```

### 2. `save_checkpoint`
**Category**: FINALIZATION  
**Purpose**: Save current population to a checkpoint file

**Parameters**:
- `file_path`: Path to save checkpoint (default: "checkpoint.vtk")
- `include_gene_states`: Whether to save gene network states (default: true)

**Example**:
```json
{
  "function_name": "save_checkpoint",
  "parameters": {
    "file_path": "checkpoint_final.vtk",
    "include_gene_states": true
  }
}
```

**Output location**:
- Relative paths: Saved to `context['output_dir']` (typically `results/YYYYMMDD_HHMMSS/`)
- Absolute paths: Saved to specified path

## Complete Workflow Example

Here's a complete workflow that loads a checkpoint, runs simulation, and saves a new checkpoint:

```json
{
  "subworkflows": {
    "main": {
      "execution_order": [
        "call_setup",
        "call_simulation",
        "call_finalization"
      ]
    },
    "setup": {
      "functions": [
        {
          "function_name": "setup_simulation",
          "parameters": {
            "name": "Checkpoint Test",
            "dt": 0.1,
            "output_dir": "results"
          }
        },
        {
          "function_name": "setup_domain",
          "parameters": {
            "dimensions": 3,
            "size_x": 100,
            "size_y": 100,
            "size_z": 100
          }
        },
        {
          "function_name": "setup_population",
          "parameters": {
            "enable_gene_network": true
          }
        },
        {
          "function_name": "read_checkpoint",
          "parameters": {},
          "parameter_nodes": ["param_checkpoint_file"]
        }
      ],
      "parameters": [
        {
          "id": "param_checkpoint_file",
          "name": "file_path",
          "value": "checkpoint_1000_cells_3d.vtk"
        }
      ]
    },
    "simulation": {
      "functions": [
        {
          "function_name": "propagate_gene_networks_netlogo",
          "parameters": {
            "propagation_steps": 100
          }
        }
      ]
    },
    "finalization": {
      "functions": [
        {
          "function_name": "save_checkpoint",
          "parameters": {
            "file_path": "checkpoint_after_propagation.vtk",
            "include_gene_states": true
          }
        }
      ]
    }
  }
}
```

## Converting CSV to VTK (for 3D workflows)

If you have existing 2D CSV checkpoints and want to use them in 3D workflows:

### 1. Run the converter script:
```bash
cd opencellcomms_engine/tests/jayatilake_experiment
python convert_csv_to_vtk.py
```

### 2. Edit the script to convert your specific CSV:
```python
# In convert_csv_to_vtk.py, change:
csv_file = Path(__file__).parent / "your_checkpoint.csv"
vtk_file = Path(__file__).parent / "your_checkpoint_3d.vtk"

convert_csv_to_vtk_3d(csv_file, vtk_file, z_position=50)
```

### 3. The converter:
- Reads 2D CSV with `x,y` positions
- Adds `z` coordinate (default: 50, center of 100um domain)
- Preserves all gene states and phenotypes
- Writes VTK format compatible with 3D simulations

## Checkpoint File Contents

### VTK Checkpoint includes:
- **Positions**: Logical grid coordinates (x, y, z)
- **Gene states**: Boolean state of each gene node (e.g., Proliferation, p53, AKT)
- **Phenotypes**: Cell fate (e.g., Proliferation, Apoptosis, Growth_Arrest)
- **Ages**: Cell age in simulation time units
- **Generations**: Number of divisions since initial cell
- **Metadata**: Cell size, dimensions, custom fields

### Example VTK header:
```
# vtk DataFile Version 3.0
| biocell_grid_size_um=20.0 | dimensions=3 | description="..." | genes=p53,AKT,ERK,... | phenotypes=Proliferation,Apoptosis,...
```

## Troubleshooting

### Error: "CSV loading is only supported for 2D simulations"
**Problem**: Trying to load a CSV checkpoint in a 3D workflow  
**Solution**: Convert your CSV to VTK using `convert_csv_to_vtk.py`

### Error: "Checkpoint file not found"
**Problem**: File path is incorrect or relative to wrong directory  
**Solution**: Use path relative to project root, e.g., `opencellcomms_engine/tests/...`

### Error: "No population in context"
**Problem**: `read_checkpoint` called before `setup_population`  
**Solution**: Ensure execution order is: `setup_simulation` → `setup_domain` → `setup_population` → `read_checkpoint`

### Warning: "VTK cube size differs from YAML cell height"
**Problem**: Checkpoint was created with different cell size than current config  
**Solution**: This is usually fine - the system uses the YAML config's cell size

## Related Files

- `opencellcomms_engine/src/workflow/functions/initialization/read_checkpoint.py`
- `opencellcomms_engine/src/workflow/functions/finalization/save_checkpoint.py`
- `opencellcomms_engine/src/io/initial_state.py` (VTK/CSV loader)
- `opencellcomms_engine/src/io/vtk_domain_loader.py` (VTK format handler)
- `opencellcomms_engine/tests/jayatilake_experiment/convert_csv_to_vtk.py` (CSV→VTK converter)
- `opencellcomms_engine/tests/jayatilake_experiment/v6_proliferation.json` (Example workflow)
