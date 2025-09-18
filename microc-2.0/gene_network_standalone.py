#!/usr/bin/env python3
"""
Standalone Gene Network Simulator

Based on the improved gene_network.py with NetLogo-style single-gene updates.
Allows testing gene networks with custom input conditions and statistical analysis.

Usage:
    python gene_network_standalone.py network.bnd inputs.txt --runs 100 --steps 1000
"""

import argparse
import random
import re
from typing import Dict, List, Set, Optional
from collections import defaultdict, Counter
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
        
        # Parse nodes
        node_pattern = r'node\s+(\w+)\s*\{([^}]+)\}'
        nodes_created = 0
        
        for match in re.finditer(node_pattern, content, re.MULTILINE | re.DOTALL):
            node_name = match.group(1)
            node_content = match.group(2)
            
            # Check if it's an input node (rate_up = 0; rate_down = 0;)
            is_input = ('rate_up = 0' in node_content and 'rate_down = 0' in node_content)
            
            # Extract logic rule
            logic_match = re.search(r'logic\s*=\s*([^;]+);', node_content)
            logic_rule = logic_match.group(1).strip() if logic_match else ""
            
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

    def print_network_structure(self):
        """Print complete network structure for debugging."""
        print("\n" + "="*80)
        print("COMPLETE GENE NETWORK STRUCTURE")
        print("="*80)

        # Group nodes by type
        input_nodes = [(name, node) for name, node in self.nodes.items() if node.is_input]
        logic_nodes = [(name, node) for name, node in self.nodes.items() if not node.is_input]

        print(f"\nINPUT NODES ({len(input_nodes)}):")
        print("-" * 40)
        for name, node in sorted(input_nodes):
            print(f"  {name}: {node.state}")

        print(f"\nLOGIC NODES ({len(logic_nodes)}):")
        print("-" * 40)
        for name, node in sorted(logic_nodes):
            print(f"  {name}:")
            print(f"    Logic: {node.logic_rule}")
            print(f"    State: {node.state}")

            # Find dependencies
            deps = []
            if node.logic_rule:
                for other_name in self.nodes:
                    if other_name != name and other_name in node.logic_rule:
                        deps.append(other_name)
            print(f"    Dependencies: {deps}")
            print()

        print("="*80)

    def load_input_states(self, input_file: str) -> Dict[str, bool]:
        """Load input node states from file."""
        input_states = {}
        
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    node_name, value = line.split('=', 1)
                    node_name = node_name.strip()
                    value = value.strip().lower()
                    
                    if value in ('true', '1', 'on', 'yes'):
                        input_states[node_name] = True
                    elif value in ('false', '0', 'off', 'no'):
                        input_states[node_name] = False
                    else:
                        print(f"Warning: Invalid value '{value}' for {node_name}, using False")
                        input_states[node_name] = False
        
        print(f"Loaded {len(input_states)} input states")
        return input_states
    
    def set_input_states(self, input_states: Dict[str, bool]):
        """Set the states of input nodes."""
        for node_name, state in input_states.items():
            if node_name in self.nodes:
                self.nodes[node_name].state = state

    def initialize_logic_states(self):
        """Initialize all non-input nodes to match their logic rules."""
        print("Initializing gene network logic states...")

        # Get current states for evaluation
        current_states = {name: node.state for name, node in self.nodes.items()}

        # Update all non-input nodes to match their logic
        updates_made = 0
        for node_name, node in self.nodes.items():
            if not node.is_input and node.update_function:
                try:
                    expected_state = node.update_function.evaluate(current_states)
                    if node.state != expected_state:
                        print(f"  Initializing {node_name}: {node.state} -> {expected_state}")
                        node.state = expected_state
                        current_states[node_name] = expected_state  # Update for next evaluations
                        updates_made += 1
                except Exception as e:
                    print(f"  Error initializing {node_name}: {e}")

        print(f"Initialization complete: {updates_made} nodes updated")
           
    
    def reset(self, random_init: bool = False):
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

    def netlogo_single_gene_update_debug(self):
        """TRUE NetLogo-style: randomly select ONE gene and update it."""
        # Get all non-input genes with update functions (FIXED: same as non-debug version)
        non_input_genes = [name for name, node in self.nodes.items()
                          if not node.is_input and node.update_function]

        if not non_input_genes:
            print("  DEBUG: No non-input genes to update")
            return None

        # TRUE NetLogo approach: randomly select ONE gene (no eligibility checking)
        selected_gene = random.choice(non_input_genes)
        gene_node = self.nodes[selected_gene]

        print(f"  DEBUG: Randomly selected gene '{selected_gene}' for update")
        print(f"    Logic rule: {gene_node.logic_rule}")
        print(f"    Current state: {gene_node.state}")

        # Get current states of all nodes for logic evaluation
        current_states = {name: node.state for name, node in self.nodes.items()}

        # Show dependency states
        deps = []
        for dep_name in gene_node.inputs:
            if dep_name in current_states:
                deps.append(f"{dep_name}={current_states[dep_name]}")
        print(f"    Dependencies: {', '.join(deps) if deps else 'None'}")

        # Evaluate the gene's rule and update ONLY this gene
        new_state = gene_node.update_function.evaluate(current_states)

        print(f"    Logic evaluation result: {new_state}")

        # Update only this one gene (NetLogo style)
        if gene_node.state != new_state:
            gene_node.state = new_state
            print(f"    STATE CHANGED: {selected_gene} {not new_state} -> {new_state}")
            return selected_gene  # Return which gene was updated
        else:
            print(f"    No state change for {selected_gene}")
            return None  # No state change
    
    def simulate(self, steps: int, debug_apoptosis: bool = False, debug_updates: bool = False,
                track_apoptosis_updates: bool = False, debug_steps: bool = False,
                print_network: bool = False, input_states: Dict[str, bool] = None) -> Dict[str, bool]:
        """Run NetLogo-style simulation for specified number of steps."""
        apoptosis_states = []
        update_counts = defaultdict(int) if debug_updates else None
        apoptosis_update_count = 0

        # Print network structure if requested
        if print_network:
            self.print_network_structure()

        for step in range(steps):
            if debug_steps:
                print(f"\nSTEP {step + 1}:")
                updated_gene = self.netlogo_single_gene_update_debug()
            else:
                updated_gene = self.netlogo_single_gene_update()

            # CRITICAL FIX: Re-enforce input states after each update to prevent corruption
            if input_states:
                for node_name, state in input_states.items():
                    if node_name in self.nodes:
                        self.nodes[node_name].state = state

            # Track apoptosis updates specifically
            if track_apoptosis_updates and updated_gene == 'Apoptosis':
                apoptosis_update_count += 1

            # Track update frequency
            if debug_updates and updated_gene:
                update_counts[updated_gene] += 1

            # Debug apoptosis pathway
            if debug_apoptosis and step % 100 == 0:
                current_states = self.get_all_states()
                apoptosis = current_states.get('Apoptosis', False)
                bcl2 = current_states.get('BCL2', False)
                erk = current_states.get('ERK', False)
                foxo3 = current_states.get('FOXO3', False)
                p53 = current_states.get('p53', False)

                apoptosis_states.append({
                    'step': step,
                    'apoptosis': apoptosis,
                    'bcl2': bcl2,
                    'erk': erk,
                    'foxo3': foxo3,
                    'p53': p53
                })

        final_states = self.get_all_states()
        if debug_apoptosis:
            final_states['_apoptosis_debug'] = apoptosis_states
        if debug_updates:
            final_states['_update_counts'] = dict(update_counts)
            final_states['_total_genes'] = len(self.nodes)
            final_states['_non_input_genes'] = len([n for n in self.nodes.values() if not n.is_input])
        if track_apoptosis_updates:
            final_states['_apoptosis_update_count'] = apoptosis_update_count

        return final_states


def run_simulation(bnd_file: str, input_file: str, runs: int, steps: int,
                  target_nodes: List[str] = None, verbose: bool = False,
                  random_init: bool = False, track_apoptosis_updates: bool = False,
                  debug_steps: bool = False, print_network: bool = False,
                  show_confusion_matrix: bool = False) -> Dict:
    """Run multiple simulations and collect statistics."""
    
    # Load network
    network = StandaloneGeneNetwork()
    network.load_bnd_file(bnd_file)
    
    # Load input conditions
    input_states = network.load_input_states(input_file)
    
    # Statistics collection
    all_results = []
    node_stats = defaultdict(Counter)
    target_stats = defaultdict(Counter)
    apoptosis_update_counts = []

    # Define all fate nodes for comprehensive tracking
    fate_nodes = ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']

    # Define metabolic nodes to track
    metabolic_nodes = ['mitoATP', 'glycoATP']

    # Confusion matrix for fate node coexistence
    fate_coexistence = defaultdict(int)

    print(f"\nRunning {runs} simulations with {steps} steps each...")

    for run in range(runs):
        if verbose and (run + 1) % (runs // 10) == 0:
            print(f"  Run {run + 1}/{runs}")

        # Reset and set inputs
        network.reset(random_init=random_init)
        network.set_input_states(input_states)

        # CRITICAL FIX: Initialize all nodes to match their logic rules
        if run == 0:  # Only show initialization output for first run
            network.initialize_logic_states()
        else:
            # Silent initialization for other runs
            current_states = {name: node.state for name, node in network.nodes.items()}
            for node_name, node in network.nodes.items():
                if not node.is_input and node.update_function:
                    try:
                        expected_state = node.update_function.evaluate(current_states)
                        if node.state != expected_state:
                            node.state = expected_state
                            current_states[node_name] = expected_state
                    except:
                        pass

        # Run simulation with debugging options
        final_states = network.simulate(steps, track_apoptosis_updates=track_apoptosis_updates,
                                       debug_steps=debug_steps, print_network=(print_network and run == 0),
                                       input_states=input_states)
        all_results.append(final_states)

        # Track apoptosis updates
        if track_apoptosis_updates:
            apoptosis_updates = final_states.get('_apoptosis_update_count', 0)
            apoptosis_final_state = final_states.get('Apoptosis', False)
            apoptosis_update_counts.append(apoptosis_updates)
            print(f"  Run {run + 1}: Apoptosis updated {apoptosis_updates} times, final state: {'ON' if apoptosis_final_state else 'OFF'}")
        
        # Collect statistics
        for node_name, state in final_states.items():
            node_stats[node_name][state] += 1

        # Track fate node coexistence for confusion matrix
        active_fate_nodes = [node for node in fate_nodes if final_states.get(node, False)]

        # Create a binary pattern for this combination
        pattern_bits = []
        for node in fate_nodes:  # ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']
            pattern_bits.append('1' if final_states.get(node, False) else '0')

        # Convert to readable pattern
        if len(active_fate_nodes) == 0:
            pattern_key = 'None'
        else:
            pattern_key = '+'.join(sorted(active_fate_nodes))

        fate_coexistence[pattern_key] += 1

        # Collect target node statistics
        if target_nodes:
            for node_name, state in final_states.items():
                if node_name in target_nodes:
                    target_stats[node_name][state] += 1

    # Calculate apoptosis update statistics
    apoptosis_stats = {}
    if track_apoptosis_updates and apoptosis_update_counts:
        apoptosis_stats = {
            'total_runs': len(apoptosis_update_counts),
            'zero_updates': sum(1 for count in apoptosis_update_counts if count == 0),
            'one_plus_updates': sum(1 for count in apoptosis_update_counts if count > 0),
            'avg_updates': sum(apoptosis_update_counts) / len(apoptosis_update_counts),
            'max_updates': max(apoptosis_update_counts),
            'update_counts': apoptosis_update_counts
        }

    # Calculate percentages
    results = {
        'runs': runs,
        'steps': steps,
        'input_conditions': input_states,
        'all_nodes': {},
        'target_nodes': {},
        'fate_nodes': {},
        'metabolic_nodes': {},
        'fate_coexistence': dict(fate_coexistence),
        'raw_results': all_results if runs <= 10 else [],  # Only store raw results for small runs
        'apoptosis_update_stats': apoptosis_stats if apoptosis_stats else None
    }
    
    # All nodes statistics
    for node_name, counts in node_stats.items():
        total = sum(counts.values())
        results['all_nodes'][node_name] = {
            'ON': f"{counts[True]}/{total} ({100*counts[True]/total:.1f}%)",
            'OFF': f"{counts[False]}/{total} ({100*counts[False]/total:.1f}%)"
        }
    
    # Fate nodes statistics (always include all fate nodes)
    for node_name in fate_nodes:
        if node_name in node_stats:
            counts = node_stats[node_name]
            total = sum(counts.values())
            results['fate_nodes'][node_name] = {
                'ON': f"{counts[True]}/{total} ({100*counts[True]/total:.1f}%)",
                'OFF': f"{counts[False]}/{total} ({100*counts[False]/total:.1f}%)"
            }

    # Metabolic nodes statistics (always include metabolic nodes)
    for node_name in metabolic_nodes:
        if node_name in node_stats:
            counts = node_stats[node_name]
            total = sum(counts.values())
            results['metabolic_nodes'][node_name] = {
                'ON': f"{counts[True]}/{total} ({100*counts[True]/total:.1f}%)",
                'OFF': f"{counts[False]}/{total} ({100*counts[False]/total:.1f}%)"
            }

    # Target nodes statistics
    if target_nodes:
        for node_name in target_nodes:
            if node_name in target_stats:
                counts = target_stats[node_name]
                total = sum(counts.values())
                results['target_nodes'][node_name] = {
                    'ON': f"{counts[True]}/{total} ({100*counts[True]/total:.1f}%)",
                    'OFF': f"{counts[False]}/{total} ({100*counts[False]/total:.1f}%)"
                }
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Standalone Gene Network Simulator')
    parser.add_argument('bnd_file', help='Path to .bnd gene network file')
    parser.add_argument('input_file', help='Path to input states file')
    parser.add_argument('--runs', type=int, default=100, help='Number of simulation runs')
    parser.add_argument('--steps', type=int, default=1000, help='Number of propagation steps per run')
    parser.add_argument('--target-nodes', nargs='+', help='Specific nodes to analyze')
    parser.add_argument('--output', help='Output file for results (JSON format)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--list-nodes', action='store_true', help='List all nodes in the network and exit')
    parser.add_argument('--random-init', action='store_true', help='Use NetLogo-style random gene initialization (50% True/False)')
    parser.add_argument('--track-apoptosis', action='store_true', help='Track and print Apoptosis node updates for each run')
    parser.add_argument('--debug-steps', action='store_true', help='Print detailed information for each simulation step')
    parser.add_argument('--print-network', action='store_true', help='Print complete network structure before simulation')
    parser.add_argument('--confusion-matrix', action='store_true', help='Show detailed confusion matrix for fate node coexistence')

    args = parser.parse_args()

    # List nodes mode
    if args.list_nodes:
        network = StandaloneGeneNetwork()
        network.load_bnd_file(args.bnd_file)

        print(f"\nNodes in {args.bnd_file}:")
        print(f"{'='*50}")

        input_nodes = [name for name, node in network.nodes.items() if node.is_input]
        output_nodes = [name for name, node in network.nodes.items() if not node.is_input and not node.logic_rule]
        logic_nodes = [name for name, node in network.nodes.items() if not node.is_input and node.logic_rule]

        print(f"Input nodes ({len(input_nodes)}):")
        for node in sorted(input_nodes):
            print(f"  {node}")

        print(f"\nLogic nodes ({len(logic_nodes)}):")
        for node in sorted(logic_nodes):
            logic = network.nodes[node].logic_rule
            print(f"  {node}: {logic}")

        if output_nodes:
            print(f"\nOutput nodes ({len(output_nodes)}):")
            for node in sorted(output_nodes):
                print(f"  {node}")

        return
    
    # Run simulation
    results = run_simulation(
        args.bnd_file,
        args.input_file,
        args.runs,
        args.steps,
        args.target_nodes,
        args.verbose,
        args.random_init,
        args.track_apoptosis,
        args.debug_steps,
        args.print_network,
        args.confusion_matrix
    )
    
    # Print results
    print(f"\n{'='*60}")
    print(f"GENE NETWORK SIMULATION RESULTS")
    print(f"{'='*60}")
    print(f"Network: {args.bnd_file}")
    print(f"Inputs: {args.input_file}")
    print(f"Runs: {args.runs}, Steps: {args.steps}")
    
    print(f"\nInput Conditions:")
    for node, state in results['input_conditions'].items():
        print(f"  {node}: {'ON' if state else 'OFF'}")
    
    # Always show fate node results
    print(f"\nFate Node Results:")
    for node in ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']:
        if node in results['fate_nodes']:
            stats = results['fate_nodes'][node]
            print(f"  {node}: ON {stats['ON']}, OFF {stats['OFF']}")
        else:
            print(f"  {node}: NOT FOUND")

    # Always show metabolic node results
    print(f"\nMetabolic Node Results:")
    for node in ['mitoATP', 'glycoATP']:
        if node in results['metabolic_nodes']:
            stats = results['metabolic_nodes'][node]
            print(f"  {node}: ON {stats['ON']}, OFF {stats['OFF']}")
        else:
            print(f"  {node}: NOT FOUND")

    # Show fate node coexistence (confusion matrix for pairs only)
    print(f"\nFate Node Pairs Coexistence Matrix:")
    print(f"{'='*40}")
    total_runs = results['runs']
    coexistence = results['fate_coexistence']

    # Generate all possible pairs (couples) of fate nodes
    import itertools
    fate_node_names = ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']

    # Show all possible pairs with their counts (including 0s)
    for combo in itertools.combinations(fate_node_names, 2):
        pattern_key = '+'.join(sorted(combo))
        count = coexistence.get(pattern_key, 0)
        percentage = (count / total_runs) * 100
        print(f"  {pattern_key}: {count}/{total_runs} ({percentage:.1f}%)")

    if args.target_nodes:
        print(f"\nTarget Node Results:")
        for node in args.target_nodes:
            if node in results['target_nodes']:
                stats = results['target_nodes'][node]
                print(f"  {node}: ON {stats['ON']}, OFF {stats['OFF']}")
            else:
                print(f"  {node}: NOT FOUND")
    
    if args.verbose:
        print(f"\nAll Node Results:")
        for node, stats in sorted(results['all_nodes'].items()):
            print(f"  {node}: ON {stats['ON']}, OFF {stats['OFF']}")

    # Show apoptosis update statistics
    if args.track_apoptosis and 'apoptosis_update_stats' in results:
        stats = results['apoptosis_update_stats']
        print(f"\nApoptosis Update Statistics:")
        print(f"  Total runs: {stats['total_runs']}")
        print(f"  Runs with 0 updates: {stats['zero_updates']} ({100*stats['zero_updates']/stats['total_runs']:.1f}%)")
        print(f"  Runs with 1+ updates: {stats['one_plus_updates']} ({100*stats['one_plus_updates']/stats['total_runs']:.1f}%)")
        print(f"  Average updates per run: {stats['avg_updates']:.2f}")
        print(f"  Max updates in a run: {stats['max_updates']}")

    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == '__main__':
    main()
