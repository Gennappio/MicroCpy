#!/usr/bin/env python3
"""
Gene Network Confusion Matrix Tool

Explores all combinations of input node activations to find which configurations
maximize the activation probability of each output node.

Usage:
    python gene_network_confusion.py network.bnd input_nodes.txt output_nodes.txt --runs 100 --steps 1000
"""

import argparse
import random
import re
import itertools
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import json


class BooleanExpression:
    """Evaluates boolean expressions with gene states."""
    
    def __init__(self, expression: str):
        self.expression = expression.strip()
    
    def evaluate(self, gene_states: Dict[str, bool]) -> bool:
        """Evaluate the boolean expression given current gene states."""
        if not self.expression:
            return False
            
        # Replace gene names with their boolean values
        expr = self.expression
        
        # Sort gene names by length (longest first) to avoid partial replacements
        gene_names = sorted(gene_states.keys(), key=len, reverse=True)
        
        for gene_name in gene_names:
            if gene_name in expr:
                value = "True" if gene_states[gene_name] else "False"
                # Use word boundaries to avoid partial replacements
                expr = re.sub(r'\b' + re.escape(gene_name) + r'\b', value, expr)
        
        # Replace logical operators
        expr = expr.replace('&', ' and ')
        expr = expr.replace('|', ' or ')
        expr = expr.replace('!', ' not ')
        
        try:
            return bool(eval(expr))
        except:
            print(f"Error evaluating expression: {self.expression} -> {expr}")
            return False


class NetworkNode:
    """Represents a single node in the gene network."""
    
    def __init__(self, name: str, logic_rule: str = "", is_input: bool = False):
        self.name = name
        self.logic_rule = logic_rule
        self.is_input = is_input
        self.state = False
        self.inputs: Set[str] = set()
        
        # Create update function from logic rule
        if logic_rule and not is_input:
            self.update_function = BooleanExpression(logic_rule)
            # Extract input nodes from logic rule
            self._extract_inputs()
        else:
            self.update_function = None
    
    def _extract_inputs(self):
        """Extract input node names from the logic rule."""
        if not self.logic_rule:
            return
            
        # Find all gene names in the expression (alphanumeric + underscore)
        gene_names = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', self.logic_rule)
        
        # Filter out boolean operators and keywords
        keywords = {'and', 'or', 'not', 'True', 'False', 'true', 'false'}
        self.inputs = {name for name in gene_names if name not in keywords}


class StandaloneGeneNetwork:
    """Standalone gene network simulator with NetLogo-style updates."""
    
    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.input_nodes: Set[str] = set()
    
    def load_bnd_file(self, bnd_file: str):
        """Load gene network from .bnd file."""
        print(f"Loading gene network from {bnd_file}")
        
        with open(bnd_file, 'r') as f:
            content = f.read()
        
        # Parse nodes (case-insensitive to handle both 'node' and 'Node')
        node_pattern = r'[Nn]ode\s+(\w+)\s*\{([^}]+)\}'
        nodes_created = 0

        for match in re.finditer(node_pattern, content, re.MULTILINE | re.DOTALL):
            node_name = match.group(1)
            node_content = match.group(2)

            # Check if it's an input node (rate_up = 0; rate_down = 0;)
            is_input = ('rate_up = 0' in node_content and 'rate_down = 0' in node_content)

            # Extract logic rule
            logic_match = re.search(r'logic\s*=\s*([^;]+);', node_content)
            logic_rule = logic_match.group(1).strip() if logic_match else ""

            # Check for self-referential logic (input node in MaBoSS format)
            # e.g., "logic = (Oxygen_supply);" where node references only itself
            if logic_rule.strip('() ') == node_name:
                is_input = True
                logic_rule = ""  # Clear logic for input nodes

            # Create node
            self.nodes[node_name] = NetworkNode(
                name=node_name,
                logic_rule=logic_rule,
                is_input=is_input
            )

            if is_input:
                self.input_nodes.add(node_name)

            nodes_created += 1
        
        print(f"Created {nodes_created} nodes ({len(self.input_nodes)} input nodes)")
        return nodes_created

    def set_input_states(self, input_states: Dict[str, bool]):
        """Set the states of input nodes."""
        for node_name, state in input_states.items():
            if node_name in self.nodes:
                self.nodes[node_name].state = state

    def initialize_logic_states(self):
        """Initialize all non-input nodes to match their logic rules."""
        # Get current states for evaluation
        current_states = {name: node.state for name, node in self.nodes.items()}

        # Update all non-input nodes to match their logic
        for node_name, node in self.nodes.items():
            if not node.is_input and node.update_function:
                try:
                    expected_state = node.update_function.evaluate(current_states)
                    if node.state != expected_state:
                        node.state = expected_state
                        current_states[node_name] = expected_state
                except:
                    pass
    
    def reset(self):
        """Reset all non-input nodes: fate nodes to False, others to random."""
        # Define output/fate nodes that should always start as False
        fate_nodes = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}

        for node in self.nodes.values():
            if not node.is_input:
                if node.name in fate_nodes:
                    # Fate nodes always start as False (biologically correct)
                    node.state = False
                else:
                    # All other non-input nodes start RANDOM by default
                    node.state = random.choice([True, False])
    
    def get_all_states(self) -> Dict[str, bool]:
        """Get current states of all nodes."""
        return {name: node.state for name, node in self.nodes.items()}
    
    def netlogo_single_gene_update(self):
        """TRUE NetLogo-style: randomly select ONE gene and update it."""
        # Get all non-input genes
        non_input_genes = [name for name, node in self.nodes.items()
                          if not node.is_input and node.update_function]

        if not non_input_genes:
            return None

        # TRUE NetLogo approach: randomly select ONE gene (no eligibility checking)
        selected_gene = random.choice(non_input_genes)
        gene_node = self.nodes[selected_gene]

        # Get current states of all nodes for logic evaluation
        current_states = {name: node.state for name, node in self.nodes.items()}

        # Evaluate the gene's rule and update ONLY this gene
        new_state = gene_node.update_function.evaluate(current_states)

        # Update only this one gene (NetLogo style)
        if gene_node.state != new_state:
            gene_node.state = new_state
            return selected_gene  # Return which gene was updated

        return None  # No state change

    def simulate(self, steps: int, input_states: Dict[str, bool] = None) -> Dict[str, bool]:
        """Run NetLogo-style simulation for specified number of steps."""
        for step in range(steps):
            self.netlogo_single_gene_update()

            # CRITICAL FIX: Re-enforce input states after each update to prevent corruption
            if input_states:
                for node_name, state in input_states.items():
                    if node_name in self.nodes:
                        self.nodes[node_name].state = state

        return self.get_all_states()


def load_node_names(file_path: str, description: str = "nodes") -> List[str]:
    """Load node names from file (one name per line)."""
    node_names = []
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            node_names.append(line)
    
    print(f"Loaded {len(node_names)} {description} from {file_path}")
    return node_names


def generate_all_combinations(input_nodes: List[str]) -> List[Dict[str, bool]]:
    """Generate all possible combinations of input node states."""
    combinations = []
    
    # Generate all 2^n combinations using itertools.product
    for values in itertools.product([False, True], repeat=len(input_nodes)):
        combination = {node: value for node, value in zip(input_nodes, values)}
        combinations.append(combination)
    
    print(f"Generated {len(combinations)} input combinations (2^{len(input_nodes)})")
    return combinations


def run_all_combinations(network: StandaloneGeneNetwork, 
                        input_nodes: List[str],
                        output_nodes: List[str],
                        runs: int,
                        steps: int,
                        verbose: bool = False) -> Dict:
    """Run simulations for all input combinations and track output activation."""
    
    # Generate all combinations
    combinations = generate_all_combinations(input_nodes)
    
    # Results structure: {combo_id: {output_node: activation_count}}
    results = {}
    
    print(f"\nRunning {len(combinations)} combinations × {runs} runs × {steps} steps...")
    print(f"Total propagation steps: {len(combinations) * runs * steps:,}")
    
    for combo_idx, input_states in enumerate(combinations):
        if verbose or (combo_idx + 1) % max(1, len(combinations) // 20) == 0:
            progress = (combo_idx + 1) / len(combinations) * 100
            print(f"  Progress: {combo_idx + 1}/{len(combinations)} ({progress:.1f}%)")
        
        # Track activation counts for this combination
        output_counts = {node: 0 for node in output_nodes}
        
        # Run multiple simulations for this combination
        for run in range(runs):
            # Reset and set inputs
            network.reset()
            network.set_input_states(input_states)
            network.initialize_logic_states()
            
            # Run simulation
            final_states = network.simulate(steps, input_states=input_states)
            
            # Count activations for each output node
            for output_node in output_nodes:
                if final_states.get(output_node, False):
                    output_counts[output_node] += 1
        
        # Store results
        results[combo_idx] = {
            'input_states': input_states,
            'output_counts': output_counts,
            'output_probabilities': {node: count / runs for node, count in output_counts.items()}
        }
    
    return results


def find_best_combinations(results: Dict, 
                           output_nodes: List[str],
                           top_n: int = 1) -> Dict:
    """Find the best input combinations for each output node."""
    
    best_combinations = {}
    
    for output_node in output_nodes:
        # Sort all combinations by activation probability for this output node
        sorted_combos = sorted(
            results.items(),
            key=lambda x: x[1]['output_probabilities'][output_node],
            reverse=True
        )
        
        # Get top N combinations
        top_combos = []
        for combo_idx, combo_data in sorted_combos[:top_n]:
            top_combos.append({
                'combo_idx': combo_idx,
                'input_states': combo_data['input_states'],
                'activation_probability': combo_data['output_probabilities'][output_node],
                'activation_count': combo_data['output_counts'][output_node],
                'other_outputs': {
                    node: combo_data['output_probabilities'][node]
                    for node in output_nodes if node != output_node
                }
            })
        
        best_combinations[output_node] = top_combos
    
    return best_combinations


def analyze_pairwise_comparisons(results: Dict, 
                                fate_nodes: List[str]) -> Dict:
    """Analyze pairwise comparisons between fate nodes."""
    
    comparisons = {}
    
    # Define all pairwise comparisons
    pairs = [
        ('Proliferation', 'Apoptosis'),
        ('Growth_Arrest', 'Apoptosis'),
        ('Proliferation', 'Growth_Arrest')
    ]
    
    for node_a, node_b in pairs:
        # Skip if nodes don't exist in the list
        if node_a not in fate_nodes or node_b not in fate_nodes:
            continue
        
        # Find combinations where node_a > node_b
        a_higher = []
        b_higher = []
        
        for combo_idx, combo_data in results.items():
            prob_a = combo_data['output_probabilities'][node_a]
            prob_b = combo_data['output_probabilities'][node_b]
            
            if prob_a > prob_b:
                a_higher.append({
                    'combo_idx': combo_idx,
                    'input_states': combo_data['input_states'],
                    'prob_a': prob_a,
                    'prob_b': prob_b,
                    'difference': prob_a - prob_b
                })
            elif prob_b > prob_a:
                b_higher.append({
                    'combo_idx': combo_idx,
                    'input_states': combo_data['input_states'],
                    'prob_a': prob_a,
                    'prob_b': prob_b,
                    'difference': prob_b - prob_a
                })
        
        # Sort by difference (highest first)
        a_higher.sort(key=lambda x: x['difference'], reverse=True)
        b_higher.sort(key=lambda x: x['difference'], reverse=True)
        
        comparisons[f"{node_a}_vs_{node_b}"] = {
            'node_a': node_a,
            'node_b': node_b,
            'a_higher_count': len(a_higher),
            'b_higher_count': len(b_higher),
            'a_higher_combos': a_higher[:10],  # Top 10
            'b_higher_combos': b_higher[:10]   # Top 10
        }
    
    return comparisons


def print_pairwise_comparisons(comparisons: Dict):
    """Print pairwise comparison analysis."""
    
    print(f"\n{'='*80}")
    print(f"PAIRWISE FATE NODE COMPARISONS")
    print(f"{'='*80}\n")
    
    for comp_key, comp_data in comparisons.items():
        node_a = comp_data['node_a']
        node_b = comp_data['node_b']
        
        print(f"\n{node_a} vs {node_b}:")
        print(f"  {node_a} > {node_b}: {comp_data['a_higher_count']} combinations")
        print(f"  {node_b} > {node_a}: {comp_data['b_higher_count']} combinations")
        
        # Show top cases where node_a > node_b
        if comp_data['a_higher_combos']:
            print(f"\n  Top cases where {node_a} > {node_b}:")
            for i, combo in enumerate(comp_data['a_higher_combos'][:5], 1):
                print(f"\n    Case {i}: {node_a}={combo['prob_a']*100:.1f}%, {node_b}={combo['prob_b']*100:.1f}% (diff: {combo['difference']*100:.1f}%)")
                print(f"      Input combination:")
                for input_node, state in sorted(combo['input_states'].items()):
                    print(f"        {input_node}: {'ON' if state else 'OFF'}")
        
        # Show top cases where node_b > node_a
        if comp_data['b_higher_combos']:
            print(f"\n  Top cases where {node_b} > {node_a}:")
            for i, combo in enumerate(comp_data['b_higher_combos'][:5], 1):
                print(f"\n    Case {i}: {node_b}={combo['prob_b']*100:.1f}%, {node_a}={combo['prob_a']*100:.1f}% (diff: {combo['difference']*100:.1f}%)")
                print(f"      Input combination:")
                for input_node, state in sorted(combo['input_states'].items()):
                    print(f"        {input_node}: {'ON' if state else 'OFF'}")
        
        print()


def print_results(best_combinations: Dict, 
                 output_nodes: List[str],
                 runs: int):
    """Print formatted results."""
    
    print(f"\n{'='*80}")
    print(f"BEST COMBINATIONS FOR OUTPUT NODES")
    print(f"{'='*80}\n")
    
    for output_node in output_nodes:
        print(f"{output_node}:")
        
        for rank, combo in enumerate(best_combinations[output_node], 1):
            if len(best_combinations[output_node]) > 1:
                print(f"  Rank {rank}:")
                indent = "    "
            else:
                indent = "  "
            
            prob = combo['activation_probability']
            count = combo['activation_count']
            print(f"{indent}Best activation: {prob*100:.1f}% ({count}/{runs} runs)")
            
            print(f"{indent}Input combination:")
            for node, state in sorted(combo['input_states'].items()):
                print(f"{indent}  {node}: {'ON' if state else 'OFF'}")
            
            print(f"{indent}Other outputs at this combination:")
            for node, prob in sorted(combo['other_outputs'].items()):
                print(f"{indent}  {node}: {prob*100:.1f}%")
            
            print()


def main():
    parser = argparse.ArgumentParser(
        description='Gene Network Confusion Matrix Tool - Find optimal input combinations for each output node'
    )
    parser.add_argument('bnd_file', help='Path to .bnd gene network file')
    parser.add_argument('input_nodes_file', help='File with input node names (one per line)')
    parser.add_argument('output_nodes_file', help='File with output node names (one per line)')
    parser.add_argument('--runs', type=int, default=100, 
                       help='Number of simulation runs per combination (default: 100)')
    parser.add_argument('--steps', type=int, default=1000, 
                       help='Number of propagation steps per run (default: 1000)')
    parser.add_argument('--output', help='Output file for results (JSON format)')
    parser.add_argument('--verbose', action='store_true', 
                       help='Show progress for each combination')
    parser.add_argument('--top-n', type=int, default=1, 
                       help='Show top N combinations per output (default: 1)')
    
    args = parser.parse_args()
    
    # Load network
    network = StandaloneGeneNetwork()
    network.load_bnd_file(args.bnd_file)
    
    # Load input and output nodes
    input_nodes = load_node_names(args.input_nodes_file, "input nodes")
    output_nodes = load_node_names(args.output_nodes_file, "output nodes")
    
    # Validate nodes exist in network
    for node in input_nodes:
        if node not in network.nodes:
            print(f"ERROR: Input node '{node}' not found in network")
            return
    
    for node in output_nodes:
        if node not in network.nodes:
            print(f"ERROR: Output node '{node}' not found in network")
            return
    
    # Run all combinations
    results = run_all_combinations(
        network,
        input_nodes,
        output_nodes,
        args.runs,
        args.steps,
        args.verbose
    )
    
    # Find best combinations
    best_combinations = find_best_combinations(results, output_nodes, args.top_n)
    
    # Print results
    print_results(best_combinations, output_nodes, args.runs)
    
    # Analyze pairwise comparisons (for fate nodes)
    pairwise_comparisons = analyze_pairwise_comparisons(results, output_nodes)
    print_pairwise_comparisons(pairwise_comparisons)
    
    # Save to JSON if requested
    if args.output:
        output_data = {
            'bnd_file': args.bnd_file,
            'input_nodes': input_nodes,
            'output_nodes': output_nodes,
            'runs': args.runs,
            'steps': args.steps,
            'total_combinations': len(results),
            'best_combinations': best_combinations,
            'pairwise_comparisons': pairwise_comparisons,
            'all_results': results
        }
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nResults saved to {args.output}")


if __name__ == '__main__':
    main()
