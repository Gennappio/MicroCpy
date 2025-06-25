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
        
        # Find dead cells
        for cell_id, cell in self.state.cells.items():
            # Get local environment for death check
            local_env = self._get_local_environment(cell.state.position)
            
            if cell.should_die(local_env, self.config):
                dead_cell_ids.append(cell_id)
        
        if not dead_cell_ids:
            return []
        
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

            # Debug output for first few cells
            if not hasattr(self, '_gene_input_debug_count'):
                self._gene_input_debug_count = 0
            self._gene_input_debug_count += 1

            if self._gene_input_debug_count <= 10:  # Show more debug info
                print(f"🔍 GENE INPUT DEBUG (call {self._gene_input_debug_count}):")
                print(f"   {substance_name} concentration: {substance_conc:.6f}")
                print(f"   {gene_input_name} threshold: {threshold_config.threshold}")
                print(f"   {gene_input_name} = {gene_inputs[gene_input_name]} ({substance_conc} > {threshold_config.threshold})")

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
            if not hasattr(self, '_substance_debug_count'):
                self._substance_debug_count = 0
            self._substance_debug_count += 1

            if self._substance_debug_count <= 3:
                print(f"🔍 SUBSTANCE CONCENTRATION DEBUG (cell {self._substance_debug_count}):")
                print(f"   Position: {cell.state.position}")
                print(f"   Initial local_env: {local_env}")
                print(f"   substance_concentrations keys: {list(substance_concentrations.keys())}")

            for substance_name, conc_field in substance_concentrations.items():
                if cell.state.position in conc_field:
                    # Update both capitalized and lowercase keys to ensure consistency
                    old_value = local_env.get(substance_name.lower(), 'NOT_FOUND')
                    local_env[substance_name.lower()] = conc_field[cell.state.position]  # lowercase for gene inputs
                    local_env[substance_name] = conc_field[cell.state.position]  # capitalized for compatibility
                    if self._substance_debug_count <= 3:
                        print(f"   Updated {substance_name.lower()}: {old_value} → {conc_field[cell.state.position]}")
                else:
                    if self._substance_debug_count <= 3:
                        print(f"   Position {cell.state.position} not found in {substance_name} field")

            if self._substance_debug_count <= 3:
                print(f"   Final local_env: {local_env}")

            # Update gene network using configuration-based thresholds
            gene_inputs = self._calculate_gene_inputs(local_env)
            self.gene_network.set_input_states(gene_inputs)

            # Get propagation steps from configuration - NO hardcoded values
            if self.config.gene_network and hasattr(self.config.gene_network, 'propagation_steps'):
                steps = self.config.gene_network.propagation_steps
            else:
                steps = self.config.gene_network_steps

            gene_states = self.gene_network.step(steps)

            # Debug output for first few cells
            if not hasattr(self, '_gene_output_debug_count'):
                self._gene_output_debug_count = 0
            self._gene_output_debug_count += 1

            if self._gene_output_debug_count <= 3:
                print(f"🔍 GENE NETWORK OUTPUT DEBUG (cell {self._gene_output_debug_count}):")
                print(f"   Position: {cell.state.position}")
                print(f"   Local environment: oxygen={local_env.get('oxygen', 'N/A'):.6f}, glucose={local_env.get('glucose', 'N/A'):.6f}")
                print(f"   Gene inputs: {gene_inputs}")
                print(f"   Gene outputs: {gene_states}")
                if 'mitoATP' in gene_states and 'glycoATP' in gene_states:
                    print(f"   → mitoATP: {gene_states['mitoATP']}, glycoATP: {gene_states['glycoATP']}")

            # Store gene states in cell for phenotype update
            cell._cached_gene_states = gene_states
            cell._cached_local_env = local_env

            updated_cells[cell_id] = cell

        # Update state
        self.state = self.state.with_updates(cells=updated_cells)

    def update_phenotypes(self):
        """
        Update cell phenotypes based on cached gene states.
        Should be called every intracellular_step (phenotype changes follow gene expression).
        """
        updated_cells = {}

        for cell_id, cell in self.state.cells.items():
            # Use cached gene states and environment from gene network update
            if hasattr(cell, '_cached_gene_states') and hasattr(cell, '_cached_local_env'):
                cell.update_phenotype(cell._cached_local_env, cell._cached_gene_states)
                # Clean up cache
                delattr(cell, '_cached_gene_states')
                delattr(cell, '_cached_local_env')

            updated_cells[cell_id] = cell

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
