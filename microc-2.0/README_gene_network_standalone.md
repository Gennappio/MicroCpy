# Standalone Gene Network Simulator

A standalone tool for simulating Boolean gene networks using NetLogo-style single-gene updates.

## Features

- **NetLogo-compatible**: Uses the same single-gene update mechanism as the original NetLogo model
- **Statistical analysis**: Runs multiple simulations and provides statistics
- **Flexible input**: Load any .bnd file and custom input conditions
- **Target analysis**: Focus on specific genes of interest
- **JSON output**: Save results for further analysis

## Usage

### Basic Usage
```bash
python gene_network_standalone.py network.bnd inputs.txt
```

### Advanced Usage
```bash
python gene_network_standalone.py network.bnd inputs.txt \
    --runs 1000 \
    --steps 2000 \
    --target-nodes mitoATP glycoATP ATP_Production_Rate Apoptosis \
    --output results.json \
    --verbose
```

## Input File Format

Create a text file with input node states:

```
# Comments start with #
Oxygen_supply = true
Glucose_supply = true
FGFR_stimulus = false
EGFR_stimulus = true
# Supported values: true/false, 1/0, on/off, yes/no
```

## Example Usage

### 1. Test Metabolic Pathways
```bash
python gene_network_standalone.py \
    tests/jayatilake_experiment/jaya_microc.bnd \
    example_inputs.txt \
    --runs 100 \
    --steps 1000 \
    --target-nodes mitoATP glycoATP ATP_Production_Rate
```

### 2. Test Apoptosis Conditions
```bash
# Create hypoxic conditions
echo "Oxygen_supply = false
Glucose_supply = true
FGFR_stimulus = false
EGFR_stimulus = false
cMET_stimulus = false" > hypoxic_inputs.txt

python gene_network_standalone.py \
    tests/jayatilake_experiment/jaya_microc.bnd \
    hypoxic_inputs.txt \
    --runs 500 \
    --steps 1500 \
    --target-nodes Apoptosis Proliferation Growth_Arrest
```

### 3. Test Growth Factor Dependencies
```bash
# Test different growth factor combinations
for gf in "FGFR_stimulus" "EGFR_stimulus" "cMET_stimulus"; do
    echo "Oxygen_supply = true
Glucose_supply = true
FGFR_stimulus = false
EGFR_stimulus = false
cMET_stimulus = false
$gf = true" > ${gf}_only.txt
    
    python gene_network_standalone.py \
        tests/jayatilake_experiment/jaya_microc.bnd \
        ${gf}_only.txt \
        --runs 200 \
        --steps 1000 \
        --target-nodes AKT ERK BCL2 Apoptosis
done
```

## Output Format

### Console Output
```
GENE NETWORK SIMULATION RESULTS
========================================
Network: jaya_microc.bnd
Inputs: example_inputs.txt
Runs: 100, Steps: 1000

Input Conditions:
  Oxygen_supply: ON
  Glucose_supply: ON
  FGFR_stimulus: ON

Target Node Results:
  mitoATP: ON 85/100 (85.0%), OFF 15/100 (15.0%)
  glycoATP: ON 92/100 (92.0%), OFF 8/100 (8.0%)
  ATP_Production_Rate: ON 95/100 (95.0%), OFF 5/100 (5.0%)
```

### JSON Output
```json
{
  "runs": 100,
  "steps": 1000,
  "input_conditions": {
    "Oxygen_supply": true,
    "Glucose_supply": true
  },
  "target_nodes": {
    "mitoATP": {
      "ON": "85/100 (85.0%)",
      "OFF": "15/100 (15.0%)"
    }
  }
}
```

## Parameters

- `--runs`: Number of independent simulations (default: 100)
- `--steps`: Number of gene update steps per simulation (default: 1000)
- `--target-nodes`: Specific genes to analyze (space-separated)
- `--output`: Save results to JSON file
- `--verbose`: Show progress and all node statistics

## NetLogo Compatibility

This simulator uses the same update mechanism as the original NetLogo model:

1. **Single gene updates**: Only one gene is updated per step
2. **Random selection**: Genes are randomly chosen from eligible candidates
3. **Gradual propagation**: Signals propagate slowly through the network
4. **Stable convergence**: Avoids oscillations common in batch updates

## Troubleshooting

### Common Issues

1. **No gene updates**: Check that input nodes are properly connected to the network
2. **Low convergence**: Increase `--steps` for complex networks
3. **Inconsistent results**: Increase `--runs` for better statistics

### Debug Mode
Add print statements to see which genes are being updated:
```python
# In netlogo_single_gene_update(), add:
print(f"Updating gene: {selected_gene} -> {new_state}")
```

## Performance

- **Small networks** (<50 nodes): 1000 runs in ~10 seconds
- **Large networks** (>200 nodes): Consider reducing runs or steps
- **Memory usage**: Scales with number of runs (raw results stored for runs ≤ 10)

## Integration

The simulator can be integrated into larger workflows:

```python
from gene_network_standalone import run_simulation

results = run_simulation(
    'network.bnd', 
    'inputs.txt', 
    runs=100, 
    steps=1000,
    target_nodes=['mitoATP', 'glycoATP']
)

# Access results
atp_rate = results['target_nodes']['mitoATP']['ON']
```
