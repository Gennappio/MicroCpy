# Jayatilake Metabolic Symbiosis Experiment

This experiment replicates the computational model from:

**Jayatilake et al. "A computational model of metabolic symbiosis in cancer"**  
*PLOS Computational Biology* (2024)

## Overview

The Jayatilake experiment models metabolic symbiosis in cancer cell populations, where cells with different metabolic states (glycolytic vs. oxidative phosphorylation) create a cooperative ecosystem. This leads to enhanced tumor growth and survival under nutrient stress conditions.

## Key Features

### 🧬 **Metabolic States**
The model implements 4 distinct metabolic phenotypes:

1. **Glycolysis Only** (Green cells)
   - `glycoATP=True, mitoATP=False`
   - High glucose consumption, lactate production
   - Survives in hypoxic conditions

2. **OXPHOS Only** (Blue cells)
   - `glycoATP=False, mitoATP=True`
   - High oxygen consumption, lactate consumption
   - Efficient ATP production in normoxic conditions

3. **Quiescent** (Gray cells)
   - `glycoATP=False, mitoATP=False`
   - Minimal metabolism
   - Survival mode under stress

4. **Mixed Metabolism** (Violet cells)
   - `glycoATP=True, mitoATP=True`
   - Flexible metabolism
   - Adapts to changing conditions

### 🔄 **Metabolic Symbiosis**
- **Glycolytic cells** produce lactate that **OXPHOS cells** can consume
- **OXPHOS cells** consume oxygen, creating hypoxic niches for glycolytic cells
- This creates a **cooperative ecosystem** that enhances overall tumor survival

### 🧪 **Substances Modeled**
- **Oxygen**: Essential for OXPHOS, creates hypoxic gradients (→ Oxygen_supply)
- **Glucose**: Primary fuel for glycolysis (→ Glucose_supply)
- **Lactate**: Waste product of glycolysis, fuel for OXPHOS (→ MCT1_stimulus)
- **H+ (Protons)**: Acidification from lactate production (→ Proton_level)
- **Growth Factors**: FGF (→ FGFR_stimulus), TGFA (→ EGFR_stimulus), HGF (→ cMET_stimulus)

## Configuration

### **Spatial Setup**
- **Domain**: 400×400 μm (40×40 grid)
- **Initial cells**: 100 cells in spheroid configuration
- **Boundary conditions**: Fixed concentrations at edges

### **Temporal Dynamics**
Multi-timescale orchestration:
- **Intracellular processes**: Every step (0.1 time units)
  - Gene network updates
  - Metabolic state changes
  - Phenotype transitions
- **Diffusion processes**: Every 2 steps
  - Substance transport
  - Concentration gradients
- **Intercellular processes**: Every 5 steps
  - Cell migration
  - Cell division
  - Cell-cell interactions

### **Key Parameters**
```yaml
# ATP production thresholds
atp_threshold: 0.8              # Minimum ATP for proliferation
max_atp: 30                     # Maximum ATP per glucose

# Necrosis thresholds
necrosis_threshold_oxygen: 0.011    # mM
necrosis_threshold_glucose: 0.23    # mM

# Cell cycle
cell_cycle_time: 1000           # Minimum time for division
```

## Running the Experiment

### **Basic Run**
```bash
python run_sim.py tests/jayatilake_experiment/jayatilake_experiment_config.yaml
```

### **Extended Run with Verbose Output**
```bash
python run_sim.py tests/jayatilake_experiment/jayatilake_experiment_config.yaml --steps 100 --verbose
```

### **Custom Time Step**
```bash
python run_sim.py tests/jayatilake_experiment/jayatilake_experiment_config.yaml --dt 0.05 --steps 200
```

## Expected Results

### **Metabolic Dynamics**
- **Glucose depletion**: 5.0 → 2.5 mM (center of spheroid)
- **Lactate accumulation**: 5.0 → 10.0 mM (center of spheroid)
- **Oxygen gradients**: 0.070 → 0.069 mM (slight depletion)
- **pH acidification**: Proton accumulation in tumor core

### **Spatial Patterns**
- **Core**: Hypoxic, glycolytic cells (green)
- **Periphery**: Normoxic, OXPHOS cells (blue)
- **Interface**: Mixed metabolism cells (violet)
- **Necrotic center**: Dead cells (black) under severe stress

### **Population Dynamics**
- **Stable cell count**: ~50-100 cells
- **Metabolic heterogeneity**: Multiple phenotypes coexist
- **Symbiotic cooperation**: Enhanced survival vs. monocultures

## Files

- `jayatilake_experiment_config.yaml`: Main configuration with gene network
- `jayatilake_experiment_custom_functions.py`: Custom metabolic logic implementation
- `README.md`: This comprehensive documentation

## Custom Functions Architecture

### **Custom Override Functions** (start with `custom_`)
- `custom_initialize_cell_placement()`: Spheroid cell placement
- `custom_update_cell_phenotype()`: Gene network-based phenotype determination
- `custom_calculate_cell_metabolism()`: Metabolic consumption/production rates
- `custom_should_divide()`: Cell division logic
- `custom_get_cell_color()`: Metabolic state visualization

### **Behavior Functions** (called by custom functions)
- `check_necrosis_conditions()`: Necrosis state logic
- `check_apoptosis_conditions()`: Apoptosis state logic
- `check_proliferation_conditions()`: Proliferation state logic
- `check_growth_arrest_conditions()`: Growth arrest state logic

## Scientific Validation

This implementation captures the key biological insights from the original paper:

1. **Metabolic heterogeneity** enhances tumor survival
2. **Lactate shuttling** creates metabolic cooperation
3. **Hypoxic gradients** drive metabolic specialization
4. **Multi-timescale dynamics** are essential for realistic modeling

## Customization

### **Modify Metabolic Parameters**
Edit `jayatilake_parameters` in the YAML config:
```yaml
jayatilake_parameters:
  max_atp: 30                    # ATP yield
  atp_threshold: 0.8             # Proliferation threshold
  necrosis_threshold_oxygen: 0.011   # Hypoxia threshold
```

### **Add Gene Network**
Extend the minimal gene network with metabolic genes:
```yaml
gene_network:
  input_nodes: ["Oxygen_supply", "Glucose_supply", "Lactate_level"]
  output_nodes: ["glycoATP", "mitoATP", "GLUT1", "MCT1", "MCT4"]
```

### **Custom Metabolic Logic**
Modify `calculate_metabolic_state()` in the custom functions file to implement different metabolic rules.

## References

1. Jayatilake et al. "A computational model of metabolic symbiosis in cancer" *PLOS Computational Biology* (2024)
2. Original NetLogo model: `microC_Metabolic_Symbiosis.nlogo3d`
3. MicroC 2.0 Framework Documentation

---

*This experiment demonstrates the power of the MicroC 2.0 framework for modeling complex biological systems with realistic multi-timescale dynamics and configurable metabolic logic.*
