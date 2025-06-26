#!/usr/bin/env python3
"""
Gene Simulator

This script reads regulatory network files (HTML or BND+CFG) and performs simulations.
It supports random initialization, fixing node states, and analyzing target nodes.

Usage:
    python gene_simulator.py <network_file> [options]

Options:
    --steps N             Number of simulation steps (default: 100)
    --runs N              Number of simulation runs (default: 1)
    --target-node NODE    Node to analyze (required)
    --fix-node NODE STATE Fix a node to a specific state (ON/OFF)
    --set-node NODE STATE Set initial state of a node (ON/OFF) - deprecated, use --fix-node

Example:
    python gene_simulator.py regulatoryGraph.html --steps 100 --runs 200 --target-node mitoATP \
        --fix-node Oxygen_supply OFF --fix-node Glucose_supply ON
"""

import sys
import os
import re
import random
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
import matplotlib.pyplot as plt
import numpy as np

# Suppress warning about parsing XML as HTML
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class Node:
    """Represents a node in the regulatory network."""

    def __init__(self, name, logic_rule=None):
        self.name = name
        self.logic_rule = logic_rule
        self.state = False  # Default to OFF
        self.updated = False  # Flag to track if node has been updated in current step

    def __str__(self):
        return f"{self.name}: {'ON' if self.state else 'OFF'}"


class BooleanExpression:
    """Evaluates boolean expressions in the context of node states."""

    def __init__(self, expression):
        self.expression = expression

    def evaluate(self, node_states):
        """
        Evaluate the boolean expression using the current node states.

        Args:
            node_states: Dictionary mapping node names to their states (True/False)

        Returns:
            bool: Result of the expression evaluation
        """
        if not self.expression:
            return False

        # Create a copy of the expression for evaluation
        expr = self.expression

        # Replace node names with their states
        for node_name, state in node_states.items():
            # Make sure we replace whole words only (not substrings)
            expr = re.sub(r'\b' + re.escape(node_name) + r'\b', 'True' if state else 'False', expr)

        # Replace logical operators - FIXED: Handle ! operator more carefully
        expr = expr.replace('&', ' and ').replace('|', ' or ')
        # Replace ! with not, but be careful about spacing
        expr = re.sub(r'!\s*', 'not ', expr)  # Replace ! followed by optional whitespace

        try:
            # Evaluate the expression
            return eval(expr)
        except Exception as e:
            # Silently handle errors and return False
            return False


class NetworkParser:
    """Base class for network parsers."""

    def __init__(self, file_path):
        self.file_path = file_path
        self.nodes = {}

    def parse(self):
        """Parse the network file."""
        raise NotImplementedError("Subclasses must implement parse()")

    def get_nodes(self):
        """Return the parsed nodes."""
        return self.nodes


class HtmlParser(NetworkParser):
    """Parser for HTML/XML format (including GraphML)."""

    def parse(self):
        """Parse the HTML/XML file to extract nodes and logic rules."""
        with open(self.file_path, 'r') as f:
            content = f.read()

        # Check if it's a GraphML file
        if '<?xml' in content and '<graphml>' in content:
            self._parse_graphml(content)
        else:
            self._parse_html(content)

    def _parse_graphml(self, content):
        """Parse GraphML format."""
        # Use XML parser for GraphML
        soup = BeautifulSoup(content, 'html.parser')

        # Find all node elements
        node_elements = soup.find_all('node')

        for node in node_elements:
            node_id = node.get('id')
            if not node_id:
                continue

            # Find data elements for this node
            rule_data = node.find('data', {'key': 'MY-RULE'})

            # Extract logic rule
            logic_rule = rule_data.text if rule_data else None

            # Standardize logic rule format
            if logic_rule:
                # Convert "and" to "&", "or" to "|", "not" to "!"
                logic_rule = logic_rule.replace(' and ', ' & ').replace(' or ', ' | ').replace('not ', '!')

                # Handle cases where there's no space after "not"
                logic_rule = logic_rule.replace('not(', '!(')

            # Create the node
            self.nodes[node_id] = Node(node_id, logic_rule)


class BndParser(NetworkParser):
    """Parser for BND format."""

    def parse(self):
        """Parse the BND file to extract nodes and logic rules."""
        with open(self.file_path, 'r') as f:
            content = f.read()

        # Extract node definitions - handle both 'Node' and 'node' formats
        node_pattern = r'[Nn]ode\s+(\w+)\s*\{([^}]*)\}'
        node_matches = re.finditer(node_pattern, content, re.DOTALL)

        for match in node_matches:
            node_name = match.group(1)
            node_content = match.group(2)

            # Extract logic rule - handle both formats: logic = (rule); and logic = rule;
            logic_match = re.search(r'logic\s*=\s*(?:\(?(.*?)\)?);', node_content, re.DOTALL)
            logic_rule = logic_match.group(1).strip() if logic_match else None

            # Create node
            self.nodes[node_name] = Node(node_name, logic_rule)


def parse_network(file_path):
    """
    Parse a network file and return the nodes.

    Args:
        file_path: Path to the network file (BND or HTML)

    Returns:
        dict: Dictionary of Node objects
    """
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == '.html':
        parser = HtmlParser(file_path)
        parser.parse()
        return parser.get_nodes()
    elif file_ext == '.bnd':
        parser = BndParser(file_path)
        parser.parse()
        return parser.get_nodes()
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")


class Simulator:
    """Simulates a regulatory network."""

    def __init__(self, nodes):
        """
        Initialize the simulator with a set of nodes.

        Args:
            nodes: Dictionary of Node objects
        """
        self.nodes = nodes
        self.fixed_nodes = {}  # Dictionary of nodes with fixed states

    def initialize_random(self, set_nodes=None):
        """
        Initialize all nodes with random states.

        Args:
            set_nodes: Dictionary of nodes with initial states (not fixed)
        """
        set_nodes = set_nodes or {}

        for node_name, node in self.nodes.items():
            # Skip fixed nodes
            if node_name in self.fixed_nodes:
                node.state = self.fixed_nodes[node_name]
            # Set initial state for set nodes
            elif node_name in set_nodes:
                node.state = set_nodes[node_name]
            else:
                # Randomize all other nodes
                node.state = random.choice([True, False])

            # Reset the updated flag
            node.updated = False

    def fix_node(self, node_name, state):
        """
        Fix a node to a specific state.

        Args:
            node_name: Name of the node
            state: State to fix the node to (True/False)
        """
        if node_name in self.nodes:
            self.fixed_nodes[node_name] = state
            self.nodes[node_name].state = state
        else:
            print(f"Warning: Node {node_name} not found in the network")

    def step(self):
        """
        Perform one simulation step.

        In each step, randomly pick a node and update it according to its logic.
        When all nodes have been updated, the step is complete.
        """
        # Reset the updated flag for all nodes
        for node in self.nodes.values():
            node.updated = False

        # Create a list of nodes that need to be updated
        nodes_to_update = list(self.nodes.keys())

        # Update nodes one by one in random order until all have been updated
        while nodes_to_update:
            # Pick a random node to update
            node_index = random.randrange(len(nodes_to_update))
            node_name = nodes_to_update.pop(node_index)
            node = self.nodes[node_name]

            # Skip fixed nodes
            if node_name in self.fixed_nodes:
                node.state = self.fixed_nodes[node_name]
                node.updated = True
                continue

            # If the node has a logic rule, evaluate it
            if node.logic_rule:
                # Create a dictionary of current node states for logic evaluation
                node_states = {n: self.nodes[n].state for n in self.nodes}

                # Evaluate the logic rule
                expr = BooleanExpression(node.logic_rule)
                node.state = expr.evaluate(node_states)

            # Mark the node as updated
            node.updated = True

    def run(self, steps):
        """
        Run the simulation for a specified number of steps.

        Args:
            steps: Number of steps to run
        """
        for _ in range(steps):
            self.step()

    def get_node_states(self):
        """
        Get the current state of all nodes.

        Returns:
            dict: Dictionary mapping node names to their states
        """
        return {node_name: node.state for node_name, node in self.nodes.items()}


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Gene Simulator')

    parser.add_argument('network_file', help='Path to the network file (HTML or BND)')
    parser.add_argument('--steps', type=int, default=100, help='Number of simulation steps (default: 100)')
    parser.add_argument('--runs', type=int, default=1, help='Number of simulation runs (default: 1)')
    parser.add_argument('--target-node', required=True, help='Node to analyze')
    parser.add_argument('--plot', action='store_true', help='Plot the activation results')
    parser.add_argument('--output', help='Path to save the plot (default: target_node_activation.png)')

    # Allow multiple --fix-node and --set-node arguments
    parser.add_argument('--fix-node', nargs=2, action='append', metavar=('NODE', 'STATE'),
                        help='Fix a node to a specific state (ON/OFF)')
    parser.add_argument('--set-node', nargs=2, action='append', metavar=('NODE', 'STATE'),
                        help='Set initial state of a node (ON/OFF) - deprecated, use --fix-node')

    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()

    # Parse the network file
    try:
        nodes = parse_network(args.network_file)
        print(f"Parsed {len(nodes)} nodes from {args.network_file}")
    except Exception as e:
        print(f"Error parsing network file: {e}")
        return 1

    # Check if the target node exists
    if args.target_node not in nodes:
        print(f"Error: Target node '{args.target_node}' not found in the network")
        return 1

    # Create the simulator
    simulator = Simulator(nodes)

    # Process fixed nodes
    if args.fix_node:
        for node_name, state in args.fix_node:
            state_bool = (state.upper() == 'ON')
            simulator.fix_node(node_name, state_bool)
            print(f"Fixed node {node_name} to {state}")

    # Process set nodes (only set initial state, not fixed)
    set_nodes = {}
    if args.set_node:
        for node_name, state in args.set_node:
            state_bool = (state.upper() == 'ON')
            set_nodes[node_name] = state_bool
            print(f"Set node {node_name} to {state} (initial state only)")

    # Run the simulations
    target_states = []
    final_states = []
    cumulative_on_percentage = []

    print(f"\nRunning {args.runs} simulations with {args.steps} steps each...")

    for run in range(args.runs):
        # Initialize with random states and set nodes
        simulator.initialize_random(set_nodes)

        # Run the simulation
        simulator.run(args.steps)

        # Record the target node state
        target_state = simulator.nodes[args.target_node].state
        target_states.append(target_state)

        # Record the final state of all nodes
        final_states.append(simulator.get_node_states())

        # Calculate cumulative ON percentage after each run
        current_on_count = sum(1 for state in target_states if state)
        current_on_percentage = (current_on_count / (run + 1)) * 100
        cumulative_on_percentage.append(current_on_percentage)

        # Print progress
        if (run + 1) % 10 == 0 or run == 0 or run == args.runs - 1:
            print(f"Completed {run + 1}/{args.runs} runs")

    # Calculate statistics for the target node
    target_counts = Counter(target_states)
    on_percentage = (target_counts[True] / args.runs) * 100
    off_percentage = (target_counts[False] / args.runs) * 100

    print(f"\nResults for target node '{args.target_node}':")
    print(f"  ON: {on_percentage:.2f}% ({target_counts[True]} runs)")
    print(f"  OFF: {off_percentage:.2f}% ({target_counts[False]} runs)")

    # Calculate the most common final state for each node
    most_common_state = {}
    for node_name in nodes:
        states = [state[node_name] for state in final_states]
        counts = Counter(states)
        most_common = counts.most_common(1)[0]
        most_common_state[node_name] = most_common

    print("\nFinal node states (most common across all runs):")
    for node_name, (state, count) in sorted(most_common_state.items()):
        percentage = (count / args.runs) * 100
        print(f"  {node_name}: {'ON' if state else 'OFF'} ({percentage:.2f}%)")

    # Plot the results if requested
    if args.plot:
        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.plot(range(1, args.runs + 1), cumulative_on_percentage, marker='o', linestyle='-', color='blue')
        plt.axhline(y=on_percentage, color='red', linestyle='--', label=f'Final ON percentage: {on_percentage:.2f}%')

        # Add labels and title
        plt.xlabel('Number of Runs')
        plt.ylabel('Cumulative ON Percentage (%)')
        plt.title(f'Activation of {args.target_node} over {args.runs} Runs')

        # Add grid and legend
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()

        # Set y-axis limits
        plt.ylim(0, 100)

        # Save or show the plot
        if args.output:
            output_file = args.output
        else:
            output_file = f"{args.target_node}_activation.png"

        plt.savefig(output_file)
        print(f"\nPlot saved to {output_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
