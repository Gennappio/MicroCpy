# Custom Functions Guide

## Overview

MicroC supports custom functions to modify simulation behaviors like cell metabolism, division conditions, and gene network updates. This guide shows how to use the existing custom function system with practical examples.

## How Custom Functions Work

Custom functions are Python functions that override default simulation behaviors. They are defined in a separate Python file and loaded via the configuration.

### Basic Structure

```python
# In your custom_functions.py file
def custom_calculate_cell_metabolism(local_environment, cell_state):
    """Override default metabolism calculation."""
    # Your custom logic here
    return {
        'oxygen_consumption_rate': 1.0e-17,
        'glucose_consumption_rate': 0.5e-17,
        'lactate_production_rate': 0.3e-17
    }
```

### Available Custom Functions
- `custom_calculate_cell_metabolism` - Cell metabolism rates
- `custom_should_divide` - Cell division conditions
- `custom_check_cell_division` - Additional division checks
- `custom_update_phenotype` - Phenotype transitions

## Example 1: Custom Metabolism Based on Phenotype

```python
# custom_functions.py
def custom_calculate_cell_metabolism(local_environment, cell_state):
    """Calculate metabolism rates based on cell phenotype and environment."""

    phenotype = cell_state.get('phenotype', 'Growth_Arrest')
    oxygen = local_environment.get('oxygen', 0.21)  # Default atmospheric oxygen
    glucose = local_environment.get('glucose', 5.0)  # Default glucose level

    if phenotype == "Proliferation":
        # High metabolic activity for proliferating cells
        return {
            'oxygen_consumption_rate': 2.0e-17 * min(oxygen/0.1, 1.0),
            'glucose_consumption_rate': 1.5e-17 * min(glucose/1.0, 1.0),
            'lactate_production_rate': 0.8e-17
        }
    elif phenotype == "Apoptosis":
        # Reduced metabolism for dying cells
        return {
            'oxygen_consumption_rate': 0.2e-17,
            'glucose_consumption_rate': 0.1e-17,
            'lactate_production_rate': 0.05e-17
        }
    else:  # Growth_Arrest or other
        # Baseline metabolism
        return {
            'oxygen_consumption_rate': 0.8e-17,
            'glucose_consumption_rate': 0.4e-17,
            'lactate_production_rate': 0.2e-17
        }
```

## Example 2: Custom Division Conditions

```python
def custom_should_divide(cell, config) -> bool:
    """Custom cell division logic with multiple conditions."""

    # Basic phenotype check
    if cell.state.phenotype != "Proliferation":
        return False

    # Age requirement
    cell_cycle_time = config.get('cell_cycle_time', 240)
    if cell.state.age < cell_cycle_time:
        return False

    # Space availability check (simple version)
    if hasattr(cell.state, 'local_density'):
        max_density = config.get('max_local_density', 0.8)
        if cell.state.local_density > max_density:
            return False

    # Energy requirement
    if hasattr(cell.state, 'atp_level'):
        min_atp = config.get('min_atp_for_division', 0.7)
        if cell.state.atp_level < min_atp:
            return False

    return True

def custom_check_cell_division(cell, config) -> bool:
    """Additional checks before division proceeds."""

    # Check if cell has enough resources
    if hasattr(cell.state, 'glucose_level'):
        min_glucose = config.get('min_glucose_for_division', 0.5)
        if cell.state.glucose_level < min_glucose:
            return False

    # Check oxygen availability
    if hasattr(cell.state, 'oxygen_level'):
        min_oxygen = config.get('min_oxygen_for_division', 0.1)
        if cell.state.oxygen_level < min_oxygen:
            return False

    return True
```

## Example 3: Custom Phenotype Transitions

```python
def custom_update_phenotype(cell, local_environment, config):
    """Custom logic for phenotype transitions based on environment and gene states."""

    current_phenotype = cell.state.phenotype
    gene_states = getattr(cell.state, 'gene_states', {})

    # Get environmental conditions
    oxygen = local_environment.get('oxygen', 0.21)
    glucose = local_environment.get('glucose', 5.0)

    # Stress conditions
    hypoxic = oxygen < 0.05
    glucose_starved = glucose < 0.5

    # Gene-based decisions (if gene network is available)
    apoptosis_active = gene_states.get('Apoptosis', False)
    proliferation_active = gene_states.get('Proliferation', False)

    # Phenotype transition logic
    if apoptosis_active or (hypoxic and glucose_starved):
        return "Apoptosis"
    elif proliferation_active and oxygen > 0.1 and glucose > 1.0:
        return "Proliferation"
    elif hypoxic or glucose_starved:
        return "Growth_Arrest"
    else:
        # Default behavior - stay in current phenotype or go to growth arrest
        if current_phenotype in ["Apoptosis", "Necrosis"]:
            return current_phenotype  # Terminal states
        else:
            return "Growth_Arrest"  # Default safe state
```

## Example 4: Advanced Metabolism with Gene Network Integration

```python
def custom_calculate_cell_metabolism(local_environment, cell_state):
    """Advanced metabolism calculation using gene network states."""

    # Get gene states if available
    gene_states = getattr(cell_state, 'gene_states', {})

    # Base metabolic rates
    base_oxygen = 1.0e-17
    base_glucose = 0.8e-17
    base_lactate = 0.4e-17

    # Environmental factors
    oxygen = local_environment.get('oxygen', 0.21)
    glucose = local_environment.get('glucose', 5.0)

    # Gene-based modulation
    if gene_states.get('mitoATP', False):
        # Mitochondrial respiration active - high oxygen consumption
        oxygen_rate = base_oxygen * 2.0 * min(oxygen/0.1, 1.0)
        glucose_rate = base_glucose * 1.5 * min(glucose/1.0, 1.0)
        lactate_rate = base_lactate * 0.5  # Less lactate in OXPHOS
    elif gene_states.get('glycoATP', False):
        # Glycolysis active - high glucose consumption, more lactate
        oxygen_rate = base_oxygen * 0.5
        glucose_rate = base_glucose * 2.0 * min(glucose/1.0, 1.0)
        lactate_rate = base_lactate * 2.0  # More lactate in glycolysis
    else:
        # Default metabolism
        oxygen_rate = base_oxygen * min(oxygen/0.1, 1.0)
        glucose_rate = base_glucose * min(glucose/1.0, 1.0)
        lactate_rate = base_lactate

    # Phenotype modulation
    phenotype = cell_state.get('phenotype', 'Growth_Arrest')
    if phenotype == "Proliferation":
        oxygen_rate *= 1.5
        glucose_rate *= 1.8
        lactate_rate *= 1.3
    elif phenotype == "Apoptosis":
        oxygen_rate *= 0.3
        glucose_rate *= 0.2
        lactate_rate *= 0.1

    return {
        'oxygen_consumption_rate': oxygen_rate,
        'glucose_consumption_rate': glucose_rate,
        'lactate_production_rate': lactate_rate
    }
```

## How to Use Custom Functions

### Step 1: Create Your Custom Functions File

Create a Python file (e.g., `my_custom_functions.py`) with your custom functions:

```python
# my_custom_functions.py

def custom_calculate_cell_metabolism(local_environment, cell_state):
    """Your custom metabolism logic here."""
    phenotype = cell_state.get('phenotype', 'Growth_Arrest')

    if phenotype == "Proliferation":
        return {
            'oxygen_consumption_rate': 2.0e-17,
            'glucose_consumption_rate': 1.5e-17,
            'lactate_production_rate': 0.8e-17
        }
    else:
        return {
            'oxygen_consumption_rate': 0.8e-17,
            'glucose_consumption_rate': 0.4e-17,
            'lactate_production_rate': 0.2e-17
        }

def custom_should_divide(cell, config) -> bool:
    """Your custom division logic here."""
    if cell.state.phenotype != "Proliferation":
        return False

    cell_cycle_time = config.get('cell_cycle_time', 240)
    return cell.state.age >= cell_cycle_time
```

### Step 2: Configure Your Simulation

In your YAML configuration file, specify the custom functions module:

```yaml
# config.yaml
simulation:
  custom_functions_module: "my_custom_functions"  # Name of your Python file (without .py)

population:
  cell_cycle_time: 240
  max_local_density: 0.8
  min_atp_for_division: 0.7

gene_network:
  bnd_file: "path/to/your/network.bnd"
  propagation_steps: 3
  random_initialization: true
```

### Step 3: Run Your Simulation

```python
# run_simulation.py
from simulation.simulation import Simulation
from config.config_loader import load_config

# Load configuration
config = load_config("config.yaml")

# Create and run simulation
sim = Simulation(config)
sim.run(num_steps=1000)
```

## Available Parameters in Custom Functions

### In `custom_calculate_cell_metabolism`:
- `local_environment`: Dict with 'oxygen', 'glucose', 'lactate', etc.
- `cell_state`: Object with 'phenotype', 'age', 'gene_states', etc.

### In `custom_should_divide`:
- `cell`: Cell object with state information
- `config`: Configuration parameters

### In `custom_update_phenotype`:
- `cell`: Cell object with current state
- `local_environment`: Environmental conditions
- `config`: Configuration parameters

## Tips for Writing Custom Functions

1. **Always return the expected data type** (dict for metabolism, bool for division, string for phenotype)
2. **Handle missing data gracefully** using `.get()` with defaults
3. **Test your functions** with simple cases first
4. **Use meaningful variable names** and add comments
5. **Check the existing examples** in `src/config/custom_functions.py` for reference

This system allows you to customize MicroC behavior for your specific research needs while keeping the core simulation engine intact.
