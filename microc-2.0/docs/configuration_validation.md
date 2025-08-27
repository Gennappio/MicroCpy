# Configuration Validation Guide

MicroC 2.0 includes comprehensive configuration validation that checks for missing or invalid parameters before running simulations. This prevents common configuration errors and provides helpful guidance.

## How Validation Works

The validation system operates in two phases:

### 1. YAML Loading Validation
- Checks for required sections and parameters during YAML parsing
- Validates YAML syntax and structure
- Provides specific error messages for missing required parameters

### 2. Custom Logic Validation
- Validates parameter values and relationships
- Checks for reasonable ranges and constraints
- Verifies file paths and dependencies

## Required Configuration Sections

### Domain Section (Required)
```yaml
domain:
  size_x: 800.0           # Domain width
  size_x_unit: "um"       # Units for width
  size_y: 800.0           # Domain height  
  size_y_unit: "um"       # Units for height
  nx: 40                  # Grid cells in x direction
  ny: 40                  # Grid cells in y direction
  dimensions: 2           # Spatial dimensions (2D)
  cell_height: 20.0       # Cell thickness
  cell_height_unit: "um"  # Units for thickness
```

**Validation Checks:**
- `size_x`, `size_y`, `nx`, `ny` must be present and positive
- Grid spacing (size/n) must be between 1-50 um
- Grid must be square (dx = dy)

### Time Section (Required)
```yaml
time:
  dt: 0.01                    # Time step size
  end_time: 2.0              # Total simulation time
  diffusion_step: 5          # Diffusion update interval
  intracellular_step: 1      # Intracellular update interval
  intercellular_step: 10     # Intercellular update interval
```

**Validation Checks:**
- All time parameters must be present and positive
- `dt` and `end_time` must be greater than 0

### Substances Section (Required)
```yaml
substances:
  Oxygen:
    diffusion_coeff: 2.1e-9    # m/s (must be non-negative)
    initial_value: 0.21        # mM (initial concentration)
    boundary_value: 0.21       # mM (boundary concentration)
    boundary_type: "fixed"     # Boundary condition type
    production_rate: 0.0       # mol/s/cell
    uptake_rate: 3.0e-17      # mol/s/cell
```

**Validation Checks:**
- At least one substance must be defined
- Each substance must have `diffusion_coeff`, `initial_value`, `boundary_value`
- `diffusion_coeff` must be non-negative
- `boundary_type` defaults to "fixed" if not specified

## Optional Configuration Sections

### Diffusion Section (Optional)
```yaml
diffusion:
  max_iterations: 1000
  tolerance: 1e-6
  solver_type: "steady_state"
  twodimensional_adjustment_coefficient: 1.0
```

### Gene Network Section (Optional)
```yaml
gene_network:
  bnd_file: "path/to/network.bnd"    # Path to Boolean network file
  propagation_steps: 3               # Gene update steps per simulation step
  random_initialization: true       # Random gene initialization
```

**Validation Checks:**
- If `bnd_file` is specified, file must exist (checked relative to config file)
- Warning if no gene network is configured

### Output Section (Optional)
```yaml
output:
  save_data_interval: 10        # Save data every N steps
  save_plots_interval: 50       # Generate plots every N steps
  save_final_plots: true        # Generate final plots
  save_initial_plots: true      # Generate initial plots
  status_print_interval: 10     # Print status every N steps
```

**Validation Checks:**
- `save_data_interval` must be positive if specified
- Uses defaults if section is missing

### Custom Functions (Optional)
```yaml
custom_functions_path: "path/to/custom_functions.py"
```

**Validation Checks:**
- If specified, file must exist (checked relative to config file)

## Error Messages and Help

### Missing Parameter Errors
```
[!] Configuration validation failed!
   Missing or invalid parameters:
   * domain.nx and domain.ny
   * substances.Oxygen.initial_value
   * time.end_time must be positive

[IDEA] Configuration Help:
   * Check example configurations in: tests/jayatilake_experiment/
   * See complete reference: src/config/complete_substances_config.yaml
   * Documentation: docs/running_simulations.md
   * Required sections: domain, time, substances
   * Optional sections: gene_network, associations, thresholds, output
```

### YAML Syntax Errors
```
[!] Failed to load configuration - Missing required parameter: 'nx'
   This parameter is required in your YAML configuration file.

[IDEA] Configuration Help:
   * Check example configurations in: tests/jayatilake_experiment/
   * See complete reference: src/config/complete_substances_config.yaml
   * Required sections: domain, time, substances
   * Each section has required parameters - see documentation
```

### Common Issues
```
[IDEA] Common issues:
   * YAML indentation must be consistent (use spaces, not tabs)
   * Missing required sections: domain, time, substances
   * Invalid YAML syntax (check colons, quotes, etc.)
```

## Example Configurations

### Minimal Valid Configuration
```yaml
domain:
  size_x: 800.0
  size_x_unit: "um"
  size_y: 800.0
  size_y_unit: "um"
  nx: 40
  ny: 40
  dimensions: 2

time:
  dt: 0.01
  end_time: 1.0
  diffusion_step: 5
  intracellular_step: 1
  intercellular_step: 10

substances:
  Oxygen:
    diffusion_coeff: 2.1e-9
    initial_value: 0.21
    boundary_value: 0.21
    boundary_type: "fixed"
    production_rate: 0.0
    uptake_rate: 3.0e-17
```

### Complete Configuration
See `src/config/complete_substances_config.yaml` for a full example with all optional sections.

## Testing Validation

To test the validation system:

```bash
# Test with incomplete configuration
python run_sim.py incomplete_config.yaml

# Test with valid configuration
python run_sim.py tests/jayatilake_experiment/jayatilake_experiment_config.yaml --steps 1
```

The validation system will catch errors early and provide helpful guidance for fixing configuration issues.
