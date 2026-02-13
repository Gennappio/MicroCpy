#!/usr/bin/env python3
"""
===============================================================================
POPULATION-LEVEL GENE NETWORK SIMULATOR WITH BIRTH/DEATH DYNAMICS
===============================================================================

This simulator extends gene_network_netlogo_periodic.py to model POPULATION
DYNAMICS where cells actually proliferate (creating daughters) and die
(removing from population), matching NetLogo's tumor growth behavior.

KEY DIFFERENCE from gene_network_netlogo_periodic.py:
- That version: Tracks individual cell fates independently (no actual births/deaths)
- This version: Maintains a POPULATION where proliferation adds cells and
  apoptosis/necrosis removes cells, showing exponential growth dynamics

===============================================================================
QUICK START
===============================================================================

Basic usage:
    python gene_network_population_simulator.py network.bnd inputs.txt \\
        --initial-cells 10 --steps 5000 --periodic-check 100 --max-population 1000

Required files:
    - network.bnd: Boolean network definition (MaBoSS/BND format)
    - inputs.txt: Input node states (one per line: NodeName=ON/OFF)

Key options:
    --initial-cells 10      Starting population size
    --steps 5000            Total simulation time (ticks)
    --periodic-check 100    Check phenotype every N ticks (NetLogo: the-intercellular-step)
    --max-population 1000   Stop if population exceeds this limit
    --seed 42               Random seed for reproducibility

Example command:
    python gene_network_population_simulator.py \\
        tests/jayatilake_experiment/jaya_microc.bnd \\
        benchmarks/test_simple_inputs.txt \\
        --initial-cells 20 --steps 5000 --periodic-check 100 \\
        --max-population 500 --seed 42

===============================================================================
POPULATION DYNAMICS
===============================================================================

At each periodic check (every 100 ticks):
1. For each living cell:
   - Evaluate gene network state → determine my-fate
   - If my-fate == "Proliferation":
     → Create daughter cell (fresh random initialization)
     → Add to population
     → Parent cell continues simulation
   - If my-fate == "Apoptosis" or "Necrosis":
     → Remove cell from population
     → Cell stops simulating
   
2. Track statistics:
   - Population count over time
   - Total births (cumulative proliferation events)
   - Total deaths (cumulative apoptosis + necrosis)
   - Growth rate
   - Survival curves

Example timeline:
    Tick 0:   Population = 10 cells
    Tick 100: 3 proliferate (→ +3 daughters), 1 dies → Population = 12
    Tick 200: 5 proliferate (→ +5 daughters), 2 die → Population = 15
    Tick 300: 8 proliferate (→ +8 daughters), 3 die → Population = 20
    ...
    Tick 5000: Population = 347 cells (exponential growth!)

This matches NetLogo's actual tumor growth behavior.

===============================================================================
OUTPUT
===============================================================================

The simulator produces:
1. Population trajectory: cell count at each periodic check
2. Birth/death rates over time
3. Final population statistics
4. Growth curves (if matplotlib available)
5. Individual cell fate tracking (optional with --track-lineages)

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
NODE_KIND_INPUT = "Input"
NODE_KIND_GENE = "Gene"
NODE_KIND_OUTPUT_FATE = "Output-Fate"
NODE_KIND_OUTPUT = "Output"

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
    """Represents a single node in the gene network."""
    
    def __init__(self, name: str, logic_rule: str = "", is_input: bool = False):
        self.name = name
        self.logic_rule = logic_rule
        self.is_input = is_input
        self.active = False
        
        # Node type classification
        if is_input:
            self.kind = NODE_KIND_INPUT
        elif name in FATE_NODE_NAMES:
            self.kind = NODE_KIND_OUTPUT_FATE
        else:
            self.kind = NODE_KIND_GENE
        
        # Graph connectivity
        self.inputs: Set[str] = set()
        self.outputs: Set[str] = set()
        
        # Boolean update function
        if logic_rule and not is_input:
            self.update_function = BooleanExpression(logic_rule)
            self._extract_inputs()
        else:
            self.update_function = None
        
        self.active_change_count = 0
        self.activation_threshold: Optional[float] = None
    
    def _extract_inputs(self):
        """Extract input node names from the logic rule."""
        if not self.logic_rule:
            return
        gene_names = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', self.logic_rule)
        keywords = {'and', 'or', 'not', 'True', 'False', 'true', 'false'}
        self.inputs = {name for name in gene_names if name not in keywords}



# =============================================================================
# SINGLE CELL SIMULATOR
# =============================================================================

class Cell:
    """
    Single cell with its own gene network state.
    
    This is a wrapper around the gene network logic that represents one cell
    in the population. Each cell has:
    - Unique ID
    - Own gene network state
    - Birth time (when it was created)
    - Parent ID (for lineage tracking)
    """
    
    _next_id = 0
    
    def __init__(self, network_template: 'GeneNetworkTemplate', 
                 birth_tick: int = 0, parent_id: Optional[int] = None):
        self.id = Cell._next_id
        Cell._next_id += 1
        
        self.birth_tick = birth_tick
        self.parent_id = parent_id
        self.death_tick: Optional[int] = None
        
        # Create own copy of network nodes
        self.nodes: Dict[str, NetworkNode] = {}
        for name, template_node in network_template.nodes.items():
            self.nodes[name] = NetworkNode(
                name=template_node.name,
                logic_rule=template_node.logic_rule,
                is_input=template_node.is_input
            )
            # Copy outputs (graph structure)
            self.nodes[name].outputs = template_node.outputs.copy()
        
        self.input_nodes = network_template.input_nodes.copy()
        
        # Cell state
        self.last_node: Optional[str] = None
        self.fate: Optional[str] = None
        self.network_steps: int = 0
        self.mutations: Set[str] = set()
        self.growth_arrest_cycle: int = 0
        self.growth_arrest_cycle_max: int = 3
        
        # Probabilistic input parameters
        self.cell_ran1: float = random.random()
        self.cell_ran2: float = random.random()
        self.input_concentrations: Dict[str, float] = network_template.input_concentrations.copy()
    
    def reset(self, random_init: bool = True):
        """Initialize/reset cell state."""
        for node in self.nodes.values():
            if not node.is_input:
                if node.kind == NODE_KIND_OUTPUT_FATE:
                    node.active = False
                else:
                    node.active = random.choice([True, False]) if random_init else False
                node.active_change_count = 0
        
        if self.input_nodes:
            self.last_node = random.choice(list(self.input_nodes))
        else:
            self.last_node = random.choice(list(self.nodes.keys()))
        
        self.fate = None
        self.network_steps = 0
        
        # New random values for this cell
        self.cell_ran1 = random.random()
        self.cell_ran2 = random.random()
    
    def set_input_states(self, input_states: Dict[str, bool]):
        """Set input node states with probabilistic activation for GLUT1I/MCT1I."""
        for node_name, state in input_states.items():
            if node_name not in self.nodes:
                continue
            
            # Probabilistic activation for MCT1I
            if node_name == 'MCT1I' and node_name in self.input_concentrations:
                concentration = self.input_concentrations[node_name]
                threshold = 1.0
                hill_value = 0.85 * (1.0 - 1.0 / (1.0 + (concentration / threshold)))
                self.nodes[node_name].active = (hill_value > self.cell_ran1)
            
            # Probabilistic activation for GLUT1I
            elif node_name == 'GLUT1I' and node_name in self.input_concentrations:
                concentration = self.input_concentrations[node_name]
                threshold = 1.0
                hill_value = 0.85 * (1.0 - 1.0 / (1.0 + (concentration / threshold)))
                self.nodes[node_name].active = (hill_value > self.cell_ran2)
            
            # Standard deterministic activation
            else:
                self.nodes[node_name].active = state
    
    def get_all_states(self) -> Dict[str, bool]:
        """Get current states of all nodes."""
        return {name: node.active for name, node in self.nodes.items()}
    
    def _get_random_input_node(self) -> str:
        """Get a random input node."""
        if self.input_nodes:
            return random.choice(list(self.input_nodes))
        nodes_with_outputs = [name for name, node in self.nodes.items() if node.outputs]
        if nodes_with_outputs:
            return random.choice(nodes_with_outputs)
        return random.choice(list(self.nodes.keys()))
    
    def update_one_step(self, current_tick: int) -> Tuple[Optional[str], bool]:
        """
        Perform one graph-walking step.
        
        Returns:
            (fate_assigned, fate_reverted)
        """
        current_node = self.nodes.get(self.last_node)
        if not current_node or not current_node.outputs:
            self.last_node = self._get_random_input_node()
            return None, False
        
        # Pick one random outgoing link
        target_name = random.choice(list(current_node.outputs))
        target_node = self.nodes[target_name]
        
        # Save current fate
        current_fate_before = self.fate
        
        # Update target node
        self.network_steps += 1
        fate_assigned = None
        fate_reverted = False
        
        if target_node.update_function:
            current_states = self.get_all_states()
            new_state = target_node.update_function.evaluate(current_states)
            
            if target_node.active != new_state and target_name not in self.mutations:
                target_node.active = new_state
                target_node.active_change_count += 1
        
        # Handle fate nodes
        if target_node.kind == NODE_KIND_OUTPUT_FATE:
            if target_node.active:
                fate_assigned = self._handle_fate_fire(target_name, current_tick)
            
            if (not target_node.active) and (target_name == current_fate_before):
                self.fate = None
                fate_reverted = True
            
            target_node.active = False
            self.last_node = self._get_random_input_node()
        
        elif target_node.kind == NODE_KIND_OUTPUT:
            self.last_node = self._get_random_input_node()
        
        elif target_node.kind in (NODE_KIND_INPUT, NODE_KIND_GENE):
            self.last_node = target_name
        
        return fate_assigned, fate_reverted
    
    def _handle_fate_fire(self, fate_name: str, current_tick: int) -> Optional[str]:
        """Handle fate node firing."""
        if fate_name == "Apoptosis":
            self.fate = "Apoptosis"
            return "Apoptosis"
        elif fate_name == "Growth_Arrest":
            self.fate = "Growth_Arrest"
            self.growth_arrest_cycle = self.growth_arrest_cycle_max
            return "Growth_Arrest"
        elif fate_name == "Proliferation":
            self.fate = "Proliferation"
            return "Proliferation"
        elif fate_name == "Necrosis":
            self.fate = "Necrosis"
            return "Necrosis"
        return None
    
    def check_phenotype(self) -> Dict[str, bool]:
        """
        Check current phenotype.
        
        Returns:
            {'proliferated': bool, 'died': bool}
        """
        proliferated = (self.fate == "Proliferation")
        died = (self.fate in ("Apoptosis", "Necrosis"))
        return {"proliferated": proliferated, "died": died}



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
        """Load gene network from .bnd file."""
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
                    
                    if node_name in ('GLUT1I', 'MCT1I'):
                        try:
                            concentration = float(value)
                            self.input_concentrations[node_name] = concentration
                            input_states[node_name] = True
                        except ValueError:
                            if value in ('true', '1', 'on', 'yes'):
                                self.input_concentrations[node_name] = 1.0
                                input_states[node_name] = True
                            else:
                                self.input_concentrations[node_name] = 0.0
                                input_states[node_name] = False
                    else:
                        if value in ('true', '1', 'on', 'yes'):
                            input_states[node_name] = True
                        elif value in ('false', '0', 'off', 'no'):
                            input_states[node_name] = False
                        else:
                            input_states[node_name] = False
        
        print(f"Loaded {len(input_states)} input states")
        if self.input_concentrations:
            print(f"  Probabilistic inputs: {', '.join(self.input_concentrations.keys())}")
        return input_states



# =============================================================================
# POPULATION SIMULATOR
# =============================================================================

class PopulationSimulator:
    """
    Population-level simulator tracking multiple cells with birth/death dynamics.
    """
    
    def __init__(self, network_template: GeneNetworkTemplate, 
                 input_states: Dict[str, bool],
                 initial_population: int = 10,
                 max_population: int = 1000):
        self.network_template = network_template
        self.input_states = input_states
        self.max_population = max_population
        
        # Population tracking
        self.cells: List[Cell] = []
        self.population_history: List[Dict] = []
        
        # Statistics
        self.total_births = 0
        self.total_deaths = 0
        self.total_apoptosis = 0
        self.total_necrosis = 0
        
        # Initialize population
        for _ in range(initial_population):
            self.add_cell(birth_tick=0, parent_id=None)
    
    def add_cell(self, birth_tick: int, parent_id: Optional[int] = None) -> Cell:
        """Create and add a new cell to the population."""
        cell = Cell(self.network_template, birth_tick=birth_tick, parent_id=parent_id)
        cell.reset(random_init=True)
        cell.set_input_states(self.input_states)
        self.cells.append(cell)
        return cell
    
    def simulate(self, total_steps: int, periodic_check_interval: int = 100,
                 reversible: bool = True, verbose: bool = False) -> Dict:
        """
        Simulate population dynamics over time.
        
        Args:
            total_steps: Total simulation time (ticks)
            periodic_check_interval: Check phenotype every N steps
            reversible: Keep updating cells until Necrosis (vs stop at any fate)
            verbose: Print progress
        
        Returns:
            Dictionary with population statistics
        """
        print(f"\nSimulating population dynamics:")
        print(f"  Initial population: {len(self.cells)}")
        print(f"  Total steps: {total_steps}")
        print(f"  Periodic checks: every {periodic_check_interval} steps")
        print(f"  Max population: {self.max_population}")
        
        # Track population at each check
        check_number = 0
        
        for tick in range(total_steps):
            # Update all living cells (one graph-walking step each)
            for cell in self.cells:
                # Check stopping condition for this cell
                if reversible:
                    if cell.fate == "Necrosis":
                        continue  # Skip this cell (it's stopped)
                else:
                    if cell.fate is not None:
                        continue  # Skip this cell (it's stopped)
                
                # Perform one update step
                cell.update_one_step(current_tick=tick)
            
            # Periodic phenotype check
            if (tick + 1) % periodic_check_interval == 0:
                check_number += 1
                births, deaths = self.periodic_check(current_tick=tick + 1)
                
                # Record population state
                self.population_history.append({
                    'tick': tick + 1,
                    'population': len(self.cells),
                    'births': births,
                    'deaths': deaths,
                    'total_births': self.total_births,
                    'total_deaths': self.total_deaths,
                })
                
                if verbose or (check_number % 10 == 0):
                    print(f"  Tick {tick + 1}: Population = {len(self.cells)} "
                          f"(+{births} births, -{deaths} deaths)")
                
                # Check for extinction or overpopulation
                if len(self.cells) == 0:
                    print(f"  EXTINCTION at tick {tick + 1}")
                    break
                
                if len(self.cells) >= self.max_population:
                    print(f"  MAX POPULATION REACHED at tick {tick + 1}")
                    break
        
        # Final statistics
        return self.get_statistics()
    
    def periodic_check(self, current_tick: int) -> Tuple[int, int]:
        """
        Periodic phenotype check for all cells.
        
        Returns:
            (num_births, num_deaths)
        """
        cells_to_add = []
        cells_to_remove = []
        
        for cell in self.cells:
            phenotype = cell.check_phenotype()
            
            # Proliferation → create daughter
            if phenotype['proliferated']:
                daughter = Cell(self.network_template, 
                              birth_tick=current_tick, 
                              parent_id=cell.id)
                daughter.reset(random_init=True)
                daughter.set_input_states(self.input_states)
                cells_to_add.append(daughter)
                self.total_births += 1
            
            # Death → remove cell
            if phenotype['died']:
                cell.death_tick = current_tick
                cells_to_remove.append(cell)
                self.total_deaths += 1
                
                if cell.fate == "Apoptosis":
                    self.total_apoptosis += 1
                elif cell.fate == "Necrosis":
                    self.total_necrosis += 1
        
        # Update population
        for daughter in cells_to_add:
            self.cells.append(daughter)
        
        for dead_cell in cells_to_remove:
            self.cells.remove(dead_cell)
        
        return len(cells_to_add), len(cells_to_remove)
    
    def get_statistics(self) -> Dict:
        """Compile final statistics."""
        return {
            'population_history': self.population_history,
            'final_population': len(self.cells),
            'total_births': self.total_births,
            'total_deaths': self.total_deaths,
            'total_apoptosis': self.total_apoptosis,
            'total_necrosis': self.total_necrosis,
            'net_growth': len(self.cells) - self.population_history[0]['population'] if self.population_history else 0,
        }



# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def print_results(results: Dict, initial_population: int):
    """Print formatted population simulation results."""
    
    print(f"\n{'='*70}")
    print(f"POPULATION SIMULATION RESULTS")
    print(f"{'='*70}")
    
    history = results['population_history']
    
    print(f"\nPopulation Dynamics:")
    print(f"  Initial population: {initial_population}")
    print(f"  Final population:   {results['final_population']}")
    print(f"  Net growth:         {results['net_growth']:+d} cells")
    print(f"  Growth factor:      {results['final_population'] / initial_population:.2f}x")
    
    print(f"\nBirth/Death Statistics:")
    print(f"  Total births:       {results['total_births']}")
    print(f"  Total deaths:       {results['total_deaths']}")
    print(f"    - Apoptosis:      {results['total_apoptosis']}")
    print(f"    - Necrosis:       {results['total_necrosis']}")
    print(f"  Birth/Death ratio:  {results['total_births'] / max(1, results['total_deaths']):.2f}")
    
    # Population trajectory
    print(f"\n{'='*70}")
    print(f"POPULATION TRAJECTORY")
    print(f"{'='*70}")
    print(f"{'Tick':<8} {'Population':<12} {'Births':<8} {'Deaths':<8}")
    print(f"{'-'*40}")
    
    for record in history[::max(1, len(history)//20)]:  # Show ~20 timepoints
        print(f"{record['tick']:<8} {record['population']:<12} "
              f"{record['births']:<8} {record['deaths']:<8}")
    
    # Growth rate analysis
    if len(history) > 1:
        initial_pop = history[0]['population']
        final_pop = history[-1]['population']
        time_span = history[-1]['tick'] - history[0]['tick']
        
        if initial_pop > 0 and final_pop > initial_pop:
            doubling_time = time_span * np.log(2) / np.log(final_pop / initial_pop)
            print(f"\nGrowth Rate:")
            print(f"  Doubling time: {doubling_time:.1f} ticks")
        elif final_pop < initial_pop:
            print(f"\nGrowth Rate:")
            print(f"  Population DECLINING (extinction risk)")
    
    print(f"{'='*70}")


# Try to import numpy/matplotlib for plotting
try:
    import numpy as np
    import matplotlib.pyplot as plt
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    np = None  # For type hints


def plot_results(results: Dict, output_file: str = None):
    """Plot population dynamics (if matplotlib available)."""
    if not PLOTTING_AVAILABLE:
        print("\nNote: Install matplotlib for population trajectory plots")
        return
    
    history = results['population_history']
    if not history:
        return
    
    ticks = [r['tick'] for r in history]
    population = [r['population'] for r in history]
    births = [r['births'] for r in history]
    deaths = [r['deaths'] for r in history]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Population trajectory
    ax1.plot(ticks, population, 'b-', linewidth=2, label='Population')
    ax1.set_xlabel('Time (ticks)')
    ax1.set_ylabel('Cell Count')
    ax1.set_title('Population Dynamics Over Time')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Birth/Death rates
    ax2.plot(ticks, births, 'g-', linewidth=2, label='Births', alpha=0.7)
    ax2.plot(ticks, deaths, 'r-', linewidth=2, label='Deaths', alpha=0.7)
    ax2.set_xlabel('Time (ticks)')
    ax2.set_ylabel('Events per Check')
    ax2.set_title('Birth and Death Rates')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"\nPlot saved to {output_file}")
    else:
        plt.show()



# =============================================================================
# COMMAND-LINE INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Population-Level Gene Network Simulator with Birth/Death Dynamics',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic population simulation
  python gene_network_population_simulator.py network.bnd inputs.txt \\
      --initial-cells 10 --steps 5000 --periodic-check 100

  # With population limits and plotting
  python gene_network_population_simulator.py network.bnd inputs.txt \\
      --initial-cells 20 --steps 5000 --periodic-check 100 \\
      --max-population 500 --plot population_growth.png

  # With seed for reproducibility
  python gene_network_population_simulator.py network.bnd inputs.txt \\
      --initial-cells 10 --steps 5000 --periodic-check 100 --seed 42
        """
    )
    parser.add_argument('bnd_file', help='Path to .bnd gene network file')
    parser.add_argument('input_file', help='Path to input states file')
    parser.add_argument('--initial-cells', type=int, default=10,
                       help='Initial population size (default: 10)')
    parser.add_argument('--steps', type=int, default=5000,
                       help='Total simulation time in ticks (default: 5000)')
    parser.add_argument('--periodic-check', type=int, default=100,
                       help='Check phenotype every N steps (default: 100)')
    parser.add_argument('--max-population', type=int, default=1000,
                       help='Stop if population exceeds this (default: 1000)')
    parser.add_argument('--non-reversible', action='store_true',
                       help='Stop cells at first fate (default: reversible)')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducibility')
    parser.add_argument('--verbose', action='store_true',
                       help='Print progress updates')
    parser.add_argument('--plot', type=str, default=None,
                       help='Save population plot to file (requires matplotlib)')
    parser.add_argument('--output', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    # Set random seed
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Random seed: {args.seed}")
    
    # Load network
    network_template = GeneNetworkTemplate()
    network_template.load_bnd_file(args.bnd_file)
    
    # Load input conditions
    input_states = network_template.load_input_states(args.input_file)
    
    # Create population simulator
    simulator = PopulationSimulator(
        network_template=network_template,
        input_states=input_states,
        initial_population=args.initial_cells,
        max_population=args.max_population
    )
    
    # Run simulation
    results = simulator.simulate(
        total_steps=args.steps,
        periodic_check_interval=args.periodic_check,
        reversible=not args.non_reversible,
        verbose=args.verbose
    )
    
    # Print results
    print_results(results, args.initial_cells)
    
    # Plot results
    if args.plot:
        plot_results(results, args.plot)
    elif PLOTTING_AVAILABLE and not args.output:
        plot_results(results)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == '__main__':
    main()
