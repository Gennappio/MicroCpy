#!/usr/bin/env python3
"""
Phenotype Hierarchy Analysis

Analyzes gene network confusion matrix results applying a phenotype hierarchy rule:
    Proliferation > Growth_Arrest > Apoptosis

When multiple fates are simultaneously ON in a simulation run, the higher-priority 
one determines the final phenotype. For example, if both Proliferation=ON and 
Apoptosis=ON, the phenotype is "Proliferation" (not Apoptosis).

This uses an independence assumption to compute effective phenotype probabilities:
- P(Phenotype=Proliferation) = P(Prolif ON)
- P(Phenotype=Growth_Arrest) = P(GA ON) * (1 - P(Prolif ON))
- P(Phenotype=Apoptosis) = P(Apop ON) * (1 - P(GA ON)) * (1 - P(Prolif ON))
- P(Quiescent) = (1 - P(Prolif)) * (1 - P(GA)) * (1 - P(Apop))

Usage:
    python phenotype_hierarchy_analysis.py results.json
    python phenotype_hierarchy_analysis.py results.json --top 20
    python phenotype_hierarchy_analysis.py results.json --output report.txt
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_results(filepath: str) -> Dict:
    """Load gene network confusion matrix results from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def compute_effective_phenotypes(
    p_prolif: float, 
    p_ga: float, 
    p_apop: float
) -> Dict[str, float]:
    """
    Compute effective phenotype probabilities with hierarchy rule.
    
    Hierarchy: Proliferation > Growth_Arrest > Apoptosis
    
    Args:
        p_prolif: Raw probability of Proliferation being ON
        p_ga: Raw probability of Growth_Arrest being ON
        p_apop: Raw probability of Apoptosis being ON
        
    Returns:
        Dictionary with effective probabilities for each phenotype
    """
    eff_prolif = p_prolif
    eff_ga = p_ga * (1 - p_prolif)
    eff_apop = p_apop * (1 - p_ga) * (1 - p_prolif)
    eff_quiescent = (1 - p_prolif) * (1 - p_ga) * (1 - p_apop)
    
    return {
        'Proliferation': eff_prolif,
        'Growth_Arrest': eff_ga,
        'Apoptosis': eff_apop,
        'Quiescent': eff_quiescent
    }


def analyze_hierarchy(data: Dict) -> Tuple[Dict, List[Dict]]:
    """
    Analyze all combinations with phenotype hierarchy applied.
    
    Args:
        data: Loaded JSON data from gene_network_confusion.py
        
    Returns:
        Tuple of (totals_dict, detailed_results_list)
    """
    all_results = data['all_results']
    
    totals = {
        'Proliferation': 0.0,
        'Growth_Arrest': 0.0,
        'Apoptosis': 0.0,
        'Quiescent': 0.0
    }
    
    detailed = []
    
    for combo_idx, combo in all_results.items():
        probs = combo['output_probabilities']
        
        # Get raw probabilities (handle missing nodes gracefully)
        p_prolif = probs.get('Proliferation', 0.0)
        p_ga = probs.get('Growth_Arrest', 0.0)
        p_apop = probs.get('Apoptosis', 0.0)
        
        # Compute effective phenotype probabilities
        eff = compute_effective_phenotypes(p_prolif, p_ga, p_apop)
        
        # Accumulate totals
        for phenotype, prob in eff.items():
            totals[phenotype] += prob
        
        # Determine dominant phenotype for this combination
        dominant = max(eff, key=eff.get)
        
        detailed.append({
            'combo_idx': combo_idx,
            'input_states': combo['input_states'],
            'raw_probs': {
                'Proliferation': p_prolif,
                'Growth_Arrest': p_ga,
                'Apoptosis': p_apop
            },
            'effective_probs': eff,
            'dominant_phenotype': dominant
        })
    
    return totals, detailed


def format_input_states(input_states: Dict[str, bool]) -> str:
    """Format input states as comma-separated ON nodes."""
    on_nodes = sorted([k for k, v in input_states.items() if v])
    return ', '.join(on_nodes) if on_nodes else '(none)'


def print_report(
    totals: Dict[str, float],
    detailed: List[Dict],
    top_n: int = 10,
    output_file=None
) -> None:
    """Print the analysis report."""
    
    def out(text=""):
        print(text, file=output_file or sys.stdout)
    
    n = len(detailed)
    
    out("=" * 70)
    out("PHENOTYPE HIERARCHY ANALYSIS")
    out("Hierarchy: Proliferation > Growth_Arrest > Apoptosis")
    out("=" * 70)
    out()
    out(f"Total combinations analyzed: {n}")
    out()
    out("AVERAGE EFFECTIVE PHENOTYPE DISTRIBUTION:")
    out("-" * 40)
    for phenotype in ['Proliferation', 'Growth_Arrest', 'Apoptosis', 'Quiescent']:
        avg = totals[phenotype] / n * 100
        out(f"  {phenotype:15s}: {avg:5.1f}%")
    out("-" * 40)
    total_check = sum(totals.values()) / n * 100
    out(f"  {'Total':15s}: {total_check:5.1f}%")
    out()
    
    # Count dominant phenotypes
    dominant_counts = {}
    for phenotype in ['Proliferation', 'Growth_Arrest', 'Apoptosis', 'Quiescent']:
        count = sum(1 for d in detailed if d['dominant_phenotype'] == phenotype)
        dominant_counts[phenotype] = count
    
    out("DOMINANT PHENOTYPE COUNTS (which phenotype has highest probability):")
    out("-" * 40)
    for phenotype in ['Proliferation', 'Growth_Arrest', 'Apoptosis', 'Quiescent']:
        count = dominant_counts[phenotype]
        pct = count / n * 100
        out(f"  {phenotype:15s}: {count:4d}/{n} ({pct:5.1f}%)")
    out()
    
    # Top combinations for Proliferation
    detailed_sorted = sorted(detailed, key=lambda x: x['effective_probs']['Proliferation'], reverse=True)
    out(f"TOP {top_n} COMBINATIONS FOR PROLIFERATION PHENOTYPE:")
    out("-" * 70)
    for i, r in enumerate(detailed_sorted[:top_n], 1):
        eff = r['effective_probs']
        raw = r['raw_probs']
        on_nodes = format_input_states(r['input_states'])
        out(f"#{i}:")
        out(f"  Effective: Prolif={eff['Proliferation']*100:.1f}%, GA={eff['Growth_Arrest']*100:.1f}%, "
            f"Apop={eff['Apoptosis']*100:.1f}%, Quiet={eff['Quiescent']*100:.1f}%")
        out(f"  Raw:       Prolif={raw['Proliferation']*100:.0f}%, GA={raw['Growth_Arrest']*100:.0f}%, "
            f"Apop={raw['Apoptosis']*100:.0f}%")
        out(f"  Inputs ON: {on_nodes}")
        out()
    
    # Combinations where Proliferation is dominant
    prolif_dominant = [r for r in detailed if r['dominant_phenotype'] == 'Proliferation']
    out(f"COMBINATIONS WHERE PROLIFERATION IS DOMINANT: {len(prolif_dominant)}/{n}")
    out("-" * 70)
    if prolif_dominant:
        for i, r in enumerate(prolif_dominant[:top_n], 1):
            eff = r['effective_probs']
            on_nodes = format_input_states(r['input_states'])
            out(f"#{i}: Prolif={eff['Proliferation']*100:.1f}%, GA={eff['Growth_Arrest']*100:.1f}%, "
                f"Apop={eff['Apoptosis']*100:.1f}%")
            out(f"    Inputs ON: {on_nodes}")
    else:
        out("  (none)")
    out()


def main():
    parser = argparse.ArgumentParser(
        description='Analyze gene network results with phenotype hierarchy rule',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'results_file',
        help='Path to results JSON file from gene_network_confusion.py'
    )
    parser.add_argument(
        '--top', '-n',
        type=int,
        default=10,
        help='Number of top combinations to show (default: 10)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (default: print to stdout)'
    )
    
    args = parser.parse_args()
    
    # Load data
    if not Path(args.results_file).exists():
        print(f"Error: File not found: {args.results_file}", file=sys.stderr)
        sys.exit(1)
    
    data = load_results(args.results_file)
    
    # Check required fields
    if 'all_results' not in data:
        print("Error: JSON file missing 'all_results' key", file=sys.stderr)
        sys.exit(1)
    
    # Analyze
    totals, detailed = analyze_hierarchy(data)
    
    # Output
    if args.output:
        with open(args.output, 'w') as f:
            print_report(totals, detailed, args.top, output_file=f)
        print(f"Report saved to: {args.output}")
    else:
        print_report(totals, detailed, args.top)


if __name__ == '__main__':
    main()
