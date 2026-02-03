#!/usr/bin/env python3
"""
Visualize Gene Network Confusion Matrix Results

Creates visualizations from the JSON output of gene_network_confusion.py

Usage:
    python visualize_confusion_results.py results.json
    python visualize_confusion_results.py results.json --output plots/
"""

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List


def load_results(json_file: str) -> Dict:
    """Load results from JSON file."""
    print(f"Loading results from {json_file}...")
    with open(json_file, 'r') as f:
        data = json.load(f)
    print(f"Loaded {data['total_combinations']} combinations")
    return data


def create_heatmap(data: Dict, output_dir: Path):
    """Create heatmap of output node activation across all combinations."""
    print("\nCreating activation probability heatmap...")
    
    output_nodes = data['output_nodes']
    all_results = data['all_results']
    
    # Build matrix: rows = combinations, cols = output nodes
    n_combos = len(all_results)
    n_outputs = len(output_nodes)
    
    activation_matrix = np.zeros((n_combos, n_outputs))
    
    for combo_idx, combo_data in all_results.items():
        idx = int(combo_idx)
        for j, output_node in enumerate(output_nodes):
            activation_matrix[idx, j] = combo_data['output_probabilities'][output_node]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, max(8, n_combos * 0.05)))
    
    # Plot heatmap
    im = ax.imshow(activation_matrix, aspect='auto', cmap='YlOrRd', vmin=0, vmax=1)
    
    # Set ticks
    ax.set_xticks(range(n_outputs))
    ax.set_xticklabels(output_nodes, rotation=45, ha='right')
    ax.set_ylabel('Input Combination Index')
    ax.set_xlabel('Output Node')
    ax.set_title('Output Node Activation Probabilities Across All Input Combinations')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Activation Probability', rotation=270, labelpad=20)
    
    plt.tight_layout()
    output_file = output_dir / 'heatmap_all_combinations.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()


def create_best_combinations_plot(data: Dict, output_dir: Path):
    """Create bar plot of best activation probabilities for each output node."""
    print("\nCreating best combinations bar plot...")
    
    best_combos = data['best_combinations']
    output_nodes = data['output_nodes']
    
    # Extract best activation for each output
    best_activations = []
    for output_node in output_nodes:
        best_combo = best_combos[output_node][0]  # Top combination
        best_activations.append(best_combo['activation_probability'] * 100)
    
    # Create bar plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = sns.color_palette('husl', len(output_nodes))
    bars = ax.bar(output_nodes, best_activations, color=colors, edgecolor='black', linewidth=1.5)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    ax.set_ylabel('Best Activation Probability (%)', fontsize=12)
    ax.set_xlabel('Output Node', fontsize=12)
    ax.set_title('Maximum Achievable Activation for Each Output Node', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    output_file = output_dir / 'best_activations.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()


def create_pairwise_comparison_plot(data: Dict, output_dir: Path):
    """Create visualization of pairwise comparisons."""
    print("\nCreating pairwise comparison plots...")
    
    if 'pairwise_comparisons' not in data:
        print("  No pairwise comparison data found, skipping...")
        return
    
    comparisons = data['pairwise_comparisons']
    
    # Create subplots for each comparison
    n_comparisons = len(comparisons)
    fig, axes = plt.subplots(1, n_comparisons, figsize=(6*n_comparisons, 5))
    
    if n_comparisons == 1:
        axes = [axes]
    
    for idx, (comp_key, comp_data) in enumerate(comparisons.items()):
        ax = axes[idx]
        
        node_a = comp_data['node_a']
        node_b = comp_data['node_b']
        a_higher = comp_data['a_higher_count']
        b_higher = comp_data['b_higher_count']
        
        # Create stacked bar
        categories = [f'{node_a}\n>\n{node_b}', f'{node_b}\n>\n{node_a}']
        values = [a_higher, b_higher]
        colors = ['#2ecc71', '#e74c3c']
        
        bars = ax.bar(categories, values, color=colors, edgecolor='black', linewidth=1.5)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=14, fontweight='bold')
        
        ax.set_ylabel('Number of Combinations', fontsize=12)
        ax.set_title(f'{node_a} vs {node_b}', fontsize=13, fontweight='bold')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.suptitle('Pairwise Fate Node Dominance Patterns', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    output_file = output_dir / 'pairwise_comparisons.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()


def create_input_pattern_analysis(data: Dict, output_dir: Path):
    """Analyze and visualize input patterns for best combinations."""
    print("\nCreating input pattern analysis...")
    
    best_combos = data['best_combinations']
    output_nodes = data['output_nodes']
    input_nodes = data['input_nodes']
    
    # Create matrix: rows = output nodes, cols = input nodes
    n_outputs = len(output_nodes)
    n_inputs = len(input_nodes)
    
    input_pattern_matrix = np.zeros((n_outputs, n_inputs))
    
    for i, output_node in enumerate(output_nodes):
        best_combo = best_combos[output_node][0]  # Top combination
        input_states = best_combo['input_states']
        
        for j, input_node in enumerate(input_nodes):
            input_pattern_matrix[i, j] = 1 if input_states[input_node] else 0
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(12, max(6, n_outputs * 0.8)))
    
    # Plot
    im = ax.imshow(input_pattern_matrix, aspect='auto', cmap='RdYlGn', vmin=0, vmax=1)
    
    # Set ticks
    ax.set_xticks(range(n_inputs))
    ax.set_xticklabels(input_nodes, rotation=45, ha='right')
    ax.set_yticks(range(n_outputs))
    ax.set_yticklabels(output_nodes)
    
    # Add text annotations
    for i in range(n_outputs):
        for j in range(n_inputs):
            text = 'ON' if input_pattern_matrix[i, j] == 1 else 'OFF'
            color = 'white' if input_pattern_matrix[i, j] == 1 else 'black'
            ax.text(j, i, text, ha='center', va='center', 
                   color=color, fontweight='bold', fontsize=9)
    
    ax.set_xlabel('Input Node', fontsize=12)
    ax.set_ylabel('Output Node', fontsize=12)
    ax.set_title('Optimal Input Patterns for Maximizing Each Output Node', 
                fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    output_file = output_dir / 'input_patterns.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()


def create_cross_output_analysis(data: Dict, output_dir: Path):
    """Analyze how other outputs behave at optimal conditions for each output."""
    print("\nCreating cross-output analysis...")
    
    best_combos = data['best_combinations']
    output_nodes = data['output_nodes']
    
    n_outputs = len(output_nodes)
    cross_matrix = np.zeros((n_outputs, n_outputs))
    
    for i, output_node in enumerate(output_nodes):
        best_combo = best_combos[output_node][0]
        
        # Diagonal: best activation for this output
        cross_matrix[i, i] = best_combo['activation_probability']
        
        # Off-diagonal: other outputs at this combination
        for j, other_node in enumerate(output_nodes):
            if i != j:
                cross_matrix[i, j] = best_combo['other_outputs'][other_node]
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(10, 8))
    
    im = ax.imshow(cross_matrix, aspect='auto', cmap='YlOrRd', vmin=0, vmax=1)
    
    # Set ticks
    ax.set_xticks(range(n_outputs))
    ax.set_xticklabels(output_nodes, rotation=45, ha='right')
    ax.set_yticks(range(n_outputs))
    ax.set_yticklabels(output_nodes)
    
    # Add text annotations
    for i in range(n_outputs):
        for j in range(n_outputs):
            text = f'{cross_matrix[i, j]*100:.0f}%'
            # Bold for diagonal
            weight = 'bold' if i == j else 'normal'
            ax.text(j, i, text, ha='center', va='center', 
                   color='white' if cross_matrix[i, j] > 0.5 else 'black',
                   fontweight=weight, fontsize=11)
    
    ax.set_xlabel('Output Node Activation', fontsize=12)
    ax.set_ylabel('Optimized For', fontsize=12)
    ax.set_title('Cross-Output Behavior at Optimal Conditions\n(Rows: Optimized for, Cols: Actual activation)',
                fontsize=13, fontweight='bold')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Activation Probability', rotation=270, labelpad=20)
    
    plt.tight_layout()
    output_file = output_dir / 'cross_output_analysis.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()


def create_summary_report(data: Dict, output_dir: Path):
    """Create a text summary report."""
    print("\nCreating summary report...")
    
    output_file = output_dir / 'summary_report.txt'
    
    with open(output_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("GENE NETWORK CONFUSION MATRIX - SUMMARY REPORT\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"BND File: {data['bnd_file']}\n")
        f.write(f"Total Combinations Tested: {data['total_combinations']}\n")
        f.write(f"Runs per Combination: {data['runs']}\n")
        f.write(f"Steps per Run: {data['steps']}\n\n")
        
        f.write(f"Input Nodes ({len(data['input_nodes'])}):\n")
        for node in data['input_nodes']:
            f.write(f"  - {node}\n")
        f.write("\n")
        
        f.write(f"Output Nodes ({len(data['output_nodes'])}):\n")
        for node in data['output_nodes']:
            f.write(f"  - {node}\n")
        f.write("\n")
        
        f.write("="*80 + "\n")
        f.write("BEST ACTIVATION PROBABILITIES\n")
        f.write("="*80 + "\n\n")
        
        best_combos = data['best_combinations']
        for output_node in data['output_nodes']:
            best = best_combos[output_node][0]
            prob = best['activation_probability'] * 100
            count = best['activation_count']
            runs = data['runs']
            
            f.write(f"{output_node}:\n")
            f.write(f"  Maximum Activation: {prob:.1f}% ({count}/{runs} runs)\n")
            f.write(f"  Optimal Input Pattern:\n")
            
            for input_node, state in sorted(best['input_states'].items()):
                f.write(f"    {input_node}: {'ON' if state else 'OFF'}\n")
            
            f.write(f"  Other Outputs at This Combination:\n")
            for other_node, other_prob in sorted(best['other_outputs'].items()):
                f.write(f"    {other_node}: {other_prob*100:.1f}%\n")
            f.write("\n")
        
        if 'pairwise_comparisons' in data:
            f.write("="*80 + "\n")
            f.write("PAIRWISE COMPARISONS\n")
            f.write("="*80 + "\n\n")
            
            for comp_key, comp_data in data['pairwise_comparisons'].items():
                node_a = comp_data['node_a']
                node_b = comp_data['node_b']
                
                f.write(f"{node_a} vs {node_b}:\n")
                f.write(f"  {node_a} > {node_b}: {comp_data['a_higher_count']} combinations\n")
                f.write(f"  {node_b} > {node_a}: {comp_data['b_higher_count']} combinations\n\n")
    
    print(f"  Saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Visualize Gene Network Confusion Matrix Results'
    )
    parser.add_argument('json_file', help='Path to results JSON file')
    parser.add_argument('--output', '-o', default='confusion_plots',
                       help='Output directory for plots (default: confusion_plots)')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Load results
    data = load_results(args.json_file)
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['font.size'] = 10
    
    # Create visualizations
    create_best_combinations_plot(data, output_dir)
    create_input_pattern_analysis(data, output_dir)
    create_cross_output_analysis(data, output_dir)
    create_pairwise_comparison_plot(data, output_dir)
    create_heatmap(data, output_dir)
    create_summary_report(data, output_dir)
    
    print(f"\n{'='*80}")
    print(f"Visualization complete! All plots saved to: {output_dir}")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
