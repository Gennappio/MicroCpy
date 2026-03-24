"""
Initialize NetLogo-Faithful Gene Networks for All Cells.

Replicates the EXACT initialization and input-setting behavior from
gene_network_netlogo_probability.py (the benchmark) inside the MicroCpy
workflow system.

WHAT THIS FUNCTION DOES (single-step replacement for
initialize_hierarchical_gene_networks + set_gene_network_inputs):

    1. Load BND file → create HierarchicalBooleanNetwork per cell
    2. Build output links (graph connectivity for graph walking)
    3. Reset node states: fate nodes → False, others → random (or False)
    4. Initialize per-cell random thresholds (_cell_ran1, _cell_ran2)
    5. Initialize graph walking state (_last_node, _fate)
    6. Apply input states WITH probabilistic activation for GLUT1I / MCT1I
    7. NO logic synchronization pass (matching benchmark default)

KEY DIFFERENCES FROM initialize_hierarchical_gene_networks:
    - Builds graph output links immediately (for graph walking propagation)
    - Initializes _last_node, _fate, _cell_ran1, _cell_ran2 per cell
    - Supports probabilistic input activation for GLUT1I and MCT1I via Hill fn
    - Marks _output_links_built so propagation skips redundant graph building
    - Replaces separate set_gene_network_inputs call (inputs set here)

PROBABILISTIC INPUT ACTIVATION (NetLogo lines 1298-1321):
    MCT1I and GLUT1I use stochastic activation instead of deterministic ON/OFF:
    - Each cell gets two persistent random values in [0, 1):
        _cell_ran1 → used for MCT1I
        _cell_ran2 → used for GLUT1I
    - Hill function:
        probability = 0.85 * (1 - 1 / (1 + (concentration / threshold)^1.0))
    - Activation:
        active = (probability > cell_random_value)
    - This creates CELL-TO-CELL VARIABILITY in response to the same inputs.

PSEUDOCODE:
    for each cell in population:
        gn = HierarchicalBooleanNetwork(bnd_file)
        build_output_links(gn)
        reset_nodes(gn, random_init)          # fate=False, genes=random
        gn._cell_ran1 = random()              # persistent MCT1I threshold
        gn._cell_ran2 = random()              # persistent GLUT1I threshold
        gn._last_node = random_input_node()   # graph walking start
        gn._fate = None                       # no fate assigned yet
        apply_input_states(gn, inputs, probabilistic=True)
        context['gene_networks'][cell_id] = gn
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import random as _random
from src.workflow.decorators import register_function


# Fate node names matching NetLogo's Output-Fate kind
FATE_NODE_NAMES = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}


def _to_bool(val) -> bool:
    """Convert a value to bool, handling strings from the GUI ("true"/"false")."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'on', 'yes')
    return bool(val)


@register_function(
    display_name="Initialize NetLogo-Faithful Gene Networks",
    description="Create gene networks matching NetLogo: graph walking, probabilistic inputs, fate reversion",
    category="INITIALIZATION",
    parameters=[
        {"name": "bnd_file", "type": "STRING", "description": "Path to BND file",
         "default": "gene_network.bnd"},
        {"name": "random_initialization", "type": "BOOL",
         "description": "Random initialization for non-input, non-fate nodes", "default": True},
        # --- Input node states (single DICT) ---
        {
            "name": "input_states",
            "type": "DICT",
            "description": "Dict mapping input node names to boolean ON/OFF values",
            "default": {
                "Oxygen_supply": True,
                "Glucose_supply": True,
                "MCT1_stimulus": False,
                "Proton_level": False,
                "FGFR_stimulus": False,
                "EGFR_stimulus": False,
                "cMET_stimulus": False,
                "Growth_Inhibitor": False,
                "DNA_damage": False,
                "TGFBR_stimulus": False,
            }
        },
        # --- Probabilistic input concentrations (single DICT) ---
        {
            "name": "concentrations",
            "type": "DICT",
            "description": "Dict mapping substance names to float concentrations for Hill function (0=OFF)",
            "default": {
                "GLUT1I_concentration": 0.0,
                "MCT1I_concentration": 0.0,
            }
        },
    ],
    outputs=["gene_network"],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def initialize_netlogo_gene_networks(
    context: Dict[str, Any],
    bnd_file: str = "gene_network.bnd",
    random_initialization: bool = True,
    input_states: Union[Dict, List, str] = None,
    concentrations: Union[Dict, List, str] = None,
    **kwargs  # catches legacy individual params for backwards compat
) -> bool:
    """
    Create and attach NetLogo-faithful gene networks to all cells.

    This single function replaces the combination of:
      initialize_hierarchical_gene_networks + set_gene_network_inputs

    It creates gene networks that are fully ready for graph walking propagation
    via propagate_gene_networks_netlogo, with all required attributes initialized.

    Args:
        context: Workflow context (must contain 'population')
        bnd_file: Path to BND file defining the network topology
        random_initialization: Randomize non-input, non-fate nodes
        input_states: Dict mapping input node names to boolean ON/OFF values
        concentrations: Dict mapping substance names to float concentrations
                        for Hill function (0 = OFF)

    Returns:
        True if successful, False otherwise
    """
    # print("[GENE_NETWORK] Initializing NetLogo-faithful gene networks for all cells")

    # =========================================================================
    # 0. VALIDATE CONTEXT
    # =========================================================================
    population = context.get('population')
    if population is None:
        print("[ERROR] No population found. Run 'Initialize Population' first.")
        return False

    try:
        # Ensure src is on the path
        import sys
        src_path = Path(__file__).parent.parent.parent.parent
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from biology.gene_network import HierarchicalBooleanNetwork

        # =================================================================
        # 1. RESOLVE BND FILE PATH
        # =================================================================
        bnd_path = _resolve_bnd_path(context, bnd_file)
        if bnd_path is None or not bnd_path.exists():
            print(f"[ERROR] BND file not found: {bnd_file}")
            return False

        # =================================================================
        # 2. BUILD CONFIG (reuse existing pattern for BooleanNetwork loader)
        # =================================================================
        # We use Proliferation as last = highest priority but the propagation
        # function uses last-overwrite-wins, not hierarchical counting.
        fate_hierarchy_list = ["Necrosis", "Apoptosis", "Growth_Arrest", "Proliferation"]

        class _GeneNetworkConfig:
            def __init__(self, bnd, random_init):
                self.bnd_file = str(bnd)
                self.propagation_steps = 500
                self.random_initialization = random_init
                self.output_nodes = fate_hierarchy_list
                self.nodes = {}

        class _MinimalConfig:
            def __init__(self):
                self.gene_network = None

        config = _MinimalConfig()
        config.gene_network = _GeneNetworkConfig(bnd_path, random_initialization)

        # Store config for later use
        context['gene_network_config'] = config
        context['random_initialization'] = random_initialization
        context['fate_hierarchy'] = fate_hierarchy_list

        # =================================================================
        # 3. COLLECT INPUT STATES
        # =================================================================
        # Accept DICT parameter or fall back to individual kwargs (backwards compat)
        if input_states is None:
            known_inputs = ['Oxygen_supply', 'Glucose_supply', 'MCT1_stimulus',
                            'Proton_level', 'FGFR_stimulus', 'EGFR_stimulus',
                            'cMET_stimulus', 'Growth_Inhibitor', 'DNA_damage',
                            'TGFBR_stimulus']
            if any(name in kwargs for name in known_inputs):
                # Legacy individual parameters passed via kwargs
                input_states = {}
                for name in known_inputs:
                    if name in kwargs:
                        input_states[name] = _to_bool(kwargs[name])
            else:
                # Use defaults
                input_states = {
                    'Oxygen_supply': True, 'Glucose_supply': True,
                    'MCT1_stimulus': False, 'Proton_level': False,
                    'FGFR_stimulus': False, 'EGFR_stimulus': False,
                    'cMET_stimulus': False, 'Growth_Inhibitor': False,
                    'DNA_damage': False, 'TGFBR_stimulus': False,
                }
        else:
            # Ensure values are booleans (GUI may send strings)
            input_states = {k: _to_bool(v) for k, v in input_states.items()}

        context['gene_network_inputs'] = input_states

        # Store concentration parameters so daughter cells created during
        # division can reuse the same probabilistic activation settings.
        if concentrations is None:
            concentrations = {
                'MCT1I_concentration': float(kwargs.get('MCT1I_concentration', 0.0)),
                'GLUT1I_concentration': float(kwargs.get('GLUT1I_concentration', 0.0)),
            }
        else:
            concentrations = {k: float(v) for k, v in concentrations.items()}

        MCT1I_concentration = concentrations.get('MCT1I_concentration', 0.0)
        GLUT1I_concentration = concentrations.get('GLUT1I_concentration', 0.0)
        context['gene_network_init_params'] = concentrations

        # =================================================================
        # 4. CREATE GENE NETWORK PER CELL
        # =================================================================
        context['gene_networks'] = {}
        cells = population.state.cells
        num_cells = len(cells)

        for cell_id, cell in cells.items():
            # --- 4a. Create network from BND file ---
            cell_gn = HierarchicalBooleanNetwork(
                config=config,
                fate_hierarchy=fate_hierarchy_list,
            )

            # --- 4b. Reset node states (benchmark: reset()) ---
            #   - Fate nodes → False
            #   - Other non-input nodes → random (or False)
            #   - Input nodes → untouched (set below)
            for node in cell_gn.nodes.values():
                if node.is_input:
                    continue
                elif node.name in FATE_NODE_NAMES:
                    node.current_state = False
                    node.next_state = False
                else:
                    state = _random.choice([True, False]) if random_initialization else False
                    node.current_state = state
                    node.next_state = state

            # --- 4c. Build output links (graph connectivity) ---
            _build_output_links(cell_gn)
            cell_gn._output_links_built = True

            # --- 4d. Initialize per-cell random thresholds (benchmark: reset()) ---
            #   NetLogo: my-cell-ran1 (MCT1I), my-cell-ran2 (GLUT1I)
            cell_gn._cell_ran1 = _random.random()
            cell_gn._cell_ran2 = _random.random()

            # --- 4e. Initialize graph walking state ---
            #   NetLogo: my-last-node = one-of my-nodes with [ kind = "Input" ]
            input_node_names = [n for n, nd in cell_gn.nodes.items() if nd.is_input]
            if input_node_names:
                cell_gn._last_node = _random.choice(input_node_names)
            else:
                cell_gn._last_node = _random.choice(list(cell_gn.nodes.keys()))

            #   NetLogo: my-fate = nobody
            cell_gn._fate = None

            # --- 4f. Apply input states (with probabilistic activation) ---
            _apply_input_states(
                cell_gn, input_states,
                MCT1I_concentration=MCT1I_concentration,
                GLUT1I_concentration=GLUT1I_concentration,
            )

            # --- 4g. Store in context ---
            context['gene_networks'][cell_id] = cell_gn

            # --- 4h. Update cell state to reflect gene states ---
            initial_gene_states = {
                name: node.current_state for name, node in cell_gn.nodes.items()
            }
            cell.state = cell.state.with_updates(gene_states=initial_gene_states)

        # =================================================================
        # 5. CREATE REFERENCE NETWORK (for input node inspection, etc.)
        # =================================================================
        reference_gn = HierarchicalBooleanNetwork(
            config=config,
            fate_hierarchy=fate_hierarchy_list,
        )
        context['reference_gene_network'] = reference_gn

        # =================================================================
        # 6. LOG SUMMARY
        # =================================================================
        active_inputs = [k for k, v in input_states.items() if v]
        print(f"[GENE_NETWORK] Initialized {num_cells} NetLogo-faithful networks "
              f"(inputs: {active_inputs})")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to initialize NetLogo-faithful gene networks: {e}")
        import traceback
        traceback.print_exc()
        return False


# =============================================================================
# HELPER: RESOLVE BND FILE PATH
# =============================================================================
def _resolve_bnd_path(context: Dict[str, Any], bnd_file: str) -> Optional[Path]:
    """
    Resolve the BND file path using context['resolve_path'] or fallback heuristics.

    Tries (in order):
        1. context['resolve_path'](bnd_file)
        2. Relative to engine_root (opencellcomms_engine/)
        3. Relative to workspace_root (MicroCpy/)
        4. Relative to CWD / tests/
    """
    if 'resolve_path' in context:
        return context['resolve_path'](bnd_file)

    bnd_path = Path(bnd_file)
    if bnd_path.exists():
        return bnd_path

    # engine_root = opencellcomms_engine/
    engine_root = Path(__file__).parent.parent.parent.parent
    candidate = engine_root / bnd_file
    if candidate.exists():
        return candidate

    # workspace_root = MicroCpy/
    workspace_root = engine_root.parent
    candidate = workspace_root / bnd_file
    if candidate.exists():
        return candidate

    # Last resort: tests/ relative to CWD
    candidate = Path("tests") / bnd_file
    if candidate.exists():
        return candidate

    return bnd_path  # will fail with clear error


# =============================================================================
# HELPER: BUILD OUTPUT LINKS
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


# =============================================================================
# HELPER: APPLY INPUT STATES (with probabilistic activation)
# =============================================================================
def _apply_input_states(
    gene_network,
    input_states: Dict[str, bool],
    MCT1I_concentration: float = 0.0,
    GLUT1I_concentration: float = 0.0,
) -> None:
    """
    Apply input node states to a gene network, matching the benchmark's
    ``set_input_states`` (gene_network_netlogo_probability.py, lines 466-504).

    Standard inputs: deterministic ON / OFF.
    MCT1I and GLUT1I: probabilistic activation via Hill function
        probability = 0.85 * (1 - 1 / (1 + (conc / threshold)^1.0))
        active = (probability > cell_random_value)

    Args:
        gene_network: The gene network to update
        input_states: Dict of input name → bool (standard inputs)
        MCT1I_concentration: Concentration for MCT1I Hill function (0 = OFF)
        GLUT1I_concentration: Concentration for GLUT1I Hill function (0 = OFF)
    """
    # --- Standard boolean inputs ---
    for node_name, state in input_states.items():
        if node_name in gene_network.nodes:
            gene_network.nodes[node_name].current_state = state

    # --- Probabilistic activation for MCT1I (NetLogo lines 1298-1312) ---
    if MCT1I_concentration > 0 and 'MCT1I' in gene_network.nodes:
        threshold = 1.0  # Default activation threshold
        hill_value = 0.85 * (1.0 - 1.0 / (1.0 + (MCT1I_concentration / threshold)))
        gene_network.nodes['MCT1I'].current_state = (hill_value > gene_network._cell_ran1)

    # --- Probabilistic activation for GLUT1I (NetLogo lines 1315-1321) ---
    if GLUT1I_concentration > 0 and 'GLUT1I' in gene_network.nodes:
        threshold = 1.0  # Default activation threshold
        hill_value = 0.85 * (1.0 - 1.0 / (1.0 + (GLUT1I_concentration / threshold)))
        gene_network.nodes['GLUT1I'].current_state = (hill_value > gene_network._cell_ran2)
