"""
Gene regulatory network implementation for MicroC 2.0

Supports Boolean networks with .bnd file format and custom update functions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Callable
from pathlib import Path
import re

from interfaces.base import IGeneNetwork, CustomizableComponent
from interfaces.hooks import get_hook_manager

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

class BooleanNetwork(IGeneNetwork, CustomizableComponent):
    """
    Fully configurable Boolean gene regulatory network

    Can be configured via:
    1. config.py - gene network structure and logic
    2. custom_functions.py - custom update functions
    3. .bnd files - Boolean network format
    """

    def __init__(self, config=None, network_file: Optional[Path] = None,
                 custom_functions_module=None):
        super().__init__(custom_functions_module)

        self.nodes: Dict[str, NetworkNode] = {}
        self.input_nodes: Set[str] = set()
        self.output_nodes: Set[str] = set()
        self.fixed_nodes: Dict[str, bool] = {}  # Track fixed nodes like gene_simulator.py
        self.hook_manager = get_hook_manager()
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

            # Check if this is MaBoSS format (contains "node" keyword)
            if 'node ' in content:
                nodes_created = self._parse_maboss_format(content, input_nodes_found)
            else:
                nodes_created = self._parse_simple_format(content, input_nodes_found)

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

            print(f"✅ Loaded {nodes_created} nodes from .bnd file")

            # Identify input and output nodes
            self._identify_input_output_nodes()

        except Exception as e:
            print(f"❌ Error loading .bnd file {bnd_file}: {e}")
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

                # Debug Apoptosis node specifically
                if node_name == 'Apoptosis':
                    print(f"🔍 APOPTOSIS NODE PARSING:")
                    print(f"   Raw expression: '{expression}'")

                # Extract input nodes from expression
                inputs = self._extract_inputs_from_expression(expression)

                # Create update function from expression
                update_func = self._create_update_function(expression)

                # Debug Apoptosis node specifically
                if node_name == 'Apoptosis':
                    print(f"   Inputs: {inputs}")
                    # Test the function with all False inputs
                    test_inputs = {inp: False for inp in inputs}
                    test_result = update_func(test_inputs)
                    print(f"   Test with all False: {test_result}")

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

    def _parse_simple_format(self, content: str, input_nodes_found: set) -> int:
        """Parse simple format .bnd file (original logic)"""
        nodes_created = 0
        lines = content.split('\n')

        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Check for simple node definition: node_name = expression
            if '=' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    node_name = parts[0].strip()
                    expression = parts[1].strip()

                    # Skip empty expressions
                    if not expression:
                        continue

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
                # Check for standalone node names (input nodes)
                node_name = line.strip()
                # Skip dependency lines (contain commas) and lines with operators
                if (node_name and
                    not any(op in node_name for op in ['=', '&', '|', '(', ')', ',']) and
                    not node_name.startswith('#')):
                    # This is likely an input node
                    if node_name not in self.nodes:
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
        """Create update function from Boolean expression - FIXED NOT operator handling"""
        def update_func(input_states: Dict[str, bool]) -> bool:
            if not expression:
                return False

            # Create a copy of the expression for evaluation
            expr = expression

            # Replace node names with their states
            for node_name, state in input_states.items():
                # Make sure we replace whole words only (not substrings)
                expr = re.sub(r'\b' + re.escape(node_name) + r'\b', 'True' if state else 'False', expr)

            # Replace logical operators - handle both symbols and words
            # FIXED: Handle ! operator more carefully
            expr = expr.replace('&', ' and ').replace('|', ' or ')
            # Replace ! with not, but be careful about spacing
            expr = re.sub(r'!\s*', 'not ', expr)  # Replace ! followed by optional whitespace
            expr = expr.replace('AND', ' and ').replace('OR', ' or ').replace('NOT', ' not ')

            try:
                # Evaluate the expression
                return eval(expr)
            except Exception as e:
                # Silently handle errors and return False
                return False

        return update_func
    
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

        print(f"✅ Identified {len(self.input_nodes)} input nodes: {sorted(self.input_nodes)}")
        print(f"✅ Identified {len(self.output_nodes)} output nodes: {sorted(self.output_nodes)}")

    def _load_from_config(self, gene_network_config):
        """Load network from configuration object"""
        from config.config import GeneNetworkConfig, GeneNodeConfig

        # Clear existing nodes
        self.nodes = {}

        # First, load .bnd file if specified
        if hasattr(gene_network_config, 'bnd_file') and gene_network_config.bnd_file:
            bnd_path = Path(gene_network_config.bnd_file)
            if bnd_path.exists():
                print(f"✅ Loading gene network from .bnd file: {bnd_path}")
                self._load_from_bnd_file(bnd_path)
            else:
                print(f"⚠️  .bnd file not found: {bnd_path}")

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

        print(f"✅ Loaded gene network from config: {len(self.nodes)} nodes")
        print(f"✅ Input nodes: {sorted(self.input_nodes)}")
        print(f"✅ Output nodes: {sorted(self.output_nodes)}")

    def _create_minimal_network(self):
        """Create minimal network - only essential nodes for basic functionality"""
        print("⚠️  Using minimal gene network - configure via config.py for full functionality")

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

        print(f"✅ Created minimal gene network: {len(essential_inputs)} inputs, {len(essential_outputs)} outputs")
    
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
        try:
            # Try custom update function first
            return self.hook_manager.call_hook(
                "custom_update_gene_network",
                current_states={name: node.current_state for name, node in self.nodes.items()},
                inputs={name: self.nodes[name].current_state for name in self.input_nodes},
                network_params={'num_steps': num_steps}
            )

        except NotImplementedError:
            # Fall back to default implementation
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
        NetLogo-style gene network update: update only ONE gene per step.

        Based on NetLogo's -DOWNSTREAM-CHANGE-590 and -INFLUENCE-LINK-END-WITH-LOGGING--36:
        1. Find all genes that have active upstream inputs
        2. Randomly select ONE gene to update
        3. Evaluate only that gene's rule
        4. Update only that gene's state
        """
        import random

        # Find all non-input genes that could potentially be updated
        updatable_genes = []

        for gene_name, gene_node in self.nodes.items():
            # Skip input nodes (they're set externally)
            if gene_node.is_input:
                continue

            # Skip nodes without update functions
            if not gene_node.update_function:
                continue

            # Check if this gene has any active upstream inputs
            # (NetLogo updates genes that have "incoming links" from active nodes)
            has_active_inputs = False
            for input_name in gene_node.inputs:
                if input_name in self.nodes and self.nodes[input_name].current_state:
                    has_active_inputs = True
                    break

            # Add to updatable list if it has active inputs OR if it's currently active
            # (NetLogo can update active genes to turn them off)
            if has_active_inputs or gene_node.current_state:
                updatable_genes.append(gene_name)

        # If no genes can be updated, return (network is stable)
        if not updatable_genes:
            return

        # NetLogo approach: randomly select ONE gene to update
        selected_gene = random.choice(updatable_genes)
        gene_node = self.nodes[selected_gene]

        # Get current states of all nodes for logic evaluation
        current_states = {name: node.current_state for name, node in self.nodes.items()}

        # Get input states for this specific gene
        input_states = {
            input_name: current_states[input_name]
            for input_name in gene_node.inputs
            if input_name in current_states
        }

        # Evaluate the gene's rule and update ONLY this gene
        new_state = gene_node.update_function(input_states)

        # Update only this one gene (NetLogo style)
        if gene_node.current_state != new_state:
            gene_node.current_state = new_state

            # Debug output for ATP genes only
            if selected_gene in ['mitoATP', 'glycoATP', 'ATP_Production_Rate']:
                print(f"🔍 NetLogo update: {selected_gene} → {new_state}")
    
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
        """Reset nodes to False or random states (NetLogo-style)"""
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
            elif random_init:
                # NetLogo-style: 50% chance True/False for non-fate genes
                import random
                state = random.choice([True, False])
                node.current_state = state
                node.next_state = state
            else:
                # Default: all genes start as False
                node.current_state = False
                node.next_state = False
    
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
    
    def __repr__(self) -> str:
        info = self.get_network_info()
        return (f"BooleanNetwork(nodes={info['total_nodes']}, "
                f"inputs={len(info['input_nodes'])}, "
                f"outputs={len(info['output_nodes'])})")
