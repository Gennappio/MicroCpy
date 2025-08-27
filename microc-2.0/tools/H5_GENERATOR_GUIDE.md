# H5 File Generator Guide

## 🎯 Overview

The H5 Generator (`h5_generator.py`) creates custom cell state files for MicroC simulations. It allows you to generate synthetic cell populations with precise control over spatial distribution, cell numbers, and gene network activation patterns.

## 🚀 Quick Start

```bash
# Create example gene probabilities file
python tools/h5_generator.py --create-example

# Generate 1000 cells with default settings
python run_microc.py --generate --cells 1000 --radius 50

# Generate sparse cells concentrated at sphere border
python run_microc.py --generate --cells 500 --radius 30 --sparseness 0.7 --radial 0.9
```

## 📋 Parameters

### 🔢 **Cell Parameters**
- **`--cells`**: Number of cells to generate (default: 1000)
- **`--size`**: Cell size in micrometers (default: 5.0 μm)

### 🌐 **Spatial Distribution**
- **`--radius`**: Radius of enclosing sphere in micrometers (default: 50.0 μm)
- **`--sparseness`**: Overall sparseness (0.0 = dense, 1.0 = very sparse, default: 0.3)
- **`--radial`**: Radial distribution (0.0 = center, 0.5 = balanced, 1.0 = border, default: 0.5)

### 🧬 **Gene Network**
- **`--gene-probs`**: Text file with gene activation probabilities (default: gene_probs.txt)

### 📁 **Output**
- **`--output`**: Output file prefix (default: generated_cells)

## 📝 Gene Probabilities File Format

Create a text file with gene activation probabilities:

```txt
# Gene Network Node Activation Probabilities
# Format: gene_name probability

# Supply nodes (usually high activation)
Oxygen_supply 0.8
Glucose_supply 0.9
MCT1_stimulus 0.6
Proton_level 0.4
FGFR_stimulus 0.3
EGFR_stimulus 0.2

# Metabolic nodes
Glycolysis 0.7
OXPHOS 0.5
ATP 0.8

# Fate nodes (usually lower activation)
Proliferation 0.3
Apoptosis 0.1
Growth_Arrest 0.2
```

**Rules:**
- Lines starting with `#` are comments
- Format: `gene_name probability`
- Probability must be between 0.0 and 1.0
- Missing genes default to 0.5 probability

## 🎨 Spatial Distribution Examples

### Balanced Distribution (radial = 0.5)
```bash
python run_microc.py --generate --cells 1000 --radius 50 --radial 0.5
```
- Cells evenly distributed throughout sphere
- Natural-looking cell population

### Center-Concentrated (radial = 0.1)
```bash
python run_microc.py --generate --cells 1000 --radius 50 --radial 0.1
```
- Most cells near sphere center
- Useful for testing core vs periphery effects

### Border-Concentrated (radial = 0.9)
```bash
python run_microc.py --generate --cells 1000 --radius 50 --radial 0.9
```
- Most cells near sphere surface
- Simulates surface growth patterns

### Sparse vs Dense
```bash
# Dense population (sparseness = 0.1)
python run_microc.py --generate --cells 1000 --sparseness 0.1

# Sparse population (sparseness = 0.8)
python run_microc.py --generate --cells 1000 --sparseness 0.8
```

## 📊 Output Files

The generator creates three files:

### 1. **Cell States H5** (`generated_cells_TIMESTAMP.h5`)
Main file compatible with all MicroC tools:
```
/metadata/          # File metadata
/cells/            # Cell data (positions, phenotypes, ages, etc.)
/gene_states/      # Gene activation states (gene_names, states matrix)
```

### 2. **Gene States H5** (`generated_cells_gene_states_TIMESTAMP.h5`)
Detailed gene states per cell:
```
/gene_states/
  /cell_000001/    # Individual cell gene states
  /cell_000002/
  ...
```

### 3. **Summary JSON** (`generated_cells_summary_TIMESTAMP.json`)
Statistical summary:
```json
{
  "generation_info": {...},
  "cell_statistics": {
    "total_cells": 1000,
    "phenotype_counts": {...}
  },
  "gene_statistics": {...}
}
```

## 🔬 Usage Examples

### Example 1: Test Different Cell Densities
```bash
# Dense tumor core
python run_microc.py --generate --cells 2000 --radius 30 --sparseness 0.1 --output dense_core

# Sparse periphery  
python run_microc.py --generate --cells 500 --radius 50 --sparseness 0.8 --output sparse_periphery
```

### Example 2: Gene Expression Gradients
Create `hypoxic_genes.txt`:
```txt
Oxygen_supply 0.2
Glucose_supply 0.9
Glycolysis 0.9
OXPHOS 0.1
Proliferation 0.1
Apoptosis 0.4
```

```bash
python run_microc.py --generate --cells 1000 --gene-probs hypoxic_genes.txt --output hypoxic_tumor
```

### Example 3: Size Scaling Study
```bash
# Small sphere
python run_microc.py --generate --cells 200 --radius 20 --output small_sphere

# Medium sphere
python run_microc.py --generate --cells 1000 --radius 40 --output medium_sphere

# Large sphere
python run_microc.py --generate --cells 5000 --radius 80 --output large_sphere
```

## 🔧 Integration with MicroC Tools

### Visualization
```bash
# Generate and visualize
python run_microc.py --generate --cells 1000 --radius 50
python run_microc.py --visualize generated_cells_TIMESTAMP.h5

# Or use convenience command
python run_microc.py --generate --cells 1000 --radius 50
python run_microc.py --all-viz generated_cells_TIMESTAMP.h5
```

### FiPy Simulation
```bash
# Generate cells and run physics simulation
python run_microc.py --generate --cells 1000 --radius 50
python run_microc.py --fipy generated_cells_TIMESTAMP.h5
```

### Analysis
```bash
# Generate and analyze
python run_microc.py --generate --cells 1000 --radius 50
python run_microc.py --analyze generated_cells_TIMESTAMP.h5
```

## 🎯 Best Practices

### 1. **Start Small**
```bash
# Test with small populations first
python run_microc.py --generate --cells 100 --radius 20
```

### 2. **Use Meaningful Names**
```bash
python run_microc.py --generate --cells 1000 --output tumor_core_dense
```

### 3. **Document Gene Probabilities**
Always comment your gene probability files:
```txt
# Hypoxic tumor core conditions
# Based on experimental data from Smith et al. 2023
Oxygen_supply 0.1  # Low oxygen availability
```

### 4. **Validate Results**
```bash
# Always visualize generated data
python run_microc.py --all-viz your_generated_file.h5
```

## 🐛 Troubleshooting

### Common Issues

#### "Gene probabilities file not found"
```bash
# Create example file first
python tools/h5_generator.py --create-example
cp example_gene_probs.txt my_genes.txt
# Edit my_genes.txt as needed
python run_microc.py --generate --gene-probs my_genes.txt
```

#### "Too few cells generated"
- Increase `--cells` parameter
- Decrease `--sparseness` parameter
- Check sphere `--radius` is appropriate

#### "Cells too concentrated"
- Adjust `--radial` parameter (0.5 for balanced)
- Increase `--sparseness` for more spread

## 🔗 Related Tools

- **Visualizer**: `python run_microc.py --visualize file.h5`
- **Analyzer**: `python run_microc.py --analyze file.h5`
- **FiPy Simulator**: `python run_microc.py --fipy file.h5`
- **Inspector**: `python run_microc.py --inspect file.h5`

The H5 Generator provides complete control over synthetic cell populations for testing, validation, and research!
