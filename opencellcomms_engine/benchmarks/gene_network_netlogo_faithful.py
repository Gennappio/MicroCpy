#!/usr/bin/env python3
"""

===============================================================================
QUICK START
===============================================================================

Basic usage:
    python gene_network_netlogo_faithful.py network.bnd inputs.txt --runs 100 --steps 500

Required files:
    - network.bnd: Boolean network definition (MaBoSS/BND format)
    - inputs.txt: Input node states (one per line: NodeName=ON/OFF)

Common options:
    --runs 100              Number of independent simulation runs
    --steps 500             Number of graph-walk steps per run
    --non-reversible        Stop at first fate (default: keep updating)
    --apply-cell-actions    Apply proliferation/death event layer
    --seed 42               Random seed for reproducibility
    --debug-steps           Print detailed step-by-step execution

Example command:
    python gene_network_netlogo_faithful.py \\
        microc.bnd \\
        benchmarks/test_simple_inputs.txt \\
        --runs 100 --steps 1000 --seed 42

===============================================================================
HOW THE UPDATE MECHANISM WORKS
===============================================================================

This simulator uses GRAPH WALKING (not synchronous or asynchronous update):

1. START: Begin at a random Input node (my-last-node)

2. STEP: Pick ONE random outgoing link from current node
   - Evaluate the target node's Boolean rule
   - Update target node's state (if rule changed it)

3. ROUTING: Move to next node based on target's type:
   - If target is a Fate node (Apoptosis, Proliferation, etc.)
     → Set cell's fate label
     → Reset fate node to false (always)
     → Jump back to a random Input node
   - If target is a Gene or Input node
     → Continue walking from that node

4. REPEAT: Go to step 2 for the specified number of steps

This is NEITHER synchronous NOR asynchronous. It's a random walk through 
the network graph, visiting one node at a time, following one random edge 
at each step.

===============================================================================
HOW TO CHANGE THE UPDATE MECHANISM
===============================================================================

The core update logic is in the `downstream_change()` method (line ~480):

Option 1: CHANGE TO SYNCHRONOUS UPDATE
    Modify `downstream_change()` to update ALL downstream nodes at once:
    
    def downstream_change(self, ...):
        for target_name in current_node.outputs:
            self.influence_link_end(self.last_node, target_name, ...)

Option 2: CHANGE TO ASYNCHRONOUS UPDATE
    Modify the main loop to pick ONE random node from the entire network:
    
    for step in range(steps):
        random_node = random.choice(list(self.nodes.keys()))
        # Update random_node based on its logic rule

Option 3: CHANGE EDGE SELECTION
    In `downstream_change()`, change from random to deterministic:
    - All edges: for target_name in current_node.outputs
    - First edge: target_name = list(current_node.outputs)[0]
    - Custom priority: sort outputs by some criterion

===============================================================================
HOW TO CHANGE PHENOTYPE EVALUATION
===============================================================================

Phenotypes are determined by Output-Fate nodes. The logic is in 
`_handle_fate_fire()` (line ~435):

Current behavior: ALL FATES ARE UNCONDITIONAL
    When a fate node's Boolean rule evaluates to true → fate fires immediately

Option 1: ADD METABOLIC/ENVIRONMENTAL GATES
    Modify `_handle_fate_fire()` to check conditions:
    
    elif fate_name == "Proliferation":
        # Add your gating conditions here
        if some_condition_met():
            self.fate = "Proliferation"
            return "Proliferation"
        else:
            return None  # Blocked

Option 2: CHANGE FATE PRIORITY (hierarchical)
    Modify `influence_link_end()` to NOT overwrite higher-priority fates:
    
    if target_node.active:
        fate = self._handle_fate_fire(target_name, ...)
        if fate and (self.fate is None or priority[fate] > priority[self.fate]):
            self.fate = fate

Option 3: ACCUMULATE FATES (counting)
    Track how many times each fate fires, pick most frequent:
    
    self.fate_counts[fate_name] += 1
    # At end: self.fate = max(self.fate_counts, key=self.fate_counts.get)

Option 4: DELAYED PHENOTYPE DECISION
    Don't set fate immediately; accumulate signals and decide at end:
    
    self.fate_signals.append((step, fate_name))
    # Decide based on timing/frequency at simulation end

===============================================================================
KEY BEHAVIORS (NetLogo-Faithful)
===============================================================================

1. FATE OVERWRITING: Last fate to fire wins (not hierarchical)
2. FATE REVERSION: If a fate node turns OFF and it's the current fate 
                   → fate resets to "nobody" (quiescent)
3. TRANSIENT FATE NODES: Fate nodes always reset to false after evaluation
4. REVERSIBLE MODE: Cell keeps updating until Necrosis (default)
   NON-REVERSIBLE MODE: Cell stops at first fate (--non-reversible flag)
5. CELL ACTIONS LAYER: Optional phenotype evaluation at simulation end
   (--apply-cell-actions flag) - checks fate only AFTER all graph walking

===============================================================================
OUTPUT INTERPRETATION
===============================================================================

"Final Fate": The cell's my-fate at the end of simulation
    - NOT determined by which node is ON
    - NOT hierarchical (no priority ranking)
    - Simply the last fate label that was set and survived to the end

"Quiescent": my-fate = nobody (no active fate at end)

"Fate Node Boolean State": The my-active value of fate nodes at end
    - Usually all OFF (because they reset after every visit)
    - ON percentage indicates fate never got visited

"Fate fires": How many times each fate was assigned during the run
"Fate reverts": How many times fate reset to nobody due to node turning OFF

"""

import argparse
import random
import re
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, Counter
import json


# =============================================================================
# CONFIGURATION
# =============================================================================
# Node types (matching NetLogo's kind attribute)
NODE_KIND_INPUT = "Input"
NODE_KIND_GENE = "Gene"
NODE_KIND_OUTPUT_FATE = "Output-Fate"
NODE_KIND_OUTPUT = "Output"

# Fate node names (these trigger phenotype decisions)
FATE_NODE_NAMES = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}



# =============================================================================
# BOOLEAN LOGIC ENGINE
# =============================================================================

class BooleanExpression:
    """Evaluates boolean expressions with gene states."""
    
    def __init__(self, expression: str):
        self.expression = expression.strip()
    
    def evaluate(self, gene_states: Dict[str, bool]) -> bool:
        """Evaluate the boolean expression given current gene states."""
        if not self.expression:
            return False
            
        expr = self.expression
        
        # Sort gene names by length (longest first) to avoid partial replacements
        gene_names = sorted(gene_states.keys(), key=len, reverse=True)
        
        for gene_name in gene_names:
            if gene_name in expr:
                value = "True" if gene_states[gene_name] else "False"
                expr = re.sub(r'\b' + re.escape(gene_name) + r'\b', value, expr)
        
        # Replace logical operators
        expr = expr.replace('&', ' and ')
        expr = expr.replace('|', ' or ')
        expr = expr.replace('!', ' not ')
        
        try:
            return bool(eval(expr))
        except:
            return False



# =============================================================================
# NETWORK STRUCTURE
# =============================================================================

class NetworkNode:
    """Represents a single node in the gene network with NetLogo-compatible attributes."""
    
    def __init__(self, name: str, logic_rule: str = "", is_input: bool = False):
        self.name = name
        self.logic_rule = logic_rule
        self.is_input = is_input
        
        # NetLogo: my-active (the node's boolean state)
        self.active = False
        
        # NetLogo: kind (Input, Gene, Output-Fate, Output)
        if is_input:
            self.kind = NODE_KIND_INPUT
        elif name in FATE_NODE_NAMES:
            self.kind = NODE_KIND_OUTPUT_FATE
        else:
            self.kind = NODE_KIND_GENE
        
        # Graph connectivity
        self.inputs: Set[str] = set()   # Nodes this node depends on
        self.outputs: Set[str] = set()  # Nodes that depend on this node
        
        # Boolean update function
        if logic_rule and not is_input:
            self.update_function = BooleanExpression(logic_rule)
            self._extract_inputs()
        else:
            self.update_function = None
        
        # NetLogo: my-active-change-count
        self.active_change_count = 0
    
    def _extract_inputs(self):
        """Extract input node names from the logic rule."""
        if not self.logic_rule:
            return
        gene_names = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', self.logic_rule)
        keywords = {'and', 'or', 'not', 'True', 'False', 'true', 'false'}
        self.inputs = {name for name in gene_names if name not in keywords}



# =============================================================================
# GRAPH-WALKING GENE NETWORK SIMULATOR
# =============================================================================

class NetLogoFaithfulGeneNetwork:
    """
    Faithful replication of the microC NetLogo gene network update mechanism.
    
    This class replicates the exact behavior of:
    - -INFLUENCE-LINK-END-WITH-LOGGING--36 (node update logic)
    - -DOWNSTREAM-CHANGE-590 (graph walking selection)
    - -RUN-MICRO-STEP-195 (main loop with stopping condition)
    - -FATE-APOPTOSIS-25, -FATE-PROLIFERATION-102, etc. (fate handlers)
    
    *** CUSTOMIZE UPDATE MECHANISM HERE ***
    See downstream_change() to modify how edges are selected
    """
    
    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.input_nodes: Set[str] = set()
        
        # NetLogo: my-last-node
        self.last_node: Optional[str] = None
        
        # NetLogo: my-fate (cell's current fate, or None = nobody)
        self.fate: Optional[str] = None
        
        # NetLogo: my-network-steps
        self.network_steps: int = 0
        
        # Mutations (NetLogo: my-table-of-mutations)
        self.mutations: Set[str] = set()

        # NetLogo: my-growth-arrest-cycle (countdown for Growth_Arrest)
        # Starts at the-growth-arrest-cycle (default 3) and counts down every intercellular step.
        # When it reaches 0, fate resets to nobody.
        self.growth_arrest_cycle: int = 0
        self.growth_arrest_cycle_max: int = 3  # NetLogo default: the-growth-arrest-cycle = 3
    
    def load_bnd_file(self, bnd_file: str):
        """Load gene network from .bnd file and build graph structure."""
        print(f"Loading gene network from {bnd_file}")
        
        with open(bnd_file, 'r') as f:
            content = f.read()
        
        # Parse nodes (case-insensitive to handle both 'node' and 'Node')
        node_pattern = r'[Nn]ode\s+(\w+)\s*\{([^}]+)\}'
        nodes_created = 0

        for match in re.finditer(node_pattern, content, re.MULTILINE | re.DOTALL):
            node_name = match.group(1)
            node_content = match.group(2)

            # Check if it's an input node
            is_input = ('rate_up = 0' in node_content and 'rate_down = 0' in node_content)

            # Extract logic rule
            logic_match = re.search(r'logic\s*=\s*([^;]+);', node_content)
            logic_rule = logic_match.group(1).strip() if logic_match else ""

            # Check for self-referential logic (input node in MaBoSS format)
            if logic_rule.strip('() ') == node_name:
                is_input = True
                logic_rule = ""

            self.nodes[node_name] = NetworkNode(
                name=node_name,
                logic_rule=logic_rule,
                is_input=is_input
            )

            if is_input:
                self.input_nodes.add(node_name)

            nodes_created += 1
        
        # Build graph structure
        self._build_graph_links()
        
        total_links = sum(len(node.outputs) for node in self.nodes.values())
        print(f"Created {nodes_created} nodes ({len(self.input_nodes)} input nodes)")
        print(f"Built graph with {total_links} directed links")
        
        # Classify node kinds
        fate_count = sum(1 for n in self.nodes.values() if n.kind == NODE_KIND_OUTPUT_FATE)
        print(f"Node kinds: {len(self.input_nodes)} Input, {fate_count} Output-Fate, "
              f"{nodes_created - len(self.input_nodes) - fate_count} Gene")
        
        return nodes_created
    
    def _build_graph_links(self):
        """Build outgoing links for each node based on logic rules."""
        for node_name, node in self.nodes.items():
            for input_name in node.inputs:
                if input_name in self.nodes:
                    self.nodes[input_name].outputs.add(node_name)
    
    def load_input_states(self, input_file: str) -> Dict[str, bool]:
        """Load input node states from file."""
        input_states = {}
        
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    node_name, value = line.split('=', 1)
                    node_name = node_name.strip()
                    value = value.strip().lower()
                    
                    if value in ('true', '1', 'on', 'yes'):
                        input_states[node_name] = True
                    elif value in ('false', '0', 'off', 'no'):
                        input_states[node_name] = False
                    else:
                        input_states[node_name] = False
        
        print(f"Loaded {len(input_states)} input states")
        return input_states
    
    def set_input_states(self, input_states: Dict[str, bool]):
        """Set the states of input nodes."""
        for node_name, state in input_states.items():
            if node_name in self.nodes:
                self.nodes[node_name].active = state
    
    def reset(self, random_init: bool = True):
        """
        Reset network for a new simulation run.
        
        NetLogo behavior:
        - Fate nodes start as False
        - Other non-input nodes: random initialization
        - last_node: random input (or random gene if no inputs)
        - fate: nobody (None)
        """
        for node in self.nodes.values():
            if not node.is_input:
                if node.kind == NODE_KIND_OUTPUT_FATE:
                    node.active = False
                else:
                    node.active = random.choice([True, False]) if random_init else False
                node.active_change_count = 0
        
        # NetLogo line 1070-1073: set my-last-node
        if self.input_nodes:
            self.last_node = random.choice(list(self.input_nodes))
        else:
            self.last_node = random.choice(list(self.nodes.keys()))
        
        # NetLogo: my-fate starts as nobody
        self.fate = None
        
        # NetLogo: my-network-steps
        self.network_steps = 0
    
    def initialize_logic_states(self, input_states: Dict[str, bool]):
        """
        Initialize node states to match their logic rules (one pass).

        IMPORTANT FOR NETLOGO FIDELITY:
        In the NetLogo model, boolean rules are evaluated *only when a node is visited*
        during graph walking. There is no global pre-initialization pass that can turn
        fate/output nodes ON before they are visited.

        Therefore this helper must NEVER change Output-Fate (and Output) nodes, otherwise
        fate nodes can end the run stuck ON (which cannot happen in NetLogo because
        fate nodes are reset to OFF whenever visited, and start OFF).
        """
        current_states = {name: node.active for name, node in self.nodes.items()}
        
        updates_made = 0
        for node_name, node in self.nodes.items():
            # Only initialize real genes. Do NOT initialize Output / Output-Fate nodes.
            if node.kind != NODE_KIND_GENE:
                continue
            if not node.is_input and node.update_function:
                try:
                    expected_state = node.update_function.evaluate(current_states)
                    if node.active != expected_state:
                        node.active = expected_state
                        current_states[node_name] = expected_state
                        updates_made += 1
                except:
                    pass
        
        return updates_made
    
    def get_all_states(self) -> Dict[str, bool]:
        """Get current states of all nodes."""
        return {name: node.active for name, node in self.nodes.items()}
    
    def _get_random_input_node(self) -> str:
        """NetLogo: one-of my-nodes with [ kind = "Input" ]"""
        if self.input_nodes:
            return random.choice(list(self.input_nodes))
        # Fallback: any node with outputs
        nodes_with_outputs = [name for name, node in self.nodes.items() if node.outputs]
        if nodes_with_outputs:
            return random.choice(nodes_with_outputs)
        return random.choice(list(self.nodes.keys()))
    
    def influence_link_end(self, source_name: str, target_name: str, *, current_tick: int, debug: bool = False):
        """
        Faithful replication of -INFLUENCE-LINK-END-WITH-LOGGING--36
        
        This is the core NetLogo update function that:
        1. Saves current fate before update
        2. Evaluates target node's boolean rule
        3. Updates target's active state (if not mutated)
        4. Handles fate nodes specially:
           - If active → set cell fate
           - If NOT active AND was current fate → revert fate to nobody
           - ALWAYS reset fate node to false
        5. Sets last_node based on target's kind
        
        Returns:
            Tuple of (fate_assigned: Optional[str], fate_reverted: bool)
        """
        target_node = self.nodes[target_name]
        
        # --- NetLogo line 1509-1513: save current fate before update ---
        current_fate_before = self.fate
        
        # --- NetLogo line 1522-1538: evaluate and update target ---
        self.network_steps += 1
        
        fate_assigned = None
        fate_reverted = False
        
        if target_node.update_function:
            current_states = self.get_all_states()
            new_state = target_node.update_function.evaluate(current_states)
            
            if debug:
                print(f"  {source_name} → {target_name} ({target_node.kind})")
                print(f"    Logic: {target_node.logic_rule}")
                print(f"    State: {target_node.active} → {new_state}")
            
            # NetLogo line 1527: skip mutated genes
            if target_node.active != new_state and target_name not in self.mutations:
                target_node.active = new_state
                target_node.active_change_count += 1
                
                if debug:
                    print(f"    STATE CHANGED: {not new_state} → {new_state}")
        
        # --- NetLogo line 1539-1578: Handle node type ---
        if target_node.kind == NODE_KIND_OUTPUT_FATE:
            # --- Fate node logic ---
            
            # NetLogo line 1540: if active → trigger fate
            if target_node.active:
                fate_assigned = self._handle_fate_fire(target_name, current_tick=current_tick, debug=debug)
            
            # NetLogo line 1563-1564: if NOT active AND was current fate → revert
            if (not target_node.active) and (target_name == current_fate_before):
                self.fate = None  # NetLogo: set my-fate nobody
                fate_reverted = True
                if debug:
                    print(f"    FATE REVERTED: {target_name} turned OFF, was current fate → nobody")
            
            # NetLogo line 1568: ALWAYS reset fate node to false
            target_node.active = False
            
            # NetLogo line 1571-1578: return to random input
            self.last_node = self._get_random_input_node()
            if debug:
                print(f"    Output-Fate → reset to input: {self.last_node}")
        
        elif target_node.kind == NODE_KIND_OUTPUT:
            # NetLogo line 1579-1582: Output → return to random input
            self.last_node = self._get_random_input_node()
            if debug:
                print(f"    Output → reset to input: {self.last_node}")
        
        elif target_node.kind in (NODE_KIND_INPUT, NODE_KIND_GENE):
            # NetLogo line 1583-1590: Input or Gene → continue from target
            self.last_node = target_name
            if debug:
                print(f"    Gene/Input → continue from: {self.last_node}")
        
        return fate_assigned, fate_reverted
    
    def _handle_fate_fire(self, fate_name: str, *, current_tick: int, debug: bool = False) -> Optional[str]:
        """
        Handle a fate node firing. All fates are unconditional (Boolean network only):
        - -FATE-APOPTOSIS-25 (unconditional)
        - -FATE-GROWTH-ARREST-96 (unconditional)
        - -FATE-PROLIFERATION-102 (unconditional)
        - -FATE-NECROSIS-20 (unconditional)
        
        *** CUSTOMIZE PHENOTYPE GATING HERE ***
        Add metabolic/environmental conditions by checking variables
        before setting self.fate
        
        Returns:
            The fate name if conditions met, None otherwise
        """
        if fate_name == "Apoptosis":
            self.fate = "Apoptosis"
            if debug:
                print(f"    FATE FIRE: Apoptosis")
            return "Apoptosis"
        
        elif fate_name == "Growth_Arrest":
            self.fate = "Growth_Arrest"
            self.growth_arrest_cycle = self.growth_arrest_cycle_max  # Reset countdown
            if debug:
                print(f"    FATE FIRE: Growth_Arrest (cycle={self.growth_arrest_cycle})")
            return "Growth_Arrest"
        
        elif fate_name == "Proliferation":
            self.fate = "Proliferation"
            if debug:
                print(f"    FATE FIRE: Proliferation")
            return "Proliferation"
        
        elif fate_name == "Necrosis":
            self.fate = "Necrosis"
            if debug:
                print(f"    FATE FIRE: Necrosis")
            return "Necrosis"
        
        return None
    
    def downstream_change(self, *, current_tick: int, debug: bool = False):
        """
        Faithful replication of -DOWNSTREAM-CHANGE-590
        
        NetLogo: ask one-of my-out-links [ -INFLUENCE-LINK-END-WITH-LOGGING--36 ]
        
        From last_node, pick one random outgoing link and update the target.
        
        *** CUSTOMIZE UPDATE STRATEGY HERE ***
        Change "one-of" to "all" for synchronous update
        Change to random.choice(all_nodes) for asynchronous update
        
        Returns:
            Tuple of (fate_assigned: Optional[str], fate_reverted: bool)
        """
        current_node = self.nodes.get(self.last_node)
        if not current_node:
            self.last_node = self._get_random_input_node()
            return None, False
        
        # NetLogo: ask one-of my-out-links
        if not current_node.outputs:
            # No outgoing links: reset to random input
            if debug:
                print(f"  {self.last_node} has no outputs → reset to input")
            self.last_node = self._get_random_input_node()
            return None, False
        
        # Pick ONE random outgoing link
        target_name = random.choice(list(current_node.outputs))
        
        # Apply the influence link update
        return self.influence_link_end(self.last_node, target_name, current_tick=current_tick, debug=debug)

    def apply_cell_actions(self, *, current_tick: int) -> Dict[str, bool]:
        """
        Evaluate phenotype based on final fate at END of simulation.
        
        This is called ONCE after all graph walking completes, matching the NetLogo
        approach where the network has time to stabilize before phenotype is evaluated.
        
        NetLogo timing:
        - Gene network updates every 1 tick (graph walk)
        - Apoptosis/proliferation checks every 100 ticks (intercellular step)
        - This delay allows transient fates to revert before being acted upon
        
        In this simplified single-cell version:
        - We let the network walk for all specified steps
        - Then evaluate the FINAL fate to determine cell outcome
        - This approximates the "network stabilization" behavior
        
        Returns:
        - If fate == Proliferation: cell would divide
        - If fate == Apoptosis or Necrosis: cell would die
        - If fate == Growth_Arrest or nobody: cell survives but doesn't divide
        """
        proliferated = False
        died = False

        # Proliferation
        if self.fate == "Proliferation":
            proliferated = True

        # Death
        if self.fate in ("Apoptosis", "Necrosis"):
            died = True

        return {"proliferated": proliferated, "died": died}
    
    def simulate(self, steps: int, input_states: Dict[str, bool] = None,
                reversible: bool = True, debug_steps: bool = False,
                print_network: bool = False,
                growth_arrest_cycle_max: int = 3,
                apply_cell_actions: bool = False) -> Dict:
        """
        Faithful replication of -RUN-MICRO-STEP-195 loop.
        
        NetLogo (line 1609-1613):
            do-every ( the-intracellular-step )
                if ( ifelse-value(the-reversible?)[my-fate != "Necrosis"][my-fate = nobody] )
                    [ ask my-last-node [ -DOWNSTREAM-CHANGE-590 ] ]
        
        Args:
            steps: Number of update steps
            input_states: Input node states to enforce
            reversible: True = keep updating until Necrosis. False = stop at any fate
            debug_steps: Print debug info per step
            print_network: Print network structure
        """
        self.growth_arrest_cycle_max = growth_arrest_cycle_max
        
        fate_events = []         # All fate assignment events
        fate_revert_events = []  # All fate revert events
        proliferation_events = 0
        died = False
        steps_completed = 0
        stopped_early = False
        
        for step in range(steps):
            current_tick = step  # 1 step ≈ 1 tick
            if debug_steps:
                print(f"\nSTEP {step + 1} (tick={current_tick}, fate={self.fate}, last_node={self.last_node}):")
            
            # === NetLogo stopping condition (line 1611) ===
            if reversible:
                # Reversible mode: keep going while fate != "Necrosis"
                if self.fate == "Necrosis":
                    stopped_early = True
                    if debug_steps:
                        print(f"  STOPPED: Necrosis reached (reversible mode)")
                    break
            else:
                # Non-reversible mode: keep going while fate == nobody
                if self.fate is not None:
                    stopped_early = True
                    if debug_steps:
                        print(f"  STOPPED: Fate '{self.fate}' reached (non-reversible mode)")
                    break
            
            # === Graph walking update ===
            fate_assigned, fate_reverted = self.downstream_change(current_tick=current_tick, debug=debug_steps)
            
            # Track events
            if fate_assigned:
                fate_events.append({'step': step, 'fate': fate_assigned})
            if fate_reverted:
                fate_revert_events.append({'step': step})
            
            steps_completed = step + 1
        
        # Apply cell actions ONCE at the end (not during simulation)
        if apply_cell_actions:
            actions = self.apply_cell_actions(current_tick=steps_completed)
            if actions["proliferated"]:
                proliferation_events += 1
            if actions["died"]:
                died = True
        
        # Compile results
        final_states = self.get_all_states()
        
        return {
            'final_states': final_states,
            'final_fate': self.fate,                   # The cell's current fate (or None = quiescent)
            'fate_events': fate_events,                 # All fate assignment events
            'fate_revert_events': fate_revert_events,   # All fate revert events
            'proliferation_events': proliferation_events,
            'died': died,
            'total_fate_fires': len(fate_events),
            'steps_completed': steps_completed,
            'stopped_early': stopped_early,
            'network_steps': self.network_steps,
        }



# =============================================================================
# SIMULATION RUNNER
# =============================================================================

def run_simulation(bnd_file: str, input_file: str, runs: int, steps: int,
                  verbose: bool = False, debug_steps: bool = False,
                  print_network: bool = False, reversible: bool = True,
                  seed: Optional[int] = None,
                  initialize_logic: bool = False,
                  growth_arrest_cycle_max: int = 3,
                  apply_cell_actions: bool = False) -> Dict:
    """Run multiple simulations and collect statistics."""
    
    # Load network
    network = NetLogoFaithfulGeneNetwork()
    network.load_bnd_file(bnd_file)
    
    # Load input conditions
    input_states = network.load_input_states(input_file)
    
    # Statistics collection
    fate_nodes = ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']
    metabolic_nodes = ['mitoATP', 'glycoATP']
    
    # Final fate counts (what fate the cell ended up with)
    final_fate_counts = Counter()
    
    # Track fate fire/revert events
    total_fate_fires_per_run = []
    total_reverts_per_run = []
    first_fate_step = defaultdict(list)
    proliferation_events_per_run = []
    died_per_run = []
    
    # Final boolean state tracking
    final_on_counts = defaultdict(int)
    
    # Steps completed
    steps_completed_list = []
    
    print(f"\nRunning {runs} simulations with {steps} steps each...")
    print(f"Mode: {'REVERSIBLE' if reversible else 'NON-REVERSIBLE'}")
    print(f"Pure Boolean network (no metabolic gating)")
    if seed is not None:
        print(f"Random seed: {seed} (per-run seed = seed + run_index)")
    print(f"Logic initialization pass: {'ON' if initialize_logic else 'OFF'}")
    print(f"Growth arrest cycle max: {growth_arrest_cycle_max} (intercellular steps)")
    print(f"Apply NetLogo cell actions layer: {'ON' if apply_cell_actions else 'OFF'}")
    
    for run in range(runs):
        if seed is not None:
            random.seed(seed + run)
        if verbose and runs >= 10 and (run + 1) % (runs // 10) == 0:
            print(f"  Run {run + 1}/{runs}")
        
        # Reset and set inputs
        network.reset(random_init=True)
        network.set_input_states(input_states)

        # Optional: initialize gene (NOT fate/output) logic states.
        # Disabled by default for NetLogo fidelity.
        if initialize_logic:
            if run == 0:
                updates = network.initialize_logic_states(input_states)
                print(f"Logic initialization (genes only): {updates} nodes updated")
            else:
                network.initialize_logic_states(input_states)
        
        # Run simulation
        result = network.simulate(
            steps, 
            input_states=input_states,
            reversible=reversible, 
            debug_steps=debug_steps,
            print_network=(print_network and run == 0),
            growth_arrest_cycle_max=growth_arrest_cycle_max,
            apply_cell_actions=apply_cell_actions,
        )
        
        # Collect statistics
        final_fate = result['final_fate'] or 'Quiescent'
        final_fate_counts[final_fate] += 1
        
        total_fate_fires_per_run.append(result['total_fate_fires'])
        total_reverts_per_run.append(len(result['fate_revert_events']))
        proliferation_events_per_run.append(int(result.get('proliferation_events', 0)))
        died_per_run.append(bool(result.get('died', False)))
        steps_completed_list.append(result['steps_completed'])
        
        # Track when each fate first fires
        seen_fates = set()
        for event in result['fate_events']:
            fate = event['fate']
            if fate not in seen_fates:
                first_fate_step[fate].append(event['step'])
                seen_fates.add(fate)
        
        # Track final boolean states
        for node_name, state in result['final_states'].items():
            if state:
                final_on_counts[node_name] += 1
    
    return {
        'runs': runs,
        'steps': steps,
        'reversible': reversible,
        'input_conditions': input_states,
        'final_fate_counts': dict(final_fate_counts),
        'final_on_counts': dict(final_on_counts),
        'total_fate_fires_per_run': total_fate_fires_per_run,
        'total_reverts_per_run': total_reverts_per_run,
        'proliferation_events_per_run': proliferation_events_per_run,
        'died_per_run': died_per_run,
        'first_fate_step': dict(first_fate_step),
        'steps_completed': steps_completed_list,
        'fate_nodes': fate_nodes,
        'metabolic_nodes': metabolic_nodes,
    }



# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def print_results(results: Dict, bnd_file: str, input_file: str):
    """Print formatted results."""
    runs = results['runs']
    steps = results['steps']
    
    print(f"\n{'='*70}")
    print(f"FAITHFUL NETLOGO GENE NETWORK SIMULATION RESULTS")
    print(f"{'='*70}")
    print(f"Network: {bnd_file}")
    print(f"Inputs: {input_file}")
    print(f"Runs: {runs}, Steps: {steps}")
    print(f"Mode: {'REVERSIBLE' if results['reversible'] else 'NON-REVERSIBLE'}")
    
    print(f"\nInput Conditions:")
    for node, state in results['input_conditions'].items():
        print(f"  {node}: {'ON' if state else 'OFF'}")
    
    # === FINAL FATE DISTRIBUTION ===
    print(f"\n{'='*70}")
    print(f"FINAL CELL FATE DISTRIBUTION (NetLogo: my-fate)")
    print(f"{'='*70}")
    print(f"{'Fate':<20} {'Count':>8} {'Percentage':>12}")
    print(f"{'-'*42}")
    
    for fate in ['Proliferation', 'Growth_Arrest', 'Apoptosis', 'Necrosis', 'Quiescent']:
        count = results['final_fate_counts'].get(fate, 0)
        pct = 100 * count / runs
        print(f"  {fate:<18} {count:>6}/{runs} ({pct:>5.1f}%)")
    
    # === FATE NODE BOOLEAN STATES ===
    print(f"\n{'='*70}")
    print(f"FATE NODE BOOLEAN STATES (final my-active values)")
    print(f"{'='*70}")
    for node in results['fate_nodes']:
        on_count = results['final_on_counts'].get(node, 0)
        off_count = runs - on_count
        print(f"  {node}: ON={on_count}/{runs} ({100*on_count/runs:.1f}%), "
              f"OFF={off_count}/{runs} ({100*off_count/runs:.1f}%)")
    
    # === METABOLIC NODES ===
    print(f"\nMetabolic Node Results (Final State):")
    for node in results['metabolic_nodes']:
        on_count = results['final_on_counts'].get(node, 0)
        print(f"  {node}: ON {on_count}/{runs} ({100*on_count/runs:.1f}%)")
    
    # === FATE FIRE/REVERT STATISTICS ===
    print(f"\n{'='*70}")
    print(f"FATE FIRE/REVERT STATISTICS")
    print(f"{'='*70}")
    fires = results['total_fate_fires_per_run']
    reverts = results['total_reverts_per_run']
    print(f"  Fate fires per run:  avg={sum(fires)/len(fires):.2f}, "
          f"min={min(fires)}, max={max(fires)}")
    print(f"  Fate reverts per run: avg={sum(reverts)/len(reverts):.2f}, "
          f"min={min(reverts)}, max={max(reverts)}")

    # Optional NetLogo-like event layer stats
    if 'proliferation_events_per_run' in results and results['proliferation_events_per_run']:
        pe = results['proliferation_events_per_run']
        print(f"\nNetLogo-like events (single-cell approximation):")
        print(f"  Proliferation events per run: avg={sum(pe)/len(pe):.2f}, min={min(pe)}, max={max(pe)}")
        died = results.get('died_per_run', [])
        if died:
            died_count = sum(1 for x in died if x)
            print(f"  Deaths (Apoptosis or Necrosis): {died_count}/{results['runs']} ({100*died_count/results['runs']:.1f}%)")
    
    # === TIMING STATISTICS ===
    first_fate = results['first_fate_step']
    if first_fate:
        print(f"\n{'='*70}")
        print(f"TIMING: When do fates first fire? (step number)")
        print(f"{'='*70}")
        print(f"{'Fate':<18} {'Count':>6} {'Min':>6} {'Median':>8} {'Mean':>8} {'Max':>6}")
        print(f"{'-'*56}")
        
        for fate in ['Proliferation', 'Growth_Arrest', 'Apoptosis', 'Necrosis']:
            if fate in first_fate:
                steps_list = sorted(first_fate[fate])
                n = len(steps_list)
                median = steps_list[n // 2]
                mean = sum(steps_list) / n
                print(f"  {fate:<16} {n:>6} {min(steps_list):>6} "
                      f"{median:>8} {mean:>8.1f} {max(steps_list):>6}")
    
    # === STEPS COMPLETED ===
    completed = results['steps_completed']
    avg_steps = sum(completed) / len(completed)
    full_runs = sum(1 for s in completed if s == results['steps'])
    early_stops = runs - full_runs
    print(f"\n{'='*70}")
    print(f"SIMULATION PROGRESS")
    print(f"{'='*70}")
    print(f"  Average steps completed: {avg_steps:.1f} / {results['steps']}")
    print(f"  Full runs (all steps): {full_runs}/{runs}")
    print(f"  Early stops: {early_stops}/{runs}")
    
    # === KEY INTERPRETATION ===
    print(f"\n{'='*70}")
    print(f"INTERPRETATION (Faithful NetLogo Behavior)")
    print(f"{'-'*70}")
    print(f"  - 'Final Fate' = NetLogo's my-fate at simulation end")
    print(f"    (NOT hierarchical -- last overwrite wins)")
    print(f"  - 'Quiescent' = my-fate was nobody (no active fate)")
    print(f"  - Fate nodes ALWAYS reset to FALSE after being checked")
    print(f"  - Fate REVERTS to nobody when fate node turns OFF")
    print(f"    (if it was the current fate)")
    if results['reversible']:
        print(f"  - REVERSIBLE mode: cell keeps updating until Necrosis")
    else:
        print(f"  - NON-REVERSIBLE mode: cell stops at first fate")
    print(f"{'='*70}")



# =============================================================================
# COMMAND-LINE INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Faithful NetLogo Gene Network Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard run (reversible mode, pure Boolean network)
  python gene_network_netlogo_faithful.py network.bnd inputs.txt --runs 100 --steps 500

  # Non-reversible mode (stop at first fate)
  python gene_network_netlogo_faithful.py network.bnd inputs.txt --runs 100 --steps 500 --non-reversible

  # With cell actions layer (proliferation/death events)
  python gene_network_netlogo_faithful.py network.bnd inputs.txt --runs 100 --steps 500 --apply-cell-actions
        """
    )
    parser.add_argument('bnd_file', help='Path to .bnd gene network file')
    parser.add_argument('input_file', help='Path to input states file')
    parser.add_argument('--runs', type=int, default=100, help='Number of simulation runs')
    parser.add_argument('--steps', type=int, default=500, help='Number of propagation steps per run')
    parser.add_argument('--non-reversible', action='store_true', 
                       help='Non-reversible mode: stop after first fate (default: reversible)')
    parser.add_argument('--seed', type=int, default=None,
                       help='Base random seed for reproducible runs (per-run seed = seed + run_index)')
    parser.add_argument('--initialize-logic', action='store_true',
                       help='Optional one-pass logic initialization for Gene nodes only (NOT fate/output). '
                            'Disabled by default for NetLogo fidelity.')
    parser.add_argument('--growth-arrest-cycle', type=int, default=3,
                       help='Growth arrest cycle max (NetLogo: the-growth-arrest-cycle = 3). '
                            'Number of intercellular steps before Growth_Arrest resets to nobody.')
    parser.add_argument('--apply-cell-actions', action='store_true',
                       help='Evaluate phenotype at simulation end based on final fate. '
                            'Proliferation = would divide, Apoptosis/Necrosis = would die. '
                            'Helps compare outcomes to NetLogo population-level metrics.')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--debug-steps', action='store_true', help='Debug each step')
    parser.add_argument('--print-network', action='store_true', help='Print network structure')
    parser.add_argument('--output', help='Output file for results (JSON format)')
    
    args = parser.parse_args()
    
    reversible = not args.non_reversible
    
    # Run simulation
    results = run_simulation(
        args.bnd_file,
        args.input_file,
        args.runs,
        args.steps,
        verbose=args.verbose,
        debug_steps=args.debug_steps,
        print_network=args.print_network,
        reversible=reversible,
        seed=args.seed,
        initialize_logic=args.initialize_logic,
        growth_arrest_cycle_max=args.growth_arrest_cycle,
        apply_cell_actions=args.apply_cell_actions,
    )
    
    # Print results
    print_results(results, args.bnd_file, args.input_file)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == '__main__':
    main()
