"""
Initialize Hierarchical Gene Networks for All Cells.

This function creates HierarchicalBooleanNetwork instances (with fate determination logic)
instead of plain BooleanNetwork instances.

The hierarchical network counts fate gene firings during propagation and applies
a hierarchy to determine the effective phenotype.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Initialize Hierarchical Gene Networks",
    description="Create hierarchical gene networks with fate determination logic for all cells",
    category="INITIALIZATION",
    parameters=[
        {"name": "bnd_file", "type": "STRING", "description": "Path to BND file", "default": "gene_network.bnd"},
        {"name": "random_initialization", "type": "BOOL", "description": "Use random initialization for non-input nodes", "default": True},
        {"name": "fate_hierarchy", "type": "STRING", "description": "Comma-separated fate genes in priority order (last=highest)", "default": "Necrosis,Apoptosis,Growth_Arrest,Proliferation"},
    ],
    outputs=["gene_network"],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def initialize_hierarchical_gene_networks(
    context: Dict[str, Any],
    bnd_file: str = "gene_network.bnd",
    random_initialization: bool = True,
    fate_hierarchy: str = "Necrosis,Apoptosis,Growth_Arrest,Proliferation",
    **kwargs
) -> bool:
    """
    Create and attach hierarchical gene networks to all cells in population.
    
    This creates HierarchicalBooleanNetwork instances instead of plain BooleanNetwork.
    The hierarchical network automatically counts fate firings and determines phenotype.
    
    Args:
        context: Workflow context
        bnd_file: Path to BND file
        random_initialization: Use random initialization for non-input nodes
        fate_hierarchy: Comma-separated fate genes in priority order (last=highest)
        **kwargs: Additional parameters
    
    Returns:
        True if successful
    """
    print(f"[GENE_NETWORK] Initializing HIERARCHICAL gene networks for all cells")
    
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
        
        from biology.gene_network import HierarchicalBooleanNetwork
        
        # Parse fate hierarchy
        fate_hierarchy_list = [fate.strip() for fate in fate_hierarchy.split(',')]
        
        # Find the BND file using context['resolve_path'] if available
        if 'resolve_path' in context:
            bnd_path = context['resolve_path'](bnd_file)
        else:
            bnd_path = Path(bnd_file)
            if not bnd_path.exists():
                # Try relative to engine root
                engine_root = Path(__file__).parent.parent.parent.parent
                candidate = engine_root / bnd_file
                if candidate.exists():
                    bnd_path = candidate
                else:
                    # Try relative to workspace root
                    workspace_root = engine_root.parent
                    candidate = workspace_root / bnd_file
                    if candidate.exists():
                        bnd_path = candidate
                    else:
                        # Try tests directory as final fallback
                        bnd_path = Path("tests") / bnd_file
        
        if not bnd_path.exists():
            print(f"[ERROR] BND file not found: {bnd_file}")
            print(f"   Tried: {bnd_file}, engine_root/{bnd_file}, workspace_root/{bnd_file}")
            return False
        
        # Create config for gene network
        class GeneNetworkConfig:
            def __init__(self, bnd, random_init):
                self.bnd_file = str(bnd)
                self.propagation_steps = 500
                self.random_initialization = random_init
                self.output_nodes = fate_hierarchy_list
                self.nodes = {}
        
        class MinimalConfig:
            def __init__(self):
                self.gene_network = None
        
        config = MinimalConfig()
        config.gene_network = GeneNetworkConfig(bnd_path, random_initialization)
        
        # Store config for later use
        context['gene_network_config'] = config
        context['random_initialization'] = random_initialization
        context['fate_hierarchy'] = fate_hierarchy_list

        # Initialize gene_networks dict in context
        context['gene_networks'] = {}

        # Create hierarchical gene network for each cell (stored in context, NOT in cell.state)
        cells = population.state.cells
        num_cells = len(cells)

        for cell_id, cell in cells.items():
            # Create a FRESH hierarchical gene network for each cell
            cell_gn = HierarchicalBooleanNetwork(
                config=config,
                fate_hierarchy=fate_hierarchy_list
            )

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
        reference_gn = HierarchicalBooleanNetwork(
            config=config,
            fate_hierarchy=fate_hierarchy_list
        )
        context['reference_gene_network'] = reference_gn
        
        print(f"   [+] Loaded BND file: {bnd_path}")
        print(f"   [+] Created HIERARCHICAL gene networks for {num_cells} cells (stored in context['gene_networks'])")
        print(f"   [+] Random initialization: {random_initialization}")
        print(f"   [+] Fate hierarchy: {' > '.join(reversed(fate_hierarchy_list))} > Quiescent")
        print(f"   [+] Input nodes: {list(reference_gn.input_nodes)}")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Failed to initialize hierarchical gene networks: {e}")
        import traceback
        traceback.print_exc()
        return False

