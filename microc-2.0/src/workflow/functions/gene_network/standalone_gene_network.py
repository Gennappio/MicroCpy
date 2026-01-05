"""
Standalone gene network functions for testing and debugging.

These functions allow running gene networks without the full simulation context,
useful for verifying gene network behavior and parameter tuning.
"""

from typing import Dict, Any, List
from pathlib import Path
from src.workflow.decorators import register_function
import random


@register_function(
    display_name="Initialize Standalone Gene Network",
    description="Load a BND file and create a standalone gene network for testing",
    category="UTILITY",
    parameters=[
        {"name": "bnd_file", "type": "STRING", "description": "Path to BND file", "default": "jaya_microc.bnd"},
        {"name": "random_initialization", "type": "BOOL", "description": "Use random initialization for non-input nodes", "default": True},
    ],
    outputs=["gene_network"],
    cloneable=False
)
def initialize_standalone_gene_network(
    context: Dict[str, Any],
    bnd_file: str = "jaya_microc.bnd",
    random_initialization: bool = True,
    **kwargs
) -> bool:
    """
    Initialize a standalone gene network from a BND file.
    
    Args:
        context: Workflow context
        bnd_file: Path to BND file
        random_initialization: Use random initialization
        
    Returns:
        True if successful
    """
    print(f"[GENE_NETWORK] Initializing standalone gene network")
    
    try:
        from src.biology.gene_network import BooleanNetwork
        
        # Find the BND file
        bnd_path = Path(bnd_file)
        if not bnd_path.exists():
            # Try relative to workflow
            workflow_file = context.get('workflow_file', '')
            if workflow_file:
                workflow_dir = Path(workflow_file).parent
                bnd_path = workflow_dir / bnd_file
            
            # Try tests/jayatilake_experiment
            if not bnd_path.exists():
                bnd_path = Path("tests/jayatilake_experiment") / bnd_file
        
        if not bnd_path.exists():
            print(f"[ERROR] BND file not found: {bnd_file}")
            return False
        
        # Create a minimal config for the gene network
        class MinimalConfig:
            def __init__(self):
                self.gene_network = None
        
        class GeneNetworkConfig:
            def __init__(self, bnd):
                self.bnd_file = str(bnd)
                self.propagation_steps = 500
                self.random_initialization = random_initialization
                self.output_nodes = ["Proliferation", "Apoptosis", "Growth_Arrest", "Necrosis"]
                self.nodes = {}
        
        config = MinimalConfig()
        config.gene_network = GeneNetworkConfig(bnd_path)
        
        # Create the gene network
        gene_network = BooleanNetwork(config=config)
        
        # Reset with random initialization if requested
        gene_network.reset(random_init=random_initialization)
        
        # Store in context
        context['standalone_gene_network'] = gene_network
        context['gene_networks'] = [gene_network]  # Array for multi-cell testing
        
        print(f"   [+] Loaded BND file: {bnd_path}")
        print(f"   [+] Total nodes: {len(gene_network.nodes)}")
        print(f"   [+] Input nodes: {len(gene_network.input_nodes)}")
        print(f"   [+] Output nodes: {len(gene_network.output_nodes)}")
        print(f"   [+] Random initialization: {random_initialization}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize gene network: {e}")
        import traceback
        traceback.print_exc()
        return False


@register_function(
    display_name="Set Gene Network Input States",
    description="Set input node states from a file or dictionary",
    category="UTILITY",
    parameters=[
        {"name": "input_file", "type": "STRING", "description": "Path to input states file", "default": ""},
        {"name": "Oxygen_supply", "type": "BOOL", "description": "Oxygen supply input", "default": True},
        {"name": "Glucose_supply", "type": "BOOL", "description": "Glucose supply input", "default": True},
        {"name": "MCT1_stimulus", "type": "BOOL", "description": "MCT1 stimulus input", "default": False},
        {"name": "Proton_level", "type": "BOOL", "description": "Proton level input", "default": False},
        {"name": "FGFR_stimulus", "type": "BOOL", "description": "FGFR stimulus input", "default": False},
        {"name": "EGFR_stimulus", "type": "BOOL", "description": "EGFR stimulus input", "default": False},
        {"name": "cMET_stimulus", "type": "BOOL", "description": "cMET stimulus input", "default": False},
        {"name": "Growth_Inhibitor", "type": "BOOL", "description": "Growth inhibitor input", "default": False},
        {"name": "DNA_damage", "type": "BOOL", "description": "DNA damage input", "default": False},
        {"name": "TGFBR_stimulus", "type": "BOOL", "description": "TGFBR stimulus input", "default": False},
    ],
    outputs=[],
    cloneable=False
)
def set_gene_network_inputs(
    context: Dict[str, Any],
    input_file: str = "",
    Oxygen_supply: bool = True,
    Glucose_supply: bool = True,
    MCT1_stimulus: bool = False,
    Proton_level: bool = False,
    FGFR_stimulus: bool = False,
    EGFR_stimulus: bool = False,
    cMET_stimulus: bool = False,
    Growth_Inhibitor: bool = False,
    DNA_damage: bool = False,
    TGFBR_stimulus: bool = False,
    **kwargs
) -> bool:
    """
    Set input node states for the standalone gene network.
    """
    print(f"[GENE_NETWORK] Setting input states")
    
    gene_network = context.get('standalone_gene_network')
    if not gene_network:
        print("[ERROR] No standalone gene network in context")
        return False
    
    # Build input states dict
    input_states = {
        'Oxygen_supply': Oxygen_supply,
        'Glucose_supply': Glucose_supply,
        'MCT1_stimulus': MCT1_stimulus,
        'Proton_level': Proton_level,
        'FGFR_stimulus': FGFR_stimulus,
        'EGFR_stimulus': EGFR_stimulus,
        'cMET_stimulus': cMET_stimulus,
        'Growth_Inhibitor': Growth_Inhibitor,
        'DNA_damage': DNA_damage,
        'TGFBR_stimulus': TGFBR_stimulus,
    }
    
    # Load from file if specified
    if input_file:
        input_path = Path(input_file)
        if input_path.exists():
            with open(input_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        node_name, value = line.split('=', 1)
                        node_name = node_name.strip()
                        value = value.strip().lower()
                        input_states[node_name] = value in ('true', '1', 'on', 'yes')
            print(f"   [+] Loaded inputs from file: {input_file}")
    
    # Apply input states
    gene_network.set_input_states(input_states)
    
    # Store for reference
    context['gene_network_inputs'] = input_states
    
    # Print active inputs
    active_inputs = [k for k, v in input_states.items() if v]
    print(f"   [+] Active inputs: {active_inputs}")

    return True


@register_function(
    display_name="Run Gene Network Propagation",
    description="Run gene network for specified propagation steps",
    category="UTILITY",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps", "default": 500},
        {"name": "num_runs", "type": "INT", "description": "Number of independent runs for statistics", "default": 1},
        {"name": "verbose", "type": "BOOL", "description": "Print detailed output", "default": False},
    ],
    outputs=["gene_states"],
    cloneable=False
)
def run_gene_network_propagation(
    context: Dict[str, Any],
    propagation_steps: int = 500,
    num_runs: int = 1,
    verbose: bool = False,
    **kwargs
) -> bool:
    """
    Run gene network propagation and collect statistics.
    """
    print(f"[GENE_NETWORK] Running {num_runs} propagation(s) with {propagation_steps} steps each")

    gene_network = context.get('standalone_gene_network')
    if not gene_network:
        print("[ERROR] No standalone gene network in context")
        return False

    input_states = context.get('gene_network_inputs', {})

    # Statistics collection
    from collections import Counter, defaultdict
    node_stats = defaultdict(Counter)
    fate_nodes = ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']
    metabolic_nodes = ['mitoATP', 'glycoATP']

    all_results = []

    for run in range(num_runs):
        # Reset and re-apply inputs for each run
        gene_network.reset(random_init=True)
        gene_network.set_input_states(input_states)
        gene_network.initialize_logic_states(verbose=verbose and run == 0)

        # Run propagation
        final_states = gene_network.step(propagation_steps)

        # Re-apply inputs after propagation to ensure they weren't corrupted
        gene_network.set_input_states(input_states)

        all_results.append(final_states)

        # Collect statistics
        for node_name, state in final_states.items():
            node_stats[node_name][state] += 1

        if verbose and num_runs <= 10:
            fate_str = ", ".join([f"{n}={'ON' if final_states.get(n, False) else 'OFF'}" for n in fate_nodes])
            meta_str = ", ".join([f"{n}={'ON' if final_states.get(n, False) else 'OFF'}" for n in metabolic_nodes])
            print(f"   Run {run+1}: {fate_str} | {meta_str}")

    # Store results
    context['gene_network_results'] = all_results
    context['gene_network_stats'] = dict(node_stats)

    # Print summary
    print(f"\n[RESULTS] Gene Network Statistics ({num_runs} runs, {propagation_steps} steps):")
    print(f"   Fate Nodes:")
    for node in fate_nodes:
        if node in node_stats:
            on_count = node_stats[node][True]
            off_count = node_stats[node][False]
            total = on_count + off_count
            print(f"      {node}: ON={on_count}/{total} ({100*on_count/total:.1f}%), OFF={off_count}/{total} ({100*off_count/total:.1f}%)")

    print(f"   Metabolic Nodes:")
    for node in metabolic_nodes:
        if node in node_stats:
            on_count = node_stats[node][True]
            off_count = node_stats[node][False]
            total = on_count + off_count
            print(f"      {node}: ON={on_count}/{total} ({100*on_count/total:.1f}%), OFF={off_count}/{total} ({100*off_count/total:.1f}%)")

    return True


@register_function(
    display_name="Print Gene Network States",
    description="Print current states of all gene network nodes",
    category="UTILITY",
    parameters=[
        {"name": "show_all_nodes", "type": "BOOL", "description": "Show all nodes, not just fate/metabolic", "default": False},
    ],
    outputs=[],
    cloneable=False
)
def print_gene_network_states(
    context: Dict[str, Any],
    show_all_nodes: bool = False,
    **kwargs
) -> bool:
    """
    Print current gene network states.
    """
    gene_network = context.get('standalone_gene_network')
    if not gene_network:
        print("[ERROR] No standalone gene network in context")
        return False

    states = gene_network.get_all_states()

    fate_nodes = ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']
    metabolic_nodes = ['mitoATP', 'glycoATP']

    print(f"\n[GENE_NETWORK] Current States:")
    print(f"   Input Nodes:")
    for node in sorted(gene_network.input_nodes):
        state = states.get(node, False)
        print(f"      {node}: {'ON' if state else 'OFF'}")

    print(f"   Fate Nodes:")
    for node in fate_nodes:
        if node in states:
            print(f"      {node}: {'ON' if states[node] else 'OFF'}")

    print(f"   Metabolic Nodes:")
    for node in metabolic_nodes:
        if node in states:
            print(f"      {node}: {'ON' if states[node] else 'OFF'}")

    if show_all_nodes:
        print(f"   All Other Nodes:")
        for node, state in sorted(states.items()):
            if node not in fate_nodes and node not in metabolic_nodes and node not in gene_network.input_nodes:
                print(f"      {node}: {'ON' if state else 'OFF'}")

    return True

