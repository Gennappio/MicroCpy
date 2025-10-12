# CSV Initial State Format for 2D Simulations

The CSV format provides a human-readable alternative to VTK files for 2D simulations. It's easy to create, edit, and understand.

## When to Use CSV vs VTK

- **CSV**: Use for 2D simulations, especially when you want to manually create or edit cell positions
- **VTK**: Use for 3D simulations or complex 2D setups with extensive gene networks

## CSV File Format

### Basic Structure

```csv
# cell_size_um=20.0, domain_size_um=500.0, description="Example initial state"
x,y,phenotype,gene_mitoATP,gene_glycoATP,gene_Proliferation
12,12,Proliferation,true,false,true
13,12,Proliferation,true,false,true
11,12,Quiescent,false,true,false
```

### Required Columns

- **x**: Logical grid X coordinate (integer or float, will be rounded)
- **y**: Logical grid Y coordinate (integer or float, will be rounded)

### Optional Columns

- **phenotype**: Cell phenotype (e.g., "Proliferation", "Quiescent", "Apoptosis")
- **age**: Cell age in simulation time units
- **gene_<name>**: Gene states for all nodes in the gene network
  - Values: `true`/`false`, `1`/`0`, `yes`/`no`, `on`/`off`, `active`/`inactive`
  - **Complete Gene Networks**: When using `--genes` flag with .bnd file, all 100+ gene nodes are included
  - **Default**: Without .bnd file, only basic genes (mitoATP, glycoATP, Proliferation) are included
  - Examples: `gene_Proliferation`, `gene_Apoptosis`, `gene_mitoATP`, `gene_AKT`, `gene_ERK`

### Metadata Comment Line (Optional)

The first line can be a comment with metadata:

```csv
# cell_size_um=20.0, domain_size_um=500.0, description="Spheroid initial state"
```

Supported metadata:
- `cell_size_um`: Cell size in micrometers (overridden by YAML config)
- `domain_size_um`: Domain size in micrometers
- `description`: Human-readable description

## Coordinate System

CSV uses the same coordinate system as VTK:

1. **Logical Coordinates**: CSV x,y values are logical grid indices
2. **Physical Coordinates**: Calculated as `logical_position × cell_size_um`
3. **Cell Size**: Always taken from YAML configuration (`domain.cell_height`)

### Example

If CSV has `x=10, y=5` and YAML has `cell_height: 20 um`:
- Logical position: `(10, 5)`
- Physical position: `(200, 100) um`

## Creating CSV Files

### Method 1: Manual Creation

Create a simple CSV file in any text editor:

```csv
x,y,phenotype
10,10,Proliferation
11,10,Proliferation
10,11,Proliferation
11,11,Quiescent
```

### Method 2: CSV Generator Tool

Use the provided generator tool:

```bash
# Generate spheroid pattern (basic genes)
python tools/csv_cell_generator.py --output cells.csv --pattern spheroid --count 25

# Generate spheroid pattern with complete gene network from BND file
python tools/csv_cell_generator.py --output cells.csv --pattern spheroid --count 25 \
  --genes tests/jayatilake_experiment/jaya_microc.bnd

# Generate grid pattern
python tools/csv_cell_generator.py --output cells.csv --pattern grid --grid_size 5x5

# Generate random pattern
python tools/csv_cell_generator.py --output cells.csv --pattern random --count 30 --domain_size 25
```

**Master Runner (Recommended):**
```bash
# Basic spheroid with default genes
python run_microc.py --generate-csv --pattern spheroid --count 25 --output cells.csv

# Complete gene network from BND file (106 nodes)
python run_microc.py --generate-csv --pattern spheroid --count 25 \
  --genes tests/jayatilake_experiment/jaya_microc.bnd --output full_genes.csv

# Grid pattern with complete gene network
python run_microc.py --generate-csv --pattern grid --grid_size 5x5 \
  --genes tests/jayatilake_experiment/jaya_microc.bnd --output grid_full.csv
```

### Method 3: Python Script

```python
import csv

cells = [
    {'x': 12, 'y': 12, 'phenotype': 'Proliferation', 'gene_mitoATP': 'true'},
    {'x': 13, 'y': 12, 'phenotype': 'Proliferation', 'gene_glycoATP': 'true'},
    {'x': 11, 'y': 12, 'phenotype': 'Quiescent', 'gene_mitoATP': 'false'},
]

with open('cells.csv', 'w', newline='') as f:
    f.write('# cell_size_um=20.0, description="Custom cells"\n')
    writer = csv.DictWriter(f, fieldnames=['x', 'y', 'phenotype', 'gene_mitoATP', 'gene_glycoATP'])
    writer.writeheader()
    writer.writerows(cells)
```

## BND File Integration

The CSV generator can read complete gene networks from Boolean Network Description (.bnd) files:

### Using BND Files
```bash
# Generate CSV with all gene nodes from BND file
python run_microc.py --generate-csv --pattern spheroid --count 25 \
  --genes tests/jayatilake_experiment/jaya_microc.bnd --output full_genes.csv
```

### Gene Initialization Rules
- **All gene nodes**: Randomly initialized (50% chance true/false)
- **Phenotype nodes**: Start as false (Proliferation, Apoptosis, Growth_Arrest, Necrosis)
- **Pattern-specific**: Some genes adjusted based on cell position (e.g., core vs. outer cells)

### BND File Format
The system supports MaBoSS format .bnd files with node definitions:
```
node AKT {
  logic = (PI3K & !PTEN);
  rate_up = @logic ? 1 : 0;
  rate_down = @logic ? 0 : 1;
}
```

## Using CSV Files in Configuration

### YAML Configuration

```yaml
domain:
  dimensions: 2
  size_x: 500
  size_x_unit: "um"
  size_y: 500
  size_y_unit: "um"
  nx: 25
  ny: 25
  cell_height: 20
  cell_height_unit: "um"

initial_state:
  file_path: "cells.csv"  # Auto-detects CSV format
```

### Loading in Code

```python
from src.io.initial_state import InitialStateManager

manager = InitialStateManager(config)

# Auto-detect format based on file extension
cell_data, cell_size_um = manager.load_initial_state("cells.csv")

# Or explicitly load CSV
cell_data, cell_size_um = manager.load_initial_state_from_csv("cells.csv")
```

## Gene State Format

Gene states in CSV use the `gene_` prefix:

```csv
x,y,gene_mitoATP,gene_glycoATP,gene_Proliferation,gene_Apoptosis
10,10,true,false,true,false
11,10,false,true,true,false
```

Boolean values are parsed as:
- **True**: `true`, `1`, `yes`, `on`, `active`
- **False**: `false`, `0`, `no`, `off`, `inactive` (case-insensitive)

## Validation and Error Handling

The CSV loader performs validation:

1. **Required columns**: `x` and `y` must be present
2. **Coordinate bounds**: Positions are clamped to valid grid bounds
3. **Data types**: Invalid coordinates are skipped with warnings
4. **Gene states**: Invalid boolean values default to `false`

## Examples

### Simple Spheroid

```csv
x,y,phenotype
12,12,Proliferation
13,12,Proliferation
11,12,Proliferation
12,13,Proliferation
12,11,Proliferation
```

### With Gene Networks

```csv
# cell_size_um=20.0, description="Metabolic heterogeneity test"
x,y,phenotype,gene_mitoATP,gene_glycoATP,gene_Proliferation
12,12,Proliferation,true,false,true
13,12,Proliferation,false,true,true
11,12,Proliferation,true,true,true
12,13,Quiescent,false,false,false
```

### Large Population

For larger populations, use the generator tool or write a script to create systematic patterns.

## Migration from VTK

To convert existing VTK workflows to CSV:

1. **Extract positions**: Use VTK tools to export cell positions
2. **Convert coordinates**: VTK logical coordinates map directly to CSV x,y
3. **Add gene states**: Use `gene_` prefix for gene network states
4. **Set phenotypes**: Map VTK phenotype scalars to CSV phenotype column

## Performance

CSV loading is optimized for typical 2D simulation sizes (hundreds to thousands of cells). For very large populations or complex gene networks, VTK format may be more efficient.
