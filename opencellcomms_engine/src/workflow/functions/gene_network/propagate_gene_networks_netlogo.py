"""
Propagate Gene Networks with NetLogo-Faithful Graph Walking.

Implements the EXACT graph walking algorithm from
microC_Metabolic_Symbiosis.nlogo3d (-RUN-MICRO-STEP-195).

PREREQUISITES:
    Run ``initialize_netlogo_gene_networks`` first.  That function builds the
    graph output links, initializes _last_node / _fate / _cell_ran1 / _cell_ran2,
    and applies input states (including probabilistic GLUT1I / MCT1I activation).

GRAPH WALKING ALGORITHM (per cell, per call):
    1. Start from _last_node (persists across calls)
    2. Pick ONE random outgoing link (NetLogo: ask one-of my-out-links)
    3. Evaluate target node's Boolean rule → update its state
    4. Handle target type:
       - Fate node (Output-Fate): set cell _fate, reset node to OFF, jump to random input
       - Output node: jump to random input
       - Gene / Input node: continue walking from that node
    5. Repeat for ``propagation_steps`` steps

KEY NETLOGO BEHAVIORS:
    - Fate nodes ALWAYS reset to false after evaluation (transient triggers)
    - Fate reversion: if fate node turns OFF and was the current fate → _fate = None
    - Fate overwriting: last fate to fire wins (NOT hierarchical counting)
    - Stopping: reversible stops only at Necrosis; non-reversible stops at first fate

PSEUDOCODE:
    for each cell:
        for step in range(propagation_steps):
            if stopping_condition_met: break
            downstream_change(cell_gn)  # one graph-walk step
        cell.phenotype = cell_gn._fate or "Quiescent"
"""

from typing import Dict, Any, Optional
from collections import Counter
import random
from src.workflow.decorators import register_function


@register_function(
    display_name="Propagate Gene Networks (NetLogo-Faithful)",
    description="NetLogo-faithful graph walking propagation (requires initialize_netlogo_gene_networks)",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT",
         "description": "Number of graph-walk steps per cell", "default": 500},
        {"name": "reversible", "type": "BOOL",
         "description": "Keep updating until Necrosis (True) or stop at first fate (False)",
         "default": True},
        {"name": "verbose", "type": "BOOL",
         "description": "Enable detailed logging", "default": False},
        {"name": "debug_steps", "type": "BOOL",
         "description": "Print step-by-step propagation details", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def propagate_gene_networks_netlogo(
    context: Dict[str, Any] = None,
    propagation_steps: int = 500,
    reversible: bool = True,
    verbose: bool = False,
    debug_steps: bool = False,
    **kwargs
) -> bool:
    """
    Propagate gene networks using NetLogo-faithful graph walking.

    Expects networks to have been set up by ``initialize_netlogo_gene_networks``
    (output links, _last_node, _fate, _cell_ran1/2 already initialized).

    Args:
        context: Workflow context with 'population' and 'gene_networks'
        propagation_steps: Number of graph-walk steps per cell
        reversible: True = keep updating until Necrosis, False = stop at first fate
        verbose: Enable detailed logging
        debug_steps: Print step-by-step propagation details

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"[GENE_NETWORK] NetLogo-faithful graph walking propagation "
              f"({propagation_steps} steps each)")
        print(f"  Mode: {'REVERSIBLE' if reversible else 'NON-REVERSIBLE'}")

    # =========================================================================
    # VALIDATE CONTEXT
    # =========================================================================
    if not context:
        print("[ERROR] No context provided")
        return False

    population = context.get('population')
    if not population:
        print("[ERROR] No population in context")
        return False

    gene_networks = context.get('gene_networks', {})
    if not gene_networks:
        print("[ERROR] No gene networks in context "
              "- run 'Initialize NetLogo Gene Networks' first")
        return False

    cells = population.state.cells
    num_cells = len(cells)

    # =========================================================================
    # PROPAGATE EACH CELL'S GENE NETWORK
    # =========================================================================
    cells_with_gn = 0
    cells_without_gn = 0
    fate_distribution = Counter()

    for cell_id, cell in cells.items():
        cell_gn = gene_networks.get(cell_id)

        if cell_gn is None:
            cells_without_gn += 1
            continue

        cells_with_gn += 1

        # === ENSURE NETLOGO ATTRIBUTES EXIST ===
        # These are dynamically added by initialize_netlogo_gene_networks.
        # Daughter cells (from division) may not have them if copy() was used.
        if not hasattr(cell_gn, '_fate'):
            cell_gn._fate = None
        if not hasattr(cell_gn, '_last_node'):
            input_nodes = [n for n, nd in cell_gn.nodes.items() if nd.is_input]
            cell_gn._last_node = random.choice(input_nodes) if input_nodes else random.choice(list(cell_gn.nodes.keys()))
        if not hasattr(cell_gn, '_cell_ran1'):
            cell_gn._cell_ran1 = random.random()
        if not hasattr(cell_gn, '_cell_ran2'):
            cell_gn._cell_ran2 = random.random()
        if not hasattr(cell_gn, '_output_links_built') or not cell_gn._output_links_built:
            _build_output_links(cell_gn)
            cell_gn._output_links_built = True

        # === TRACK STATISTICS ===
        fate_fires = 0
        fate_reverts = 0

        # === GRAPH WALKING PROPAGATION (NetLogo: -RUN-MICRO-STEP-195) ===
        for step in range(propagation_steps):
            if debug_steps:
                print(f"\n  Cell {cell_id}, Step {step+1}: "
                      f"fate={cell_gn._fate}, last_node={cell_gn._last_node}")

            # === STOPPING CONDITION (NetLogo line 1611) ===
            if reversible:
                if cell_gn._fate == "Necrosis":
                    if debug_steps:
                        print("    STOPPED: Necrosis reached (reversible mode)")
                    break
            else:
                if cell_gn._fate is not None:
                    if debug_steps:
                        print(f"    STOPPED: Fate '{cell_gn._fate}' reached "
                              "(non-reversible mode)")
                    break

            # === ONE GRAPH WALKING STEP ===
            fate_assigned, fate_reverted = _netlogo_downstream_change(
                cell_gn,
                current_tick=step,
                debug=debug_steps,
            )

            if fate_assigned:
                fate_fires += 1
            if fate_reverted:
                fate_reverts += 1

        # === COLLECT FINAL FATE ===
        final_fate = cell_gn._fate or "Quiescent"
        fate_distribution[final_fate] += 1

        # === UPDATE CELL STATE ===
        gene_states = {
            name: node.current_state
            for name, node in cell_gn.nodes.items()
        }
        # Fate nodes are transient triggers in the NetLogo model: they reset
        # to False after evaluation (line 1568).  However, the determined fate
        # is stored in cell_gn._fate.  We write it back into gene_states so
        # downstream marking functions can read it via gene_states[<fate>].
        if cell_gn._fate and cell_gn._fate in gene_states:
            gene_states[cell_gn._fate] = True

        # NOTE: We only update gene_states here, not phenotype.
        # Phenotype will be set by downstream marking functions:
        # - mark_apoptotic_cells
        # - mark_growth_arrest_cells
        # - mark_proliferating_cells
        cell.state = cell.state.with_updates(
            gene_states=gene_states,
        )

    # =========================================================================
    # LOG SUMMARY
    # =========================================================================
    if verbose:
        print(f"   [+] Updated {cells_with_gn}/{num_cells} cells")
        if cells_without_gn > 0:
            print(f"   [!] Skipped {cells_without_gn} cells without gene network")

        if fate_distribution:
            pheno_str = ", ".join(
                f"'{k}': {v}"
                for k, v in sorted(fate_distribution.items(), key=lambda x: -x[1])
            )
            print(f"   [+] Fate distribution: {{{pheno_str}}}")

    return True


# =============================================================================
# HELPER: GET RANDOM INPUT NODE
# =============================================================================
def _get_random_start_node(gene_network) -> str:
    """
    Get a random input node to start / restart graph walking.
    NetLogo: one-of my-nodes with [ kind = "Input" ]
    """
    input_nodes = [name for name, node in gene_network.nodes.items() if node.is_input]
    if input_nodes:
        return random.choice(input_nodes)

    nodes_with_outputs = [
        name for name, node in gene_network.nodes.items()
        if hasattr(node, 'outputs') and node.outputs
    ]
    if nodes_with_outputs:
        return random.choice(nodes_with_outputs)

    return random.choice(list(gene_network.nodes.keys()))


def _netlogo_downstream_change(gene_network, current_tick: int, debug: bool = False):
    """
    Faithful replication of NetLogo's -DOWNSTREAM-CHANGE-590
    
    From last_node, pick ONE random outgoing link and update the target.
    This implements the graph walking core of the NetLogo model.
    
    NetLogo code (line 1273-1280):
        to -DOWNSTREAM-CHANGE-590
           ask one-of my-out-links [ -INFLUENCE-LINK-END-WITH-LOGGING--36 ]
        end
    
    Returns:
        Tuple of (fate_assigned: Optional[str], fate_reverted: bool)
    """
    # Get current node
    current_node = gene_network.nodes.get(gene_network._last_node)
    if not current_node:
        gene_network._last_node = _get_random_start_node(gene_network)
        return None, False
    
    # Check if node has outputs
    if not hasattr(current_node, 'outputs') or not current_node.outputs:
        # No outgoing links: reset to random input
        if debug:
            print(f"    {gene_network._last_node} has no outputs → reset to input")
        gene_network._last_node = _get_random_start_node(gene_network)
        return None, False
    
    # Pick ONE random outgoing link (NetLogo: ask one-of my-out-links)
    target_name = random.choice(list(current_node.outputs))
    
    # Apply the influence link update
    return _netlogo_influence_link_end(
        gene_network,
        source_name=gene_network._last_node,
        target_name=target_name,
        current_tick=current_tick,
        debug=debug
    )


def _netlogo_influence_link_end(gene_network, source_name: str, target_name: str, 
                                 current_tick: int, debug: bool = False):
    """
    Faithful replication of NetLogo's -INFLUENCE-LINK-END-WITH-LOGGING--36
    
    This is the core NetLogo update function (lines 1487-1591):
    1. Save current fate before update
    2. Evaluate target node's Boolean rule
    3. Update target's active state
    4. Handle fate nodes specially:
       - If active → set cell fate
       - If NOT active AND was current fate → revert fate to nobody
       - ALWAYS reset fate node to false (transient triggers)
    5. Set last_node based on target's kind
    
    Returns:
        Tuple of (fate_assigned: Optional[str], fate_reverted: bool)
    """
    target_node = gene_network.nodes[target_name]
    
    # NetLogo line 1509-1513: save current fate before update
    current_fate_before = gene_network._fate
    
    fate_assigned = None
    fate_reverted = False
    
    # NetLogo line 1522-1538: evaluate and update target
    if target_node.update_function:
        current_states = {name: node.current_state for name, node in gene_network.nodes.items()}
        new_state = target_node.update_function(current_states)
        
        if debug:
            print(f"    {source_name} → {target_name}")
            print(f"      State: {target_node.current_state} → {new_state}")
        
        # Update node state
        if target_node.current_state != new_state:
            target_node.current_state = new_state
            if debug:
                print(f"      STATE CHANGED")
    
    # NetLogo line 1539-1591: Handle node type
    # Check if this is a fate node
    fate_nodes = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}
    
    if target_name in fate_nodes:
        # === OUTPUT-FATE NODE LOGIC (NetLogo lines 1540-1578) ===
        
        # NetLogo line 1540: if active → trigger fate
        if target_node.current_state:
            fate_assigned = target_name
            gene_network._fate = target_name
            if debug:
                print(f"      FATE FIRE: {target_name}")
        
        # NetLogo line 1563-1564: if NOT active AND was current fate → revert
        if (not target_node.current_state) and (target_name == current_fate_before):
            gene_network._fate = None  # NetLogo: set my-fate nobody
            fate_reverted = True
            if debug:
                print(f"      FATE REVERTED: {target_name} turned OFF → nobody")
        
        # NetLogo line 1568: ALWAYS reset fate node to false (transient trigger)
        target_node.current_state = False
        
        # NetLogo line 1571-1578: return to random input
        gene_network._last_node = _get_random_start_node(gene_network)
        if debug:
            print(f"      Output-Fate → reset to input: {gene_network._last_node}")
    
    else:
        # === GENE/INPUT NODE LOGIC (NetLogo lines 1583-1590) ===
        # Continue walking from this node
        gene_network._last_node = target_name
        if debug:
            print(f"      Gene/Input → continue from: {gene_network._last_node}")
    
    return fate_assigned, fate_reverted


# =============================================================================
# HELPER: BUILD OUTPUT LINKS (for networks missing graph connectivity)
# =============================================================================
def _build_output_links(gene_network) -> None:
    """
    Build output links (which nodes depend on each node) for graph walking.

    For each node, find all nodes whose inputs list mentions it.
    This creates the directed edges needed for graph walking.

    After this call every node has a ``node.outputs: Set[str]`` attribute.
    """
    for node in gene_network.nodes.values():
        if not hasattr(node, 'outputs'):
            node.outputs = set()

    for node_name, node in gene_network.nodes.items():
        if node.is_input or not node.update_function:
            continue

        dependencies = node.inputs if isinstance(node.inputs, set) else set(node.inputs)
        for dep_name in dependencies:
            if dep_name in gene_network.nodes:
                gene_network.nodes[dep_name].outputs.add(node_name)
