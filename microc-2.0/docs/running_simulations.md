# MicroC Simulation Guide

## Overview

MicroC is a multi-scale cellular simulation platform that integrates gene networks, metabolism, and spatial dynamics. This guide covers how to set up and run simulations.

## Quick Start

### Basic Simulation
```bash
python run_sim.py config.yaml --steps 100
```

### With Visualization
```bash
python run_sim.py config.yaml --steps 100 --plot
```

## Configuration Structure

### Main Configuration File (YAML)
```yaml
# Basic simulation parameters
simulation:
  grid_size: [50, 50]
  time_step: 0.1
  total_time: 10.0

# Cell population settings
population:
  initial_count: 100
  initial_phenotype: "Proliferation"

# Gene network configuration
gene_network:
  bnd_file: "path/to/network.bnd"
  propagation_steps: 50
  random_initialization: true

# Substance diffusion
substances:
  Oxygen:
    diffusion_coeff: 2.0e-9
    initial_value: 0.21
    boundary_value: 0.21
    boundary_type: "fixed"
  Glucose:
    diffusion_coeff: 6.7e-10
    initial_value: 5.0e-3
    boundary_value: 5.0e-3
    boundary_type: "fixed"

# Gene-substance associations
associations:
  Oxygen: "Oxygen_supply"
  Glucose: "Glucose_supply"
```

## Gene Network Setup

### BND File Format
Gene networks are defined in Boolean Network Description (.bnd) files:

```
node Apoptosis {
  logic = ! BCL2 & ! ERK & FOXO3 & p53;
  rate_up = @logic ? 1 : 0;
  rate_down = @logic ? 0 : 1;
}

node BCL2 {
  logic = CREB & AKT;
  rate_up = @logic ? 1 : 0;
  rate_down = @logic ? 0 : 1;
}

node Oxygen_supply {
  rate_up = 0;
  rate_down = 0;
}
```

### Input Nodes
Input nodes represent environmental conditions:
- Set `rate_up = 0; rate_down = 0;` for input nodes
- Map to substances via associations in config
- Control via substance concentrations

### Gene Network Parameters
```yaml
gene_network:
  bnd_file: "network.bnd"
  propagation_steps: 50        # NetLogo-style sparse updates
  random_initialization: true  # 50% chance for non-fate genes
  output_nodes: ["Apoptosis", "Proliferation", "Growth_Arrest"]
```

## Substance Configuration

### Diffusion Parameters
```yaml
substances:
  SubstanceName:
    diffusion_coeff: 1.0e-9     # m/s
    production_rate: 1.0e-18    # mol/cell/s
    uptake_rate: 1.0e-18        # mol/cell/s
    initial_value: 1.0e-6       # M (molarity)
    boundary_value: 1.0e-6      # M
    boundary_type: "fixed"      # "fixed" or "no_flux"
    unit: "M"
```

### Growth Factors
```yaml
substances:
  EGF:
    diffusion_coeff: 2.2e-10
    initial_value: 2.0e-6       # Present for survival
    boundary_value: 2.0e-6
    boundary_type: "fixed"
  FGF:
    diffusion_coeff: 2.2e-10
    initial_value: 2.0e-6
    boundary_value: 2.0e-6
    boundary_type: "fixed"
```

## Running Experiments

### Command Line Options
```bash
python run_sim.py config.yaml [options]

Options:
  --steps N          Number of simulation steps
  --output DIR       Output directory
  --plot            Generate plots
  --verbose         Detailed logging
  --seed N          Random seed for reproducibility
```

### Batch Experiments
```bash
# Run multiple configurations
for config in configs/*.yaml; do
    python run_sim.py "$config" --steps 100 --output "results/$(basename $config .yaml)"
done
```

### Parameter Sweeps
```python
# Python script for parameter sweeps
import yaml
import subprocess

base_config = yaml.load(open('base_config.yaml'))

for egf_conc in [0, 1e-6, 2e-6, 5e-6]:
    config = base_config.copy()
    config['substances']['EGF']['initial_value'] = egf_conc
    
    with open(f'config_egf_{egf_conc:.0e}.yaml', 'w') as f:
        yaml.dump(config, f)
    
    subprocess.run(['python', 'run_sim.py', f'config_egf_{egf_conc:.0e}.yaml', '--steps', '100'])
```

## Output Analysis

### Generated Files
- `population_stats.csv` - Cell counts by phenotype over time
- `substance_fields/` - Concentration fields at each time step
- `plots/` - Visualization outputs
- `gene_network_states.csv` - Gene expression data

### Data Structure
```csv
# population_stats.csv
time,Proliferation,Apoptosis,Growth_Arrest,Quiescent,total
0.0,100,0,0,0,100
0.1,98,2,0,0,100
0.2,95,3,2,0,100
```

## Troubleshooting

### Common Issues

**High Apoptosis Rates**
- Check gene network propagation_steps (use 10-50)
- Ensure growth factors are present
- Verify fate nodes start as False

**Simulation Crashes**
- Check substance diffusion coefficients (not too large)
- Verify BND file syntax
- Ensure all associations are defined

**Slow Performance**
- Reduce grid size
- Decrease propagation_steps
- Use fewer substances

### Debug Mode
```bash
python run_sim.py config.yaml --verbose --steps 1
```

## Example Configurations

### Survival Conditions
```yaml
substances:
  Oxygen: {initial_value: 0.21, boundary_value: 0.21}
  Glucose: {initial_value: 5.0e-3, boundary_value: 5.0e-3}
  EGF: {initial_value: 2.0e-6, boundary_value: 2.0e-6}
  FGF: {initial_value: 2.0e-6, boundary_value: 2.0e-6}
  HGF: {initial_value: 2.0e-6, boundary_value: 2.0e-6}

gene_network:
  propagation_steps: 50
  random_initialization: true
```

### Stress Conditions
```yaml
substances:
  Oxygen: {initial_value: 0.05, boundary_value: 0.05}  # Hypoxia
  Glucose: {initial_value: 1.0e-3, boundary_value: 1.0e-3}  # Low glucose
  EGF: {initial_value: 0.0, boundary_value: 0.0}  # No growth factors
```

### Drug Treatment
```yaml
substances:
  EGFRD: {initial_value: 1.0e-6, boundary_value: 1.0e-6}  # EGFR inhibitor
  
associations:
  EGFRD: "EGFRI"  # Maps to gene network inhibitor node
```
