"""
Generic Gene Network Propagation and Update.

This is the UNIVERSAL loop function that works with ANY gene network implementation:
- BooleanNetwork (no fate logic)
- HierarchicalBooleanNetwork (with fate logic)
- Any future IGeneNetwork implementation

The function:
1. Calls cell_gn.step(N) to propagate
2. Updates cell.state.gene_states with the results
3. Checks cell_gn.get_phenotype() and updates phenotype if not None

This allows the loop to be IDENTICAL across all workflows. The only thing that changes
between experiments is which concrete class is created in kernel_setup.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import IGeneNetwork


@register_function(
    display_name="Propagate and Update Gene Networks",
    description="Universal gene network propagation - works with any IGeneNetwork implementation",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps", "default": 500},
        {"name": "verbose", "type": "BOOL", "description": "Enable detailed logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def propagate_and_update_gene_networks(
    context: Dict[str, Any] = None,
    propagation_steps: int = 500,
    verbose: bool = False,
    **kwargs
) -> bool:
    """
    Propagate gene networks and update cell states.

    This is a UNIVERSAL function that works with any IGeneNetwork implementation:
    - BooleanNetwork: propagates, updates gene_states only
    - HierarchicalBooleanNetwork: propagates, updates gene_states AND phenotype

    The loop doesn't know or care which concrete class it's working with.
    It just calls the interface methods: step() and get_phenotype().

    Gene networks are accessed from context['gene_networks'] (dict mapping cell_id → IGeneNetwork).

    Args:
        context: Workflow context containing population and gene_networks
        propagation_steps: Number of propagation steps
        verbose: Enable detailed logging
        **kwargs: Additional parameters

    Returns:
        True if successful
    """
    # =========================================================================
    # GET REQUIRED ITEMS FROM CONTEXT
    # =========================================================================
    if not context:
        print("[ERROR] No context provided")
        return False

    population = context.get('population')
    if population is None:
        print("[ERROR] No population in context")
        return False

    gene_networks = context.get('gene_networks', {})
    if not gene_networks:
        print("[ERROR] No gene networks in context - run 'Initialize Gene Networks' first")
        return False

    cells = population.state.cells
    num_cells = len(cells)

    if num_cells == 0:
        print("[ERROR] No cells in population")
        return False

    if verbose:
        print(f"[GENE_NETWORK] Propagating gene networks for {num_cells} cells ({propagation_steps} steps each)")

    # =========================================================================
    # UPDATE EACH CELL'S GENE NETWORK
    # =========================================================================
    updated_cells = {}
    cells_with_gn = 0
    cells_without_gn = 0
    phenotype_updates = 0

    for cell_id, cell in cells.items():
        # Get gene network from context (NOT from cell.state)
        cell_gn: Optional[IGeneNetwork] = gene_networks.get(cell_id)

        if cell_gn is None:
            cells_without_gn += 1
            updated_cells[cell_id] = cell
            continue

        cells_with_gn += 1

        # === INLINE step() logic ===
        # Check if this is a HierarchicalBooleanNetwork (has fate_hierarchy attribute)
        is_hierarchical = hasattr(cell_gn, 'fate_hierarchy')

        if is_hierarchical:
            # === INLINE HierarchicalBooleanNetwork.step() (line 642) ===
            import random

            # Reset fate fire counts
            fate_hierarchy = cell_gn.fate_hierarchy
            fate_fire_counts = {fate: 0 for fate in fate_hierarchy}

            # Propagate step by step and count fate firings
            for _ in range(propagation_steps):
                # === INLINE _netlogo_single_gene_update() (line 476) ===
                # Cache the list of updatable genes (only computed once)
                if not hasattr(cell_gn, '_cached_updatable_genes'):
                    cell_gn._cached_updatable_genes = [
                        name for name, gene_node in cell_gn.nodes.items()
                        if not gene_node.is_input and gene_node.update_function
                    ]

                if cell_gn._cached_updatable_genes:
                    # Randomly select ONE gene (NetLogo style)
                    selected_gene = random.choice(cell_gn._cached_updatable_genes)
                    gene_node = cell_gn.nodes[selected_gene]

                    # Cache and reuse the current states dictionary
                    if not hasattr(cell_gn, '_state_cache'):
                        cell_gn._state_cache = {}

                    # Update the cached states with current values
                    for name, node in cell_gn.nodes.items():
                        cell_gn._state_cache[name] = node.current_state

                    # Evaluate the gene's rule and update ONLY this gene
                    new_state = gene_node.update_function(cell_gn._state_cache)
                    gene_node.current_state = new_state
                # === END INLINE _netlogo_single_gene_update() ===

                # Get current states and count fate gene activations
                current_states = {name: node.current_state for name, node in cell_gn.nodes.items()}
                for fate in fate_hierarchy:
                    if current_states.get(fate, False):
                        fate_fire_counts[fate] += 1

            # === INLINE _apply_fate_hierarchy() (line 678) ===
            # Default to Quiescent if no fate genes fired
            effective_fate = "Quiescent"

            # Apply hierarchy: iterate through list, last one that fired wins
            for fate in fate_hierarchy:
                if fate_fire_counts[fate] > 0:
                    effective_fate = fate
            # === END INLINE _apply_fate_hierarchy() ===

            # Store the effective fate in the network object
            cell_gn.effective_fate = effective_fate
            cell_gn.fate_fire_counts = fate_fire_counts

            # Get final gene states
            gene_states = {name: node.current_state for name, node in cell_gn.nodes.items()}
            # === END INLINE HierarchicalBooleanNetwork.step() ===
        else:
            # === INLINE BooleanNetwork._default_step() (line 467) ===
            import random

            for step in range(propagation_steps):
                # === INLINE _netlogo_single_gene_update() (line 476) ===
                # Cache the list of updatable genes (only computed once)
                if not hasattr(cell_gn, '_cached_updatable_genes'):
                    cell_gn._cached_updatable_genes = [
                        name for name, gene_node in cell_gn.nodes.items()
                        if not gene_node.is_input and gene_node.update_function
                    ]

                if cell_gn._cached_updatable_genes:
                    # Randomly select ONE gene (NetLogo style)
                    selected_gene = random.choice(cell_gn._cached_updatable_genes)
                    gene_node = cell_gn.nodes[selected_gene]

                    # Cache and reuse the current states dictionary
                    if not hasattr(cell_gn, '_state_cache'):
                        cell_gn._state_cache = {}

                    # Update the cached states with current values
                    for name, node in cell_gn.nodes.items():
                        cell_gn._state_cache[name] = node.current_state

                    # Evaluate the gene's rule and update ONLY this gene
                    new_state = gene_node.update_function(cell_gn._state_cache)
                    gene_node.current_state = new_state
                # === END INLINE _netlogo_single_gene_update() ===

            # Get all states
            gene_states = {name: node.current_state for name, node in cell_gn.nodes.items()}
            # === END INLINE BooleanNetwork._default_step() ===
        # === END INLINE step() ===

        # Prepare updates
        updates = {'gene_states': gene_states}

        # === INLINE get_phenotype() (line 695) ===
        # Check if this network determined a phenotype
        phenotype = None
        if is_hierarchical:
            phenotype = cell_gn.effective_fate
        # === END INLINE get_phenotype() ===

        if phenotype is not None:
            updates['phenotype'] = phenotype
            phenotype_updates += 1

        # Update cell state
        cell.state = cell.state.with_updates(**updates)
        updated_cells[cell_id] = cell

    # Update population
    population.state = population.state.with_updates(cells=updated_cells)

    # =========================================================================
    # LOG SUMMARY
    # =========================================================================
    if verbose:
        print(f"   [+] Updated {cells_with_gn}/{num_cells} cells")
        if cells_without_gn > 0:
            print(f"   [!] Skipped {cells_without_gn} cells without gene network")
        if phenotype_updates > 0:
            print(f"   [+] Updated phenotype for {phenotype_updates} cells (hierarchical fate logic)")
        else:
            print(f"   [+] No phenotype updates (using BooleanNetwork without fate logic)")

    return True

