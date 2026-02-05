"""
Update Gene Networks with Hierarchical Fate Logic.

This function propagates gene networks and applies a hierarchical fate determination
based on how many times each fate gene fired during propagation.

Hierarchy: Proliferation > Growth_Arrest > Apoptosis > Necrosis > Quiescent

The logic counts how many times each fate gene was TRUE during propagation steps,
then applies the hierarchy to determine the effective fate.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function


@register_function(
    display_name="Update Gene Networks (Hierarchical Fate)",
    description="Propagate gene networks and determine fate using hierarchical logic based on firing counts",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps", "default": 500},
        {"name": "verbose", "type": "BOOL", "description": "Enable detailed logging", "default": None},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def update_gene_networks_hierarchical(
    context: Dict[str, Any],
    propagation_steps: int = 500,
    verbose: bool = None,
    **kwargs
) -> None:
    """
    Update gene networks with hierarchical fate determination.
    
    For each cell:
    1. Propagate gene network for N steps
    2. Count how many times each fate gene was TRUE during propagation
    3. Apply hierarchy: Proliferation > Growth_Arrest > Apoptosis > Necrosis
    4. Set effective fate based on hierarchy
    
    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
        propagation_steps: Number of gene network propagation steps
        verbose: Enable detailed logging
        **kwargs: Additional parameters (ignored)
    """
    from src.workflow.logging import log, log_always
    
    # =========================================================================
    # EXTRACT CONTEXT
    # =========================================================================
    population = context.get('population')
    
    # =========================================================================
    # VALIDATE REQUIRED ITEMS
    # =========================================================================
    if population is None:
        log_always("[ERROR] No population in context - skipping", prefix="[HIERARCHICAL]")
        return
    
    cells = population.state.cells
    num_cells = len(cells)
    
    if num_cells == 0:
        log_always("[ERROR] No cells in population", prefix="[HIERARCHICAL]")
        return
    
    log(context, f"Updating {num_cells} cells with hierarchical fate logic ({propagation_steps} steps)", 
        prefix="[HIERARCHICAL]", node_verbose=verbose)
    
    # =========================================================================
    # DEFINE FATE HIERARCHY
    # =========================================================================
    # Order matters: higher index = higher priority
    fate_hierarchy = ["Necrosis", "Apoptosis", "Growth_Arrest", "Proliferation"]
    
    # =========================================================================
    # UPDATE EACH CELL'S GENE NETWORK
    # =========================================================================
    updated_cells = {}
    cells_with_gn = 0
    fate_counts = {fate: 0 for fate in fate_hierarchy}
    fate_counts["Quiescent"] = 0
    
    for cell_id, cell in cells.items():
        cell_gn = cell.state.gene_network
        
        if cell_gn is None:
            # No gene network - keep cell as is
            updated_cells[cell_id] = cell
            continue
        
        cells_with_gn += 1
        
        # =====================================================================
        # PROPAGATE AND COUNT FATE FIRINGS
        # =====================================================================
        fate_fire_counts = {fate: 0 for fate in fate_hierarchy}
        
        # Propagate step by step and count fate gene activations
        for step in range(propagation_steps):
            # Single step propagation (NetLogo-style)
            gene_states = cell_gn.step(1)
            
            # Count which fate genes are TRUE
            for fate in fate_hierarchy:
                if gene_states.get(fate, False):
                    fate_fire_counts[fate] += 1
        
        # Get final gene states after all propagation
        final_gene_states = cell_gn.get_all_states()
        
        # =====================================================================
        # APPLY HIERARCHICAL FATE LOGIC
        # =====================================================================
        # Determine which fates fired at least once
        fates_fired = {fate: (fate_fire_counts[fate] > 0) for fate in fate_hierarchy}
        
        # Apply hierarchy (Proliferation > Growth_Arrest > Apoptosis > Necrosis)
        effective_fate = "Quiescent"  # Default
        
        for fate in fate_hierarchy:
            if fates_fired[fate]:
                effective_fate = fate
        
        # =====================================================================
        # UPDATE CELL STATE
        # =====================================================================
        # Cache gene states and fate
        cell._cached_gene_states = final_gene_states
        cell._cached_effective_fate = effective_fate
        cell._cached_fate_fire_counts = fate_fire_counts
        
        # Update cell's gene states and phenotype
        cell.state = cell.state.with_updates(
            gene_states=final_gene_states,
            phenotype=effective_fate
        )
        
        updated_cells[cell_id] = cell
        fate_counts[effective_fate] += 1
    
    # Update population
    population.state = population.state.with_updates(cells=updated_cells)
    
    # =========================================================================
    # LOG SUMMARY
    # =========================================================================
    log(context, f"Updated {cells_with_gn}/{num_cells} cells", 
        prefix="[HIERARCHICAL]", node_verbose=verbose)
    log(context, f"Fate distribution: {fate_counts}", 
        prefix="[HIERARCHICAL]", node_verbose=verbose)

