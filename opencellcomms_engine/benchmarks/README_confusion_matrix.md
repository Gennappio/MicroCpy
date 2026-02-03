# Gene Network Confusion Matrix Tool

## Overview

`gene_network_confusion.py` systematically explores all possible combinations of input node activations to identify which configurations maximize the activation probability of each output node.

## Features

- **Exhaustive search**: Tests all 2^N combinations of N input nodes
- **Statistical analysis**: Runs multiple simulations per combination for robust probability estimates
- **Multi-output optimization**: Finds best combinations for each output node independently
- **Cross-output analysis**: Shows how other outputs behave at the optimal configuration

## Usage

### Basic Usage

```bash
python gene_network_confusion.py <bnd_file> <input_nodes_file> <output_nodes_file>
```

### Example

```bash
python gene_network_confusion.py \
    ../tests/jayatilake_experiment/jaya_microc.bnd \
    example_input_nodes.txt \
    example_output_nodes.txt \
    --runs 100 \
    --steps 1000
```

### Command Line Arguments

- `bnd_file`: Path to .bnd gene network file
- `input_nodes_file`: File listing input nodes (one per line)
- `output_nodes_file`: File listing output nodes to analyze (one per line)
- `--runs`: Number of simulation runs per combination (default: 100)
- `--steps`: Number of propagation steps per run (default: 1000)
- `--output`: Save results to JSON file
- `--verbose`: Show progress for each combination
- `--top-n`: Show top N combinations per output (default: 1)

## Input File Format

### Input Nodes File (`example_input_nodes.txt`)

```
# List input nodes to vary (one per line)
Oxygen_supply
Glucose_supply
MCT1_stimulus
FGFR_stimulus
EGFR_stimulus
cMET_stimulus
Growth_Inhibitor
DNA_damage
TGFBR_stimulus
```

### Output Nodes File (`example_output_nodes.txt`)

```
# List output nodes to optimize (one per line)
Apoptosis
mitoATP
glycoATP
Proliferation
```

## Output Format

The tool produces two main sections of output:

### 1. Best Combinations for Each Output Node

For each output node, the tool reports:

1. **Activation probability**: Percentage of runs where the node was ON
2. **Input combination**: Which inputs were ON/OFF for maximum activation
3. **Other outputs**: Activation probabilities of other output nodes at this combination

### 2. Pairwise Fate Node Comparisons

Analyzes when one fate node has higher activation probability than another:
- Proliferation vs Apoptosis
- Growth_Arrest vs Apoptosis
- Proliferation vs Growth_Arrest

For each pair, reports:
- Count of combinations where each node dominates
- Top 5 cases with largest probability differences
- Input combinations for those cases

### Example Output

```
================================================================================
BEST COMBINATIONS FOR OUTPUT NODES
================================================================================

Apoptosis:
  Best activation: 92.0% (92/100 runs)
  Input combination:
    DNA_damage: ON
    EGFR_stimulus: OFF
    FGFR_stimulus: OFF
    Glucose_supply: OFF
    Growth_Inhibitor: ON
    MCT1_stimulus: OFF
    Oxygen_supply: OFF
    TGFBR_stimulus: OFF
    cMET_stimulus: OFF
  Other outputs at this combination:
    Growth_Arrest: 5.0%
    Proliferation: 0.0%

Proliferation:
  Best activation: 85.0% (85/100 runs)
  Input combination:
    DNA_damage: OFF
    EGFR_stimulus: ON
    FGFR_stimulus: ON
    Glucose_supply: ON
    Growth_Inhibitor: OFF
    MCT1_stimulus: OFF
    Oxygen_supply: ON
    TGFBR_stimulus: OFF
    cMET_stimulus: ON
  Other outputs at this combination:
    Apoptosis: 0.0%
    Growth_Arrest: 2.0%

Growth_Arrest:
  Best activation: 78.0% (78/100 runs)
  Input combination:
    DNA_damage: OFF
    EGFR_stimulus: OFF
    FGFR_stimulus: OFF
    Glucose_supply: ON
    Growth_Inhibitor: ON
    MCT1_stimulus: ON
    Oxygen_supply: OFF
    TGFBR_stimulus: ON
    cMET_stimulus: OFF
  Other outputs at this combination:
    Apoptosis: 15.0%
    Proliferation: 0.0%

================================================================================
PAIRWISE FATE NODE COMPARISONS
================================================================================

Proliferation vs Apoptosis:
  Proliferation > Apoptosis: 324 combinations
  Apoptosis > Proliferation: 188 combinations

  Top cases where Proliferation > Apoptosis:

    Case 1: Proliferation=85.0%, Apoptosis=0.0% (diff: 85.0%)
      Input combination:
        DNA_damage: OFF
        EGFR_stimulus: ON
        FGFR_stimulus: ON
        Glucose_supply: ON
        Growth_Inhibitor: OFF
        MCT1_stimulus: OFF
        Oxygen_supply: ON
        TGFBR_stimulus: OFF
        cMET_stimulus: ON

  Top cases where Apoptosis > Proliferation:

    Case 1: Apoptosis=92.0%, Proliferation=0.0% (diff: 92.0%)
      Input combination:
        DNA_damage: ON
        EGFR_stimulus: OFF
        FGFR_stimulus: OFF
        Glucose_supply: OFF
        Growth_Inhibitor: ON
        MCT1_stimulus: OFF
        Oxygen_supply: OFF
        TGFBR_stimulus: OFF
        cMET_stimulus: OFF
```

## Performance Considerations

The total number of propagation steps is:
```
2^N × runs × steps
```

For example, with:
- 9 input nodes (512 combinations)
- 100 runs per combination
- 1000 steps per run

Total: **51.2 million propagation steps**

Use `--verbose` to monitor progress. Consider reducing `--runs` or `--steps` for faster exploratory analysis, then increase for final results.

## Use Cases

1. **Identify pro-apoptotic conditions**: Find input combinations that maximize Apoptosis
2. **Optimize metabolic states**: Maximize mitoATP or glycoATP activation
3. **Prevent proliferation**: Find conditions that minimize Proliferation
4. **Multi-objective analysis**: Compare trade-offs between different output goals

## Technical Details

- Uses NetLogo-style single-gene asynchronous updates
- Random initialization for non-input, non-fate nodes
- Fate nodes (Apoptosis, Proliferation, etc.) always start as False
- Input states are enforced after each update to prevent corruption
