"""
Update cell division based on ATP threshold and cell cycle time.

This function checks which cells should divide based on:
- ATP production rate above threshold
- Cell age exceeds cell cycle time
- Phenotype is 'Proliferation'

Users can customize this to implement different division criteria.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
See run_diffusion_solver.py for full documentation.
================================================================================
"""

from typing import Dict, Any, Optional
import random
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation, IConfig
from src.biology.cell import Cell
from src.biology.gene_network import HierarchicalBooleanNetwork


@register_function(
    display_name="Update Cell Division",
    description="Handle cell division based on ATP and cell cycle",
    category="INTERCELLULAR",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def update_cell_division(
    context: Dict[str, Any],
    **kwargs
) -> None:
    """
    Update cell division based on ATP threshold and cell cycle time.

    For each cell:
    1. Check if cell should divide (ATP rate, age, phenotype)
    2. If yes, create a daughter cell
    3. Reset parent cell age
    4. Place daughter cell near parent

    Division criteria:
    - Cell age >= cell_cycle_time
    - ATP rate / max_atp_rate > atp_threshold
    - Phenotype is 'Proliferation'

    Args:
        context: Workflow execution context containing:
            - population: Cell population (REQUIRED)
            - config: Configuration object
        **kwargs: Additional parameters (ignored)

    Returns:
        None (modifies population in-place)
    """
    # =========================================================================
    # EXTRACT CORE CONTEXT ITEMS
    # =========================================================================
    population: Optional[ICellPopulation] = context.get('population')
    config: Optional[IConfig] = context.get('config')

    # =========================================================================
    # VALIDATE REQUIRED CORE ITEMS
    # =========================================================================
    if population is None:
        print("[update_cell_division] No population in context - skipping")
        return

    # Get division parameters from config
    atp_threshold = _get_config_param(config, 'atp_threshold', 0.8)
    max_atp_rate = _get_config_param(config, 'max_atp_rate', 30.0)
    cell_cycle_time = _get_config_param(config, 'cell_cycle_time', 240.0)
    cell_radius = _get_config_param(config, 'cell_radius', 10.0)

    # Get simulation dimensions (2D or 3D) from context
    dimensions = context.get('dimensions', 3)

    # Collect cells that should divide
    cells_to_divide = []

    for cell_id, cell in population.state.cells.items():
        # Check division criteria
        if _should_divide(cell, atp_threshold, max_atp_rate, cell_cycle_time):
            cells_to_divide.append((cell_id, cell))

    # Perform divisions
    if cells_to_divide:
        _perform_divisions(population, cells_to_divide, cell_radius, config, context, dimensions)


def _should_divide(cell, atp_threshold: float, max_atp_rate: float, cell_cycle_time: float) -> bool:
    """
    Determine if a cell should divide.

    Args:
        cell: Cell object
        atp_threshold: Minimum ATP rate ratio for division
        max_atp_rate: Maximum ATP rate for normalization
        cell_cycle_time: Minimum age for division

    Returns:
        True if cell should divide, False otherwise
    """
 
    # Check phenotype
    if cell.state.phenotype != 'Proliferation':
        return False

    # Check ATP rate
    # metabolic_state = cell.state.metabolic_state
    # if not metabolic_state:
    #     return False

    # atp_rate = metabolic_state.get('atp_rate', 0.0)
    # atp_rate_normalized = atp_rate / max_atp_rate if max_atp_rate > 0 else 0.0

    # if atp_rate_normalized <= atp_threshold:
    #     return False

    return True


def _perform_divisions(population, cells_to_divide, cell_radius: float, config,
                       context: Dict[str, Any] = None, dimensions: int = 3):
    """
    Perform cell divisions by creating daughter cells.

    Args:
        population: Population object
        cells_to_divide: List of (cell_id, cell) tuples
        cell_radius: Cell radius for placement
        config: Configuration object
        context: Workflow context (for gene networks)
        dimensions: Simulation dimensions (2 or 3)
    """
    new_cells = {}
    updated_cells = {}
    failed_divisions = 0

    # Get gene networks from context if available
    gene_networks = context.get('gene_networks', {}) if context else {}

    # Build spatial map of occupied positions for collision detection
    occupied_positions = {cell.state.position for cell in population.state.cells.values()}

    # Get domain bounds from config
    domain_bounds = _get_domain_bounds(config)

    growth_arrest_blocked = 0

    for cell_id, parent_cell in cells_to_divide:
        # Try to find a valid neighbour position for the daughter cell
        daughter_position = _find_daughter_position(
            parent_cell.state.position,
            occupied_positions,
            domain_bounds,
            dimensions
        )

        # =====================================================================
        # NO SPACE → NetLogo's -TURN-QUIESCENCE-3
        # Parent switches to Growth_Arrest with cycle = 3
        # =====================================================================
        if daughter_position is None:
            failed_divisions += 1
            growth_arrest_blocked += 1
            parent_cell.state = parent_cell.state.with_updates(
                phenotype='Growth_Arrest'
            )
            # Reset fate on the gene network object
            parent_gn = gene_networks.get(cell_id) if gene_networks else None
            if parent_gn is not None:
                parent_gn._fate = "Growth_Arrest"
                if hasattr(parent_gn, '_growth_arrest_cycle'):
                    parent_gn._growth_arrest_cycle = 3
            # Track in growth arrest counters
            ga_counters = context.get('growth_arrest_counters', {})
            ga_counters[cell_id] = 3
            context['growth_arrest_counters'] = ga_counters
            updated_cells[cell_id] = parent_cell
            continue

        # =====================================================================
        # SPACE FOUND → Division succeeds
        # =====================================================================

        # --- RESET PARENT (NetLogo's -RESET-FATE-145) ---
        # After successful division:
        #   my-fate = nobody
        #   my-cell-age = ticks  (age reset)
        #   my-cell-ran1 = random-float 1.0
        #   my-cell-ran2 = random-float 1.0
        parent_cell.state = parent_cell.state.with_updates(
            age=0.0,
            phenotype='Quiescent',
            division_count=parent_cell.state.division_count + 1
        )
        parent_gn = gene_networks.get(cell_id) if gene_networks else None
        if parent_gn is not None:
            parent_gn._fate = None
            parent_gn._cell_ran1 = random.random()
            parent_gn._cell_ran2 = random.random()
        updated_cells[cell_id] = parent_cell

        # --- CREATE DAUGHTER ---
        new_cell_id = _generate_cell_id(population)

        # Create a FRESH gene network for the daughter cell.
        # In NetLogo, daughter cells get a completely new gene network
        # (random gene states, new random thresholds, fate=None).
        daughter_gene_states = {}
        if gene_networks and cell_id in gene_networks:
            daughter_gn = _create_fresh_daughter_network(context)
            if daughter_gn is not None:
                gene_networks[new_cell_id] = daughter_gn
                daughter_gene_states = {
                    name: node.current_state
                    for name, node in daughter_gn.nodes.items()
                }

        daughter_cell = Cell(
            position=daughter_position,
            phenotype='Quiescent',
            custom_functions_module=parent_cell.custom_functions
        )

        daughter_cell.state = daughter_cell.state.with_updates(
            age=0.0,
            division_count=0,
            gene_states=daughter_gene_states if daughter_gene_states else parent_cell.state.gene_states.copy(),
            metabolic_state=parent_cell.state.metabolic_state.copy()
        )

        new_cells[new_cell_id] = daughter_cell

        # Mark position as occupied
        occupied_positions.add(daughter_position)

    # Update population with new and updated cells
    initial_count = len(population.state.cells)
    all_cells = {**population.state.cells, **updated_cells, **new_cells}
    population.state = population.state.with_updates(cells=all_cells)
    final_count = len(all_cells)

    # Log cell count change
    if final_count != initial_count or failed_divisions > 0:
        print(f"[DIVISION] Cell count: {initial_count} -> {final_count} "
              f"(+{len(new_cells)} daughters, "
              f"{failed_divisions} blocked → {growth_arrest_blocked} Growth_Arrest)")
    elif failed_divisions > 0:
        print(f"[DIVISION] No divisions completed ({failed_divisions} blocked → Growth_Arrest)")


def _create_fresh_daughter_network(context: Dict[str, Any]):
    """
    Create a fresh gene network for a daughter cell, matching NetLogo behaviour.

    In NetLogo (and the population benchmark), daughter cells start with:
    - Fate nodes → False
    - Gene nodes → random True/False
    - fate = None  (no fate assigned yet)
    - last_node = random input node
    - cell_ran1, cell_ran2 = new random values (cell-to-cell variability)
    - Input states applied (with probabilistic activation for GLUT1I/MCT1I)

    This mirrors ``Cell.reset(random_init=True)`` + ``Cell.set_input_states()``
    in gene_network_population_simulator.py.

    Args:
        context: Workflow context containing 'gene_network_config',
                 'gene_network_inputs', and optionally concentration parameters.

    Returns:
        A fully initialised HierarchicalBooleanNetwork, or None on failure.
    """
    FATE_NODE_NAMES = {'Apoptosis', 'Proliferation', 'Growth_Arrest', 'Necrosis'}

    gn_config = context.get('gene_network_config')
    if gn_config is None:
        return None

    random_init = context.get('random_initialization', True)
    fate_hierarchy = context.get('fate_hierarchy',
                                 ["Necrosis", "Apoptosis", "Growth_Arrest", "Proliferation"])
    input_states = context.get('gene_network_inputs', {})

    try:
        daughter_gn = HierarchicalBooleanNetwork(
            config=gn_config,
            fate_hierarchy=fate_hierarchy,
        )

        # Reset node states (benchmark: reset())
        for node in daughter_gn.nodes.values():
            if node.is_input:
                continue
            elif node.name in FATE_NODE_NAMES:
                node.current_state = False
                node.next_state = False
            else:
                state = random.choice([True, False]) if random_init else False
                node.current_state = state
                node.next_state = state

        # Build output links for graph walking
        from src.workflow.functions.gene_network.initialize_netlogo_gene_networks import (
            _build_output_links, _apply_input_states,
        )
        _build_output_links(daughter_gn)
        daughter_gn._output_links_built = True

        # New per-cell random thresholds
        daughter_gn._cell_ran1 = random.random()
        daughter_gn._cell_ran2 = random.random()

        # Graph walking start: random input node
        input_node_names = [n for n, nd in daughter_gn.nodes.items() if nd.is_input]
        if input_node_names:
            daughter_gn._last_node = random.choice(input_node_names)
        else:
            daughter_gn._last_node = random.choice(list(daughter_gn.nodes.keys()))

        daughter_gn._fate = None

        # Apply input states (with probabilistic activation)
        # Retrieve concentration values stored during initialization
        init_params = context.get('gene_network_init_params', {})
        MCT1I_conc = init_params.get('MCT1I_concentration', 0.0)
        GLUT1I_conc = init_params.get('GLUT1I_concentration', 0.0)
        _apply_input_states(
            daughter_gn, input_states,
            MCT1I_concentration=MCT1I_conc,
            GLUT1I_concentration=GLUT1I_conc,
        )

        return daughter_gn

    except Exception as e:
        print(f"[DIVISION] WARNING: Failed to create fresh daughter network: {e}")
        return None


def _find_daughter_position(parent_position, occupied_positions, domain_bounds,
                           dimensions: int = 3):
    """
    Find first available neighbour position on the integer grid around the parent.

    Uses context['dimensions'] to decide 2D (8 neighbours, x-y only) or
    3D (26 neighbours, x-y-z).  This is the single source of truth for
    whether the simulation is 2D or 3D -- never the tuple length of the
    parent position.

    Args:
        parent_position: Parent cell position (always a tuple of ints)
        occupied_positions: Set of currently occupied grid positions
        domain_bounds: Dict with 'xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax'
        dimensions: Simulation dimensions (2 or 3)

    Returns:
        First available (int tuple) position, or None if all spaces are taken
    """
    if dimensions == 2:
        # 2D: 8 neighbours in the x-y plane.  z is kept from parent.
        offsets_2d = [
            (-1, -1), (-1, 0), (-1, 1),
            ( 0, -1),          ( 0, 1),
            ( 1, -1), ( 1, 0), ( 1, 1),
        ]
        # Shuffle so we don't always prefer the same direction
        random.shuffle(offsets_2d)

        px, py = int(parent_position[0]), int(parent_position[1])
        pz = int(parent_position[2]) if len(parent_position) > 2 else 0

        for di, dj in offsets_2d:
            cx, cy = px + di, py + dj
            # Build candidate with same dimensionality as parent
            if len(parent_position) > 2:
                candidate = (cx, cy, pz)  # z unchanged in 2D sim
            else:
                candidate = (cx, cy)

            if candidate in occupied_positions:
                continue
            if not _is_within_bounds(candidate, domain_bounds):
                continue
            return candidate

    else:
        # 3D: 26 neighbours
        offsets_3d = []
        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                for dk in [-1, 0, 1]:
                    if di == 0 and dj == 0 and dk == 0:
                        continue
                    offsets_3d.append((di, dj, dk))
        random.shuffle(offsets_3d)

        px = int(parent_position[0])
        py = int(parent_position[1])
        pz = int(parent_position[2]) if len(parent_position) > 2 else 0

        for di, dj, dk in offsets_3d:
            candidate = (px + di, py + dj, pz + dk)
            if candidate in occupied_positions:
                continue
            if not _is_within_bounds(candidate, domain_bounds):
                continue
            return candidate

    return None  # Completely surrounded


def _is_within_bounds(position, domain_bounds) -> bool:
    """
    Check if a position is within domain bounds.

    Args:
        position: Position tuple (x, y) or (x, y, z)
        domain_bounds: Dict with 'xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax'

    Returns:
        True if within bounds
    """
    x, y = position[0], position[1]
    if not (domain_bounds['xmin'] <= x <= domain_bounds['xmax']):
        return False
    if not (domain_bounds['ymin'] <= y <= domain_bounds['ymax']):
        return False
    if len(position) > 2:
        z = position[2]
        if not (domain_bounds['zmin'] <= z <= domain_bounds['zmax']):
            return False
    return True


def _get_domain_bounds(config) -> Dict[str, int]:
    """
    Extract domain bounds from config.

    Returns:
        Dict with xmin, xmax, ymin, ymax, zmin, zmax
    """
    if config and hasattr(config, 'domain') and config.domain:
        domain = config.domain
        is_3d = hasattr(domain, 'nz') and domain.nz is not None
        # Use biological grid size based on cell_height
        cell_height_um = domain.cell_height.micrometers if hasattr(domain.cell_height, 'micrometers') else float(domain.cell_height)
        xmax = int(domain.size_x.micrometers / cell_height_um) - 1 if hasattr(domain.size_x, 'micrometers') else 39
        ymax = int(domain.size_y.micrometers / cell_height_um) - 1 if hasattr(domain.size_y, 'micrometers') else 39
        zmax = int(domain.size_z.micrometers / cell_height_um) - 1 if (is_3d and hasattr(domain.size_z, 'micrometers')) else 39
        return {
            'xmin': 0, 'xmax': xmax,
            'ymin': 0, 'ymax': ymax,
            'zmin': 0, 'zmax': zmax,
        }

    # Fallback: generous bounds
    return {
        'xmin': 0, 'xmax': 999,
        'ymin': 0, 'ymax': 999,
        'zmin': 0, 'zmax': 999,
    }


def _generate_cell_id(population):
    """Generate a unique cell ID (UUID string)."""
    import uuid
    return str(uuid.uuid4())


def _get_config_param(config, param_name: str, default_value):
    """Safely get a parameter from config with fallback to default."""
    if not config:
        return default_value

    if hasattr(config, 'custom_parameters'):
        custom_params = config.custom_parameters
        if isinstance(custom_params, dict) and param_name in custom_params:
            return custom_params[param_name]

    if hasattr(config, param_name):
        return getattr(config, param_name)
    elif isinstance(config, dict) and param_name in config:
        return config[param_name]

    return default_value

