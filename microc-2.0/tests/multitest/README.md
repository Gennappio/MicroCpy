# Multi-Test System

This folder contains a system for running multiple single-cell simulations with different substance concentration combinations.

## Overview

The multi-test system creates 16 separate configuration files, each representing a different combination of substance concentrations:

- **4 key substances**: Oxygen, Lactate, Glucose, TGFA
- **2 levels each**: HIGH (above threshold) and LOW (below threshold)  
- **16 total combinations**: All possible HIGH/LOW combinations (2^4 = 16)

Each configuration file:
- Has a **single cell** in a **small domain** (40μm × 40μm, 1×1 grid)
- Uses **fixed concentrations** (no diffusion)
- Uses the **complete Jayatilake gene network**
- Saves results to **separate output directories**

## Files

- `generate_configs.py` - Generates all 16 config files
- `test_combination.py` - Validates config files and shows concentrations
- `config_00.yaml` to `config_15.yaml` - Individual configuration files
- `README.md` - This file

## Usage

### 1. Generate Config Files (if not already done)

```bash
python tests/multitest/generate_configs.py
```

This creates 16 config files with different substance combinations.

### 2. Validate All Configurations

```bash
python tests/multitest/test_combination.py all
```

This checks that all config files are properly formatted and shows the substance concentrations for each combination.

### 3. Test Individual Combinations

```bash
python tests/multitest/test_combination.py 0   # Test combination 0 (all LOW)
python tests/multitest/test_combination.py 15  # Test combination 15 (all HIGH)
```

### 4. Run Individual Simulations

To run an actual simulation for a specific combination:

```bash
python run_sim.py tests/multitest/config_00.yaml
python run_sim.py tests/multitest/config_01.yaml
# ... etc for other combinations
```

## Combination Table

| ID | Oxygen | Lactate | Glucose | TGFA | Description |
|----|--------|---------|---------|------|-------------|
| 00 | LOW    | LOW     | LOW     | LOW  | Worst conditions |
| 01 | HIGH   | LOW     | LOW     | LOW  | High oxygen only |
| 02 | LOW    | HIGH    | LOW     | LOW  | High lactate only |
| 03 | HIGH   | HIGH    | LOW     | LOW  | High O2 + lactate |
| 04 | LOW    | LOW     | HIGH    | LOW  | High glucose only |
| 05 | HIGH   | LOW     | HIGH    | LOW  | High O2 + glucose |
| 06 | LOW    | HIGH    | HIGH    | LOW  | High lactate + glucose |
| 07 | HIGH   | HIGH    | HIGH    | LOW  | High O2 + lactate + glucose |
| 08 | LOW    | LOW     | LOW     | HIGH | High TGFA only |
| 09 | HIGH   | LOW     | LOW     | HIGH | High O2 + TGFA |
| 10 | LOW    | HIGH    | LOW     | HIGH | High lactate + TGFA |
| 11 | HIGH   | HIGH    | LOW     | HIGH | High O2 + lactate + TGFA |
| 12 | LOW    | LOW     | HIGH    | HIGH | High glucose + TGFA |
| 13 | HIGH   | LOW     | HIGH    | HIGH | High O2 + glucose + TGFA |
| 14 | LOW    | HIGH    | HIGH    | HIGH | High lactate + glucose + TGFA |
| 15 | HIGH   | HIGH    | HIGH    | HIGH | Best conditions |

## Concentration Values

- **Oxygen**: LOW = 0.010 mM, HIGH = 0.060 mM (threshold: 0.022 mM)
- **Lactate**: LOW = 0.5 mM, HIGH = 3.0 mM (threshold: 1.5 mM)
- **Glucose**: LOW = 2.0 mM, HIGH = 6.0 mM (threshold: 4.0 mM)
- **TGFA**: LOW = 5.0e-07 mM, HIGH = 2.0e-06 mM (threshold: 1.0e-06 mM)

## Output Directories

Each combination saves results to separate directories:
- `results/multitest/combination_XX/` - Simulation data
- `plots/multitest/combination_XX/` - Visualization plots
- `data/multitest/combination_XX/` - Raw data files

## Expected Results

Based on the gene network, you should see different cell phenotypes:
- **Necrosis/Apoptosis**: In poor conditions (low oxygen + low glucose)
- **Quiescent**: In moderate conditions
- **Proliferation**: In good conditions (high oxygen + high glucose)
- **Growth_Arrest**: In intermediate conditions

The TGFA growth factor may help cells survive in otherwise poor conditions.

## Troubleshooting

If simulations fail:
1. Check that all config files are valid: `python tests/multitest/test_combination.py all`
2. Try running a single combination manually: `python run_sim.py tests/multitest/config_00.yaml`
3. Check the error messages in the terminal output
4. Ensure all dependencies are installed and the environment is set up correctly

## Research Applications

This system is perfect for:
- **Systematic testing** of environmental effects on cell behavior
- **Parameter sensitivity analysis** for the gene network
- **Comparative studies** of different substance combinations
- **Validation** of biological hypotheses about cell responses

Each combination represents a controlled experiment with a single cell in a defined chemical environment, allowing you to isolate the effects of specific substance combinations on cell phenotype.
