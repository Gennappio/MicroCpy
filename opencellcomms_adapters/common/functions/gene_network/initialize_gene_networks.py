"""
Initialize Gene Networks - Create gene networks for all cells in population.

This function creates a Boolean gene network for each cell and stores them
in context['gene_networks'] (a dict mapping cell_id → BooleanNetwork).

Gene networks are NOT stored in cell.state to keep cell state clean and
allow gene network operations to be fully controlled by workflow functions.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from src.workflow.decorators import register_function
from src.interfaces.base import IGeneNetwork


def get_gene_network(context: Dict[str, Any], cell_id: str) -> Optional[IGeneNetwork]:
    """
    Helper function to safely get a cell's gene network from context.

    Args:
        context: Workflow context containing gene_networks dict
        cell_id: The cell's unique identifier

    Returns:
        IGeneNetwork instance or None if not found
    """
    gene_networks = context.get('gene_networks', {})
    return gene_networks.get(cell_id)


def set_gene_network(context: Dict[str, Any], cell_id: str, gene_network: IGeneNetwork) -> None:
    """
    Helper function to set a cell's gene network in context.

    Args:
        context: Workflow context containing gene_networks dict
        cell_id: The cell's unique identifier
        gene_network: IGeneNetwork instance to store
    """
    if 'gene_networks' not in context:
        context['gene_networks'] = {}
    context['gene_networks'][cell_id] = gene_network


@register_function(
    display_name="Initialize Gene Networks",
    description="Create gene networks for all cells in population (stored in context['gene_networks'])",
    category="INITIALIZATION",
    parameters=[
        {"name": "bnd_file", "type": "STRING", "description": "Path to BND file", "default": "gene_network.bnd"},
        {"name": "random_initialization", "type": "BOOL", "description": "Use random initialization for non-input nodes", "default": True},
    ],
    outputs=["gene_networks"],
    cloneable=False
)
def initialize_gene_networks(
    context: Dict[str, Any],
    bnd_file: str = "gene_network.bnd",
    random_initialization: bool = True,
    **kwargs
) -> bool:
    """
    Create gene networks for all cells in population.

    Gene networks are stored in context['gene_networks'] as a dict mapping
    cell_id → BooleanNetwork instance. This keeps cell state clean and allows
    gene network operations to be fully controlled by workflow functions.

    This is REUSABLE:
    - Each cell gets its OWN copy of the gene network
    - Non-input nodes are randomly initialized (for stochasticity)
    - Input nodes are NOT set here (use 'Set Gene Network Input States')
    """
    print(f"[GENE_NETWORK] Initializing gene networks for all cells")

    population = context.get('population')
    if population is None:
        print("[ERROR] No population found. Run 'Initialize Population' first.")
        return False

    try:
        # Ensure src is in path
        import sys
        from pathlib import Path as SysPath
        src_path = SysPath(__file__).parent.parent.parent.parent
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from biology.gene_network import BooleanNetwork

        # Find the BND file
        bnd_path = Path(bnd_file)
        if not bnd_path.exists():
            # Try tests directory as fallback
            bnd_path = Path("tests") / bnd_file

        if not bnd_path.exists():
            print(f"[ERROR] BND file not found: {bnd_file}")
            return False

        # Create config for gene network
        class GeneNetworkConfig:
            def __init__(self, bnd, random_init):
                self.bnd_file = str(bnd)
                self.propagation_steps = 500
                self.random_initialization = random_init
                self.output_nodes = ["Proliferation", "Apoptosis", "Growth_Arrest", "Necrosis"]
                self.nodes = {}

        class MinimalConfig:
            def __init__(self):
                self.gene_network = None

        config = MinimalConfig()
        config.gene_network = GeneNetworkConfig(bnd_path, random_initialization)

        # Store config for later use
        context['gene_network_config'] = config
        context['random_initialization'] = random_initialization

        # Initialize gene_networks dict in context
        context['gene_networks'] = {}

        # Create gene network for each cell (stored in context, NOT in cell.state)
        cells = population.state.cells
        num_cells = len(cells)

        for cell_id, cell in cells.items():
            # Create a FRESH gene network for each cell
            cell_gn = BooleanNetwork(config=config)

            # === INLINE reset() logic (from BooleanNetwork.reset() line 533) ===
            # Reset nodes: fate nodes to False, others to random by default
            import random

            # Define output/fate nodes that should always start as False
            fate_nodes = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}

            for node in cell_gn.nodes.values():
                if node.is_input:
                    # Input nodes keep their externally set states
                    continue
                elif node.name in fate_nodes:
                    # Fate nodes always start as False (biologically correct)
                    node.current_state = False
                    node.next_state = False
                else:
                    # ALL other non-input nodes start RANDOM by default
                    state = random.choice([True, False]) if random_initialization else False
                    node.current_state = state
                    node.next_state = state
            # === END INLINE reset() ===

            # Store gene network in context (NOT in cell.state)
            context['gene_networks'][cell_id] = cell_gn

            # === INLINE get_all_states() logic (from BooleanNetwork.get_all_states() line 529) ===
            # Get all node states
            initial_gene_states = {name: node.current_state for name, node in cell_gn.nodes.items()}
            # === END INLINE get_all_states() ===

            cell.state = cell.state.with_updates(gene_states=initial_gene_states)

        # Create a reference gene network for getting input node names etc.
        # NOTE: We do NOT add this to context['gene_network'] because that would
        # trigger "full simulation mode" in run_sim.py. We want "workflow-only mode".
        reference_gn = BooleanNetwork(config=config)
        context['reference_gene_network'] = reference_gn

        print(f"   [+] Loaded BND file: {bnd_path}")
        print(f"   [+] Created gene networks for {num_cells} cells (stored in context['gene_networks'])")
        print(f"   [+] Random initialization: {random_initialization}")
        print(f"   [+] Input nodes: {list(reference_gn.input_nodes)}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to initialize gene networks: {e}")
        import traceback
        traceback.print_exc()
        return False

