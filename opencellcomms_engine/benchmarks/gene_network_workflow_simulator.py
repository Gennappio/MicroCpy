#!/usr/bin/env python3
"""
===============================================================================
NETLOGO-FAITHFUL GENE NETWORK POPULATION SIMULATOR (no spatial constraints)
===============================================================================

Standalone simulator that replicates **exactly** the gene-network + cell-action
logic of the NetLogo model ``microC_Metabolic_Symbiosis.nlogo3d`` with **no**
spatial grid, diffusion-reaction PDE, collision detection, or domain bounds.
Every division attempt succeeds (unlimited space).

PURPOSE
-------
Isolate the pure gene-network population dynamics from spatial/metabolic
effects, so we can verify the Boolean network walk and fate handling match
NetLogo tick-for-tick.

===============================================================================
NETLOGO BEHAVIOUR SUMMARY (from microC_Metabolic_Symbiosis.nlogo3d)
===============================================================================

Graph walk (-RUN-MICRO-STEP-195):
    Every ``the-intracellular-step`` (=1) tick, each cell does ONE graph-walk
    step.  The walk is gated by ``the-reversible?``:
        - reversible (true):  walk unless ``my-fate = "Necrosis"``
        - non-reversible (false): walk only if ``my-fate = nobody``

Fate node handling (INFLUENCE-LINK-END-WITH-LOGGING--36):
    When the walk visits an Output-Fate node:
      1. Evaluate the node's Boolean rule → ``new-state``
      2. Update ``my-active`` only if changed
      3. If ``my-active`` = true → call the fate-specific procedure:
         - Apoptosis / Growth_Arrest / Necrosis: set ``my-fate`` immediately
         - Proliferation: set ``my-fate`` ONLY IF ATP-gate AND age-gate pass
           (in this simulator without metabolics, the gate always passes when
           ``the-cell-atp-rate-max = 0``, because ``0 > 0`` is FALSE — see
           IMPORTANT NOTE below)
      4. If ``my-active`` = false AND this node is the cell's current fate
         → REVERT: ``my-fate = nobody``
      5. Reset ``my-active = false`` (transient trigger)
      6. Jump to a random Input node

    IMPORTANT NOTE — Proliferation gate with maxATP=0:
        In NetLogo, Proliferation requires ``atp-rate > threshold * maxATP``
        AND ``age > cell-cycle-time``.  When ``the-cell-atp-rate-max = 0``
        (commented-out initialisation), the threshold is ``0.8 * 0 = 0``.
        The check ``0 > 0`` is FALSE, so Proliferation is **always blocked**
        until cells actually produce non-zero ATP from the metabolic system.
        Since this simulator has no metabolics, we provide a ``--no-atp-gate``
        flag to bypass this gate (defaulting to gate OFF = always allow
        Proliferation when the fate node fires).

Cell actions (run in order, each with its own timer):
    -PROLIFERATE-870:
        do-after(the-proliferation-delay),
        do-every(the-intercellular-step):
          if my-fate = "Proliferation" → -RESET-FATE-145, -TURN-QUIESCENCE-3,
          -PROLIFERATE-869 (divide)
    -GROWTH-ARREST-10:
        do-after(the-proliferation-delay),
        do-every(the-intercellular-step):
          if my-fate = "Growth_Arrest" → cycle countdown → reset fate
    -APOPTOSIS-NECROSIS-100:
        do-after(1),
        do-every(the-apoptosis-step):
          if my-fate = "Apoptosis" → die
          if my-fate = "Necrosis"  → count (tracked, not killed here)
    J-DEATH:
        do-after(1),
        do-every(the-intercellular-step):
          if my-fate = "Necrosis" → stochastic decay death

Coexisting fates:
    Only ONE ``my-fate`` exists per cell.  The LAST fate node to fire during
    the graph walk overwrites the previous one.  In reversible mode the walk
    continues after a fate is set, so fates can toggle multiple times within
    one intercellular period.  The fate that happens to be active at the
    action-check boundary determines what happens.  There is NO explicit
    priority between Proliferation, Apoptosis, Growth_Arrest — it is purely
    stochastic (which fate node the random walk visits last).  However,
    Apoptosis has a TIMING advantage: it is checked every tick (apoptosis_step
    = 1), while Proliferation is checked every intercellular_step (= 100)
    ticks.

Input refresh (-UPDATE-INPUTS-15):
    do-after(0.01), do-every(the-diffusion-step):
      Re-evaluate all Input nodes from patch concentrations.
      cell_ran1 / cell_ran2 are NOT re-randomised (they are fixed per cell
      lifetime, only reset at creation and after proliferation).
      Without a diffusion system, this is a NO-OP because concentrations
      never change.

cell_ran1 / cell_ran2:
    Set at cell creation (-CELL-AGE) and after proliferation (-RESET-FATE-145).
    NEVER re-randomised during input refresh.

===============================================================================
MODES
===============================================================================

BATCH-ON (default):  propagate N steps → mark → divide → remove
BATCH-OFF (--batch-off):  tick-by-tick, faithful to NetLogo non-batch mode
--reversible:  only Necrosis stops walking (default: any fate stops)
--no-atp-gate:  bypass the ATP/age proliferation gate (default: ON, with the
    effective threshold = 0 this means Proliferation fires freely)

===============================================================================
QUICK START
===============================================================================

  # Batch-OFF, reversible, no ATP gate (closest to pure NetLogo gene walk)
  python gene_network_workflow_simulator.py network.bnd inputs.txt \\
      --batch-off --reversible --no-atp-gate --initial-cells 100 \\
      --total-ticks 7000 --seed 42

  # Batch-ON, non-reversible (MicroCpy workflow mode)
  python gene_network_workflow_simulator.py network.bnd inputs.txt \\
      --initial-cells 1000 --iterations 7 --propagation-steps 100 --seed 42
"""

import argparse
import random
import re
import json
from typing import Dict, List, Set, Optional
from collections import Counter

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================
FATE_NODE_NAMES = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}
NODE_KIND_INPUT = "Input"
NODE_KIND_GENE = "Gene"
NODE_KIND_OUTPUT_FATE = "Output-Fate"


# =============================================================================
# BOOLEAN LOGIC ENGINE  (identical to population simulator)
# =============================================================================

class BooleanExpression:
    """Evaluates boolean expressions with gene states."""

    def __init__(self, expression: str):
        self.expression = expression.strip()

    def evaluate(self, gene_states: Dict[str, bool]) -> bool:
        if not self.expression:
            return False
        expr = self.expression
        gene_names = sorted(gene_states.keys(), key=len, reverse=True)
        for gene_name in gene_names:
            if gene_name in expr:
                value = "True" if gene_states[gene_name] else "False"
                expr = re.sub(r'\b' + re.escape(gene_name) + r'\b', value, expr)
        expr = expr.replace('&', ' and ').replace('|', ' or ').replace('!', ' not ')
        try:
            return bool(eval(expr))
        except Exception:
            return False


# =============================================================================
# NETWORK NODE
# =============================================================================

class NetworkNode:
    """Single node in the gene network."""

    def __init__(self, name: str, logic_rule: str = "", is_input: bool = False):
        self.name = name
        self.logic_rule = logic_rule
        self.is_input = is_input
        self.active = False
        if is_input:
            self.kind = NODE_KIND_INPUT
        elif name in FATE_NODE_NAMES:
            self.kind = NODE_KIND_OUTPUT_FATE
        else:
            self.kind = NODE_KIND_GENE
        self.inputs: Set[str] = set()
        self.outputs: Set[str] = set()
        if logic_rule and not is_input:
            self.update_function = BooleanExpression(logic_rule)
            self._extract_inputs()
        else:
            self.update_function = None
        self.active_change_count = 0

    def _extract_inputs(self):
        if not self.logic_rule:
            return
        gene_names = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', self.logic_rule)
        keywords = {'and', 'or', 'not', 'True', 'False', 'true', 'false'}
        self.inputs = {n for n in gene_names if n not in keywords}


# =============================================================================
# GENE NETWORK TEMPLATE  (shared BND loader)
# =============================================================================

class GeneNetworkTemplate:
    """Template for creating cells with the same network structure."""

    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.input_nodes: Set[str] = set()
        self.input_concentrations: Dict[str, float] = {}

    def load_bnd_file(self, bnd_file: str):
        print(f"Loading gene network from {bnd_file}")
        with open(bnd_file, 'r') as f:
            content = f.read()
        node_pattern = r'[Nn]ode\s+(\w+)\s*\{([^}]+)\}'
        nodes_created = 0
        for match in re.finditer(node_pattern, content, re.MULTILINE | re.DOTALL):
            node_name = match.group(1)
            node_content = match.group(2)
            is_input = ('rate_up = 0' in node_content and 'rate_down = 0' in node_content)
            logic_match = re.search(r'logic\s*=\s*([^;]+);', node_content)
            logic_rule = logic_match.group(1).strip() if logic_match else ""
            if logic_rule.strip('() ') == node_name:
                is_input = True
                logic_rule = ""
            self.nodes[node_name] = NetworkNode(name=node_name, logic_rule=logic_rule, is_input=is_input)
            if is_input:
                self.input_nodes.add(node_name)
            nodes_created += 1
        self._build_graph_links()
        total_links = sum(len(n.outputs) for n in self.nodes.values())
        print(f"Created {nodes_created} nodes ({len(self.input_nodes)} input)")
        print(f"Built graph with {total_links} directed links")
        return nodes_created

    def _build_graph_links(self):
        for node_name, node in self.nodes.items():
            for input_name in node.inputs:
                if input_name in self.nodes:
                    self.nodes[input_name].outputs.add(node_name)

    def load_input_states(self, input_file: str) -> Dict[str, bool]:
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
                    if node_name in ('GLUT1I', 'MCT1I'):
                        try:
                            conc = float(value)
                            self.input_concentrations[node_name] = conc
                            input_states[node_name] = True
                        except ValueError:
                            if value in ('true', '1', 'on', 'yes'):
                                self.input_concentrations[node_name] = 1.0
                                input_states[node_name] = True
                            else:
                                self.input_concentrations[node_name] = 0.0
                                input_states[node_name] = False
                    else:
                        input_states[node_name] = value in ('true', '1', 'on', 'yes')
        print(f"Loaded {len(input_states)} input states")
        if self.input_concentrations:
            print(f"  Probabilistic inputs: {', '.join(self.input_concentrations.keys())}")
        return input_states


# =============================================================================
# CELL  (mirrors workflow Cell + gene network)
# =============================================================================

class Cell:
    """
    A single cell with its own gene network state.

    Attributes follow the workflow's representation:
        fate        – the gene-network-level fate (_fate on the GN object)
        phenotype   – the workflow-level phenotype set by marking functions
        gene_states – dict of node_name → bool
    """

    _next_id = 0

    def __init__(self, template: GeneNetworkTemplate):
        self.id = Cell._next_id
        Cell._next_id += 1

        # Copy network structure (each cell owns its own node states)
        self.nodes: Dict[str, NetworkNode] = {}
        for name, tmpl_node in template.nodes.items():
            n = NetworkNode(name=tmpl_node.name, logic_rule=tmpl_node.logic_rule,
                            is_input=tmpl_node.is_input)
            n.outputs = tmpl_node.outputs.copy()
            self.nodes[name] = n

        self.input_nodes = template.input_nodes.copy()
        self.input_concentrations = template.input_concentrations.copy()

        # Per-cell state
        self.last_node: Optional[str] = None
        self.fate: Optional[str] = None
        self.phenotype: str = 'Quiescent'
        self.cell_ran1: float = random.random()
        self.cell_ran2: float = random.random()
        self.age: float = 0.0
        self.growth_arrest_counter: int = 0
        self.proliferation_delay: int = 1          # batch-off: random start offset
        self.growth_arrest_cycle: int = 0           # countdown (NetLogo: 3 → 0)

    # -----------------------------------------------------------------
    # Initialisation helpers
    # -----------------------------------------------------------------
    def reset(self, random_init: bool = True):
        """Initialise node states like the workflow's initialize_netlogo_gene_networks."""
        for node in self.nodes.values():
            if node.is_input:
                continue
            if node.name in FATE_NODE_NAMES:
                node.active = False
            else:
                node.active = random.choice([True, False]) if random_init else False
            node.active_change_count = 0
        if self.input_nodes:
            self.last_node = random.choice(list(self.input_nodes))
        else:
            self.last_node = random.choice(list(self.nodes.keys()))
        self.fate = None
        self.phenotype = 'Quiescent'
        self.cell_ran1 = random.random()
        self.cell_ran2 = random.random()
        self.age = 0.0
        self.growth_arrest_counter = 0
        self.growth_arrest_cycle = 0

    def set_input_states(self, input_states: Dict[str, bool]):
        """Apply input states (with probabilistic GLUT1I/MCT1I)."""
        for node_name, state in input_states.items():
            if node_name not in self.nodes:
                continue
            if node_name == 'MCT1I' and node_name in self.input_concentrations:
                conc = self.input_concentrations[node_name]
                hill = 0.85 * (1.0 - 1.0 / (1.0 + (conc / 1.0)))
                self.nodes[node_name].active = (hill > self.cell_ran1)
            elif node_name == 'GLUT1I' and node_name in self.input_concentrations:
                conc = self.input_concentrations[node_name]
                hill = 0.85 * (1.0 - 1.0 / (1.0 + (conc / 1.0)))
                self.nodes[node_name].active = (hill > self.cell_ran2)
            else:
                self.nodes[node_name].active = state

    def get_all_states(self) -> Dict[str, bool]:
        return {name: node.active for name, node in self.nodes.items()}

    # -----------------------------------------------------------------
    # Graph walking  (workflow's propagate_gene_networks_netlogo)
    # -----------------------------------------------------------------
    def _get_random_input(self) -> str:
        if self.input_nodes:
            return random.choice(list(self.input_nodes))
        nodes_with_out = [n for n, nd in self.nodes.items() if nd.outputs]
        return random.choice(nodes_with_out) if nodes_with_out else random.choice(list(self.nodes.keys()))

    def propagate(self, steps: int, reversible: bool = False):
        """
        Run ``steps`` graph-walking steps.

        This replicates propagate_gene_networks_netlogo exactly:
        - Non-reversible (default): stop at ANY fate
        - Reversible: stop only at Necrosis
        """
        for step in range(steps):
            # --- stopping condition (NetLogo line 1611) ---
            if reversible:
                if self.fate == "Necrosis":
                    break
            else:
                if self.fate is not None:
                    break

            # --- one graph-walk step ---
            self._downstream_change()

    def _downstream_change(self):
        """One graph-walking step (NetLogo -DOWNSTREAM-CHANGE-590)."""
        current = self.nodes.get(self.last_node)
        if not current or not current.outputs:
            self.last_node = self._get_random_input()
            return

        target_name = random.choice(list(current.outputs))
        target = self.nodes[target_name]
        current_fate_before = self.fate

        # Evaluate boolean rule
        if target.update_function:
            states = self.get_all_states()
            new_state = target.update_function.evaluate(states)
            if target.active != new_state:
                target.active = new_state

        # Handle fate nodes (Output-Fate)
        if target.kind == NODE_KIND_OUTPUT_FATE:
            if target.active:
                self.fate = target_name
            if (not target.active) and (target_name == current_fate_before):
                self.fate = None
            target.active = False   # transient trigger
            self.last_node = self._get_random_input()
        else:
            self.last_node = target_name

    # -----------------------------------------------------------------
    # Gene-state snapshot (after propagation, write _fate back)
    # -----------------------------------------------------------------
    def write_fate_to_gene_states(self):
        """
        Mirrors the workflow's post-propagation step:
        gene_states[_fate] = True so marking functions can read it.
        """
        if self.fate and self.fate in self.nodes:
            self.nodes[self.fate].active = True


# =============================================================================
# WORKFLOW SIMULATOR  (no spatial constraints)
# =============================================================================

class WorkflowSimulator:
    """
    NetLogo-faithful gene-network population simulator (no spatial constraints).

    BATCH-ON:  propagate N steps → mark → divide → remove  (workflow mode)
    BATCH-OFF: tick-by-tick, faithful to NetLogo non-batch mode

    No spatial grid: every division succeeds (unlimited space).
    """

    def __init__(self, template: GeneNetworkTemplate,
                 input_states: Dict[str, bool],
                 initial_population: int = 1000,
                 max_population: int = 10000,
                 no_atp_gate: bool = True):
        self.template = template
        self.input_states = input_states
        self.max_population = max_population
        self.no_atp_gate = no_atp_gate

        self.cells: List[Cell] = []
        self.population_history: List[Dict] = []
        self.total_births = 0
        self.total_deaths = 0

        for _ in range(initial_population):
            c = Cell(template)
            c.reset(random_init=True)
            c.set_input_states(self.input_states)
            self.cells.append(c)

    # =================================================================
    # BATCH-ON SIMULATION  (workflow-style)
    # =================================================================
    def simulate_batch_on(self, iterations: int, propagation_steps: int = 100,
                          reversible: bool = False, verbose: bool = False) -> Dict:
        """
        Batch-on mode (MicroCpy workflow): propagate all cells N steps, then
        mark phenotypes, then divide/kill.  Input nodes are set once at start
        and never refreshed (no diffusion in this mode).
        """
        print(f"\n[BATCH-ON] {iterations} iterations x {propagation_steps} steps, "
              f"{'REVERSIBLE' if reversible else 'NON-REVERSIBLE'}")
        print(f"  Initial population: {len(self.cells)}")

        self.population_history.append({
            'tick': 0, 'population': len(self.cells), 'births': 0, 'deaths': 0,
        })

        for it in range(1, iterations + 1):
            # 1. PROPAGATE
            fate_dist = Counter()
            for cell in self.cells:
                cell.propagate(propagation_steps, reversible=reversible)
                cell.write_fate_to_gene_states()
                fate_dist[cell.fate or "Quiescent"] += 1

            # 2. MARK APOPTOTIC (reset all first)
            for cell in self.cells:
                cell.phenotype = 'Quiescent'
            for cell in self.cells:
                if cell.nodes.get('Apoptosis') and cell.nodes['Apoptosis'].active:
                    cell.phenotype = 'Apoptosis'

            # 3. MARK GROWTH ARREST
            for cell in self.cells:
                if cell.nodes.get('Growth_Arrest') and cell.nodes['Growth_Arrest'].active:
                    cell.phenotype = 'Growth_Arrest'

            # 4. MARK PROLIFERATING (overwrites Apoptosis/GA; else keep)
            active_fates = {'Apoptosis', 'Growth_Arrest'}
            for cell in self.cells:
                if cell.nodes.get('Proliferation') and cell.nodes['Proliferation'].active:
                    cell.phenotype = 'Proliferation'
                else:
                    if cell.phenotype not in active_fates:
                        cell.phenotype = 'Quiescent'

            # 5. DIVIDE
            daughters = self._do_divisions()

            # 6. REMOVE APOPTOTIC
            deaths_this = self._remove_apoptotic()

            self.population_history.append({
                'tick': it * propagation_steps,
                'population': len(self.cells),
                'births': len(daughters),
                'deaths': deaths_this,
            })
            if verbose:
                print(f"  Iter {it} (tick {it * propagation_steps}): "
                      f"Pop={len(self.cells)} "
                      f"(+{len(daughters)} births, -{deaths_this} deaths)  "
                      f"fates={dict(fate_dist)}")

            if len(self.cells) == 0:
                print(f"  EXTINCTION at iteration {it}")
                break
            if len(self.cells) >= self.max_population:
                print(f"  MAX POPULATION at iteration {it}")
                break

        return self._statistics()

    # =================================================================
    # BATCH-OFF SIMULATION  (NetLogo non-batch-mode, faithful)
    # =================================================================
    def simulate_batch_off(self, total_ticks: int,
                           intercellular_step: int = 100,
                           diffusion_step: int = 250,
                           reversible: bool = False,
                           verbose: bool = False) -> Dict:
        """
        Batch-off mode — faithful to NetLogo ``the-batch-mode? = false``.

        Timeline per tick (matching NetLogo scheduling):
            1. Apoptosis check: ``do-after(1), do-every(the-apoptosis-step)``
               → if ``my-fate = "Apoptosis"`` → die immediately
            2. One graph-walk step: ``do-every(the-intracellular-step)``
               → gated by reversible? flag
            3. Proliferation/GA check: ``do-after(the-proliferation-delay),
               do-every(the-intercellular-step)``
               → if ``my-fate = "Proliferation"`` → reset parent + create
                 daughter
               → if ``my-fate = "Growth_Arrest"`` → cycle countdown
            4. Necrosis decay check: ``do-after(1),
               do-every(the-intercellular-step)``
               → stochastic removal (not modelled here — no metabolics)

        Input refresh (``-UPDATE-INPUTS-15``):
            Every ``diffusion_step`` ticks, re-evaluate inputs from
            (unchanged) concentrations with the cell's **fixed**
            ``cell_ran1``/``cell_ran2``.  Without diffusion this is a no-op.
            NetLogo does NOT re-randomise ran1/ran2 at refresh.
        """
        print(f"\n[BATCH-OFF] {total_ticks} ticks, intercellular_step={intercellular_step}, "
              f"diffusion_step={diffusion_step}, "
              f"{'REVERSIBLE' if reversible else 'NON-REVERSIBLE'}, "
              f"ATP gate {'OFF' if self.no_atp_gate else 'ON'}")
        print(f"  Initial population: {len(self.cells)}")

        # NetLogo batch-off: one GLOBAL random proliferation delay
        proliferation_delay = 1 + random.randint(0, intercellular_step - 1)
        print(f"  Global proliferation_delay: {proliferation_delay}")

        self.population_history.append({
            'tick': 0, 'population': len(self.cells), 'births': 0, 'deaths': 0,
        })

        cumulative_births = 0
        cumulative_deaths = 0
        last_report_births = 0
        last_report_deaths = 0

        for tick in range(1, total_ticks + 1):
            # ==========================================================
            # 1. APOPTOSIS CHECK — do-after(1), do-every(apoptosis_step=1)
            #    Cells that acquired Apoptosis fate on previous tick(s)
            #    die now.  This gives a 1-tick delay (matching do-after(1)).
            # ==========================================================
            dead_this_tick = [c for c in self.cells if c.fate == "Apoptosis"]
            if dead_this_tick:
                self.total_deaths += len(dead_this_tick)
                cumulative_deaths += len(dead_this_tick)
                self.cells = [c for c in self.cells if c.fate != "Apoptosis"]

            # ==========================================================
            # 2. INPUT REFRESH — do-after(0.01), do-every(diffusion_step)
            #    In NetLogo this re-evaluates inputs from patch
            #    concentrations.  cell_ran1/cell_ran2 are NOT changed.
            #    Without diffusion, concentrations don't change so this
            #    is a no-op.  We call set_input_states anyway for
            #    correctness (e.g. if inputs were modified externally).
            # ==========================================================
            if tick % diffusion_step == 0:
                for cell in self.cells:
                    cell.set_input_states(self.input_states)

            # ==========================================================
            # 3. ONE GRAPH-WALK STEP — do-every(intracellular_step=1)
            #    Gated by the-reversible? flag:
            #      reversible:     walk unless my-fate = "Necrosis"
            #      non-reversible: walk only if my-fate = nobody (None)
            # ==========================================================
            for cell in self.cells:
                if reversible:
                    if cell.fate == "Necrosis":
                        continue
                else:
                    if cell.fate is not None:
                        continue
                cell._downstream_change()

            # ==========================================================
            # 4. PROLIFERATION / GROWTH-ARREST — do-after(prolif_delay),
            #    do-every(intercellular_step)
            # ==========================================================
            daughters_this_tick: List[Cell] = []
            if tick >= proliferation_delay and \
               (tick - proliferation_delay) % intercellular_step == 0:
                for cell in list(self.cells):
                    if cell.fate == "Proliferation":
                        # Reset parent (NetLogo -RESET-FATE-145)
                        prev_fate = cell.fate
                        cell.fate = None
                        cell.age = 0.0
                        cell.cell_ran1 = random.random()
                        cell.cell_ran2 = random.random()
                        cell.set_input_states(self.input_states)
                        for fn in FATE_NODE_NAMES:
                            if fn in cell.nodes:
                                cell.nodes[fn].active = False

                        # Create daughter (fresh random init)
                        daughter = Cell(self.template)
                        daughter.reset(random_init=True)
                        daughter.set_input_states(self.input_states)
                        daughters_this_tick.append(daughter)
                        self.total_births += 1
                        cumulative_births += 1

                    elif cell.fate == "Growth_Arrest":
                        # NetLogo: -GROWTH-ARREST-CYCLE-258 / -RESET-FATE-278
                        if cell.growth_arrest_cycle == 0:
                            cell.growth_arrest_cycle = 3
                        cell.growth_arrest_cycle -= 1
                        if cell.growth_arrest_cycle <= 0:
                            cell.fate = None
                            cell.growth_arrest_cycle = 0

            self.cells.extend(daughters_this_tick)

            # ==========================================================
            # 5. AGE ALL CELLS
            # ==========================================================
            for cell in self.cells:
                cell.age += 1.0

            # ==========================================================
            # 6. PERIODIC REPORTING
            # ==========================================================
            if tick % intercellular_step == 0:
                period_births = cumulative_births - last_report_births
                period_deaths = cumulative_deaths - last_report_deaths
                self.population_history.append({
                    'tick': tick,
                    'population': len(self.cells),
                    'births': period_births,
                    'deaths': period_deaths,
                })
                if verbose:
                    fate_dist = Counter(c.fate or 'None' for c in self.cells)
                    print(f"  Tick {tick}: Pop={len(self.cells)} "
                          f"(+{period_births} births, -{period_deaths} deaths) "
                          f"fates={dict(fate_dist)}")
                last_report_births = cumulative_births
                last_report_deaths = cumulative_deaths

                if len(self.cells) == 0:
                    print(f"  EXTINCTION at tick {tick}")
                    break
                if len(self.cells) >= self.max_population:
                    print(f"  MAX POPULATION at tick {tick}")
                    break

        return self._statistics()

    # =================================================================
    # SHARED HELPERS
    # =================================================================
    def _do_divisions(self) -> List[Cell]:
        """Divide all cells with phenotype Proliferation (batch-on mode)."""
        daughters = []
        for cell in self.cells:
            if cell.phenotype != 'Proliferation':
                continue
            # Reset parent (NetLogo -RESET-FATE-145)
            cell.fate = None
            cell.phenotype = 'Quiescent'
            cell.age = 0.0
            cell.cell_ran1 = random.random()
            cell.cell_ran2 = random.random()
            cell.set_input_states(self.input_states)
            for fn in FATE_NODE_NAMES:
                if fn in cell.nodes:
                    cell.nodes[fn].active = False

            daughter = Cell(self.template)
            daughter.reset(random_init=True)
            daughter.set_input_states(self.input_states)
            daughters.append(daughter)
            self.total_births += 1

        self.cells.extend(daughters)
        return daughters

    def _remove_apoptotic(self) -> int:
        """Remove cells with phenotype == Apoptosis. Returns count removed."""
        dead = [c for c in self.cells if c.phenotype == 'Apoptosis']
        self.total_deaths += len(dead)
        self.cells = [c for c in self.cells if c.phenotype != 'Apoptosis']
        return len(dead)

    def _statistics(self) -> Dict:
        final_fate_dist = Counter()
        final_phenotype_dist = Counter()
        for c in self.cells:
            final_fate_dist[c.fate or "Quiescent"] += 1
            final_phenotype_dist[c.phenotype] += 1

        return {
            'population_history': self.population_history,
            'final_population': len(self.cells),
            'total_births': self.total_births,
            'total_deaths': self.total_deaths,
            'final_fate_distribution': dict(final_fate_dist),
            'final_phenotype_distribution': dict(final_phenotype_dist),
        }


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def print_results(results: Dict, initial_pop: int, mode: str = "batch-on"):
    print("\n" + "=" * 60)
    print(f"WORKFLOW SIMULATOR RESULTS  ({mode.upper()})")
    print("=" * 60)

    history = results['population_history']
    print(f"\nPopulation dynamics:")
    print(f"  Initial: {initial_pop}")
    print(f"  Final:   {results['final_population']}")
    print(f"  Births:  {results['total_births']}")
    print(f"  Deaths:  {results['total_deaths']}")
    if results['total_deaths'] > 0:
        print(f"  Birth/Death ratio: "
              f"{results['total_births'] / results['total_deaths']:.2f}")

    print(f"\nPopulation trajectory:")
    print(f"{'Tick':<8} {'Pop':<10} {'Births':<8} {'Deaths':<8}")
    print("-" * 36)
    for r in history:
        print(f"{r['tick']:<8} {r['population']:<10} "
              f"{r['births']:<8} {r['deaths']:<8}")

    print(f"\nFinal fate distribution (gene network _fate):")
    for k, v in sorted(results['final_fate_distribution'].items(),
                        key=lambda x: -x[1]):
        pct = 100.0 * v / max(1, results['final_population'])
        print(f"  {k}: {v} ({pct:.1f}%)")

    print(f"\nFinal phenotype distribution (workflow marking):")
    for k, v in sorted(results['final_phenotype_distribution'].items(),
                        key=lambda x: -x[1]):
        pct = 100.0 * v / max(1, results['final_population'])
        print(f"  {k}: {v} ({pct:.1f}%)")


def plot_results(results: Dict, output_file: Optional[str] = None,
                 mode: str = "batch-on"):
    if not PLOTTING_AVAILABLE:
        print("\nNote: install matplotlib for plots")
        return
    history = results['population_history']
    ticks = [r['tick'] for r in history]
    pops = [r['population'] for r in history]
    births = [r['births'] for r in history]
    deaths = [r['deaths'] for r in history]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    ax1.plot(ticks, pops, 'b-o', linewidth=2, markersize=4, label='Population')
    ax1.set_xlabel('Tick')
    ax1.set_ylabel('Cell count')
    ax1.set_title(f'Workflow Simulator — Population Trajectory ({mode})')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    bar_width = max(1, (ticks[-1] - ticks[0]) / (len(ticks) * 3)) if len(ticks) > 1 else 1
    ax2.bar([t - bar_width / 2 for t in ticks], births, width=bar_width,
            color='green', alpha=0.7, label='Births')
    ax2.bar([t + bar_width / 2 for t in ticks], deaths, width=bar_width,
            color='red', alpha=0.7, label='Deaths')
    ax2.set_xlabel('Tick')
    ax2.set_ylabel('Count')
    ax2.set_title('Births / Deaths per Reporting Period')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"\nPlot saved to {output_file}")
    else:
        plt.show()


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='NetLogo-faithful Gene Network Population Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # BATCH-OFF, reversible, no ATP gate (closest to pure NetLogo gene walk)
  python gene_network_workflow_simulator.py network.bnd inputs.txt \\
      --batch-off --reversible --no-atp-gate --initial-cells 100 \\
      --total-ticks 7000 --seed 42 --verbose

  # BATCH-ON, non-reversible (MicroCpy workflow mode)
  python gene_network_workflow_simulator.py network.bnd inputs.txt \\
      --initial-cells 1000 --iterations 7 --propagation-steps 100 --seed 42
        """)
    parser.add_argument('bnd_file', help='Path to .bnd gene network file')
    parser.add_argument('input_file', help='Path to input states file')

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--batch-on', action='store_true', default=True,
                            help='Batch-on mode (default): propagate N steps '
                                 'then mark/divide/remove')
    mode_group.add_argument('--batch-off', action='store_true',
                            help='Batch-off mode (NetLogo non-batch): '
                                 'tick-by-tick, apoptosis every tick')

    # Reversibility
    parser.add_argument('--reversible', action='store_true',
                        help='Reversible: walk continues unless Necrosis '
                             '(default: NON-reversible, stop at any fate)')

    # ATP gate
    parser.add_argument('--no-atp-gate', action='store_true',
                        help='Bypass the ATP/age proliferation gate '
                             '(default: gate ON but with threshold=0, '
                             'effectively Proliferation requires age > '
                             'cell-cycle-time only)')

    # Population
    parser.add_argument('--initial-cells', type=int, default=1000,
                        help='Initial population size (default: 1000)')
    parser.add_argument('--max-population', type=int, default=10000,
                        help='Stop if population exceeds this (default: 10000)')

    # Batch-ON params
    parser.add_argument('--iterations', type=int, default=7,
                        help='[batch-on] Number of workflow iterations (default: 7)')
    parser.add_argument('--propagation-steps', type=int, default=100,
                        help='[batch-on] Graph-walk steps per iteration (default: 100)')

    # Batch-OFF params
    parser.add_argument('--total-ticks', type=int, default=700,
                        help='[batch-off] Total simulation ticks (default: 700)')
    parser.add_argument('--intercellular-step', type=int, default=100,
                        help='[batch-off] Ticks between proliferation/GA checks '
                             '(default: 100)')
    parser.add_argument('--diffusion-step', type=int, default=250,
                        help='[batch-off] Ticks between input refresh '
                             '(default: 250, matches NetLogo the-diffusion-step)')

    # General
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    parser.add_argument('--verbose', action='store_true',
                        help='Print per-iteration / per-period progress')
    parser.add_argument('--plot', type=str, default=None,
                        help='Save population plot to file')
    parser.add_argument('--output', type=str, default=None,
                        help='Save results JSON to file')

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        print(f"Random seed: {args.seed}")

    # Load network
    template = GeneNetworkTemplate()
    template.load_bnd_file(args.bnd_file)
    input_states = template.load_input_states(args.input_file)

    # Create simulator
    sim = WorkflowSimulator(
        template=template,
        input_states=input_states,
        initial_population=args.initial_cells,
        max_population=args.max_population,
        no_atp_gate=args.no_atp_gate,
    )

    # Determine mode
    is_batch_off = args.batch_off
    mode_label = "batch-off" if is_batch_off else "batch-on"
    rev_label = "reversible" if args.reversible else "non-reversible"
    print(f"\nMode: {mode_label}, {rev_label}")

    # Run
    if is_batch_off:
        total_ticks = args.total_ticks
        results = sim.simulate_batch_off(
            total_ticks=total_ticks,
            intercellular_step=args.intercellular_step,
            diffusion_step=args.diffusion_step,
            reversible=args.reversible,
            verbose=args.verbose,
        )
    else:
        results = sim.simulate_batch_on(
            iterations=args.iterations,
            propagation_steps=args.propagation_steps,
            reversible=args.reversible,
            verbose=args.verbose,
        )

    # Output
    print_results(results, args.initial_cells, mode=mode_label)

    if args.plot:
        plot_results(results, args.plot, mode=mode_label)
    elif PLOTTING_AVAILABLE and not args.output:
        plot_results(results, mode=mode_label)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == '__main__':
    main()
