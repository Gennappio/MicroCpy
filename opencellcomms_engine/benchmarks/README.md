# MicroC 2.0 Benchmarks

This folder contains standalone benchmark and validation scripts for MicroC simulations.

## Scripts Overview

### 1. `standalone_steadystate_fipy_3D.py` - Reference Implementation

A standalone 3D FiPy implementation that exactly matches MicroC's approach.

**Purpose:**
- Validate MicroC's FiPy integration
- Benchmark diffusion solver performance
- Test parameter configurations
- Generate reference results

**Features:**
- Exact parameter matching with MicroC configs
- Same cell placement algorithms
- Same reaction rate calculations
- Independent verification of diffusion results

**Usage:**
```bash
python standalone_steadystate_fipy_3D.py
```

### 2. VTK-based State Simulation (deprecated HDF5 reader)

The previous H5-based FiPy simulator is deprecated. For state-based simulations or validations, use VTK domain exports and write small adapters to construct FiPy fields from VTK cell positions and phenotypes.

## Validation Workflow

### 1. Reference Validation
```bash
# Generate reference results
python standalone_steadystate_fipy_3D.py

# Compare with MicroC simulation
python run_sim.py tests/jayatilake_experiment/jayatilake_experiment_config.yaml --steps 1
```

### 2. State-Based Validation
- Export your state via VTK utilities and build a FiPy source field using those coordinates and phenotypes.

### 3. Temporal Evolution Analysis
- Generate VTK snapshots periodically (custom exporters) and analyze with your plotting tools.

## Expected Results

### Reference Implementation
- **Lactate**: 1.000022 - 2.643564 mM (production by proliferating cells)
- **Clear gradients**: Higher concentrations in cell-dense areas
- **Spatial patterns**: Radial diffusion from cell cluster

### H5 State Simulation
- **Initial State**: All cells Proliferation phenotype
  - Lactate: ~1.000 - 1.162 mM
- **Evolved State**: Mixed phenotypes (Growth_Arrest + Proliferation)
  - Lactate: ~1.000 - 1.096 mM (reduced due to fewer proliferating cells)
- **Oxygen/Glucose**: Consumption patterns based on phenotype distribution

## Performance Benchmarks

### Typical Performance (1000 cells, 25×25×25 grid)
- **File Loading**: < 1 second
- **Cell Mapping**: < 1 second  
- **FiPy Solving**: 2-5 seconds per substance
- **Visualization**: 1-2 seconds
- **Total Runtime**: 5-15 seconds

### Memory Usage
- **H5 File**: ~300 KB (1000 cells, 107 genes)
- **FiPy Mesh**: ~50 MB (25×25×25 grid)
- **Peak Memory**: ~100-200 MB

## Validation Criteria

### ✅ Successful Validation
- Cell mapping: 100% cells mapped to grid
- Concentration gradients: Clear spatial patterns
- Mass conservation: Realistic concentration ranges
- Phenotype effects: Different rates for different phenotypes
- Temporal consistency: Logical evolution patterns

### ❌ Failed Validation
- Zero cell mapping (coordinate conversion issues)
- Uniform concentrations (no gradients)
- Negative concentrations (solver instability)
- Unrealistic values (parameter errors)

## Troubleshooting

### Common Issues

**1. No cells mapped (0/1000)**
- Check coordinate conversion
- Verify domain size vs cell positions
- Ensure H5 file contains valid position data

**2. Uniform concentrations**
- Check reaction rates
- Verify source field calculation
- Ensure boundary conditions are correct

**3. Negative concentrations**
- Reduce reaction rates
- Check solver tolerance
- Verify mesh resolution

**4. File loading errors**
- Check H5 file integrity
- Verify file format compatibility
- Ensure all required datasets exist

### Debug Commands
```bash
# Check H5 file structure
python tools/quick_inspect.py file.h5

# Detailed analysis
python tools/cell_state_analyzer.py file.h5 --detailed-cells 5

# Visualize cell positions
python tools/simple_visualizer.py file.h5 --positions-3d
```

## Integration with MicroC

The H5 reader integrates seamlessly with MicroC's initial state system:

1. **Generate States**: Use MicroC with `save_initial_state: true`
2. **Validate States**: Use H5 reader to verify diffusion behavior
3. **Analyze Evolution**: Use periodic saves with `save_cellstate_interval`
4. **Compare Results**: Cross-validate with reference implementation

This provides a complete validation and analysis pipeline for MicroC simulations.

## Requirements

- Python 3.7+
- FiPy
- h5py
- numpy
- matplotlib
- pathlib

## Output Files

- **Plots**: PNG images showing concentration fields with cell positions
- **Console**: Detailed simulation statistics and validation metrics
- **Directory**: `h5_simulation_results/` (default output location)

The benchmark suite ensures MicroC's accuracy and provides tools for detailed analysis of simulation results.
