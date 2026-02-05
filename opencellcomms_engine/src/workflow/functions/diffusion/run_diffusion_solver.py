"""
Run the diffusion solver to update substance concentrations.

This function solves the diffusion PDE with source/sink terms from cells
for all substances (Oxygen, Glucose, Lactate, H+, pH).

The diffusion equation is:
    ∂C/∂t = D∇²C + R(x,y,z)

Where:
- C is the concentration field
- D is the diffusion coefficient
- R(x,y,z) is the reaction term (cell consumption/production)

Users can customize this to implement different diffusion solvers or boundary conditions.

================================================================================
ARCHITECTURE: Context-Based Function Pattern
================================================================================

All workflow functions follow this pattern:

    def function_name(context: Dict[str, Any], user_param1=default1, ...):
        '''
        Args:
            context: The workflow execution context (see below)
            user_param1, ...: User-configurable parameters (shown in GUI)
        '''

The CONTEXT contains two logical sections:

1. CORE CONTEXT (read-mostly, provided by SimulationEngine):
   - population: Cell population object (may be None if no cells)
   - simulator: Diffusion simulator object (may be None if no diffusion)
   - config: Simulation configuration
   - dt: Time step
   - step: Current step number
   - time: Current simulation time
   - helpers: Helper functions from engine
   - substances: Configured substances (part of core context)

2. USER CONTEXT (mutable, for custom data):
   - results: Tracking results
   - simulation_params: User-defined simulation parameters
   - Custom keys added by user functions

WHY THIS PATTERN:
- Functions should access what they need from context, not receive everything as args
- Only USER-CONFIGURABLE parameters should be function arguments
- Core objects may be None - functions handle this gracefully
- Decouples functions from specific simulation components they may not need
- gene_network is NOT a dependency of diffusion (separation of concerns)

================================================================================
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from interfaces.base import ICellPopulation, ISubstanceSimulator


@register_function(
    display_name="Run Diffusion Solver",
    description="Solve diffusion PDE with optional cell reactions",
    category="DIFFUSION",
    # Only USER-CONFIGURABLE parameters are listed here
    # Core context items (simulator, population, etc.) are accessed from context
    parameters=[
        {
            "name": "max_iterations",
            "type": "INT",
            "description": "Maximum solver iterations",
            "default": 1000,
            "min_value": 1
        },
        {
            "name": "tolerance",
            "type": "FLOAT",
            "description": "Convergence tolerance",
            "default": 1e-6,
            "min_value": 0.0
        },
        {
            "name": "solver_type",
            "type": "STRING",
            "description": "Solver type",
            "default": "steady_state",
            "options": ["steady_state", "transient"]
        }
    ],
    # Explicitly specify inputs - only 'context' since we pull everything from there
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def run_diffusion_solver(
    context: Dict[str, Any],
    max_iterations: int = 1000,
    tolerance: float = 1e-6,
    solver_type: str = "steady_state",
    **kwargs
) -> None:
    """
    Run the diffusion solver to update substance concentrations.

    This function:
    1. Configures substances if not already configured (first run)
    2. Optionally collects reaction terms from cells (if population exists)
    3. Solves the PDE using FiPy
    4. Updates substance concentrations in the simulator

    Args:
        context: Workflow execution context containing:
            - simulator: Diffusion simulator (REQUIRED for this function)
            - population: Cell population (OPTIONAL - if None, runs pure diffusion)
            - config: Simulation configuration
            - substances: Substance definitions (from core context)
            - dt: Time step
        max_iterations: Maximum iterations for solver (user parameter)
        tolerance: Convergence tolerance for solver (user parameter)
        solver_type: Type of solver - "steady_state" or "transient" (user parameter)
        **kwargs: Additional parameters (e.g., substances list from parameter nodes)

    Returns:
        None (modifies simulator state in-place, updates context['substances'])

    Note:
        - gene_network is NOT used here (separation of concerns)
        - If you need gene network effects on diffusion, use a separate function
          to update cell states before calling this function
    """
    # =========================================================================
    # EXTRACT CORE CONTEXT ITEMS
    # These may be None in workflow-only mode or custom simulations
    # =========================================================================
    simulator: Optional[ISubstanceSimulator] = context.get('simulator')
    population: Optional[ICellPopulation] = context.get('population')  # May be None - that's OK
    config = context.get('config')
    dt = context.get('dt', 0.1)

    # =========================================================================
    # VALIDATE REQUIRED CORE ITEMS
    # Simulator is required for diffusion - log and exit if missing
    # =========================================================================
    if simulator is None:
        print("[run_diffusion_solver] No simulator in context - cannot run diffusion.")
        print("                       Ensure setup_domain() was called first.")
        return

    # =========================================================================
    # COLLECT SUBSTANCE DEFINITIONS
    # Substances can come from:
    # 1. kwargs (from connected parameter nodes)
    # 2. context['substances'] (from previous setup)
    # =========================================================================
    substances = _collect_substance_definitions(kwargs, context)

    # Configure substances if provided and not already configured
    if substances and config:
        if not hasattr(config, 'substances') or not config.substances:
            _configure_substances(config, simulator, substances)
            # Store in context for other functions to access
            context['substances'] = config.substances
    elif substances and not config:
        # Workflow-only mode without full config - store in context
        print("[run_diffusion_solver] No config object - storing substances in context only")
        context['substances'] = {s['name']: s for s in substances}

    # =========================================================================
    # CONFIGURE SOLVER PARAMETERS
    # =========================================================================
    if hasattr(simulator, 'set_solver_params'):
        simulator.set_solver_params(
            max_iterations=max_iterations,
            tolerance=tolerance,
            solver_type=solver_type
        )

    # =========================================================================
    # GET CURRENT SUBSTANCE CONCENTRATIONS
    # =========================================================================
    try:
        substance_concentrations = simulator.get_substance_concentrations()
    except Exception as e:
        print(f"[run_diffusion_solver] Failed to get substance concentrations: {e}")
        return

    # =========================================================================
    # COLLECT REACTION TERMS FROM CELLS (OPTIONAL)
    # If no population, run pure diffusion without cell reactions
    # =========================================================================
    position_reactions = None

    if population is not None:
        # We have cells - collect their reaction terms
        position_reactions = _collect_cell_reactions(
            population, config, substance_concentrations
        )
    else:
        # No cells - pure diffusion mode
        print("[run_diffusion_solver] No population - running pure diffusion (no cell reactions)")
        position_reactions = {}

    # =========================================================================
    # RUN DIFFUSION SOLVER
    # =========================================================================
    try:
        simulator.update(position_reactions)
    except Exception as e:
        print(f"[run_diffusion_solver] Solver failed: {e}")
        raise

    # Log population count at end
    if population is not None:
        final_count = len(population.state.cells)
        print(f"[DIFFUSION-END] Population count: {final_count} cells")


def _collect_substance_definitions(kwargs: Dict[str, Any], context: Dict[str, Any]) -> list:
    """
    Collect substance definitions from kwargs and context.

    Substances can come from:
    1. kwargs['substances'] - list passed from parameter nodes
    2. kwargs individual fields (name, diffusion_coeff, etc.) - single substance
    3. context['substances'] - already configured substances

    Args:
        kwargs: Dictionary of user parameters (from connected nodes)
        context: Workflow execution context

    Returns:
        List of substance definitions
    """
    substances = []

    # Priority 1: Explicit 'substances' list in kwargs
    if 'substances' in kwargs:
        return kwargs['substances']

    # Priority 2: Individual substance parameters in kwargs
    if 'name' in kwargs:
        substances.append({
            'name': kwargs.get('name'),
            'diffusion_coeff': kwargs.get('diffusion_coeff', 1e-10),
            'production_rate': kwargs.get('production_rate', 0.0),
            'uptake_rate': kwargs.get('uptake_rate', 0.0),
            'initial_value': kwargs.get('initial_value', 0.0),
            'boundary_value': kwargs.get('boundary_value', 0.0),
            'boundary_type': kwargs.get('boundary_type', 'fixed'),
            'unit': kwargs.get('unit', 'mM'),
        })
        return substances

    # Priority 3: Already in context (from previous setup functions)
    ctx_substances = context.get('substances')
    if ctx_substances:
        if isinstance(ctx_substances, dict):
            # Convert from dict to list format
            return list(ctx_substances.values())
        return ctx_substances

    return substances


def _configure_substances(config, simulator, substances, reinitialize_simulator=True):
    """
    Configure substances in the simulator.

    Note: gene_network_input is stored in associations but NOT processed here.
    Gene network effects are handled by separate functions (separation of concerns).

    Args:
        config: Configuration object
        simulator: Diffusion simulator
        substances: List of substance definitions (each with name, diffusion_coeff, etc.)
        reinitialize_simulator: Whether to reinitialize the simulator after adding substances.
    """
    from src.config.config import SubstanceConfig
    from src.core.units import Concentration

    # Initialize substances dict if not exists
    if not hasattr(config, 'substances'):
        config.substances = {}

    # Initialize associations dict (for gene network, handled elsewhere)
    if not hasattr(config, 'associations'):
        config.associations = {}

    for sub_def in substances:
        # Handle both dict and SubstanceConfig objects
        if hasattr(sub_def, 'name'):
            # Already a SubstanceConfig
            config.substances[sub_def.name] = sub_def
            print(f"   [+] Configured substance: {sub_def.name}")
            continue

        name = sub_def['name']

        # Create SubstanceConfig with all required parameters
        sub_config = SubstanceConfig(
            name=name,
            diffusion_coeff=sub_def.get('diffusion_coeff', 1e-10),
            production_rate=sub_def.get('production_rate', 0.0),
            uptake_rate=sub_def.get('uptake_rate', 0.0),
            initial_value=Concentration(sub_def.get('initial_value', 0.0), sub_def.get('unit', 'mM')),
            boundary_value=Concentration(sub_def.get('boundary_value', 0.0), sub_def.get('unit', 'mM')),
            boundary_type=sub_def.get('boundary_type', 'fixed')
        )

        config.substances[name] = sub_config
        print(f"   [+] Configured substance: {name} (D={sub_config.diffusion_coeff:.2e})")

    # Reinitialize simulator with ALL substances (only if requested)
    if reinitialize_simulator and hasattr(simulator, 'initialize_substances'):
        simulator.initialize_substances(config.substances)
        print(f"   [+] Initialized {len(config.substances)} substances in diffusion solver")


def _collect_cell_reactions(population, config, substance_concentrations) -> Dict:
    """
    Collect reaction terms from cells (if available).

    This function abstracts the logic of getting cell reactions, supporting:
    1. CellPopulation.get_substance_reactions() - preferred method
    2. Local fallback implementation - for compatibility

    Args:
        population: Cell population object
        config: Configuration object (may be None)
        substance_concentrations: Current substance concentrations

    Returns:
        Dict of {position: {substance: rate}}
    """
    position_reactions = None

    # Check if we can use the population's built-in method
    can_use_population_reactions = (
        hasattr(population, "get_substance_reactions")
        and config is not None
        and hasattr(config, "environment")
        and getattr(config, "environment") is not None
    )

    if can_use_population_reactions:
        try:
            position_reactions = population.get_substance_reactions(substance_concentrations)
        except Exception as e:
            print(
                f"[run_diffusion_solver] Warning: get_substance_reactions failed, "
                f"using fallback: {e}"
            )

    if position_reactions is None:
        # Fallback to local implementation
        reaction_terms = _collect_reaction_terms(population, substance_concentrations)
        position_reactions = _convert_to_position_reactions(reaction_terms)

    return position_reactions


def _convert_to_position_reactions(reaction_terms):
    """
    Convert reaction terms from {substance: {position: rate}} to {position: {substance: rate}}.

    The MultiSubstanceSimulator.update() expects reactions organized by position.

    Args:
        reaction_terms: Dict of {substance_name: {position: rate}}

    Returns:
        Dict of {position: {substance_name: rate}}
    """
    position_reactions = {}

    for substance_name, position_rates in reaction_terms.items():
        for position, rate in position_rates.items():
            if position not in position_reactions:
                position_reactions[position] = {}
            position_reactions[position][substance_name] = rate

    return position_reactions


def _collect_reaction_terms(population, substance_concentrations):
    """
    Collect reaction terms (consumption/production rates) from all cells.

    For each substance, creates a grid of reaction rates based on cell
    metabolism at each position.

    Args:
        population: Population object with cells
        substance_concentrations: Dict of substance -> concentration grid

    Returns:
        Dict of substance_name -> reaction_grid
        Reaction rates are in mol/s/volume
    """
    reaction_terms = {}

    # Initialize reaction grids for each substance
    for substance_name in substance_concentrations.keys():
        reaction_terms[substance_name] = {}

    print(f"[DIFFUSION] Collecting reaction terms from {len(population.state.cells)} cells")
    print(f"[DIFFUSION] Substances: {list(substance_concentrations.keys())}")

    cells_with_metabolism = 0
    cells_without_metabolism = 0

    # Collect reactions from each cell
    for cell_id, cell in population.state.cells.items():
        position = cell.state.position

        # Get cell's metabolic state (calculated in update_metabolism)
        metabolic_state = cell.state.metabolic_state

        if not metabolic_state:
            cells_without_metabolism += 1
            if cells_without_metabolism <= 3:
                print(f"[DIFFUSION] Cell {cell_id} has NO metabolic_state (type={type(metabolic_state)})")
            continue

        cells_with_metabolism += 1
        if cells_with_metabolism <= 3:
            print(f"[DIFFUSION] Cell {cell_id} metabolic_state: {metabolic_state}")

        # Get local environment
        local_env = {}
        for substance_name, conc_grid in substance_concentrations.items():
            local_env[substance_name] = conc_grid.get(position, 0.0)

        # Build reactions from metabolic_state keys
        # (Skip calculate_cell_metabolism - use static rates from metabolic_state directly)
        reactions = {}

        # Standard keys (backward compatible)
        reactions['Oxygen'] = -metabolic_state.get('oxygen_consumption', 0.0)
        reactions['Glucose'] = -metabolic_state.get('glucose_consumption', 0.0)
        reactions['Lactate'] = metabolic_state.get('lactate_production', 0.0) - metabolic_state.get('lactate_consumption', 0.0)

        # Dynamic keys from SubstanceConfig: "{Substance}_consumption" and "{Substance}_production"
        for key, value in metabolic_state.items():
            if key.endswith('_consumption'):
                substance_name = key.replace('_consumption', '')
                if substance_name not in reactions:
                    reactions[substance_name] = 0.0
                reactions[substance_name] -= value  # Consumption is negative
            elif key.endswith('_production'):
                substance_name = key.replace('_production', '')
                if substance_name not in reactions:
                    reactions[substance_name] = 0.0
                reactions[substance_name] += value  # Production is positive

        # Log first cell's reactions for debugging
        if cells_with_metabolism <= 1:
            print(f"[DIFFUSION] Cell {cell_id} reactions built: {reactions}")

        # Add cell's reactions to the grid
        for substance_name, rate in reactions.items():
            if substance_name in reaction_terms:
                if position not in reaction_terms[substance_name]:
                    reaction_terms[substance_name][position] = 0.0
                reaction_terms[substance_name][position] += rate

    print(f"[DIFFUSION] Summary: {cells_with_metabolism} cells WITH metabolic_state, {cells_without_metabolism} cells WITHOUT")

    # Log total reaction rates per substance
    for substance_name, pos_rates in reaction_terms.items():
        total_rate = sum(pos_rates.values())
        if abs(total_rate) > 1e-30:
            print(f"[DIFFUSION] {substance_name} total reaction rate: {total_rate:.2e}")

    return reaction_terms

