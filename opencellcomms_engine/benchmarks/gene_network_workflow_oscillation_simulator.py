#!/usr/bin/env python3
"""
===============================================================================
OSCILLATION VARIANT — Gene Network Population Simulator
===============================================================================

Extends the faithful NetLogo gene-network simulator
(``gene_network_workflow_simulator.py``) with an **artificial oscillation
mechanism** that emulates the diffusion-driven input perturbation observed
in the full NetLogo model.

WHY THIS FILE EXISTS
--------------------
In the full NetLogo model (``microC_Metabolic_Symbiosis.nlogo3d``), the
reaction-diffusion PDE solver runs every ``the-diffusion-step`` (250) ticks.
Between diffusion steps, cells consume substances (Lactate, Glucose, O2),
depleting local patch concentrations.  At the diffusion step, boundary
conditions replenish concentrations.  This creates a sawtooth pattern:
concentrations jump up at the diffusion step, then decay.

For substances whose steady-state concentration hovers near a threshold
(e.g. Lactate / MCT1_stimulus at ~1.5), this sawtooth causes the
corresponding input node to toggle ON→OFF periodically (~500 tick period
observed in logs).  Additionally, cMET_stimulus (from HGF production)
turns ON only after the first diffusion step.

This periodic perturbation breaks Boolean attractors and is the primary
driver of sustained fate activity in NetLogo.  Without it, cells settle
into fixed points and the population stagnates.

The ``gene_network_workflow_simulator.py`` (faithful version) deliberately
does NOT include this mechanism, since it is not part of the gene-network
logic itself but rather an emergent property of the diffusion system.  This
file adds it back as a configurable option so we can study its effect.

OSCILLATION MODES
-----------------
--oscillation
    Toggle inputs listed in ``OSCILLATING_INPUTS`` ON/OFF with a period of
    ``--oscillation-period`` ticks (default 500).  ON for the first half of
    the period, OFF for the second half.

--ran-refresh
    Re-randomize ``cell_ran1`` / ``cell_ran2`` every ``diffusion_step``
    ticks.  This is NOT faithful to NetLogo (NetLogo keeps ran fixed), but
    it emulates the effect of changing patch concentrations on the
    probabilistic GLUT1I / MCT1I inputs.  Useful when those inputs are
    present in the input file.

Both flags can be combined.

===============================================================================
QUICK START
===============================================================================

  # Oscillation only (MCT1_stimulus toggles, cMET_stimulus delayed ON)
  python gene_network_workflow_oscillation_simulator.py network.bnd inputs.txt \\
      --batch-off --reversible --oscillation --initial-cells 100 \\
      --total-ticks 7000 --seed 42 --verbose

  # Oscillation + ran refresh (also perturb probabilistic inputs)
  python gene_network_workflow_oscillation_simulator.py network.bnd inputs.txt \\
      --batch-off --reversible --oscillation --ran-refresh \\
      --initial-cells 100 --total-ticks 7000 --seed 42 --verbose
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
# BOOLEAN LOGIC ENGINE
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
# GENE NETWORK TEMPLATE
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
            self.nodes[node_name] = NetworkNode(
                name=node_name, logic_rule=logic_rule, is_input=is_input)
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
            print(f"  Probabilistic inputs: "
                  f"{', '.join(self.input_concentrations.keys())}")
        return input_states


# =============================================================================
# CELL
# =============================================================================

class Cell:
    """A single cell with its own gene network state."""

    _next_id = 0

    def __init__(self, template: GeneNetworkTemplate):
        self.id = Cell._next_id
        Cell._next_id += 1

        self.nodes: Dict[str, NetworkNode] = {}
        for name, tmpl_node in template.nodes.items():
            n = NetworkNode(name=tmpl_node.name, logic_rule=tmpl_node.logic_rule,
                            is_input=tmpl_node.is_input)
            n.outputs = tmpl_node.outputs.copy()
            self.nodes[name] = n

        self.input_nodes = template.input_nodes.copy()
        self.input_concentrations = template.input_concentrations.copy()

        self.last_node: Optional[str] = None
        self.fate: Optional[str] = None
        self.phenotype: str = 'Quiescent'
        self.cell_ran1: float = random.random()
        self.cell_ran2: float = random.random()
        self.age: float = 0.0
        self.growth_arrest_counter: int = 0
        self.proliferation_delay: int = 1
        self.growth_arrest_cycle: int = 0

    def reset(self, random_init: bool = True):
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

    def _get_random_input(self) -> str:
        if self.input_nodes:
            return random.choice(list(self.input_nodes))
        nodes_with_out = [n for n, nd in self.nodes.items() if nd.outputs]
        return (random.choice(nodes_with_out) if nodes_with_out
                else random.choice(list(self.nodes.keys())))

    def propagate(self, steps: int, reversible: bool = False):
        for step in range(steps):
            if reversible:
                if self.fate == "Necrosis":
                    break
            else:
                if self.fate is not None:
                    break
            self._downstream_change()

    def _downstream_change(self):
        current = self.nodes.get(self.last_node)
        if not current or not current.outputs:
            self.last_node = self._get_random_input()
            return

        target_name = random.choice(list(current.outputs))
        target = self.nodes[target_name]
        current_fate_before = self.fate

        if target.update_function:
            states = self.get_all_states()
            new_state = target.update_function.evaluate(states)
            if target.active != new_state:
                target.active = new_state

        if target.kind == NODE_KIND_OUTPUT_FATE:
            if target.active:
                self.fate = target_name
            if (not target.active) and (target_name == current_fate_before):
                self.fate = None
            target.active = False
            self.last_node = self._get_random_input()
        else:
            self.last_node = target_name

    def write_fate_to_gene_states(self):
        if self.fate and self.fate in self.nodes:
            self.nodes[self.fate].active = True


# =============================================================================
# OSCILLATION SIMULATOR
# =============================================================================

class OscillationSimulator:
    """
    Gene-network population simulator with artificial oscillation to emulate
    the diffusion-driven input perturbation of the NetLogo model.

    Adds two perturbation mechanisms on top of the faithful gene-walk:

    1. **Input oscillation** (--oscillation): specific inputs toggle ON/OFF
       with a configurable period, mimicking the sawtooth from the diffusion
       solver.  Configurable via ``oscillating_inputs`` and
       ``delayed_on_inputs``.

    2. **Ran refresh** (--ran-refresh): re-randomize ``cell_ran1``/
       ``cell_ran2`` every ``diffusion_step`` ticks, emulating the effect of
       changing patch concentrations on GLUT1I/MCT1I probabilistic inputs.
    """

    OSCILLATING_INPUTS = {'MCT1_stimulus'}
    DELAYED_ON_INPUTS = {'cMET_stimulus'}

    def __init__(self, template: GeneNetworkTemplate,
                 input_states: Dict[str, bool],
                 initial_population: int = 1000,
                 max_population: int = 10000,
                 oscillation: bool = False,
                 oscillation_period: int = 500,
                 ran_refresh: bool = False):
        self.template = template
        self.input_states = input_states
        self.max_population = max_population
        self.oscillation = oscillation
        self.oscillation_period = oscillation_period
        self.ran_refresh = ran_refresh

        self._effective_inputs: Dict[str, bool] = dict(input_states)

        self.cells: List[Cell] = []
        self.population_history: List[Dict] = []
        self.total_births = 0
        self.total_deaths = 0

        for _ in range(initial_population):
            c = Cell(template)
            c.reset(random_init=True)
            c.set_input_states(self._effective_inputs)
            self.cells.append(c)

    def _compute_oscillation_state(self, tick: int, diffusion_step: int):
        """
        Update ``_effective_inputs`` based on the current tick.

        For OSCILLATING_INPUTS: ON for the first half of the oscillation
        period, OFF for the second half.  This is a square-wave
        approximation of the sawtooth observed in NetLogo logs.

        For DELAYED_ON_INPUTS: OFF until ``tick >= diffusion_step``, then ON.
        """
        if not self.oscillation:
            return

        half = self.oscillation_period // 2
        phase = tick % self.oscillation_period

        for inp in self.OSCILLATING_INPUTS:
            if inp in self._effective_inputs:
                self._effective_inputs[inp] = (phase < half)

        if tick >= diffusion_step:
            for inp in self.DELAYED_ON_INPUTS:
                if inp in self._effective_inputs:
                    self._effective_inputs[inp] = True

    # =================================================================
    # BATCH-OFF SIMULATION  (with oscillation / ran-refresh)
    # =================================================================
    def simulate_batch_off(self, total_ticks: int,
                           intercellular_step: int = 100,
                           diffusion_step: int = 250,
                           reversible: bool = False,
                           verbose: bool = False) -> Dict:
        """
        Batch-off mode with optional oscillation and ran-refresh.

        Same tick timeline as the faithful simulator, with two additions
        at the input-refresh step:
          - If --oscillation: toggle effective inputs
          - If --ran-refresh: re-randomize cell_ran1/cell_ran2
        """
        flags = []
        if reversible:
            flags.append('REVERSIBLE')
        else:
            flags.append('NON-REVERSIBLE')
        if self.oscillation:
            flags.append(f'OSCILLATION period={self.oscillation_period}')
        if self.ran_refresh:
            flags.append('RAN-REFRESH')

        print(f"\n[BATCH-OFF+OSC] {total_ticks} ticks, "
              f"intercellular_step={intercellular_step}, "
              f"diffusion_step={diffusion_step}, "
              f"{', '.join(flags)}")
        print(f"  Initial population: {len(self.cells)}")

        proliferation_delay = 1 + random.randint(0, intercellular_step - 1)
        print(f"  Global proliferation_delay: {proliferation_delay}")

        self.population_history.append({
            'tick': 0, 'population': len(self.cells),
            'births': 0, 'deaths': 0,
        })

        cumulative_births = 0
        cumulative_deaths = 0
        last_report_births = 0
        last_report_deaths = 0

        for tick in range(1, total_ticks + 1):
            # 1. APOPTOSIS CHECK
            dead_this_tick = [c for c in self.cells if c.fate == "Apoptosis"]
            if dead_this_tick:
                self.total_deaths += len(dead_this_tick)
                cumulative_deaths += len(dead_this_tick)
                self.cells = [c for c in self.cells
                              if c.fate != "Apoptosis"]

            # 2. INPUT REFRESH (with oscillation / ran-refresh)
            if tick % diffusion_step == 0:
                self._compute_oscillation_state(tick, diffusion_step)

                for cell in self.cells:
                    if self.ran_refresh:
                        cell.cell_ran1 = random.random()
                        cell.cell_ran2 = random.random()
                    cell.set_input_states(self._effective_inputs)

            # 3. ONE GRAPH-WALK STEP
            for cell in self.cells:
                if reversible:
                    if cell.fate == "Necrosis":
                        continue
                else:
                    if cell.fate is not None:
                        continue
                cell._downstream_change()

            # 4. PROLIFERATION / GROWTH-ARREST
            daughters_this_tick: List[Cell] = []
            if tick >= proliferation_delay and \
               (tick - proliferation_delay) % intercellular_step == 0:
                for cell in list(self.cells):
                    if cell.fate == "Proliferation":
                        cell.fate = None
                        cell.age = 0.0
                        cell.cell_ran1 = random.random()
                        cell.cell_ran2 = random.random()
                        cell.set_input_states(self._effective_inputs)
                        for fn in FATE_NODE_NAMES:
                            if fn in cell.nodes:
                                cell.nodes[fn].active = False

                        daughter = Cell(self.template)
                        daughter.reset(random_init=True)
                        daughter.set_input_states(self._effective_inputs)
                        daughters_this_tick.append(daughter)
                        self.total_births += 1
                        cumulative_births += 1

                    elif cell.fate == "Growth_Arrest":
                        if cell.growth_arrest_cycle == 0:
                            cell.growth_arrest_cycle = 3
                        cell.growth_arrest_cycle -= 1
                        if cell.growth_arrest_cycle <= 0:
                            cell.fate = None
                            cell.growth_arrest_cycle = 0

            self.cells.extend(daughters_this_tick)

            # 5. AGE
            for cell in self.cells:
                cell.age += 1.0

            # 6. REPORTING
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
                          f"(+{period_births} births, "
                          f"-{period_deaths} deaths) "
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

def print_results(results: Dict, initial_pop: int, mode: str = "batch-off"):
    print("\n" + "=" * 60)
    print(f"OSCILLATION SIMULATOR RESULTS  ({mode.upper()})")
    print("=" * 60)

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
    for r in results['population_history']:
        print(f"{r['tick']:<8} {r['population']:<10} "
              f"{r['births']:<8} {r['deaths']:<8}")

    print(f"\nFinal fate distribution:")
    for k, v in sorted(results['final_fate_distribution'].items(),
                        key=lambda x: -x[1]):
        pct = 100.0 * v / max(1, results['final_population'])
        print(f"  {k}: {v} ({pct:.1f}%)")


def plot_results(results: Dict, output_file: Optional[str] = None,
                 mode: str = "batch-off"):
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
    ax1.set_title(f'Oscillation Simulator — Population ({mode})')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    bw = max(1, (ticks[-1] - ticks[0]) / (len(ticks) * 3)) if len(ticks) > 1 else 1
    ax2.bar([t - bw / 2 for t in ticks], births, width=bw,
            color='green', alpha=0.7, label='Births')
    ax2.bar([t + bw / 2 for t in ticks], deaths, width=bw,
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
        description='Oscillation Variant — Gene Network Population Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Oscillation only (MCT1_stimulus toggles)
  python gene_network_workflow_oscillation_simulator.py network.bnd inputs.txt \\
      --batch-off --reversible --oscillation --initial-cells 100 \\
      --total-ticks 7000 --seed 42 --verbose

  # Oscillation + ran-refresh (also perturb GLUT1I/MCT1I)
  python gene_network_workflow_oscillation_simulator.py network.bnd inputs.txt \\
      --batch-off --reversible --oscillation --ran-refresh \\
      --initial-cells 100 --total-ticks 7000 --seed 42 --verbose

  # Ran-refresh only (no input oscillation, just ran perturbation)
  python gene_network_workflow_oscillation_simulator.py network.bnd inputs.txt \\
      --batch-off --reversible --ran-refresh --initial-cells 100 \\
      --total-ticks 7000 --seed 42 --verbose
        """)
    parser.add_argument('bnd_file', help='Path to .bnd gene network file')
    parser.add_argument('input_file', help='Path to input states file')

    parser.add_argument('--batch-off', action='store_true', default=True,
                        help='Batch-off mode (default and only supported mode)')
    parser.add_argument('--reversible', action='store_true',
                        help='Walk continues unless Necrosis '
                             '(default: stop at any fate)')

    # Oscillation flags
    parser.add_argument('--oscillation', action='store_true',
                        help='Toggle OSCILLATING_INPUTS ON/OFF periodically')
    parser.add_argument('--oscillation-period', type=int, default=500,
                        help='ON/OFF period in ticks (default: 500)')
    parser.add_argument('--ran-refresh', action='store_true',
                        help='Re-randomize cell_ran1/ran2 at each diffusion '
                             'step (emulates changing patch concentrations)')

    # Population
    parser.add_argument('--initial-cells', type=int, default=100,
                        help='Initial population size (default: 100)')
    parser.add_argument('--max-population', type=int, default=10000,
                        help='Stop if population exceeds this (default: 10000)')

    # Timing
    parser.add_argument('--total-ticks', type=int, default=7000,
                        help='Total simulation ticks (default: 7000)')
    parser.add_argument('--intercellular-step', type=int, default=100,
                        help='Ticks between proliferation/GA checks '
                             '(default: 100)')
    parser.add_argument('--diffusion-step', type=int, default=250,
                        help='Ticks between input refresh (default: 250)')

    # General
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    parser.add_argument('--verbose', action='store_true',
                        help='Print per-period progress')
    parser.add_argument('--plot', type=str, default=None,
                        help='Save population plot to file')
    parser.add_argument('--output', type=str, default=None,
                        help='Save results JSON to file')

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        print(f"Random seed: {args.seed}")

    template = GeneNetworkTemplate()
    template.load_bnd_file(args.bnd_file)
    input_states = template.load_input_states(args.input_file)

    sim = OscillationSimulator(
        template=template,
        input_states=input_states,
        initial_population=args.initial_cells,
        max_population=args.max_population,
        oscillation=args.oscillation,
        oscillation_period=args.oscillation_period,
        ran_refresh=args.ran_refresh,
    )

    rev_label = "reversible" if args.reversible else "non-reversible"
    print(f"\nMode: batch-off, {rev_label}")

    results = sim.simulate_batch_off(
        total_ticks=args.total_ticks,
        intercellular_step=args.intercellular_step,
        diffusion_step=args.diffusion_step,
        reversible=args.reversible,
        verbose=args.verbose,
    )

    print_results(results, args.initial_cells)

    if args.plot:
        plot_results(results, args.plot)
    elif PLOTTING_AVAILABLE and not args.output:
        plot_results(results)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == '__main__':
    main()
