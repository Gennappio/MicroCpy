"""
Gene regulatory network implementation for MicroC 2.0

Supports Boolean networks with .bnd file format and custom update functions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Callable, Any
from pathlib import Path
from collections import defaultdict
import os
import random
import re

from interfaces.base import IGeneNetwork


class BooleanExpression:
    """Evaluates boolean expressions with gene states (matches standalone version)."""

    def __init__(self, expression: str):
        self.expression = expression.strip()

    def __call__(self, gene_states: Dict[str, bool]) -> bool:
        """Make callable to match update_function interface."""
        return self.evaluate(gene_states)

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
            return False

@dataclass
class NetworkNode:
    """Represents a node in the Boolean network"""
    name: str
    current_state: bool = False
    next_state: bool = False
    update_function: Optional[Callable] = None
    inputs: List[str] = field(default_factory=list)
    is_input: bool = False
    is_output: bool = False

class BooleanNetwork(IGeneNetwork):
    """
    Fully configurable Boolean gene regulatory network

    Can be configured via:
    1. config.py - gene network structure and logic
    2. custom_functions.py - custom update functions
    3. .bnd files - Boolean network format
    """

    def __init__(self, config=None, network_file: Optional[Path] = None,
                 custom_functions_module=None):
        self.nodes: Dict[str, NetworkNode] = {}
        self.input_nodes: Set[str] = set()
        self.output_nodes: Set[str] = set()
        self.fixed_nodes: Dict[str, bool] = {}  # Track fixed nodes like gene_simulator.py
        self.config = config

        # Priority: config > .bnd file > default
        if config and config.gene_network:
            self._load_from_config(config.gene_network)
        elif network_file and network_file.exists():
            self._load_from_bnd_file(network_file)
        else:
            self._create_minimal_network()
    
    def _load_from_bnd_file(self, bnd_file: Path):
        """Load network from .bnd file format (supports both simple and MaBoSS formats)"""
        try:
            with open(bnd_file, 'r') as f:
                content = f.read()

            nodes_created = 0
            input_nodes_found = set()

            nodes_created = self._parse_maboss_format(content, input_nodes_found) 
        
            # Create any missing input nodes that were referenced but not defined
            for input_name in input_nodes_found:
                if input_name not in self.nodes:
                    self.nodes[input_name] = NetworkNode(
                        name=input_name,
                        update_function=None,
                        inputs=[],
                        is_input=True
                    )
                    nodes_created += 1

            # print(f"[+] Loaded {nodes_created} nodes from .bnd file")

            # Identify input and output nodes
            self._identify_input_output_nodes()

        except Exception as e:
            print(f"[!] Error loading .bnd file {bnd_file}: {e}")
            import traceback
            traceback.print_exc()

    def _parse_maboss_format(self, content: str, input_nodes_found: set) -> int:
        """Parse MaBoSS format .bnd file"""
        nodes_created = 0

        # Split into node blocks
        node_blocks = re.split(r'node\s+(\w+)\s*{', content)[1:]  # Skip first empty element

        for i in range(0, len(node_blocks), 2):
            if i + 1 >= len(node_blocks):
                break

            node_name = node_blocks[i].strip()
            node_content = node_blocks[i + 1].split('}')[0]  # Get content before closing brace

            # Look for logic line
            logic_match = re.search(r'logic\s*=\s*([^;]+);', node_content)

            if logic_match:
                expression = logic_match.group(1).strip()

                # Extract input nodes from expression
                inputs = self._extract_inputs_from_expression(expression)

                # Create update function from expression
                update_func = self._create_update_function(expression)

                # Create node
                self.nodes[node_name] = NetworkNode(
                    name=node_name,
                    update_function=update_func,
                    inputs=inputs
                )
                nodes_created += 1

                # Track input nodes referenced in expressions
                input_nodes_found.update(inputs)
            else:
                # Check if this is an input node (has rate_up = 0; rate_down = 0;)
                if 'rate_up = 0;' in node_content and 'rate_down = 0;' in node_content:
                    self.nodes[node_name] = NetworkNode(
                        name=node_name,
                        update_function=None,
                        inputs=[],
                        is_input=True
                    )
                    nodes_created += 1
                    input_nodes_found.add(node_name)

        return nodes_created
    
    def _extract_inputs_from_expression(self, expression: str) -> List[str]:
        """Extract input node names from Boolean expression"""
        # Simple regex to find variable names (letters, numbers, underscore)
        variables = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', expression)
        # Filter out Boolean operators
        boolean_ops = {'and', 'or', 'not', 'AND', 'OR', 'NOT', 'True', 'False'}
        return [var for var in variables if var not in boolean_ops]
    
    def _create_update_function(self, expression: str) -> Callable:
        """Create update function from Boolean expression using BooleanExpression class"""
        return BooleanExpression(expression) # TODO: why _create_update_function? just call BooleanExpression in the _load_from_config
    
    def _identify_input_output_nodes(self):
        """Identify input and output nodes based on network structure"""
        all_referenced_nodes = set()  # Nodes that appear in other nodes' inputs

        # Collect all nodes that are referenced as inputs
        for node in self.nodes.values():
            all_referenced_nodes.update(node.inputs)

        # Input nodes: nodes that have no update function (they get their values from outside)
        self.input_nodes = set()
        for node_name, node in self.nodes.items():
            if node.update_function is None:
                self.input_nodes.add(node_name)
                node.is_input = True

        # Output nodes: nodes that are not used as inputs to other nodes (leaf nodes)
        self.output_nodes = set()
        for node_name, node in self.nodes.items():
            if node_name not in all_referenced_nodes and node.update_function is not None:
                self.output_nodes.add(node_name)
                node.is_output = True

        # print(f"[+] Identified {len(self.input_nodes)} input nodes: {sorted(self.input_nodes)}")
        # print(f"[+] Identified {len(self.output_nodes)} output nodes: {sorted(self.output_nodes)}")

    def _load_from_config(self, gene_network_config):
        """Load network from configuration object"""
        from config.config import GeneNetworkConfig, GeneNodeConfig

        # Clear existing nodes
        self.nodes = {}

        # First, load .bnd file if specified
        if hasattr(gene_network_config, 'bnd_file') and gene_network_config.bnd_file:
            bnd_path = Path(gene_network_config.bnd_file)
            if bnd_path.exists():
                # print(f"[+] Loading gene network from .bnd file: {bnd_path}")
                self._load_from_bnd_file(bnd_path)
            else:
                print(f"[WARNING]  .bnd file not found: {bnd_path}")

        # Then, create/override nodes from config
        for name, node_config in gene_network_config.nodes.items():
            # Create update function from logic string
            update_func = None
            if node_config.logic:
                update_func = self._create_update_function(node_config.logic)

            # Create or update node
            if name in self.nodes:
                # Update existing node from .bnd file with config properties
                node = self.nodes[name]
                node.current_state = node_config.default_state
                node.is_input = node_config.is_input
                node.is_output = node_config.is_output

                # Input nodes should not have update functions - they get values from environment
                if node_config.is_input:
                    node.update_function = None
                    node.inputs = []
                elif update_func:  # Override .bnd logic if config has logic
                    node.update_function = update_func
                    node.inputs = node_config.inputs
            else:
                # Create new node from config
                # Input nodes should not have update functions
                if node_config.is_input:
                    update_func = None
                    inputs = []
                else:
                    inputs = node_config.inputs

                self.nodes[name] = NetworkNode(
                    name=name,
                    current_state=node_config.default_state,
                    update_function=update_func,
                    inputs=inputs,
                    is_input=node_config.is_input,
                    is_output=node_config.is_output
                )

        # Identify input and output nodes based on node properties
        self.input_nodes = set()
        self.output_nodes = set()

        for node_name, node in self.nodes.items():
            if node.is_input:
                self.input_nodes.add(node_name)
            if node.is_output:
                self.output_nodes.add(node_name)

        # If no explicit input/output nodes from config, use the ones identified from .bnd structure
        if not self.input_nodes and not self.output_nodes:
            self._identify_input_output_nodes()

        # print(f"[+] Loaded gene network from config: {len(self.nodes)} nodes")
        # print(f"[+] Input nodes: {sorted(self.input_nodes)}")
        # print(f"[+] Output nodes: {sorted(self.output_nodes)}")

    def _create_minimal_network(self):
        """Create minimal network - only essential nodes for basic functionality"""
        print("[WARNING]  Using minimal gene network - configure via config.py for full functionality")

        # Minimal input nodes
        essential_inputs = [
            'Oxygen_supply', 'Glucose_supply', 'ATP_Production_Rate'
        ]

        for input_name in essential_inputs:
            self.nodes[input_name] = NetworkNode(name=input_name, is_input=True)

        # Minimal output nodes (4 phenotypes from .bnd file)
        essential_outputs = [
            'Necrosis', 'Apoptosis', 'Growth_Arrest', 'Proliferation'
        ]

        for output_name in essential_outputs:
            # Simple default logic - can be overridden via custom_functions.py
            if output_name == 'Necrosis':
                logic = "not Oxygen_supply and not Glucose_supply"
            elif output_name == 'Apoptosis':
                logic = "not Oxygen_supply"
            elif output_name == 'Proliferation':
                logic = "Oxygen_supply and Glucose_supply and ATP_Production_Rate"
            else:  # Growth_Arrest
                logic = "True"  # Default state

            self.nodes[output_name] = NetworkNode(
                name=output_name,
                inputs=['Oxygen_supply', 'Glucose_supply', 'ATP_Production_Rate'],
                update_function=self._create_update_function(logic),
                is_output=True
            )

        # Set node collections
        self.input_nodes = set(essential_inputs)
        self.output_nodes = set(essential_outputs)

        print(f"[+] Created minimal gene network: {len(essential_inputs)} inputs, {len(essential_outputs)} outputs")
    
    def fix_node(self, node_name: str, state: bool):
        """Fix a node to a specific state - IDENTICAL to gene_simulator.py"""
        self.fixed_nodes[node_name] = state
        if node_name in self.nodes:
            self.nodes[node_name].current_state = state

    def set_input_states(self, inputs: Dict[str, bool]):
        """Set input node states"""
        for node_name, state in inputs.items():
            if node_name in self.nodes:
                self.nodes[node_name].current_state = state
    
    def initialize_logic_states(self, verbose: bool = False):
        """Initialize all non-input nodes to match their logic rules."""
        if verbose:
            print("Initializing gene network logic states...")

        # Get current states for evaluation
        current_states = {name: node.current_state for name, node in self.nodes.items()}

        # Update all non-input nodes to match their logic
        updates_made = 0
        for node_name, node in self.nodes.items():
            if not node.is_input and node.update_function:
                try:
                    expected_state = node.update_function(current_states)
                    if node.current_state != expected_state:
                        if verbose:
                            print(f"  Initializing {node_name}: {node.current_state} -> {expected_state}")
                        node.current_state = expected_state
                        current_states[node_name] = expected_state  # Update for next evaluations
                        updates_made += 1
                except Exception as e:
                    if verbose:
                        print(f"  Error initializing {node_name}: {e}")

        if verbose:
            print(f"Initialization complete: {updates_made} nodes updated")

        return updates_made
    
    def initialize_random(self):
        """Initialize ALL nodes with random states - IDENTICAL to gene_simulator.py"""
        import random

        for node_name, node in self.nodes.items():
            # Skip fixed nodes (identical to gene_simulator.py)
            if node_name in self.fixed_nodes:
                node.current_state = self.fixed_nodes[node_name]
            else:
                # Randomize all other nodes (identical to gene_simulator.py)
                node.current_state = random.choice([True, False])

    def step(self, num_steps: int = 1) -> Dict[str, bool]:
        """Run network for specified steps"""
        # Use default implementation (no custom gene network functions)
        return self._default_step(num_steps)
    
    def _default_step(self, num_steps: int = 1) -> Dict[str, bool]:
        """NetLogo-style gene network update: single gene per step"""
        for step in range(num_steps):
            # NetLogo approach: update only ONE gene per step
            self._netlogo_single_gene_update()

        # Return ALL states, not just output states (needed for ATP genes)
        return self.get_all_states()

    def _netlogo_single_gene_update(self):
        """
        TRUE NetLogo-style gene network update: randomly select ONE gene and update it.

        This matches the standalone version exactly:
        1. Get all non-input genes with update functions (cached)
        2. Randomly select ONE gene (no eligibility checking)
        3. Evaluate the gene's rule with ALL current states (cached dict)
        4. Update only that gene's state

        Performance optimization: Caches updatable genes list and reuses state dict.
        """
        import random

        # Cache the list of updatable genes (only computed once since gene structure doesn't change)
        if not hasattr(self, '_cached_updatable_genes'):
            self._cached_updatable_genes = [name for name, gene_node in self.nodes.items()
                                          if not gene_node.is_input and gene_node.update_function]

        if not self._cached_updatable_genes:
            return None

        # TRUE NetLogo approach: randomly select ONE gene (no eligibility checking)
        selected_gene = random.choice(self._cached_updatable_genes)
        gene_node = self.nodes[selected_gene]

        # Cache and reuse the current states dictionary structure
        if not hasattr(self, '_state_cache'):
            self._state_cache = {}

        # Update the cached states with current values (reuse dict structure)
        for name, node in self.nodes.items():
            self._state_cache[name] = node.current_state

        # Evaluate the gene's rule and update ONLY this gene
        # Pass ALL current states (like standalone version)
        new_state = gene_node.update_function(self._state_cache)

        # Update only this one gene (NetLogo style)
        if gene_node.current_state != new_state: # TODO: why this if? just write it
            gene_node.current_state = new_state
            return selected_gene  # Return which gene was updated

        return None  # No state change
    
    def get_output_states(self) -> Dict[str, bool]:
        """Get current output node states"""
        return {
            name: self.nodes[name].current_state 
            for name in self.output_nodes 
            if name in self.nodes
        }
    
    def get_all_states(self) -> Dict[str, bool]:
        """Get all node states"""
        return {name: node.current_state for name, node in self.nodes.items()}
    
    def reset(self, random_init: bool = False):
        """Reset nodes: fate nodes to False, others to random by default"""
        # Define output/fate nodes that should always start as False
        fate_nodes = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}

        for node in self.nodes.values():
            if node.is_input:
                # Input nodes keep their externally set states
                continue
            elif node.name in fate_nodes:
                # Fate nodes always start as False (biologically correct)
                node.current_state = False
                node.next_state = False
            else:
                # ALL other non-input nodes start RANDOM by default
                import random
                state = random.choice([True, False])
                node.current_state = state
                node.next_state = state
    
    def get_network_info(self) -> Dict[str, any]:
        """Get information about the network structure"""
        return {
            'total_nodes': len(self.nodes),
            'input_nodes': list(self.input_nodes),
            'output_nodes': list(self.output_nodes),
            'internal_nodes': [name for name in self.nodes.keys() 
                             if name not in self.input_nodes and name not in self.output_nodes],
            'connections': {name: node.inputs for name, node in self.nodes.items() if node.inputs}
        }
    
    def copy(self):
        """Create a deep copy of this gene network for use by individual cells"""
        import copy

        # Create new instance with same config
        new_network = BooleanNetwork(config=self.config)

        # Deep copy all nodes
        new_network.nodes = {}
        for name, node in self.nodes.items():
            new_node = NetworkNode(
                name=node.name,
                current_state=node.current_state,
                next_state=node.next_state,
                update_function=node.update_function,  # Functions can be shared
                inputs=node.inputs.copy(),
                is_input=node.is_input,
                is_output=node.is_output
            )
            new_network.nodes[name] = new_node

        # Copy other attributes
        new_network.input_nodes = self.input_nodes.copy()
        new_network.output_nodes = self.output_nodes.copy()
        new_network.fixed_nodes = self.fixed_nodes.copy()

        return new_network

    def __repr__(self) -> str:
        info = self.get_network_info()
        return (f"BooleanNetwork(nodes={info['total_nodes']}, "
                f"inputs={len(info['input_nodes'])}, "
                f"outputs={len(info['output_nodes'])})")
