"""
Initialize NetLogo-Faithful Gene Networks for All Cells.

Replicates the EXACT initialization and input-setting behavior from
gene_network_netlogo_probability.py (the benchmark) inside the OpenCellComms
workflow system.

WHAT THIS FUNCTION DOES (single-step replacement for
initialize_hierarchical_gene_networks + set_gene_network_inputs):

    1. Load BND file -> create HierarchicalBooleanNetwork per cell
    2. Build output links (graph connectivity for graph walking)
    3. Reset node states: fate nodes -> False, others -> random (or False)
    4. Initialize per-cell random thresholds (_cell_ran1, _cell_ran2)
    5. Initialize graph walking state (_last_node, _fate)
    6. Apply input states WITH probabilistic activation for GLUT1I / MCT1I
    7. NO logic synchronization pass (matching benchmark default)

PROBABILISTIC INPUT ACTIVATION (NetLogo lines 1298-1321):
    MCT1I and GLUT1I use stochastic activation instead of deterministic ON/OFF:
    - Each cell gets two persistent random values in [0, 1):
        _cell_ran1 -> used for MCT1I
        _cell_ran2 -> used for GLUT1I
    - Hill function:
        probability = 0.85 * (1 - 1 / (1 + (concentration / threshold)^1.0))
    - Activation:
        active = (probability > cell_random_value)
    - This creates CELL-TO-CELL VARIABILITY in response to the same inputs.
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import random as _random
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


FATE_NODE_NAMES = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}


def _to_bool(val) -> bool:
    """Convert a value to bool, handling strings from the GUI ("true"/"false")."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'on', 'yes')
    return bool(val)


@register_function(
    requires=['gene_networks', 'population'],
    display_name="Initialize NetLogo-Faithful Gene Networks",
    description="Create gene networks matching NetLogo: graph walking, probabilistic inputs, fate reversion",
    category="INITIALIZATION",
    parameters=[
        {"name": "bnd_file", "type": "STRING", "description": "Path to BND file",
         "default": "gene_network.bnd"},
        {"name": "random_initialization", "type": "BOOL",
         "description": "Random initialization for non-input, non-fate nodes", "default": True},
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
    inputs=["context"],
    outputs=["gene_network"],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def initialize_netlogo_gene_networks(
    env: BiologicalContext,
    bnd_file: str = "gene_network.bnd",
    random_initialization: bool = True,
    input_states: Union[Dict, List, str] = None,
    concentrations: Union[Dict, List, str] = None,
    **kwargs
) -> bool:
    ctx = env.raw_context
    if len(env.cells) == 0:
        print("[ERROR] No population found. Run 'Initialize Population' first.")
        return False

    try:
        import sys
        src_path = Path(__file__).parent.parent.parent.parent
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from biology.gene_network import HierarchicalBooleanNetwork

        bnd_path = _resolve_bnd_path(ctx, bnd_file)
        if bnd_path is None or not bnd_path.exists():
            print(f"[ERROR] BND file not found: {bnd_file}")
            return False

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

        ctx['gene_network_config'] = config
        ctx['random_initialization'] = random_initialization
        ctx['fate_hierarchy'] = fate_hierarchy_list

        if input_states is None:
            known_inputs = ['Oxygen_supply', 'Glucose_supply', 'MCT1_stimulus',
                            'Proton_level', 'FGFR_stimulus', 'EGFR_stimulus',
                            'cMET_stimulus', 'Growth_Inhibitor', 'DNA_damage',
                            'TGFBR_stimulus']
            if any(name in kwargs for name in known_inputs):
                input_states = {}
                for name in known_inputs:
                    if name in kwargs:
                        input_states[name] = _to_bool(kwargs[name])
            else:
                input_states = {
                    'Oxygen_supply': True, 'Glucose_supply': True,
                    'MCT1_stimulus': False, 'Proton_level': False,
                    'FGFR_stimulus': False, 'EGFR_stimulus': False,
                    'cMET_stimulus': False, 'Growth_Inhibitor': False,
                    'DNA_damage': False, 'TGFBR_stimulus': False,
                }
        else:
            input_states = {k: _to_bool(v) for k, v in input_states.items()}

        ctx['gene_network_inputs'] = input_states

        if concentrations is None:
            concentrations = {
                'MCT1I_concentration': float(kwargs.get('MCT1I_concentration', 0.0)),
                'GLUT1I_concentration': float(kwargs.get('GLUT1I_concentration', 0.0)),
            }
        else:
            concentrations = {k: float(v) for k, v in concentrations.items()}

        MCT1I_concentration = concentrations.get('MCT1I_concentration', 0.0)
        GLUT1I_concentration = concentrations.get('GLUT1I_concentration', 0.0)
        ctx['gene_network_init_params'] = concentrations

        ctx['gene_networks'] = {}
        num_cells = 0

        for cell in env.cells:
            num_cells += 1
            cell_gn = HierarchicalBooleanNetwork(
                config=config,
                fate_hierarchy=fate_hierarchy_list,
            )

            # Reset node states (benchmark: reset())
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

            _build_output_links(cell_gn)
            cell_gn._output_links_built = True

            # Per-cell random thresholds and graph-walking state
            cell_gn._cell_ran1 = _random.random()
            cell_gn._cell_ran2 = _random.random()

            input_node_names = [n for n, nd in cell_gn.nodes.items() if nd.is_input]
            if input_node_names:
                cell_gn._last_node = _random.choice(input_node_names)
            else:
                cell_gn._last_node = _random.choice(list(cell_gn.nodes.keys()))

            cell_gn._fate = None

            _apply_input_states(
                cell_gn, input_states,
                MCT1I_concentration=MCT1I_concentration,
                GLUT1I_concentration=GLUT1I_concentration,
            )

            env.set_gene_network(cell, cell_gn)

            initial_gene_states = {
                name: node.current_state for name, node in cell_gn.nodes.items()
            }
            cell.set_gene_state_snapshot(initial_gene_states)

        # Reference network (for input node inspection, etc.)
        reference_gn = HierarchicalBooleanNetwork(
            config=config,
            fate_hierarchy=fate_hierarchy_list,
        )
        ctx['reference_gene_network'] = reference_gn

        active_inputs = [k for k, v in input_states.items() if v]
        print(f"[GENE_NETWORK] Initialized {num_cells} NetLogo-faithful networks "
              f"(inputs: {active_inputs})")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to initialize NetLogo-faithful gene networks: {e}")
        import traceback
        traceback.print_exc()
        return False


def _resolve_bnd_path(ctx: Dict[str, Any], bnd_file: str) -> Optional[Path]:
    """Resolve BND file path using ctx['resolve_path'] or fallback heuristics."""
    if 'resolve_path' in ctx:
        return ctx['resolve_path'](bnd_file)

    bnd_path = Path(bnd_file)
    if bnd_path.exists():
        return bnd_path

    engine_root = Path(__file__).parent.parent.parent.parent
    candidate = engine_root / bnd_file
    if candidate.exists():
        return candidate

    workspace_root = engine_root.parent
    candidate = workspace_root / bnd_file
    if candidate.exists():
        return candidate

    candidate = Path("tests") / bnd_file
    if candidate.exists():
        return candidate

    return bnd_path


def _build_output_links(gene_network) -> None:
    """Build output links (which nodes depend on each node) for graph walking."""
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


def _apply_input_states(
    gene_network,
    input_states: Dict[str, bool],
    MCT1I_concentration: float = 0.0,
    GLUT1I_concentration: float = 0.0,
) -> None:
    """Apply input node states with probabilistic activation for MCT1I/GLUT1I."""
    for node_name, state in input_states.items():
        if node_name in gene_network.nodes:
            gene_network.nodes[node_name].current_state = state

    if MCT1I_concentration > 0 and 'MCT1I' in gene_network.nodes:
        threshold = 1.0
        hill_value = 0.85 * (1.0 - 1.0 / (1.0 + (MCT1I_concentration / threshold)))
        gene_network.nodes['MCT1I'].current_state = (hill_value > gene_network._cell_ran1)

    if GLUT1I_concentration > 0 and 'GLUT1I' in gene_network.nodes:
        threshold = 1.0
        hill_value = 0.85 * (1.0 - 1.0 / (1.0 + (GLUT1I_concentration / threshold)))
        gene_network.nodes['GLUT1I'].current_state = (hill_value > gene_network._cell_ran2)
