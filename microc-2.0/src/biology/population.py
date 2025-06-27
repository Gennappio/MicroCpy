"""
Cell population management for MicroC 2.0

Provides spatial population management with immutable state tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
import numpy as np

from interfaces.base import ICellPopulation, CustomizableComponent
from interfaces.hooks import get_hook_manager
from .cell import Cell, CellState
from .gene_network import BooleanNetwork

@dataclass
class PopulationState:
    """Immutable population state representation"""
    cells: Dict[str, Cell] = field(default_factory=dict)
    spatial_grid: Dict[Tuple[int, int], str] = field(default_factory=dict)  # position -> cell_id
    total_cells: int = 0
    generation_count: int = 0
    
    def with_updates(self, **kwargs) -> 'PopulationState':
        """Create new PopulationState with updates (immutable pattern)"""
        updates = {
            'cells': self.cells.copy(),
            'spatial_grid': self.spatial_grid.copy(),
            'total_cells': self.total_cells,
            'generation_count': self.generation_count
        }
        updates.update(kwargs)
        return PopulationState(**updates)

class CellPopulation(ICellPopulation, CustomizableComponent):
    """
    Spatial cell population management with immutable state tracking
    
    Manages cell positions, division, death, and migration on a spatial grid.
    All behaviors can be customized via the hook system.
    """
    
    def __init__(self, grid_size: Tuple[int, int], gene_network: Optional[BooleanNetwork] = None,
                 custom_functions_module=None, config=None):
        super().__init__(custom_functions_module)

        self.grid_size = grid_size
        self.gene_network = gene_network or BooleanNetwork()
        self.hook_manager = get_hook_manager()
        self.config = config  # Store config for threshold calculations
        
        # Initialize empty population state
        self.state = PopulationState()

        # Default parameters
        self.default_params = {
            'max_cells_per_position': 1,  # Spatial exclusion
            'migration_probability': 0.1,
            'division_success_rate': 0.8,
            'max_population_size': grid_size[0] * grid_size[1] * 2  # Prevent runaway growth
        }

    def initialize_with_custom_placement(self, simulation_params: Optional[Dict] = None) -> int:
        """Initialize population using custom placement function"""
        simulation_params = simulation_params or {}

        try:
            # Try custom placement function
            cell_placements = self.hook_manager.call_hook(
                "custom_initialize_cell_placement",
                grid_size=self.grid_size,
                simulation_params=simulation_params
            )

            # Add cells according to custom placement
            cells_added = 0
            for placement in cell_placements:
                if isinstance(placement, dict):
                    position = placement.get('position')
                    phenotype = placement.get('phenotype', 'normal')
                elif isinstance(placement, tuple) and len(placement) == 2:
                    # Simple (position, phenotype) tuple
                    position, phenotype = placement
                elif isinstance(placement, tuple) and len(placement) == 3:
                    # (x, y, phenotype) tuple
                    x, y, phenotype = placement
                    position = (x, y)
                else:
                    continue  # Skip invalid placements

                if self.add_cell(position, phenotype):
                    cells_added += 1

            return cells_added

        except NotImplementedError:
            # Fall back to default single cell at center
            center_x = self.grid_size[0] // 2
            center_y = self.grid_size[1] // 2
            if self.add_cell((center_x, center_y), "normal"):
                return 1
            return 0
    
    def add_cell(self, position: Tuple[int, int], phenotype: str = "normal") -> bool:
        """Add cell at lattice position"""
        # Validate position
        if not self._is_valid_position(position):
            return False
        
        # Check if position is occupied
        if position in self.state.spatial_grid:
            return False  # Position occupied
        
        # Check population limit
        if self.state.total_cells >= self.default_params['max_population_size']:
            return False
        
        # Create new cell
        cell = Cell(position=position, phenotype=phenotype, 
                   custom_functions_module=self.custom_functions)
        
        # Update state
        new_cells = self.state.cells.copy()
        new_cells[cell.state.id] = cell
        
        new_spatial_grid = self.state.spatial_grid.copy()
        new_spatial_grid[position] = cell.state.id
        
        self.state = self.state.with_updates(
            cells=new_cells,
            spatial_grid=new_spatial_grid,
            total_cells=self.state.total_cells + 1
        )
        
        return True
    
    def attempt_division(self, parent_id: str) -> bool:
        """Attempt to divide a cell"""
        if parent_id not in self.state.cells:
            return False
        
        parent_cell = self.state.cells[parent_id]
        
        # Check if parent should divide
        if not parent_cell.should_divide(self.config):
            return False
        
        # Try custom division direction selection
        try:
            target_position = self.hook_manager.call_hook(
                "custom_select_division_direction",
                parent_position=parent_cell.state.position,
                available_positions=self._get_available_neighbors(parent_cell.state.position)
            )
        except NotImplementedError:
            # Fall back to default implementation
            target_position = self._default_select_division_direction(parent_cell.state.position)
        
        if target_position is None:
            return False  # No space available
        
        # Check division success rate
        if np.random.random() > self.default_params['division_success_rate']:
            return False
        
        # Create daughter cell
        daughter_cell = parent_cell.divide()
        daughter_cell.move_to(target_position)
        
        # Update state
        new_cells = self.state.cells.copy()
        new_cells[daughter_cell.state.id] = daughter_cell
        new_cells[parent_id] = parent_cell  # Update parent
        
        new_spatial_grid = self.state.spatial_grid.copy()
        new_spatial_grid[target_position] = daughter_cell.state.id
        
        self.state = self.state.with_updates(
            cells=new_cells,
            spatial_grid=new_spatial_grid,
            total_cells=self.state.total_cells + 1,
            generation_count=self.state.generation_count + 1
        )
        
        return True
    
    def _default_select_division_direction(self, parent_position: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Default division direction selection"""
        available_positions = self._get_available_neighbors(parent_position)
        if not available_positions:
            return None
        
        # Random selection from available positions
        return available_positions[np.random.randint(len(available_positions))]
    
    def _get_available_neighbors(self, position: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get available neighboring positions"""
        x, y = position
        neighbors = [
            (x-1, y), (x+1, y), (x, y-1), (x, y+1),  # Von Neumann neighborhood
            (x-1, y-1), (x-1, y+1), (x+1, y-1), (x+1, y+1)  # Moore neighborhood
        ]
        
        available = []
        for pos in neighbors:
            if self._is_valid_position(pos) and pos not in self.state.spatial_grid:
                available.append(pos)
        
        return available
    
    def _is_valid_position(self, position: Tuple[int, int]) -> bool:
        """Check if position is within grid bounds"""
        x, y = position
        return 0 <= x < self.grid_size[0] and 0 <= y < self.grid_size[1]
    
    def remove_dead_cells(self) -> List[str]:
        """Remove dead cells and return their IDs"""
        dead_cell_ids = []

        # Debug: Track cell death and population changes
        if not hasattr(self, '_death_debug_count'):
            self._death_debug_count = 0

        # Always print current cell count
        current_count = len(self.state.cells)
        if not hasattr(self, '_last_cell_count'):
            self._last_cell_count = current_count

        if current_count != self._last_cell_count:
            print(f"📊 CELL COUNT CHANGE: {self._last_cell_count} → {current_count}")
            self._last_cell_count = current_count

        # Find dead cells
        for cell_id, cell in self.state.cells.items():
            # Get local environment for death check
            local_env = self._get_local_environment(cell.state.position)

            # Check death condition with detailed logging
            should_die = cell.should_die(local_env, self.config)

            if should_die:
                dead_cell_ids.append(cell_id)
                # Debug ALL deaths
                print(f"💀 DEATH: Cell {cell_id[:8]} at {cell.state.position}")
                print(f"   O2={local_env.get('oxygen', 'N/A'):.3f}, Glc={local_env.get('glucose', 'N/A'):.1f}, Age={cell.state.age}, Pheno={cell.state.phenotype}")
                if hasattr(cell, 'state') and hasattr(cell.state, 'gene_states'):
                    gs = cell.state.gene_states
                    print(f"   Genes: Necr={gs.get('Necrosis', 'N/A')}, Apop={gs.get('Apoptosis', 'N/A')}")
                self._death_debug_count += 1

        if not dead_cell_ids:
            # Print cell count periodically to track population
            if not hasattr(self, '_cell_count_debug_counter'):
                self._cell_count_debug_counter = 0
            self._cell_count_debug_counter += 1
            if self._cell_count_debug_counter % 10 == 1:  # Every 10 calls
                print(f"📊 Population stable: {len(self.state.cells)} cells")
            return []

        # Debug: Report cell deaths
        print(f"💀 Removing {len(dead_cell_ids)} dead cells. Remaining: {len(self.state.cells) - len(dead_cell_ids)}")

        # Remove dead cells
        new_cells = self.state.cells.copy()
        new_spatial_grid = self.state.spatial_grid.copy()

        for cell_id in dead_cell_ids:
            cell = new_cells[cell_id]
            del new_cells[cell_id]
            del new_spatial_grid[cell.state.position]

        self.state = self.state.with_updates(
            cells=new_cells,
            spatial_grid=new_spatial_grid,
            total_cells=self.state.total_cells - len(dead_cell_ids)
        )

        return dead_cell_ids

    def _calculate_gene_inputs(self, local_env: Dict[str, float]) -> Dict[str, bool]:
        """
        Calculate gene network inputs based ONLY on configuration.
        NO hardcoded fallbacks - proper configuration is required.
        """
        if not self.config:
            raise ValueError("Configuration is required for gene input calculation - no hardcoded defaults allowed")

        if not self.config.associations:
            raise ValueError("Association configuration is required - no hardcoded associations allowed")

        gene_inputs = {}

        # Process each association (substance -> gene_input mapping)
        for substance_name, gene_input_name in self.config.associations.items():
            # Get substance concentration from local environment
            substance_conc = local_env.get(substance_name.lower())

            if substance_conc is None:
                raise ValueError(f"Substance '{substance_name}' not found in local environment - check configuration")

            # Get threshold configuration for this gene input
            if gene_input_name not in self.config.thresholds:
                raise ValueError(f"Threshold for '{gene_input_name}' not configured - no hardcoded thresholds allowed")

            threshold_config = self.config.thresholds[gene_input_name]
            # Gene input is TRUE if concentration exceeds threshold
            gene_inputs[gene_input_name] = substance_conc > threshold_config.threshold

            # Compact debug for gene inputs (only first call)
            if not hasattr(self, '_gene_input_debug_shown'):
                print(f"🔍 Gene thresholds: {substance_name}>{threshold_config.threshold}={gene_inputs[gene_input_name]}")
                self._gene_input_debug_shown = True

        # Handle composite gene inputs using configuration
        if hasattr(self.config, 'composite_genes') and self.config.composite_genes: #TODO: revise
            for composite_config in self.config.composite_genes:
                gene_inputs[composite_config.name] = self._evaluate_composite_logic(
                    composite_config, gene_inputs
                )

        return gene_inputs

    def _evaluate_composite_logic(self, composite_config, gene_inputs: Dict[str, bool]) -> bool:
        """
        Evaluate composite gene logic based on configuration.
        NO hardcoded logic - all logic comes from config.
        """
        logic = composite_config.logic.upper()
        inputs = composite_config.inputs

        # Validate that all required inputs exist
        for input_name in inputs:
            if input_name not in gene_inputs:
                raise ValueError(f"Composite gene '{composite_config.name}' requires input '{input_name}' which is not available")

        # Evaluate logic based on configuration
        if logic == "AND":
            return all(gene_inputs[input_name] for input_name in inputs)
        elif logic == "OR":
            return any(gene_inputs[input_name] for input_name in inputs)
        elif logic == "NOT" and len(inputs) == 1:
            return not gene_inputs[inputs[0]]
        elif logic == "XOR" and len(inputs) == 2:
            return gene_inputs[inputs[0]] != gene_inputs[inputs[1]]
        else:
            raise ValueError(f"Unsupported composite logic '{logic}' for gene '{composite_config.name}'. Supported: AND, OR, NOT, XOR")

    def _get_local_environment(self, position: Tuple[int, int]) -> Dict[str, float]:
        """
        Get local environment at position using ONLY configuration values.
        NO hardcoded fallbacks - configuration is required.
        """
        if not self.config:
            raise ValueError("Configuration is required for local environment - no hardcoded defaults allowed")

        local_env = {}

        # Use configured initial values - NO fallbacks
        if not self.config.substances:
            raise ValueError("Substance configuration is required - no hardcoded substance defaults allowed")

        for substance_name, substance_config in self.config.substances.items():
            local_env[substance_name.lower()] = substance_config.initial_value.value

        # Add environmental factors from config - NO fallbacks
        if not hasattr(self.config, 'environment') or not self.config.environment:
            raise ValueError("Environment configuration is required - no hardcoded environment defaults allowed")

        local_env['ph'] = self.config.environment.ph

        return local_env
    
    def get_substance_reactions(self) -> Dict[Tuple[float, float], Dict[str, float]]:
        """Get all cell reactions for substances"""
       
        reactions = {}

        for cell in self.state.cells.values():
            # Get local environment
            local_env = self._get_local_environment(cell.state.position)

            # Use cell's metabolism calculation (which handles custom hooks internally)
            metabolism = cell.calculate_metabolism(local_env, self.config)

            # Convert grid position to physical coordinates (would use mesh manager)
            # For now, use grid coordinates as physical coordinates
            physical_pos = (float(cell.state.position[0]), float(cell.state.position[1]))

            reactions[physical_pos] = metabolism

        return reactions
    
    def update_cells(self, dt: float, substance_concentrations: Optional[Dict[str, Dict[Tuple[int, int], float]]] = None):
        """
        DEPRECATED: Use update_intracellular_processes() for multi-timescale simulation.
        This method is kept for backward compatibility but updates everything every step.
        """
        # For backward compatibility, update all processes
        self.update_intracellular_processes(dt, substance_concentrations)
        self.update_gene_networks(substance_concentrations)
        self.update_phenotypes()
        self.remove_dead_cells()

    def update_intracellular_processes(self, dt: float, substance_concentrations: Optional[Dict[str, Dict[Tuple[int, int], float]]] = None):
        """
        Update intracellular processes: aging, metabolism, division, death.
        Should be called every intracellular_step.
        """
        substance_concentrations = substance_concentrations or {}
        updated_cells = {}

        for cell_id, cell in self.state.cells.items():
            # Age the cell
            cell.age(dt)

            # Update cell metabolism and internal state
            # (This could include ATP production, protein synthesis, etc.)

            updated_cells[cell_id] = cell

        # Update state
        self.state = self.state.with_updates(cells=updated_cells)

    def update_gene_networks(self, substance_concentrations: Optional[Dict[str, Dict[Tuple[int, int], float]]] = None):
        """
        Update gene networks based on current environment.
        Should be called every intracellular_step (genes respond quickly to environment).
        """
        substance_concentrations = substance_concentrations or {}
        updated_cells = {}

        for cell_id, cell in self.state.cells.items():
            # Get local environment
            local_env = self._get_local_environment(cell.state.position)

            # Update substance concentrations IF PROVIDED
            for substance_name, conc_field in substance_concentrations.items():
                if cell.state.position in conc_field:
                    # Update both capitalized and lowercase keys to ensure consistency
                    local_env[substance_name.lower()] = conc_field[cell.state.position]  # lowercase for gene inputs
                    local_env[substance_name] = conc_field[cell.state.position]  # capitalized for compatibility

            # RESET gene network to ensure clean state for each cell
            # Use NetLogo-style random initialization if configured
            random_init = getattr(self.config.gene_network, 'random_initialization', False)
            self.gene_network.reset(random_init=random_init)

            # Update gene network using configuration-based thresholds
            gene_inputs = self._calculate_gene_inputs(local_env)
            self.gene_network.set_input_states(gene_inputs)

            # Get propagation steps from gene network configuration
            if not (self.config.gene_network and hasattr(self.config.gene_network, 'propagation_steps')):
                raise ValueError("gene_network.propagation_steps must be configured")

            steps = self.config.gene_network.propagation_steps

            gene_states = self.gene_network.step(steps)

            # Collect ATP statistics for all cells
            if not hasattr(self, '_atp_stats'):
                self._atp_stats = {
                    'total_cells': 0,
                    'mito_only': 0,
                    'glyco_only': 0,
                    'both_atp': 0,
                    'no_atp': 0,
                    'atp_production_rate_true': 0
                }

            # Get all gene network states for ATP analysis
            all_states = self.gene_network.get_all_states()
            atp_rate = all_states.get('ATP_Production_Rate', False)
            mito_atp = all_states.get('mitoATP', False)
            glyco_atp = all_states.get('glycoATP', False)

            # Update ATP statistics
            self._atp_stats['total_cells'] += 1
            if atp_rate:
                self._atp_stats['atp_production_rate_true'] += 1

            if mito_atp and glyco_atp:
                self._atp_stats['both_atp'] += 1
            elif mito_atp and not glyco_atp:
                self._atp_stats['mito_only'] += 1
            elif not mito_atp and glyco_atp:
                self._atp_stats['glyco_only'] += 1
            else:
                self._atp_stats['no_atp'] += 1

            # Debug output for first few cells
            if not hasattr(self, '_gene_output_debug_count'):
                self._gene_output_debug_count = 0
            self._gene_output_debug_count += 1

            # Debug apoptosis cases specifically
            apoptosis = gene_states.get('Apoptosis', False)
            if apoptosis:
                pos = cell.state.position
                oxygen = local_env.get('oxygen', 0.0)
                glucose = local_env.get('glucose', 0.0)
                print(f"🚨 APOPTOSIS CELL at {pos}: O2={oxygen:.3f}, Gluc={glucose:.3f}")
                print(f"   Gene inputs: {gene_inputs}")

                # Debug apoptosis pathway components
                bcl2 = gene_states.get('BCL2', False)
                erk = gene_states.get('ERK', False)
                foxo3 = gene_states.get('FOXO3', False)
                p53 = gene_states.get('p53', False)
                print(f"   Apoptosis logic: !BCL2({bcl2}) & !ERK({erk}) & FOXO3({foxo3}) & p53({p53})")
                print(f"   = !{bcl2} & !{erk} & {foxo3} & {p53} = {not bcl2 and not erk and foxo3 and p53}")

                # Debug what's driving p53 and FOXO3
                dna_damage = gene_states.get('DNA_damage', False)
                atm = gene_states.get('ATM', False)
                growth_inhibitor = gene_inputs.get('Growth_Inhibitor', False)
                print(f"   p53 drivers: DNA_damage={dna_damage}, ATM={atm}")
                print(f"   FOXO3 drivers: Growth_Inhibitor={growth_inhibitor}")

                # Debug what's blocking BCL2 and ERK (survival signals)
                akt = gene_states.get('AKT', False)
                pi3k = gene_states.get('PI3K', False)
                egfr = gene_states.get('EGFR', False)
                fgfr = gene_states.get('FGFR', False)
                cmet = gene_states.get('cMET', False)
                print(f"   Survival signals: AKT={akt}, PI3K={pi3k}, EGFR={egfr}, FGFR={fgfr}, cMET={cmet}")

                # Debug the apoptosis pathway in detail
                print(f"   Growth factor inputs: FGFR_stimulus={gene_inputs.get('FGFR_stimulus', False)}, EGFR_stimulus={gene_inputs.get('EGFR_stimulus', False)}, cMET_stimulus={gene_inputs.get('cMET_stimulus', False)}")

                # Test apoptosis function directly
                apoptosis_node = self.gene_network.nodes.get('Apoptosis')
                if apoptosis_node and apoptosis_node.update_function:
                    test_inputs = {'BCL2': bcl2, 'ERK': erk, 'FOXO3': foxo3, 'p53': p53}
                    direct_result = apoptosis_node.update_function(test_inputs)
                    print(f"   Apoptosis direct test: {direct_result}, actual state: {apoptosis}")

                # Only show first few apoptosis cases to avoid spam
                if not hasattr(self, '_apoptosis_debug_count'):
                    self._apoptosis_debug_count = 0
                self._apoptosis_debug_count += 1
                if self._apoptosis_debug_count >= 3:
                    print(f"   ... (showing only first 3 apoptosis cases)")
                    return  # Stop showing more

                # Debug ATP production for this apoptotic cell
                atp_rate = gene_states.get('ATP_Production_Rate', False)
                mito_atp = gene_states.get('mitoATP', False)
                glyco_atp = gene_states.get('glycoATP', False)
                print(f"   ATP status: ATP_Rate={atp_rate}, mitoATP={mito_atp}, glycoATP={glyco_atp}")

            # Debug ATP gene outputs for first cell
            elif self._gene_output_debug_count == 1:
                atp_rate = gene_states.get('ATP_Production_Rate', False)
                mito_atp = gene_states.get('mitoATP', False)
                glyco_atp = gene_states.get('glycoATP', False)
                print(f"🔍 ATP Gene outputs: ATP_Rate={atp_rate}, mitoATP={mito_atp}, glycoATP={glyco_atp}")
                print(f"   Environmental: Oxygen_supply={gene_inputs.get('Oxygen_supply', False)}, Glucose_supply={gene_inputs.get('Glucose_supply', False)}")

            # Store gene states in cell for phenotype update (FIXED INDENTATION)
            cell._cached_gene_states = gene_states
            cell._cached_local_env = local_env

            updated_cells[cell_id] = cell

        # Print ATP statistics summary after processing all cells (only at status_print_interval)
        if hasattr(self, '_atp_stats') and self._atp_stats['total_cells'] == len(self.state.cells):
            # Store stats for potential printing
            self._current_atp_stats = self._atp_stats.copy()
            # Reset stats for next time step
            self._atp_stats = {
                'total_cells': 0,
                'mito_only': 0,
                'glyco_only': 0,
                'both_atp': 0,
                'no_atp': 0,
                'atp_production_rate_true': 0
            }


        # Update state
        self.state = self.state.with_updates(cells=updated_cells)

    def print_atp_statistics(self):
        """Print ATP statistics - called only at status_print_interval"""
        if hasattr(self, '_current_atp_stats'):
            stats = self._current_atp_stats
            total = stats['total_cells']

            # Avoid division by zero
            if total == 0:
                print(f"\n📊 ATP PRODUCTION STATISTICS: No cells to analyze")
                return

            print(f"\n📊 ATP PRODUCTION STATISTICS (Total cells: {total}):")
            print(f"   🔋 ATP_Production_Rate=TRUE: {stats['atp_production_rate_true']} cells ({stats['atp_production_rate_true']/total*100:.1f}%)")
            print(f"   ⚡ mitoATP only: {stats['mito_only']} cells ({stats['mito_only']/total*100:.1f}%)")
            print(f"   🍯 glycoATP only: {stats['glyco_only']} cells ({stats['glyco_only']/total*100:.1f}%)")
            print(f"   🚀 Both mitoATP & glycoATP: {stats['both_atp']} cells ({stats['both_atp']/total*100:.1f}%)")
            print(f"   💀 No ATP production: {stats['no_atp']} cells ({stats['no_atp']/total*100:.1f}%)")
            print()

    def update_phenotypes(self):
        """
        Update cell phenotypes based on cached gene states.
        Should be called every intracellular_step (phenotype changes follow gene expression).
        """
        updated_cells = {}

        # Compact phenotype tracking
        if not hasattr(self, '_phenotype_debug_count'):
            self._phenotype_debug_count = 0

        phenotype_changes = {}
        for cell_id, cell in self.state.cells.items():
            # Use cached gene states and environment from gene network update
            if hasattr(cell, '_cached_gene_states') and hasattr(cell, '_cached_local_env'):
                old_phenotype = cell.state.phenotype
                new_phenotype = cell.update_phenotype(cell._cached_local_env, cell._cached_gene_states)

                # Track phenotype changes compactly
                if old_phenotype != new_phenotype:
                    change_key = f"{old_phenotype}→{new_phenotype}"
                    phenotype_changes[change_key] = phenotype_changes.get(change_key, 0) + 1

                # Clean up cache
                delattr(cell, '_cached_gene_states')
                delattr(cell, '_cached_local_env')

            updated_cells[cell_id] = cell

        # Print compact phenotype summary
        if phenotype_changes:
            changes_str = ", ".join([f"{k}:{v}" for k, v in phenotype_changes.items()])
            print(f"🧬 Phenotype changes: {changes_str}")

        # Update state
        self.state = self.state.with_updates(cells=updated_cells)

    def update_intercellular_processes(self):
        """
        Update intercellular processes: migration, cell-cell interactions, signaling.
        Should be called every intercellular_step (slower than intracellular processes).
        """
        # Attempt cell migration
        migrations = self.attempt_migration()

        # Cell division attempts (intercellular because it requires space)
        divisions = self.attempt_divisions()

        # Cell-cell signaling (if implemented)
        # self.update_cell_signaling()

        return {
            'migrations': migrations,
            'divisions': divisions
        }

    def attempt_divisions(self) -> int:
        """Attempt cell division for cells that are ready"""
        divisions = 0

        # Get cells that might divide
        dividing_cells = [cell for cell in self.state.cells.values()
                         if cell.should_divide(self.config)]

        for cell in dividing_cells:
            if self.attempt_division(cell.state.id):
                divisions += 1

        return divisions

    def attempt_migration(self) -> int:
        pass # TODO: Implement migration
        """Attempt migration for cells that can move"""
        migrations = 0
        
        # Get list of cells that might migrate
        mobile_cells = [cell for cell in self.state.cells.values() 
                       if cell.state.phenotype in ["normal", "hypoxic"]]  # Some phenotypes are mobile
        
        new_spatial_grid = self.state.spatial_grid.copy()
        updated_cells = self.state.cells.copy()
        
        for cell in mobile_cells:
            # Try custom migration probability
            try:
                migration_prob = self.hook_manager.call_hook(
                    "custom_calculate_migration_probability",
                    cell_state=cell.state.__dict__,
                    local_environment=self._get_local_environment(cell.state.position),
                    target_position=None  # Would be calculated for each neighbor
                )
            except NotImplementedError:
                migration_prob = self.default_params['migration_probability']
            
            if np.random.random() < migration_prob:
                # Find available neighbors
                available_positions = self._get_available_neighbors(cell.state.position)
                
                if available_positions:
                    # Select random target
                    target_position = available_positions[np.random.randint(len(available_positions))]
                    
                    # Move cell
                    old_position = cell.state.position
                    cell.move_to(target_position)
                    
                    # Update spatial grid
                    del new_spatial_grid[old_position]
                    new_spatial_grid[target_position] = cell.state.id
                    updated_cells[cell.state.id] = cell
                    
                    migrations += 1
        
        # Update state if any migrations occurred
        if migrations > 0:
            self.state = self.state.with_updates(
                cells=updated_cells,
                spatial_grid=new_spatial_grid
            )
        
        return migrations
    
    def get_population_statistics(self) -> Dict[str, any]:
        """Get population statistics"""
        if not self.state.cells:
            return {
                'total_cells': 0,
                'phenotype_counts': {},
                'average_age': 0.0,
                'generation_count': self.state.generation_count
            }
        
        phenotype_counts = {}
        total_age = 0.0
        
        for cell in self.state.cells.values():
            phenotype = cell.state.phenotype
            phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1
            total_age += cell.state.age
        
        return {
            'total_cells': self.state.total_cells,
            'phenotype_counts': phenotype_counts,
            'average_age': total_age / self.state.total_cells,
            'generation_count': self.state.generation_count,
            'grid_occupancy': len(self.state.spatial_grid) / (self.grid_size[0] * self.grid_size[1])
        }
    
    def get_cell_positions(self) -> List[Tuple[Tuple[int, int], str]]:
        """Get list of (position, phenotype) for all cells"""
        return [(cell.state.position, cell.state.phenotype)
                for cell in self.state.cells.values()]

    def get_cell_at_position(self, position: Tuple[int, int]):
        """Get cell at specific position, if any"""
        for cell in self.state.cells.values():
            if cell.state.position == position:
                return cell
        return None
    
    def get_state(self) -> PopulationState:
        """Get current population state (immutable)"""
        return self.state
    
    def __repr__(self) -> str:
        stats = self.get_population_statistics()
        return (f"CellPopulation(cells={stats['total_cells']}, "
                f"generations={stats['generation_count']}, "
                f"occupancy={stats['grid_occupancy']:.2%})")
