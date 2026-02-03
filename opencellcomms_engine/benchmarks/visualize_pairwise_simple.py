#!/usr/bin/env python3
"""
Simple Pairwise Fate Node Comparison Visualizer

Shows clearly: when is one fate (e.g., Proliferation) more likely than another (e.g., Apoptosis)?

Usage:
    python visualize_pairwise_simple.py results.json
"""

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def load_results(json_file: str) -> dict:
    """Load results from JSON file."""
    with open(json_file, 'r') as f:
        return json.load(f)


def format_input_pattern(input_states: dict) -> str:
    """Format input pattern as a readable string."""
    on_nodes = [k for k, v in sorted(input_states.items()) if v]
    off_nodes = [k for k, v in sorted(input_states.items()) if not v]
    
    result = "ON: " + ", ".join(on_nodes) if on_nodes else "ON: (none)"
    result += "\nOFF: " + ", ".join(off_nodes) if off_nodes else "\nOFF: (none)"
    return result


def plot_pairwise_scatter(data: dict, node_a: str, node_b: str, output_dir: Path):
    """
    Create a scatter plot: X = prob(node_a), Y = prob(node_b)
    Points above diagonal: node_b > node_a
    Points below diagonal: node_a > node_b
    """
    all_results = data['all_results']
    
    probs_a = []
    probs_b = []
    
    for combo_data in all_results.values():
        probs = combo_data['output_probabilities']
        if node_a in probs and node_b in probs:
            probs_a.append(probs[node_a] * 100)
            probs_b.append(probs[node_b] * 100)
    
    if not probs_a:
        print(f"ERROR: {node_a} or {node_b} not found in results!")
        return
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Plot diagonal line (where they're equal)
    ax.plot([0, 100], [0, 100], 'k--', linewidth=2, label='Equal probability')
    
    # Color points by which is higher
    colors = []
    for pa, pb in zip(probs_a, probs_b):
        if pa > pb:
            colors.append('green')  # node_a wins
        elif pb > pa:
            colors.append('red')    # node_b wins
        else:
            colors.append('gray')   # equal
    
    ax.scatter(probs_a, probs_b, c=colors, alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
    
    # Labels
    ax.set_xlabel(f'{node_a} Probability (%)', fontsize=14)
    ax.set_ylabel(f'{node_b} Probability (%)', fontsize=14)
    ax.set_title(f'{node_a} vs {node_b}\n(512 input combinations)', fontsize=16, fontweight='bold')
    
    # Count
    a_wins = sum(1 for pa, pb in zip(probs_a, probs_b) if pa > pb)
    b_wins = sum(1 for pa, pb in zip(probs_a, probs_b) if pb > pa)
    
    # Add legend with counts
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', edgecolor='black', label=f'{node_a} > {node_b}: {a_wins} combos'),
        Patch(facecolor='red', edgecolor='black', label=f'{node_b} > {node_a}: {b_wins} combos'),
        Patch(facecolor='gray', edgecolor='black', label=f'Equal: {len(probs_a) - a_wins - b_wins} combos')
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=12)
    
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    # Add annotation
    ax.annotate(f'Below diagonal:\n{node_a} wins', xy=(70, 30), fontsize=11, color='green', fontweight='bold')
    ax.annotate(f'Above diagonal:\n{node_b} wins', xy=(20, 70), fontsize=11, color='red', fontweight='bold')
    
    plt.tight_layout()
    output_file = output_dir / f'scatter_{node_a}_vs_{node_b}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()


def print_best_cases(data: dict, node_a: str, node_b: str, top_n: int = 5):
    """Print the input patterns where node_a > node_b (and vice versa)."""
    all_results = data['all_results']
    
    # Collect all cases
    cases = []
    for combo_idx, combo_data in all_results.items():
        probs = combo_data['output_probabilities']
        if node_a in probs and node_b in probs:
            cases.append({
                'input_states': combo_data['input_states'],
                'prob_a': probs[node_a] * 100,
                'prob_b': probs[node_b] * 100,
                'diff': probs[node_a] - probs[node_b]
            })
    
    print(f"\n{'='*80}")
    print(f"WHEN IS {node_a.upper()} MORE PROBABLE THAN {node_b.upper()}?")
    print(f"{'='*80}\n")
    
    # Cases where node_a > node_b (sort by difference)
    a_wins = [c for c in cases if c['diff'] > 0]
    a_wins.sort(key=lambda x: x['diff'], reverse=True)
    
    print(f"Found {len(a_wins)} combinations where {node_a} > {node_b}\n")
    
    if a_wins:
        print(f"TOP {min(top_n, len(a_wins))} CASES WHERE {node_a} > {node_b}:")
        print("-" * 80)
        
        for i, case in enumerate(a_wins[:top_n], 1):
            print(f"\nCase {i}:")
            print(f"  {node_a}: {case['prob_a']:.0f}%")
            print(f"  {node_b}: {case['prob_b']:.0f}%")
            print(f"  Difference: +{case['diff']*100:.0f}% for {node_a}")
            print(f"  Input pattern:")
            
            # Show inputs that are ON
            on_inputs = [k for k, v in sorted(case['input_states'].items()) if v]
            off_inputs = [k for k, v in sorted(case['input_states'].items()) if not v]
            
            print(f"    ON:  {', '.join(on_inputs) if on_inputs else '(none)'}")
            print(f"    OFF: {', '.join(off_inputs) if off_inputs else '(none)'}")
    
    print(f"\n{'='*80}")
    print(f"WHEN IS {node_b.upper()} MORE PROBABLE THAN {node_a.upper()}?")
    print(f"{'='*80}\n")
    
    # Cases where node_b > node_a
    b_wins = [c for c in cases if c['diff'] < 0]
    b_wins.sort(key=lambda x: x['diff'])  # Most negative = biggest b win
    
    print(f"Found {len(b_wins)} combinations where {node_b} > {node_a}\n")
    
    if b_wins:
        print(f"TOP {min(top_n, len(b_wins))} CASES WHERE {node_b} > {node_a}:")
        print("-" * 80)
        
        for i, case in enumerate(b_wins[:top_n], 1):
            print(f"\nCase {i}:")
            print(f"  {node_b}: {case['prob_b']:.0f}%")
            print(f"  {node_a}: {case['prob_a']:.0f}%")
            print(f"  Difference: +{-case['diff']*100:.0f}% for {node_b}")
            print(f"  Input pattern:")
            
            on_inputs = [k for k, v in sorted(case['input_states'].items()) if v]
            off_inputs = [k for k, v in sorted(case['input_states'].items()) if not v]
            
            print(f"    ON:  {', '.join(on_inputs) if on_inputs else '(none)'}")
            print(f"    OFF: {', '.join(off_inputs) if off_inputs else '(none)'}")


def main():
    parser = argparse.ArgumentParser(
        description='Simple pairwise fate node comparison'
    )
    parser.add_argument('json_file', help='Path to results JSON file')
    parser.add_argument('--node-a', default='Proliferation', help='First node (default: Proliferation)')
    parser.add_argument('--node-b', default='Apoptosis', help='Second node (default: Apoptosis)')
    parser.add_argument('--top', type=int, default=5, help='Show top N cases (default: 5)')
    parser.add_argument('--output', '-o', default='pairwise_plots', help='Output directory')
    
    args = parser.parse_args()
    
    # Load results
    print(f"Loading {args.json_file}...")
    data = load_results(args.json_file)
    
    print(f"Output nodes in file: {data['output_nodes']}")
    
    # Check if requested nodes are in the data
    if args.node_a not in data['output_nodes']:
        print(f"\nERROR: '{args.node_a}' not found in results!")
        print(f"Available nodes: {data['output_nodes']}")
        return
    
    if args.node_b not in data['output_nodes']:
        print(f"\nERROR: '{args.node_b}' not found in results!")
        print(f"Available nodes: {data['output_nodes']}")
        return
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    # Print analysis
    print_best_cases(data, args.node_a, args.node_b, args.top)
    
    # Create scatter plot
    print(f"\nCreating scatter plot...")
    plot_pairwise_scatter(data, args.node_a, args.node_b, output_dir)
    
    print(f"\nDone! Check {output_dir}/ for the plot.")


if __name__ == '__main__':
    main()
