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

LOOP STRUCTURE (step-outer, cell-inner — matches simulator):
    All cells advance 1 step together per "tick", matching the simulator's
    ``simulate_batch_off`` tick loop where every cell gets exactly 1
    ``_downstream_change()`` call per tick before the next tick begins.

KEY NETLOGO BEHAVIORS:
    - Fate nodes ALWAYS reset to false after evaluation (transient triggers)
    - Fate reversion: if fate node turns OFF and was the current fate → _fate = None
    - Fate overwriting: last fate to fire wins (NOT hierarchical counting)
    - Stopping: reversible stops only at Necrosis; non-reversible stops at first fate

OSCILLATION / RAN-REFRESH (mirrors gene_network_workflow_oscillation_simulator.py):
    oscillation     — toggle MCT1_stimulus ON/OFF every oscillation_period steps;
                      cMET_stimulus turns ON after the first diffusion_step
    ran_refresh     — re-randomize _cell_ran1/_cell_ran2 at every diffusion_step
    diffusion_step  — interval (in steps) at which inputs are refreshed

PSEUDOCODE:
    # build active cell list once
    for step in range(propagation_steps):
        if step > 0 and step % diffusion_step == 0:
            refresh_inputs(oscillation, ran_refresh, ...)
        for each cell:
            if stopping_condition_met: continue
            downstream_change(cell_gn)  # one graph-walk step
    for each cell:
        cell.phenotype = cell_gn._fate or "Quiescent"
"""

from typing import Dict, Any, Optional, List, Tuple
from collections import Counter
import random
from src.workflow.decorators import register_function

# =============================================================================
# OSCILLATION CONSTANTS (mirrors gene_network_workflow_oscillation_simulator.py)
# =============================================================================
_OSCILLATING_INPUTS = {'MCT1_stimulus'}
_DELAYED_ON_INPUTS  = {'cMET_stimulus'}


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
        {"name": "oscillation", "type": "BOOL",
         "description": "Toggle MCT1_stimulus/cMET_stimulus ON/OFF periodically "
                        "(mimics diffusion sawtooth from NetLogo)",
         "default": False},
        {"name": "oscillation_period", "type": "INT",
         "description": "ON/OFF period in steps (default: 500)",
         "default": 500},
        {"name": "ran_refresh", "type": "BOOL",
         "description": "Re-randomize _cell_ran1/_cell_ran2 at each diffusion_step "
                        "(emulates changing patch concentrations)",
         "default": False},
        {"name": "diffusion_step", "type": "INT",
         "description": "Steps between input refresh (default: 250)",
         "default": 250},
        {"name": "reset_fate", "type": "BOOL",
         "description": "Clear _fate before propagation so cells are re-evaluated every call "
                        "(use when apply_associations provides fresh inputs each loop iteration)",
         "default": False},
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
    oscillation: bool = False,
    oscillation_period: int = 500,
    ran_refresh: bool = False,
    diffusion_step: int = 250,
    reset_fate: bool = False,
    **kwargs
) -> bool:
    """
    Propagate gene networks using NetLogo-faithful graph walking.

    Expects networks to have been set up by ``initialize_netlogo_gene_networks``
    (output links, _last_node, _fate, _cell_ran1/2 already initialized).

    Loop structure mirrors the simulator's ``simulate_batch_off``: step-outer,
    cell-inner — all cells advance 1 graph-walk step per tick in lockstep.

    Args:
        context: Workflow context with 'population' and 'gene_networks'
        propagation_steps: Number of graph-walk steps (ticks) per call
        reversible: True = keep updating until Necrosis, False = stop at first fate
        verbose: Enable detailed logging
        debug_steps: Print step-by-step propagation details
        oscillation: Toggle MCT1_stimulus/cMET_stimulus periodically
        oscillation_period: ON/OFF period in steps
        ran_refresh: Re-randomize _cell_ran1/_cell_ran2 at each diffusion_step
        diffusion_step: Steps between input refresh
        reset_fate: Clear _fate before propagation so cells are re-evaluated

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        flags = []
        if oscillation:
            flags.append(f"OSCILLATION period={oscillation_period}")
        if ran_refresh:
            flags.append("RAN-REFRESH")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"[GENE_NETWORK] NetLogo-faithful graph walking propagation "
              f"({propagation_steps} steps each){flag_str}")
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
    # BUILD ACTIVE CELL LIST & ENSURE NETLOGO ATTRIBUTES
    # =========================================================================
    # Build once before the step loop (matches simulator: fixed population list
    # per propagation call).  Daughter cells added during this call are NOT
    # included — they will be picked up in the next loop iteration.
    active_cells: List[Tuple] = []
    cells_without_gn = 0

    for cell_id, cell in cells.items():
        cell_gn = gene_networks.get(cell_id)
        if cell_gn is None:
            cells_without_gn += 1
            continue
        _ensure_netlogo_attrs(cell_gn)
        active_cells.append((cell_id, cell, cell_gn))

    # =========================================================================
    # RESET FATE (allow re-evaluation when spatial inputs change each iteration)
    # =========================================================================
    if reset_fate:
        fates_cleared = 0
        for _cell_id, _cell, cell_gn in active_cells:
            if cell_gn._fate is not None:
                fates_cleared += 1
                cell_gn._fate = None
        if verbose and fates_cleared > 0:
            print(f"   [+] reset_fate: cleared _fate on {fates_cleared}/{len(active_cells)} cells")

    # =========================================================================
    # STEP-OUTER / CELL-INNER PROPAGATION LOOP
    # (mirrors simulate_batch_off tick structure)
    # =========================================================================
    for step in range(propagation_steps):
        # --- Input refresh at diffusion_step intervals ---
        if step > 0 and diffusion_step > 0 and step % diffusion_step == 0:
            _refresh_inputs_step(
                context, active_cells,
                oscillation, step, oscillation_period, ran_refresh,
            )

        # --- One graph-walk step per cell ---
        for cell_id, cell, cell_gn in active_cells:
            # STOPPING CONDITION (use continue — skip this cell this step,
            # matching the simulator's `continue` not `break`)
            if reversible:
                if cell_gn._fate == "Necrosis":
                    continue
            else:
                if cell_gn._fate is not None:
                    continue

            if debug_steps:
                print(f"\n  Cell {cell_id}, Step {step+1}: "
                      f"fate={cell_gn._fate}, last_node={cell_gn._last_node}")

            _netlogo_downstream_change(
                cell_gn,
                current_tick=step,
                debug=debug_steps,
            )

    # =========================================================================
    # COLLECT RESULTS & UPDATE CELL STATES
    # =========================================================================
    fate_distribution = Counter()

    for cell_id, cell, cell_gn in active_cells:
        final_fate = cell_gn._fate or "Quiescent"
        fate_distribution[final_fate] += 1

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
    cells_with_gn = len(active_cells)
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
# HELPER: ENSURE NETLOGO ATTRIBUTES EXIST (for daughter cells from division)
# =============================================================================
def _ensure_netlogo_attrs(cell_gn) -> None:
    """
    Ensure all NetLogo-specific attributes exist on a gene network object.

    Daughter cells created during division may not have these if copy() was used.
    Called once per cell before the step loop.
    """
    if not hasattr(cell_gn, '_fate'):
        cell_gn._fate = None
    if not hasattr(cell_gn, '_last_node'):
        input_nodes = [n for n, nd in cell_gn.nodes.items() if nd.is_input]
        cell_gn._last_node = (random.choice(input_nodes) if input_nodes
                              else random.choice(list(cell_gn.nodes.keys())))
    if not hasattr(cell_gn, '_cell_ran1'):
        cell_gn._cell_ran1 = random.random()
    if not hasattr(cell_gn, '_cell_ran2'):
        cell_gn._cell_ran2 = random.random()
    if not hasattr(cell_gn, '_output_links_built') or not cell_gn._output_links_built:
        _build_output_links(cell_gn)
        cell_gn._output_links_built = True


# =============================================================================
# HELPER: REFRESH INPUTS AT DIFFUSION STEP
# =============================================================================
def _refresh_inputs_step(
    context: Dict[str, Any],
    active_cells: List[Tuple],
    oscillation: bool,
    step: int,
    oscillation_period: int,
    ran_refresh: bool,
) -> None:
    """
    Refresh input states at diffusion_step intervals.

    Mirrors ``simulate_batch_off`` input-refresh block (lines 480-487 of
    gene_network_workflow_oscillation_simulator.py):
      - Compute oscillation state (toggle OSCILLATING_INPUTS, delay DELAYED_ON_INPUTS)
      - Optionally re-randomize _cell_ran1/_cell_ran2 (ran_refresh)
      - Re-apply input states to every cell's gene network

    Reads ``context['gene_network_inputs']`` and
    ``context['gene_network_init_params']`` stored by
    ``initialize_netlogo_gene_networks``.
    """
    base_inputs: Dict[str, bool] = context.get('gene_network_inputs', {})
    init_params: Dict[str, float] = context.get('gene_network_init_params', {})
    effective = dict(base_inputs)

    if oscillation:
        half = oscillation_period // 2
        phase = step % oscillation_period
        for inp in _OSCILLATING_INPUTS:
            if inp in effective:
                effective[inp] = (phase < half)
        # DELAYED_ON_INPUTS turn ON only after the first diffusion_step
        if step >= 250:
            for inp in _DELAYED_ON_INPUTS:
                if inp in effective:
                    effective[inp] = True

    mct1i_conc = init_params.get('MCT1I_concentration', 0.0)
    glut1i_conc = init_params.get('GLUT1I_concentration', 0.0)

    for _cell_id, _cell, cell_gn in active_cells:
        if ran_refresh:
            cell_gn._cell_ran1 = random.random()
            cell_gn._cell_ran2 = random.random()
        _apply_input_states_inline(cell_gn, effective, mct1i_conc, glut1i_conc)


def _apply_input_states_inline(
    cell_gn,
    input_states: Dict[str, bool],
    mct1i_concentration: float = 0.0,
    glut1i_concentration: float = 0.0,
) -> None:
    """
    Re-apply input states to a gene network (mirrors _apply_input_states from
    initialize_netlogo_gene_networks.py).

    Standard inputs → deterministic ON/OFF via current_state.
    MCT1I / GLUT1I → probabilistic via Hill function if concentration > 0.
    """
    for node_name, state in input_states.items():
        if node_name in cell_gn.nodes:
            cell_gn.nodes[node_name].current_state = state

    if mct1i_concentration > 0 and 'MCT1I' in cell_gn.nodes:
        hill = 0.85 * (1.0 - 1.0 / (1.0 + mct1i_concentration))
        cell_gn.nodes['MCT1I'].current_state = (hill > cell_gn._cell_ran1)

    if glut1i_concentration > 0 and 'GLUT1I' in cell_gn.nodes:
        hill = 0.85 * (1.0 - 1.0 / (1.0 + glut1i_concentration))
        cell_gn.nodes['GLUT1I'].current_state = (hill > cell_gn._cell_ran2)


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
