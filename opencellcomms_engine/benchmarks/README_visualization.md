# Confusion Matrix Results Visualization

Quick visualization tool for gene network confusion matrix results.

## Usage

```bash
python visualize_confusion_results.py results.json
```

This will create a `confusion_plots/` directory with all visualizations.

### Custom Output Directory

```bash
python visualize_confusion_results.py results.json --output my_plots/
```

## Generated Visualizations

The tool creates 6 visualizations:

### 1. **best_activations.png**
Bar chart showing the maximum achievable activation probability for each output node.

### 2. **input_patterns.png**
Heatmap showing which inputs should be ON/OFF to maximize each output node.
- Green = ON
- Red = OFF
- Easy to see the optimal input pattern for each fate

### 3. **cross_output_analysis.png**
Heatmap showing how other outputs behave when optimizing for each output.
- Rows: Which output you're optimizing for
- Columns: Actual activation levels of all outputs
- Diagonal (bold): The output you're maximizing
- Off-diagonal: Side effects on other outputs

### 4. **pairwise_comparisons.png**
Bar charts showing dominance patterns between fate node pairs:
- Proliferation vs Apoptosis
- Growth_Arrest vs Apoptosis
- Proliferation vs Growth_Arrest

### 5. **heatmap_all_combinations.png**
Full heatmap of all input combinations vs output activations.
- Each row is one input combination (512 total for 9 inputs)
- Each column is an output node
- Color intensity = activation probability

### 6. **summary_report.txt**
Text file with:
- Experiment parameters
- Best activation for each output with exact input patterns
- Pairwise comparison counts

## Dependencies

```bash
pip install matplotlib seaborn numpy
```

## Quick Start Example

```bash
# Run confusion matrix analysis
python gene_network_confusion.py \
    ../tests/jayatilake_experiment/jaya_microc.bnd \
    example_input_nodes.txt \
    example_output_nodes.txt \
    --runs 100 --steps 1000 \
    --output results.json

# Visualize results
python visualize_confusion_results.py results.json

# View plots
open confusion_plots/*.png
```

## Tips

- The **input_patterns.png** is most useful for quickly seeing what conditions maximize each fate
- The **cross_output_analysis.png** reveals trade-offs (e.g., maximizing Proliferation while minimizing Apoptosis)
- The **pairwise_comparisons.png** shows competitive dynamics between fates
- Check **summary_report.txt** for exact numerical values
