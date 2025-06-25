# OSP: Metabolism Improvements - Jayathilake et al. 2024 Implementation

## Overview

This document describes the metabolism improvements implemented in the Jayathilake experiment custom functions, based on the metabolic symbiosis model from Jayathilake et al. 2024 (journal.pcbi.1011944).

## Key Improvements

### 1. **YAML Configuration Integration**

**Problem**: Previously, metabolism parameters were hardcoded in the custom function.

**Solution**: All metabolism parameters now come from the YAML configuration file under the `metabolism` section.

**Benefits**:
- Easy parameter tuning without code changes
- Consistent parameter management
- Better reproducibility and documentation

### 2. **Metabolism Exceptions Implementation**

Based on the article (pages 5-7), we implemented five key metabolism exceptions:

#### Exception 1: Glucose Depletion Forces Lactate Metabolism
- **Trigger**: Local glucose < `glucose_depletion_threshold` (default: 0.05 mM)
- **Effect**: Cells switch to lactate-fueled OXPHOS even if glucose transporters are active
- **Biological Rationale**: Cells adapt to glucose scarcity by utilizing available lactate

#### Exception 2: Lactate Saturation Inhibits Glycolysis
- **Trigger**: Local lactate > `lactate_saturation_threshold` (default: 8.0 mM)
- **Effect**: Reduces glycolytic activity (50% glucose consumption, 30% lactate production)
- **Biological Rationale**: High lactate levels create feedback inhibition

#### Exception 3: Oxygen-Dependent Metabolic Switching
- **Trigger**: Local oxygen < `oxygen_switch_threshold` (default: 0.015 mM)
- **Effect**: Forces glycolysis even if OXPHOS genes are active
- **Biological Rationale**: Hypoxic conditions prevent mitochondrial respiration

#### Exception 4: pH Inhibition
- **Trigger**: Local H+ > `ph_inhibition_threshold` (default: 1e-4 mM)
- **Effect**: Inhibits all metabolic pathways
- **Biological Rationale**: Extreme acidosis disrupts cellular metabolism

#### Exception 5: Metabolic Rescue
- **Trigger**: When both OXPHOS and glycolysis fail but nutrients are available
- **Effect**: Minimal survival metabolism (10% of normal rates)
- **Biological Rationale**: Cells maintain basic survival functions

## Configuration Parameters

### Base Rates (per cell per time step)
```yaml
metabolism:
  base_oxygen_consumption: 0.001      # Base oxygen consumption rate
  base_glucose_consumption: 0.01      # Base glucose consumption rate  
  base_lactate_production: 0.008      # Base lactate production rate
  base_lactate_consumption: 0.005     # Base lactate consumption rate
  base_h_production: 0.0001           # Base H+ production rate
  base_h_consumption: 0.00005         # Base H+ consumption rate
```

### Metabolic Thresholds
```yaml
  min_glucose_for_glycolysis: 0.1     # Minimum glucose needed for glycolysis
  min_oxygen_for_oxphos: 0.01         # Minimum oxygen needed for OXPHOS
  min_lactate_for_consumption: 0.1    # Minimum lactate needed for consumption
```

### Exception Thresholds
```yaml
  glucose_depletion_threshold: 0.05   # Below this, switch to lactate metabolism
  lactate_saturation_threshold: 8.0   # Above this, lactate inhibits glycolysis
  oxygen_switch_threshold: 0.015      # Oxygen level for metabolic switching
  ph_inhibition_threshold: 6.5        # pH below which metabolism is inhibited
```

## Metabolic Pathways

### OXPHOS Pathway (Oxygen Available)
1. **Lactate-fueled OXPHOS** (preferred when glucose depleted or MCT1 active):
   - Consumes: Lactate, Oxygen
   - Produces: Minimal glucose consumption
   - Consumes: H+ (alkalinization)

2. **Glucose-fueled OXPHOS** (when lactate not saturated):
   - Consumes: Glucose, Oxygen, H+
   - Produces: Minimal lactate

### Glycolysis Pathway (Hypoxic or Gene-driven)
1. **Normal Glycolysis**:
   - Consumes: Glucose (1.5x rate), minimal oxygen
   - Produces: Lactate, H+ (acidification)

2. **Inhibited Glycolysis** (lactate saturated):
   - Reduced rates: 50% glucose consumption, 30% lactate production

### Environmental Constraints
- **Safety margins**: Never consume more than 90% of available substrate
- **Substrate availability**: Metabolism scales down if substrates are limited
- **Transporter dependency**: MCT1/MCT4 and GLUT1 gates affect pathway selection

## Gene Network Integration

The metabolism function integrates with the Boolean gene network:
- **mitoATP**: Enables OXPHOS pathway
- **glycoATP**: Enables glycolysis pathway  
- **GLUT1**: Required for glucose consumption
- **MCT1**: Enables lactate consumption
- **MCT4**: Enhances lactate export (1.2x multiplier)
- **Necrosis**: Completely shuts down metabolism

## Usage Example

```python
# The function is automatically called by the simulation framework
reactions = custom_calculate_cell_metabolism(
    local_environment={'Oxygen': 0.02, 'Glucose': 0.8, 'Lactate': 6.0, 'H': 5e-5},
    cell_state={'gene_states': {'mitoATP': True, 'MCT1': True, 'GLUT1': True}}
)

# Expected result: Lactate-fueled OXPHOS due to glucose depletion exception
# reactions = {'Lactate': -0.005, 'Oxygen': -0.003, 'H': -0.00005, 'Glucose': -0.001, ...}
```

## Testing and Validation

The improved metabolism function has been tested with:
- ✅ Configuration parameter loading
- ✅ Gene network integration
- ✅ Environmental constraint handling
- ✅ Exception pathway triggering
- ✅ Substance consumption/production balance

## References

Jayathilake, P.G., et al. (2024). Metabolic symbiosis between oxygenated and hypoxic tumour cells: An agent-based modelling study. PLOS Computational Biology, 20(3), e1011944.
