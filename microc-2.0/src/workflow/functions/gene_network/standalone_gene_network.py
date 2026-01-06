"""
REUSABLE gene network functions for testing and workflows.

These are GRANULAR, REUSABLE nodes that can be used in:
- Gene network testing workflows (without full simulation)
- Full simulation workflows

REUSABLE FUNCTIONS:
- Initialize Population: creates a population with N cells
- Initialize Gene Networks: attaches gene networks to all cells in population
- Set Gene Network Input States: sets input nodes for all cells
- Print Gene Network States: prints statistics

These functions work with both mock populations (for testing) and
real CellPopulation objects (for full simulation).
"""

from typing import Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field
from src.workflow.decorators import register_function
import random


# ============================================================================
# Mock classes for lightweight testing (no FiPy/diffusion required)
# ============================================================================

@dataclass
class MockPosition:
    """Mock position for a cell."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __iter__(self):
        return iter((self.x, self.y))

    def __hash__(self):
        return hash((self.x, self.y, self.z))


@dataclass
class MockCellState:
    """Mock cell state with gene network."""
    position: MockPosition = field(default_factory=MockPosition)
    gene_network: Any = None
    gene_states: Dict[str, bool] = field(default_factory=dict)

    def with_updates(self, **kwargs):
        """Return a copy with updated fields."""
        new_state = MockCellState(
            position=self.position,
            gene_network=self.gene_network,
            gene_states=kwargs.get('gene_states', self.gene_states)
        )
        return new_state


@dataclass
class MockCell:
    """Mock cell containing state and gene network."""
    id: str = ""
    state: MockCellState = field(default_factory=MockCellState)
    _cached_gene_states: Dict[str, bool] = field(default_factory=dict)
    _cached_local_env: Dict[str, float] = field(default_factory=dict)


@dataclass
class MockPopulationState:
    """Mock population state."""
    cells: Dict[str, MockCell] = field(default_factory=dict)

    def with_updates(self, **kwargs):
        """Return a copy with updated cells."""
        new_state = MockPopulationState(
            cells=kwargs.get('cells', self.cells)
        )
        return new_state


@dataclass
class MockPopulation:
    """Mock population for gene network testing."""
    state: MockPopulationState = field(default_factory=MockPopulationState)


class MockSimulator:
    """Mock simulator that returns fixed substance concentrations."""

    def __init__(self, concentrations: Dict[str, float] = None):
        self.concentrations = concentrations or {}

    def get_substance_concentrations(self) -> Dict[str, Dict]:
        result = {}
        for substance, conc in self.concentrations.items():
            result[substance] = UniformConcentration(conc)
        return result


class UniformConcentration:
    """A concentration 'grid' that returns the same value for any position."""
    def __init__(self, value: float):
        self.value = value

    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        return self.value


@dataclass
class MockTime:
    """Mock time configuration."""
    dt: float = 1.0


@dataclass
class MockConfig:
    """Mock config for gene network testing."""
    associations: Dict[str, str] = field(default_factory=dict)
    thresholds: Dict[str, Dict[str, float]] = field(default_factory=dict)
    gene_network: Any = None
    time: MockTime = field(default_factory=MockTime)


# ============================================================================
# REUSABLE NODE 1: Initialize Population
# Creates N cells (without gene networks yet)
# ============================================================================

@register_function(
    display_name="Initialize Population",
    description="Create a population with N cells (without gene networks). Works for both testing and full simulation.",
    category="INITIALIZATION",
    parameters=[
        {"name": "num_cells", "type": "INT", "description": "Number of cells to create", "default": 100},
    ],
    outputs=["population"],
    cloneable=False
)
def initialize_population(
    context: Dict[str, Any],
    num_cells: int = 100,
    **kwargs
) -> bool:
    """
    Create a population with N cells.

    This is REUSABLE:
    - For testing: creates mock population
    - For full simulation: creates real CellPopulation (if simulator exists)

    Gene networks are attached separately by 'Initialize Gene Networks'.
    """
    print(f"[POPULATION] Initializing population with {num_cells} cells")

    try:
        # Check if we're in a full simulation context (has simulator)
        simulator = context.get('simulator')

        if simulator is not None and not isinstance(simulator, MockSimulator):
            # Full simulation mode - use real population
            print(f"   [!] Full simulation mode - population should be created via setup_population")
            return True

        # Testing mode - create mock population
        population = MockPopulation()
        cells = {}

        for i in range(num_cells):
            cell = MockCell(id=f"cell_{i}")
            cell.state = MockCellState(
                position=MockPosition(x=float(i), y=0.0),
                gene_network=None,  # No gene network yet!
                gene_states={}
            )
            cells[f"cell_{i}"] = cell

        population.state = MockPopulationState(cells=cells)

        # Store in context
        context['population'] = population
        context['num_cells'] = num_cells

        # Create mock simulator if not present (for testing)
        if 'simulator' not in context:
            context['simulator'] = MockSimulator(concentrations={})

        # Create mock config if not present (for testing)
        if 'config' not in context:
            context['config'] = MockConfig(associations={}, thresholds={})

        if 'helpers' not in context:
            context['helpers'] = {}

        print(f"   [+] Created {num_cells} cells (no gene networks yet)")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to initialize population: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# REUSABLE NODE 2: Initialize Gene Networks
# Attaches gene networks to all cells in population
# ============================================================================

@register_function(
    display_name="Initialize Gene Networks",
    description="Create and attach gene networks to all cells in population",
    category="INITIALIZATION",
    parameters=[
        {"name": "bnd_file", "type": "STRING", "description": "Path to BND file", "default": "jaya_microc.bnd"},
        {"name": "random_initialization", "type": "BOOL", "description": "Use random initialization for non-input nodes", "default": True},
    ],
    outputs=["gene_network"],
    cloneable=False
)
def initialize_gene_networks(
    context: Dict[str, Any],
    bnd_file: str = "jaya_microc.bnd",
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
            bnd_path = Path("tests/jayatilake_experiment") / bnd_file

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


# ============================================================================
# REUSABLE NODE 3: Set Gene Network Input States
# Sets input states for all cells (these stay FIXED during propagation)
# ============================================================================

@register_function(
    display_name="Set Gene Network Input States",
    description="Set input node states for all cells. These stay FIXED during propagation.",
    category="INITIALIZATION",
    parameters=[
        {"name": "Oxygen_supply", "type": "BOOL", "description": "Oxygen supply input", "default": True},
        {"name": "Glucose_supply", "type": "BOOL", "description": "Glucose supply input", "default": True},
        {"name": "MCT1_stimulus", "type": "BOOL", "description": "MCT1 stimulus input", "default": False},
        {"name": "Proton_level", "type": "BOOL", "description": "Proton level input", "default": False},
        {"name": "FGFR_stimulus", "type": "BOOL", "description": "FGFR stimulus input", "default": False},
        {"name": "EGFR_stimulus", "type": "BOOL", "description": "EGFR stimulus input", "default": False},
        {"name": "cMET_stimulus", "type": "BOOL", "description": "cMET stimulus input", "default": False},
        {"name": "Growth_Inhibitor", "type": "BOOL", "description": "Growth inhibitor input", "default": False},
        {"name": "DNA_damage", "type": "BOOL", "description": "DNA damage input", "default": False},
        {"name": "TGFBR_stimulus", "type": "BOOL", "description": "TGFBR stimulus input", "default": False},
    ],
    outputs=[],
    cloneable=False
)
def set_gene_network_inputs(
    context: Dict[str, Any],
    Oxygen_supply: bool = True,
    Glucose_supply: bool = True,
    MCT1_stimulus: bool = False,
    Proton_level: bool = False,
    FGFR_stimulus: bool = False,
    EGFR_stimulus: bool = False,
    cMET_stimulus: bool = False,
    Growth_Inhibitor: bool = False,
    DNA_damage: bool = False,
    TGFBR_stimulus: bool = False,
    **kwargs
) -> bool:
    """
    Set input node states for all cells in population.

    Input nodes (is_input=True) are NEVER updated during propagation.
    They stay FIXED at the values set here.
    """
    print(f"[GENE_NETWORK] Setting input states for all cells")

    # Build input states dict
    input_states = {
        'Oxygen_supply': Oxygen_supply,
        'Glucose_supply': Glucose_supply,
        'MCT1_stimulus': MCT1_stimulus,
        'Proton_level': Proton_level,
        'FGFR_stimulus': FGFR_stimulus,
        'EGFR_stimulus': EGFR_stimulus,
        'cMET_stimulus': cMET_stimulus,
        'Growth_Inhibitor': Growth_Inhibitor,
        'DNA_damage': DNA_damage,
        'TGFBR_stimulus': TGFBR_stimulus,
    }

    # Store for later use
    context['gene_network_inputs'] = input_states

    # Apply to all cells in population
    population = context.get('population')
    if population:
        cells = population.state.cells
        for cell_id, cell in cells.items():
            if cell.state.gene_network:
                cell.state.gene_network.set_input_states(input_states)
        print(f"   [+] Applied input states to {len(cells)} cells")
    else:
        print(f"   [!] No population yet - inputs will be applied when gene networks are created")

    # Print active inputs
    active_inputs = [k for k, v in input_states.items() if v]
    print(f"   [+] Active inputs (FIXED): {active_inputs}")

    return True


# ============================================================================
# REUSABLE NODE: Apply Associations to Gene Input States
# Reads substance concentrations and associations, sets gene inputs accordingly
# ============================================================================

@register_function(
    display_name="Apply Associations to Inputs",
    description="Set gene input states based on substance concentrations and association thresholds",
    category="INITIALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def apply_associations_to_inputs(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Apply substance-to-gene associations.

    For each association (substance -> gene_input):
    - Read substance concentration
    - Compare to threshold
    - Set gene_input = ON if concentration > threshold, else OFF

    This is for use after add_substance and add_association.
    """
    try:
        population = context.get('population')
        config = context.get('config')

        # Get substances from context
        substances = context.get('substances', {})

        # Get associations and thresholds from either context or config
        associations = context.get('associations', {})
        thresholds = context.get('thresholds', {})

        # If not in context directly, try config object
        if not associations and config:
            associations = getattr(config, 'associations', {}) or {}
            thresholds_config = getattr(config, 'thresholds', {}) or {}
            # Convert config thresholds to simple dict
            for gene_input, threshold_obj in thresholds_config.items():
                if hasattr(threshold_obj, 'threshold'):
                    thresholds[gene_input] = threshold_obj.threshold
                else:
                    thresholds[gene_input] = threshold_obj

        if not associations:
            print("[WARNING] No associations defined")
            return True

        # Build input states based on associations
        input_states = {}

        print(f"[ASSOCIATIONS] Applying {len(associations)} associations:")
        for substance_name, gene_input in associations.items():
            concentration = substances.get(substance_name, 0.0)
            threshold = thresholds.get(gene_input, 0.0)

            # Compare concentration to threshold
            is_on = concentration > threshold
            input_states[gene_input] = is_on

            status = "ON" if is_on else "OFF"
            print(f"   {substance_name} ({concentration}) > {threshold} -> {gene_input} = {status}")

        # Apply to all cells
        if population:
            cells = population.state.cells
            for cell_id, cell in cells.items():
                if cell.state.gene_network:
                    cell.state.gene_network.set_input_states(input_states)
            print(f"   [+] Applied input states to {len(cells)} cells")
        else:
            print(f"   [!] No population yet")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to apply associations: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# REUSABLE NODE 4: Update Gene Networks (Standalone)
# Propagates gene networks without needing simulator/gene_network in context
# ============================================================================

@register_function(
    display_name="Update Gene Networks (Standalone)",
    description="Propagate gene networks for all cells. Input nodes stay FIXED.",
    category="INTRACELLULAR",
    parameters=[
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps", "default": 500},
    ],
    inputs=["population"],  # Only needs population!
    outputs=[],
    cloneable=False
)
def update_gene_networks_standalone(
    population=None,
    context: Dict[str, Any] = None,
    propagation_steps: int = 500,
    **kwargs
) -> bool:
    """
    Propagate gene networks for all cells.

    Unlike the full update_gene_networks, this function:
    - Does NOT read from substance concentrations
    - Does NOT set input states from environment (they stay FIXED)
    - Only propagates the Boolean network for N steps

    This is for testing when input states are set manually.
    """
    # Get population from context if not passed directly
    if population is None and context:
        population = context.get('population')

    if population is None:
        print("[ERROR] No population found")
        return False

    cells = population.state.cells
    num_cells = len(cells)

    if num_cells == 0:
        print("[ERROR] No cells in population")
        return False

    print(f"[GENE_NETWORK] Propagating gene networks for {num_cells} cells ({propagation_steps} steps each)")

    updated_cells = {}

    for cell_id, cell in cells.items():
        cell_gn = cell.state.gene_network

        if cell_gn is None:
            continue

        # Propagate Boolean network (input nodes stay FIXED - they're excluded from updates)
        gene_states = cell_gn.step(propagation_steps)

        # Cache gene states
        cell._cached_gene_states = gene_states

        # Update cell's gene states
        cell.state = cell.state.with_updates(gene_states=gene_states)

        updated_cells[cell_id] = cell

    # Update population state
    population.state = population.state.with_updates(cells=updated_cells)

    print(f"   [+] Updated {len(updated_cells)} cells")

    return True


# ============================================================================
# REUSABLE NODE 5: Print Gene Network States
# ============================================================================

@register_function(
    display_name="Print Gene Network States",
    description="Print current gene network states from all cells",
    category="FINALIZATION",
    parameters=[
        {"name": "show_per_cell", "type": "BOOL", "description": "Show per-cell results", "default": False},
    ],
    inputs=["population"],
    outputs=[],
    cloneable=False
)
def print_gene_network_states(
    context: Dict[str, Any] = None,
    population=None,
    show_per_cell: bool = False,
    **kwargs
) -> bool:
    """
    Print gene network statistics from all cells.
    """
    # Get population from context or parameter
    if population is None and context:
        population = context.get('population')

    if population is None:
        print("[ERROR] No population found")
        return False

    cells = population.state.cells
    num_cells = len(cells)

    if num_cells == 0:
        print("[ERROR] No cells in population")
        return False

    from collections import Counter

    fate_nodes = ['Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis']
    metabolic_nodes = ['mitoATP', 'glycoATP']
    all_nodes = fate_nodes + metabolic_nodes

    # Collect statistics
    node_stats = {node: Counter() for node in all_nodes}

    for cell_id, cell in cells.items():
        gene_states = cell.state.gene_states or {}

        if show_per_cell:
            fate_str = ", ".join([f"{n}={'ON' if gene_states.get(n, False) else 'OFF'}" for n in fate_nodes])
            meta_str = ", ".join([f"{n}={'ON' if gene_states.get(n, False) else 'OFF'}" for n in metabolic_nodes])
            print(f"   {cell_id}: {fate_str} | {meta_str}")

        for node in all_nodes:
            state = gene_states.get(node, False)
            node_stats[node][state] += 1

    # Print summary
    print(f"\n[RESULTS] Gene Network Statistics ({num_cells} cells):")
    print(f"   Fate Nodes:")
    for node in fate_nodes:
        on_count = node_stats[node][True]
        off_count = node_stats[node][False]
        total = on_count + off_count
        if total > 0:
            print(f"      {node}: ON={on_count}/{total} ({100*on_count/total:.1f}%), OFF={off_count}/{total} ({100*off_count/total:.1f}%)")

    print(f"   Metabolic Nodes:")
    for node in metabolic_nodes:
        on_count = node_stats[node][True]
        off_count = node_stats[node][False]
        total = on_count + off_count
        if total > 0:
            print(f"      {node}: ON={on_count}/{total} ({100*on_count/total:.1f}%), OFF={off_count}/{total} ({100*off_count/total:.1f}%)")

    return True
