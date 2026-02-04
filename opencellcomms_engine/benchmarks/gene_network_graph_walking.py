#!/usr/bin/env python3
"""
Gene Network Simulator with NetLogo-style Graph Walking Updates

This implementation replicates the NetLogo gene network update mechanism:
1. Graph-walking updates: Follow links from the last visited node instead of 
   randomly selecting any gene uniformly
2. Transient fate nodes: Fate nodes reset to OFF after firing (triggering action)
3. Tracks "ever reached fate" instead of just final state

Key differences from gene_network_standalone.py:
- Updates follow the network topology (signal propagation chains)
- Fate nodes are triggers that reset after firing
- Statistics track both "ever fired" and "final state" for comparison

Usage:
    python gene_network_graph_walking.py network.bnd inputs.txt --runs 100 --steps 1000
"""

import argparse
import random
import re
from typing import Dict, List, Set, Optional, Tuple
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
    """Represents a single node in the gene network with graph connectivity."""
    
    # Class-level fate node names
    FATE_NODES = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}
    
    def __init__(self, name: str, logic_rule: str = "", is_input: bool = False):
        self.name = name
        self.logic_rule = logic_rule
        self.is_input = is_input
        self.state = False
        self.inputs: Set[str] = set()  # Nodes that this node depends on
        self.outputs: Set[str] = set()  # Nodes that depend on this node (outgoing links)
        self.is_fate_node = name in self.FATE_NODES
        
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


class GraphWalkingGeneNetwork:
    """
    Gene network simulator with NetLogo-style graph-walking updates.
    
    Key features:
    - Builds explicit graph structure with outgoing links
    - Updates follow links from last visited node
    - Fate nodes reset after firing (transient triggers)
    - Tracks both "ever fired" and "final state" statistics
    """
    
    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.input_nodes: Set[str] = set()
        self.last_node: Optional[str] = None  # NetLogo's my-last-node
        
        # Statistics for fate node firing events
        self.fate_fire_counts: Dict[str, int] = defaultdict(int)
    
    def load_bnd_file(self, bnd_file: str):
        """Load gene network from .bnd file and build graph structure."""
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
            if logic_rule.strip('() ') == node_name:
                is_input = True
                logic_rule = ""

            # Create node
            self.nodes[node_name] = NetworkNode(
                name=node_name,
                logic_rule=logic_rule,
                is_input=is_input
            )

            if is_input:
                self.input_nodes.add(node_name)

            nodes_created += 1
        
        # Build graph structure: add outgoing links
        self._build_graph_links()
        
        print(f"Created {nodes_created} nodes ({len(self.input_nodes)} input nodes)")
        
        # Print graph statistics
        total_links = sum(len(node.outputs) for node in self.nodes.values())
        print(f"Built graph with {total_links} directed links")
        
        return nodes_created
    
    def _build_graph_links(self):
        """Build outgoing links for each node based on logic rules."""
        # For each node B with a logic rule, find all nodes A that B depends on
        # Then add B to A's outputs (A → B means A influences B)
        for node_name, node in self.nodes.items():
            for input_name in node.inputs:
                if input_name in self.nodes:
                    # input_name influences node_name, so add outgoing link
                    self.nodes[input_name].outputs.add(node_name)
    
    def print_network_structure(self):
        """Print complete network structure with graph connectivity."""
        print("\n" + "="*80)
        print("GENE NETWORK STRUCTURE (Graph Walking Mode)")
        print("="*80)

        # Group nodes by type
        input_nodes = [(name, node) for name, node in self.nodes.items() if node.is_input]
        fate_nodes = [(name, node) for name, node in self.nodes.items() if node.is_fate_node]
        logic_nodes = [(name, node) for name, node in self.nodes.items() 
                       if not node.is_input and not node.is_fate_node]

        print(f"\nINPUT NODES ({len(input_nodes)}):")
        print("-" * 40)
        for name, node in sorted(input_nodes):
            out_links = ', '.join(sorted(node.outputs)) if node.outputs else '(none)'
            print(f"  {name}: state={node.state}, outputs→[{out_links}]")

        print(f"\nFATE NODES ({len(fate_nodes)}):")
        print("-" * 40)
        for name, node in sorted(fate_nodes):
            in_links = ', '.join(sorted(node.inputs)) if node.inputs else '(none)'
            print(f"  {name}: state={node.state}")
            print(f"    Logic: {node.logic_rule}")
            print(f"    Inputs←[{in_links}]")

        print(f"\nLOGIC NODES ({len(logic_nodes)}):")
        print("-" * 40)
        for name, node in sorted(logic_nodes):
            in_links = ', '.join(sorted(node.inputs)) if node.inputs else '(none)'
            out_links = ', '.join(sorted(node.outputs)) if node.outputs else '(none)'
            print(f"  {name}:")
            print(f"    Logic: {node.logic_rule}")
            print(f"    State: {node.state}")
            print(f"    Inputs←[{in_links}]")
            print(f"    Outputs→[{out_links}]")
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
    
    def reset(self, random_init: bool = True):
        """Reset network for new simulation run."""
        # Reset all non-input nodes
        for node in self.nodes.values():
            if not node.is_input:
                if node.is_fate_node:
                    # Fate nodes always start as False
                    node.state = False
                else:
                    # Other nodes: random initialization (NetLogo style)
                    node.state = random.choice([True, False]) if random_init else False
        
        # Reset last_node to a random input node (or any node if no inputs)
        if self.input_nodes:
            self.last_node = random.choice(list(self.input_nodes))
        else:
            self.last_node = random.choice(list(self.nodes.keys()))
        
        # Reset fate fire counts for this run
        self.fate_fire_counts = defaultdict(int)
    
    def get_all_states(self) -> Dict[str, bool]:
        """Get current states of all nodes."""
        return {name: node.state for name, node in self.nodes.items()}
    
    def _get_random_input_node(self) -> str:
        """Get a random input node (for resetting after fate node)."""
        if self.input_nodes:
            return random.choice(list(self.input_nodes))
        # Fallback: any node with outputs
        nodes_with_outputs = [name for name, node in self.nodes.items() if node.outputs]
        if nodes_with_outputs:
            return random.choice(nodes_with_outputs)
        return random.choice(list(self.nodes.keys()))
    
    def graph_walking_update(self, debug: bool = False) -> Tuple[Optional[str], bool]:
        """
        NetLogo-style graph walking update.
        
        1. Start from last_node
        2. Pick one random outgoing link
        3. Update the target node
        4. If it's a fate node and it fires, reset it and return to input
        5. Otherwise, set last_node to the updated node
        
        Returns:
            Tuple of (updated_node_name, fate_fired)
        """
        current_node = self.nodes.get(self.last_node)
        if not current_node:
            # Fallback: pick random input
            self.last_node = self._get_random_input_node()
            current_node = self.nodes[self.last_node]
        
        # Get outgoing links (nodes that depend on current node)
        if not current_node.outputs:
            # No outgoing links: reset to random input node
            if debug:
                print(f"  Node '{self.last_node}' has no outputs, resetting to input")
            self.last_node = self._get_random_input_node()
            return None, False
        
        # Pick ONE random outgoing link (NetLogo: ask one-of my-out-links)
        target_name = random.choice(list(current_node.outputs))
        target_node = self.nodes[target_name]
        
        if debug:
            print(f"  Graph walk: {self.last_node} → {target_name}")
            print(f"    Target logic: {target_node.logic_rule}")
            print(f"    Target current state: {target_node.state}")
        
        # Evaluate target node's logic rule
        current_states = self.get_all_states()
        
        if target_node.update_function:
            new_state = target_node.update_function.evaluate(current_states)
            old_state = target_node.state
            
            if debug:
                print(f"    Logic evaluation: {new_state}")
            
            # Check if state changed
            state_changed = (old_state != new_state)
            
            # Update the node
            target_node.state = new_state
            
            # Handle fate nodes specially (NetLogo transient behavior)
            fate_fired = False
            if target_node.is_fate_node and new_state:
                # Fate node fired!
                self.fate_fire_counts[target_name] += 1
                fate_fired = True
                
                if debug:
                    print(f"    FATE FIRED: {target_name} (count: {self.fate_fire_counts[target_name]})")
                
                # Reset fate node to OFF (NetLogo: ask end2 [ set my-active false ])
                target_node.state = False
                
                # Return to a random input node (NetLogo behavior)
                self.last_node = self._get_random_input_node()
                
                if debug:
                    print(f"    Reset to input node: {self.last_node}")
            else:
                # Regular node: continue walking from this node
                self.last_node = target_name
            
            if state_changed and debug:
                print(f"    State changed: {old_state} → {new_state}")
            
            return target_name, fate_fired
        else:
            # No update function (shouldn't happen for non-input nodes)
            self.last_node = target_name
            return None, False
    
    def simulate(self, steps: int, input_states: Dict[str, bool] = None,
                debug_steps: bool = False, print_network: bool = False,
                reversible: bool = True) -> Dict:
        """
        Run NetLogo-style graph walking simulation.
        
        Args:
            steps: Number of update steps
            input_states: Dictionary of input node states to enforce
            debug_steps: Print debug info for each step
            print_network: Print network structure at start
            reversible: If False, stop after first fate fires (NetLogo non-reversible mode)
        
        Returns:
            Dictionary with final states and fate firing statistics
        """
        if print_network:
            self.print_network_structure()
        
        fate_events = []  # Track when fates fire
        first_fate = None  # Track first fate (for non-reversible mode)
        stopped_early = False
        
        for step in range(steps):
            if debug_steps:
                print(f"\nSTEP {step + 1}:")
            
            updated_node, fate_fired = self.graph_walking_update(debug=debug_steps)
            
            # Re-enforce input states after each update
            if input_states:
                for node_name, state in input_states.items():
                    if node_name in self.nodes:
                        self.nodes[node_name].state = state
            
            # Track fate events
            if fate_fired and updated_node:
                fate_events.append({
                    'step': step,
                    'fate': updated_node
                })
                
                # Non-reversible mode: stop after first fate fires
                if not reversible and first_fate is None:
                    first_fate = updated_node
                    stopped_early = True
                    if debug_steps:
                        print(f"    NON-REVERSIBLE: Stopping after first fate '{first_fate}'")
                    break
        
        # Compile results
        final_states = self.get_all_states()
        
        return {
            'final_states': final_states,
            'fate_fire_counts': dict(self.fate_fire_counts),
            'fate_events': fate_events,
            'total_fate_fires': sum(self.fate_fire_counts.values()),
            'first_fate': first_fate,
            'stopped_early': stopped_early
        }


def apply_hierarchy(fates_fired: Dict[str, bool]) -> str:
    """
    Apply phenotype hierarchy to determine effective fate.
    Hierarchy: Proliferation > Growth_Arrest > Apoptosis > Necrosis
    
    Args:
        fates_fired: Dictionary of fate_name -> bool (True if ever fired)
    
    Returns:
        The winning fate name, or 'Quiescent' if none fired
    """
    hierarchy = ['Proliferation', 'Growth_Arrest', 'Apoptosis', 'Necrosis']
    for fate in hierarchy:
        if fates_fired.get(fate, False):
            return fate
    return 'Quiescent'


def run_simulation(bnd_file: str, input_file: str, runs: int, steps: int,
                  verbose: bool = False, debug_steps: bool = False,
                  print_network: bool = False, reversible: bool = True,
                  use_hierarchy: bool = False) -> Dict:
    """Run multiple simulations and collect statistics."""
    
    # Load network
    network = GraphWalkingGeneNetwork()
    network.load_bnd_file(bnd_file)
    
    # Load input conditions
    input_states = network.load_input_states(input_file)
    
    # Statistics collection
    fate_nodes = ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']
    metabolic_nodes = ['mitoATP', 'glycoATP']
    
    # Track both "ever fired" and "final state" statistics
    ever_fired_counts = defaultdict(int)  # Runs where fate fired at least once
    final_state_counts = defaultdict(lambda: Counter())  # Final state statistics
    total_fire_counts = defaultdict(int)  # Total fire events across all runs
    first_fate_counts = defaultdict(int)  # First fate to fire in each run (non-reversible)
    hierarchy_fate_counts = defaultdict(int)  # Fate after applying hierarchy
    first_fire_steps = defaultdict(list)  # Step when each fate FIRST fires (for timing analysis)
    no_fate_count = 0  # Runs where no fate fired
    
    # Build mode string
    if use_hierarchy:
        mode_str = "GRAPH WALKING (HIERARCHY: Prolif > GA > Apop)"
    elif not reversible:
        mode_str = "GRAPH WALKING (NON-REVERSIBLE)"
    else:
        mode_str = "GRAPH WALKING (REVERSIBLE)"
    print(f"\nRunning {runs} simulations with {steps} steps each ({mode_str})...")
    
    for run in range(runs):
        if verbose and runs >= 10 and (run + 1) % (runs // 10) == 0:
            print(f"  Run {run + 1}/{runs}")
        
        # Reset network
        network.reset(random_init=True)
        network.set_input_states(input_states)
        
        # Run simulation
        result = network.simulate(
            steps, 
            input_states=input_states,
            debug_steps=debug_steps and run == 0,
            print_network=print_network and run == 0,
            reversible=reversible
        )
        
        # Collect "ever fired" statistics
        fates_fired_this_run = {}
        for fate_name, count in result['fate_fire_counts'].items():
            if count > 0:
                ever_fired_counts[fate_name] += 1
                fates_fired_this_run[fate_name] = True
            total_fire_counts[fate_name] += count
        
        # Track first fire step for each fate (for timing analysis)
        first_fire_in_run = {}
        for event in result.get('fate_events', []):
            fate_name = event['fate']
            step = event['step']
            if fate_name not in first_fire_in_run:
                first_fire_in_run[fate_name] = step
        for fate_name, step in first_fire_in_run.items():
            first_fire_steps[fate_name].append(step)
        
        # Track first fate (for non-reversible mode statistics)
        if result.get('first_fate'):
            first_fate_counts[result['first_fate']] += 1
        elif not reversible:
            # In non-reversible mode, if no fate fired, count it
            no_fate_count += 1
        
        # Apply hierarchy to determine effective fate
        if use_hierarchy or reversible:  # Always track hierarchy stats for comparison
            effective_fate = apply_hierarchy(fates_fired_this_run)
            hierarchy_fate_counts[effective_fate] += 1
        
        # Collect final state statistics
        for node_name, state in result['final_states'].items():
            final_state_counts[node_name][state] += 1
    
    # Compile results
    results = {
        'runs': runs,
        'steps': steps,
        'update_mode': 'graph_walking',
        'reversible': reversible,
        'use_hierarchy': use_hierarchy,
        'input_conditions': input_states,
        'fate_statistics': {},
        'first_fate_statistics': {},
        'hierarchy_statistics': {},
        'metabolic_statistics': {},
        'all_node_final_states': {}
    }
    
    # Fate node statistics (both "ever fired" and "final state")
    for fate_name in fate_nodes:
        ever_count = ever_fired_counts.get(fate_name, 0)
        total_fires = total_fire_counts.get(fate_name, 0)
        final_on = final_state_counts[fate_name].get(True, 0)
        final_off = final_state_counts[fate_name].get(False, 0)
        first_fate = first_fate_counts.get(fate_name, 0)
        
        results['fate_statistics'][fate_name] = {
            'ever_fired_runs': ever_count,
            'ever_fired_pct': 100 * ever_count / runs,
            'total_fire_events': total_fires,
            'avg_fires_per_run': total_fires / runs,
            'final_state_ON': final_on,
            'final_state_ON_pct': 100 * final_on / runs,
            'final_state_OFF': final_off,
            'final_state_OFF_pct': 100 * final_off / runs,
            'first_fate_count': first_fate,
            'first_fate_pct': 100 * first_fate / runs
        }
    
    # First fate summary (for non-reversible mode)
    results['first_fate_statistics'] = {
        'counts': dict(first_fate_counts),
        'no_fate': no_fate_count,
        'no_fate_pct': 100 * no_fate_count / runs
    }
    
    # Hierarchy statistics (effective fate after applying priority rules)
    for fate_name in fate_nodes + ['Quiescent']:
        count = hierarchy_fate_counts.get(fate_name, 0)
        results['hierarchy_statistics'][fate_name] = {
            'count': count,
            'pct': 100 * count / runs
        }
    
    # Metabolic node statistics (final state only)
    for node_name in metabolic_nodes:
        if node_name in final_state_counts:
            final_on = final_state_counts[node_name].get(True, 0)
            final_off = final_state_counts[node_name].get(False, 0)
            results['metabolic_statistics'][node_name] = {
                'ON': final_on,
                'ON_pct': 100 * final_on / runs,
                'OFF': final_off,
                'OFF_pct': 100 * final_off / runs
            }
    
    # All nodes final state
    for node_name, counts in final_state_counts.items():
        total = sum(counts.values())
        results['all_node_final_states'][node_name] = {
            'ON': counts.get(True, 0),
            'ON_pct': 100 * counts.get(True, 0) / total if total > 0 else 0,
            'OFF': counts.get(False, 0),
            'OFF_pct': 100 * counts.get(False, 0) / total if total > 0 else 0
        }
    
    # Timing statistics: when do fates first fire?
    results['timing_statistics'] = {}
    for fate_name in fate_nodes:
        steps_list = first_fire_steps.get(fate_name, [])
        if steps_list:
            import statistics
            results['timing_statistics'][fate_name] = {
                'count': len(steps_list),
                'min_step': min(steps_list),
                'max_step': max(steps_list),
                'mean_step': statistics.mean(steps_list),
                'median_step': statistics.median(steps_list),
                'stdev_step': statistics.stdev(steps_list) if len(steps_list) > 1 else 0,
                'percentile_25': sorted(steps_list)[len(steps_list) // 4] if len(steps_list) >= 4 else min(steps_list),
                'percentile_75': sorted(steps_list)[3 * len(steps_list) // 4] if len(steps_list) >= 4 else max(steps_list)
            }
        else:
            results['timing_statistics'][fate_name] = {
                'count': 0,
                'min_step': None,
                'max_step': None,
                'mean_step': None,
                'median_step': None,
                'stdev_step': None,
                'percentile_25': None,
                'percentile_75': None
            }
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Gene Network Simulator with NetLogo-style Graph Walking Updates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('bnd_file', help='Path to .bnd gene network file')
    parser.add_argument('input_file', help='Path to input states file')
    parser.add_argument('--runs', type=int, default=100, help='Number of simulation runs')
    parser.add_argument('--steps', type=int, default=1000, help='Number of propagation steps per run')
    parser.add_argument('--output', help='Output file for results (JSON format)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--debug-steps', action='store_true', help='Print detailed info for each step (first run only)')
    parser.add_argument('--print-network', action='store_true', help='Print network structure')
    parser.add_argument('--list-nodes', action='store_true', help='List all nodes and exit')
    parser.add_argument('--non-reversible', action='store_true', 
                       help='Stop simulation after first fate fires (NetLogo non-reversible mode)')
    parser.add_argument('--hierarchy', action='store_true',
                       help='Apply phenotype hierarchy: Proliferation > Growth_Arrest > Apoptosis')
    
    args = parser.parse_args()
    
    # List nodes mode
    if args.list_nodes:
        network = GraphWalkingGeneNetwork()
        network.load_bnd_file(args.bnd_file)
        network.print_network_structure()
        return
    
    # Validate options
    if args.non_reversible and args.hierarchy:
        print("Warning: --hierarchy implies reversible mode. Ignoring --non-reversible.")
        args.non_reversible = False
    
    # Run simulation
    reversible = not args.non_reversible
    use_hierarchy = args.hierarchy
    results = run_simulation(
        args.bnd_file,
        args.input_file,
        args.runs,
        args.steps,
        args.verbose,
        args.debug_steps,
        args.print_network,
        reversible=reversible,
        use_hierarchy=use_hierarchy
    )
    
    # Print results
    if use_hierarchy:
        mode_str = "HIERARCHY (Prolif > GA > Apop)"
    elif not reversible:
        mode_str = "NON-REVERSIBLE"
    else:
        mode_str = "REVERSIBLE"
    print(f"\n{'='*70}")
    print(f"GENE NETWORK SIMULATION RESULTS (GRAPH WALKING - {mode_str})")
    print(f"{'='*70}")
    print(f"Network: {args.bnd_file}")
    print(f"Inputs: {args.input_file}")
    print(f"Runs: {args.runs}, Steps: {args.steps}")
    print(f"Mode: {mode_str}")
    
    print(f"\nInput Conditions:")
    for node, state in results['input_conditions'].items():
        print(f"  {node}: {'ON' if state else 'OFF'}")
    
    # Hierarchy mode: show effective fate with hierarchy applied
    if use_hierarchy:
        print(f"\n{'='*70}")
        print(f"EFFECTIVE FATE (with hierarchy: Proliferation > Growth_Arrest > Apoptosis)")
        print(f"{'='*70}")
        hier_stats = results['hierarchy_statistics']
        for fate_name in ['Proliferation', 'Growth_Arrest', 'Apoptosis', 'Necrosis', 'Quiescent']:
            if fate_name in hier_stats:
                count = hier_stats[fate_name]['count']
                pct = hier_stats[fate_name]['pct']
                bar = '█' * int(pct / 2)
                print(f"  {fate_name:<15}: {count:4d}/{args.runs} ({pct:5.1f}%) {bar}")
    
    # Non-reversible mode: show first fate statistics prominently
    elif not reversible:
        print(f"\n{'='*70}")
        print(f"FIRST FATE STATISTICS (which fate fired FIRST in each run)")
        print(f"{'='*70}")
        first_stats = results['first_fate_statistics']
        for fate_name in ['Proliferation', 'Growth_Arrest', 'Apoptosis', 'Necrosis']:
            count = first_stats['counts'].get(fate_name, 0)
            pct = 100 * count / args.runs
            bar = '█' * int(pct / 2)
            print(f"  {fate_name:<15}: {count:4d}/{args.runs} ({pct:5.1f}%) {bar}")
        print(f"  {'No Fate':<15}: {first_stats['no_fate']:4d}/{args.runs} ({first_stats['no_fate_pct']:5.1f}%)")
    
    # Fate node results - show both "ever fired" and "final state"
    print(f"\n{'='*70}")
    print(f"FATE NODE DETAILED STATISTICS")
    print(f"{'='*70}")
    if reversible:
        print(f"{'Node':<20} {'Ever Fired':<20} {'Total Fires':<15} {'Final ON':<15}")
    else:
        print(f"{'Node':<20} {'First Fate':<20} {'Ever Fired':<20}")
    print(f"{'-'*70}")
    
    for fate_name in ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']:
        if fate_name in results['fate_statistics']:
            stats = results['fate_statistics'][fate_name]
            ever = f"{stats['ever_fired_runs']}/{args.runs} ({stats['ever_fired_pct']:.1f}%)"
            if reversible:
                fires = f"{stats['total_fire_events']} ({stats['avg_fires_per_run']:.2f}/run)"
                final = f"{stats['final_state_ON']}/{args.runs} ({stats['final_state_ON_pct']:.1f}%)"
                print(f"{fate_name:<20} {ever:<20} {fires:<15} {final:<15}")
            else:
                first = f"{stats['first_fate_count']}/{args.runs} ({stats['first_fate_pct']:.1f}%)"
                print(f"{fate_name:<20} {first:<20} {ever:<20}")
    
    # Metabolic nodes
    print(f"\nMetabolic Node Results (Final State):")
    for node_name in ['mitoATP', 'glycoATP']:
        if node_name in results['metabolic_statistics']:
            stats = results['metabolic_statistics'][node_name]
            print(f"  {node_name}: ON {stats['ON']}/{args.runs} ({stats['ON_pct']:.1f}%)")
    
    # Timing statistics
    print(f"\n{'='*70}")
    print(f"TIMING STATISTICS: When do fates first fire? (step number)")
    print(f"{'='*70}")
    print(f"{'Fate':<15} {'Count':<8} {'Min':<8} {'Median':<10} {'Mean':<10} {'Max':<8} {'P25-P75':<15}")
    print(f"{'-'*70}")
    for fate_name in ['Proliferation', 'Growth_Arrest', 'Apoptosis', 'Necrosis']:
        if fate_name in results['timing_statistics']:
            ts = results['timing_statistics'][fate_name]
            if ts['count'] > 0:
                p25_p75 = f"{ts['percentile_25']}-{ts['percentile_75']}"
                print(f"{fate_name:<15} {ts['count']:<8} {ts['min_step']:<8} {ts['median_step']:<10.0f} {ts['mean_step']:<10.1f} {ts['max_step']:<8} {p25_p75:<15}")
            else:
                print(f"{fate_name:<15} {'--':<8} {'--':<8} {'--':<10} {'--':<10} {'--':<8} {'--':<15}")
    
    # Comparison explanation
    print(f"\n{'='*70}")
    print("INTERPRETATION:")
    print("-" * 70)
    if use_hierarchy:
        print("HIERARCHY MODE: Run full simulation, then apply fate priority.")
        print("  - Multiple fates can fire during the run")
        print("  - Priority: Proliferation > Growth_Arrest > Apoptosis > Necrosis")
        print("  - If Proliferation ever fired → cell proliferates")
        print("  - Else if Growth_Arrest ever fired → cell arrests")
        print("  - Else if Apoptosis ever fired → cell dies")
        print("  - Otherwise → Quiescent (no fate fired)")
    elif reversible:
        print("REVERSIBLE MODE: Network keeps updating after fate fires.")
        print("  - Multiple fates can fire in the same run")
        print("  - 'Ever Fired': Runs where fate triggered at least once")
        print("  - 'Total Fires': Sum of all fate firing events")
        print("  - Fate nodes reset to OFF after firing (transient triggers)")
    else:
        print("NON-REVERSIBLE MODE: Network STOPS after first fate fires.")
        print("  - Only ONE fate can fire per run (the first one)")
        print("  - 'First Fate': Which fate won the race to fire first")
        print("  - This matches NetLogo's the-reversible?=FALSE behavior")
        print("  - Useful for determining the cell's definitive fate")
    print("="*70)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == '__main__':
    main()
