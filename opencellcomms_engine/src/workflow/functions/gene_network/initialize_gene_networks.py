"""
Initialize Gene Networks - Attach gene networks to all cells in population.

This function creates and attaches a Boolean gene network to each cell.
Each cell gets its OWN copy of the gene network with random initialization.
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Initialize Gene Networks",
    description="Create and attach gene networks to all cells in population",
    category="INITIALIZATION",
    parameters=[
        {"name": "bnd_file", "type": "STRING", "description": "Path to BND file", "default": "gene_network.bnd"},
        {"name": "random_initialization", "type": "BOOL", "description": "Use random initialization for non-input nodes", "default": True},
    ],
    outputs=["gene_network"],
    cloneable=False
)
def initialize_gene_networks(
    context: Dict[str, Any],
    bnd_file: str = "gene_network.bnd",
    random_initialization: bool = True,
    **kwargs
) -> bool:
    """
    Create and attach gene networks to all cells in population.

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

        # Attach gene network to each cell
        cells = population.state.cells
        num_cells = len(cells)

        for cell_id, cell in cells.items():
            # Create a FRESH gene network for each cell
            cell_gn = BooleanNetwork(config=config)
            cell_gn.reset(random_init=random_initialization)

            # Update cell state with gene network
            cell.state.gene_network = cell_gn

        # Create a reference gene network for getting input node names etc.
        # NOTE: We do NOT add this to context['gene_network'] because that would
        # trigger "full simulation mode" in run_sim.py. We want "workflow-only mode".
        reference_gn = BooleanNetwork(config=config)
        context['reference_gene_network'] = reference_gn

        print(f"   [+] Loaded BND file: {bnd_path}")
        print(f"   [+] Attached gene networks to {num_cells} cells")
        print(f"   [+] Random initialization: {random_initialization}")
        print(f"   [+] Input nodes: {list(reference_gn.input_nodes)}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to initialize gene networks: {e}")
        import traceback
        traceback.print_exc()
        return False

