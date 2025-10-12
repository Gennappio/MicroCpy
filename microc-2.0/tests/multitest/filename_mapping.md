# Multitest Configuration Filename Mapping

This document shows the mapping from old numeric filenames to new descriptive filenames.

## Filename Changes

| Old Filename | New Filename | Description |
|--------------|--------------|-------------|
| config_00.yaml | config_O2low_Laclow_Gluclow_TGFAlow.yaml | O2=Low, Lactate=Low, Glucose=Low, TGFA=Low |
| config_01.yaml | config_O2high_Laclow_Gluclow_TGFAlow.yaml | O2=High, Lactate=Low, Glucose=Low, TGFA=Low |
| config_02.yaml | config_O2low_Lachigh_Gluclow_TGFAlow.yaml | O2=Low, Lactate=High, Glucose=Low, TGFA=Low |
| config_03.yaml | config_O2high_Lachigh_Gluclow_TGFAlow.yaml | O2=High, Lactate=High, Glucose=Low, TGFA=Low |
| config_04.yaml | config_O2low_Laclow_Gluchigh_TGFAlow.yaml | O2=Low, Lactate=Low, Glucose=High, TGFA=Low |
| config_05.yaml | config_O2high_Laclow_Gluchigh_TGFAlow.yaml | O2=High, Lactate=Low, Glucose=High, TGFA=Low |
| config_06.yaml | config_O2low_Lachigh_Gluchigh_TGFAlow.yaml | O2=Low, Lactate=High, Glucose=High, TGFA=Low |
| config_07.yaml | config_O2high_Lachigh_Gluchigh_TGFAlow.yaml | O2=High, Lactate=High, Glucose=High, TGFA=Low |
| config_08.yaml | config_O2low_Laclow_Gluclow_TGFAhigh.yaml | O2=Low, Lactate=Low, Glucose=Low, TGFA=High |
| config_09.yaml | config_O2high_Laclow_Gluclow_TGFAhigh.yaml | O2=High, Lactate=Low, Glucose=Low, TGFA=High |
| config_10.yaml | config_O2low_Lachigh_Gluclow_TGFAhigh.yaml | O2=Low, Lactate=High, Glucose=Low, TGFA=High |
| config_11.yaml | config_O2high_Lachigh_Gluclow_TGFAhigh.yaml | O2=High, Lactate=High, Glucose=Low, TGFA=High |
| config_12.yaml | config_O2low_Laclow_Gluchigh_TGFAhigh.yaml | O2=Low, Lactate=Low, Glucose=High, TGFA=High |
| config_13.yaml | config_O2high_Laclow_Gluchigh_TGFAhigh.yaml | O2=High, Lactate=Low, Glucose=High, TGFA=High |
| config_14.yaml | config_O2low_Lachigh_Gluchigh_TGFAhigh.yaml | O2=Low, Lactate=High, Glucose=High, TGFA=High |
| config_15.yaml | config_O2high_Lachigh_Gluchigh_TGFAhigh.yaml | O2=High, Lactate=High, Glucose=High, TGFA=High |

## Substance Concentration Levels

- **Low O2**: 0.01 mM
- **High O2**: 0.21 mM
- **Low Lactate**: 0.5 mM
- **High Lactate**: 2.0 mM
- **Low Glucose**: 2.0 mM
- **High Glucose**: 5.0 mM
- **Low TGFA**: 5e-07 mM
- **High TGFA**: 2e-06 mM

## Output Directory Structure

Results are now saved in descriptive directories that match the substance combinations:

- **Results**: `results/multitest/O2{level}_Lac{level}_Gluc{level}_TGFA{level}/`
- **Plots**: `plots/multitest/O2{level}_Lac{level}_Gluc{level}_TGFA{level}/`
- **Data**: `data/multitest/O2{level}_Lac{level}_Gluc{level}_TGFA{level}/`

**Examples:**
- `results/multitest/O2low_Laclow_Gluclow_TGFAlow/`
- `plots/multitest/O2high_Lachigh_Gluchigh_TGFAhigh/`
- `data/multitest/O2high_Laclow_Gluchigh_TGFAlow/`

## Usage

```bash
# Run specific combination
python run_sim.py tests/multitest/config_O2low_Laclow_Gluclow_TGFAlow.yaml

# Run all combinations
python tests/multitest/run_all_simulations.py

# Quick test (first 3 combinations)
python tests/multitest/run_all_simulations.py test
```
