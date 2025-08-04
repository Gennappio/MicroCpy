"""
Cell population management for MicroC 2.0

Provides spatial population management with immutable state tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set, Union
import numpy as np
import os
import time
from pathlib import Path

from interfaces.base import ICellPopulation
from .cell import Cell, CellState
from .gene_network import BooleanNetwork
import importlib.util

class PhenotypeLogger:
    """Detailed logging system for cell phenotype debugging"""

    def __init__(self, config=None, output_dir="logs"):
        self.config = config
        self.debug_enabled = getattr(config, 'debug_phenotype_detailed', False) if config else False
        self.simulation_status_logging = getattr(config, 'log_simulation_status', False) if config else False
        self.output_dir = Path(output_dir)
        self.log_file = None
        self.status_log_file = None
        self.step_count = 0

        if self.debug_enabled:
            self.output_dir.mkdir(exist_ok=True)
            log_filename = f"phenotype_debug_{int(time.time())}.log"
            self.log_file = self.output_dir / log_filename

            print(f"🐛 Creating debug log file: {self.log_file}")

            # Write header
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("=== PHENOTYPE DEBUG LOG ===\n")
                f.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")

        if self.simulation_status_logging:
            self.output_dir.mkdir(exist_ok=True)
            self.status_log_file = self.output_dir / "log_simulation_status.txt"

            # Write header for simulation status log
            with open(self.status_log_file, 'w', encoding='utf-8') as f:
                f.write("=== SIMULATION STATUS LOG ===\n")
                f.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                f.write("Cell ID | Oxygen | Glucose | Lactate | TGFA | Oxygen_supply | Glucose_supply | MCT1_stimulus | EGFR_stimulus | Apoptosis | Proliferation | Necrosis | Growth_Arrest | mitoATP | glycoATP | Final Phenotype | Step\n")
                f.write("-" * 150 + "\n")

    def log_step_start(self, step):
        """Log the start of a simulation step"""
        self.step_count = step

        if self.debug_enabled:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*20} STEP {step} {'='*20}\n")

    def log_cell_substances_and_nodes(self, cell_id, position, local_env, gene_inputs, gene_states, phenotype, cell=None, config=None):
        """Log detailed cell information for each cell and phenotype update"""
        if not self.debug_enabled:
            return

        # Important substances to track
        important_substances = {
            'Oxygen': 'Oxygen_supply',
            'Glucose': 'Glucose_supply',
            'Lactate': 'MCT1_stimulus',
            'H': 'Proton_level',
            'FGF': 'FGFR_stimulus',
            'TGFA': 'EGFR_stimulus'
        }

        # Phenotype nodes to track
        phenotype_nodes = ['Proliferation', 'Apoptosis', 'Growth_Arrest', 'Necrosis']

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\nCELL {cell_id[:8]} at {position}:\n")

            # Log important substances and their corresponding nodes
            f.write("  Important Substances & Nodes:\n")
            for substance, node in important_substances.items():
                substance_val = local_env.get(substance.lower(), 'N/A')
                node_state = gene_inputs.get(node, 'N/A')
                f.write(f"    {substance}: {substance_val} -> {node}: {node_state}\n")

            # Log phenotype nodes
            f.write("  Phenotype Nodes:\n")
            for node in phenotype_nodes:
                state = gene_states.get(node, 'N/A')
                f.write(f"    {node}: {state}\n")

            # Log final phenotype
            f.write(f"  Final Phenotype: {phenotype}\n")

            # Add division decision logging
            if cell and config:
                try:
                    should_divide = cell.should_divide(config)
                    f.write(f"  Division Decision: {should_divide}\n")

                    # Get division reasoning - check what information is available
                    f.write(f"  Division Reasoning:\n")
                    f.write(f"    Age: {cell.state.age:.1f}\n")
                    f.write(f"    Current Phenotype: {cell.state.phenotype}\n")

                    # Check if metabolic state exists
                    if hasattr(cell.state, 'metabolic_state'):
                        f.write(f"    Metabolic State: {cell.state.metabolic_state}\n")
                        if 'atp_rate' in cell.state.metabolic_state:
                            atp_rate = cell.state.metabolic_state['atp_rate']
                            f.write(f"    ATP Rate: {atp_rate:.2e}\n")
                    else:
                        f.write(f"    Metabolic State: Not available\n")

                    # Try to get division parameters from config
                    try:
                        # Import the function dynamically
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("custom_functions",
                            "tests/jayatilake_experiment/jayatilake_experiment_custom_functions.py")
                        custom_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(custom_module)

                        atp_threshold = custom_module.get_parameter_from_config(config, 'atp_threshold', 0.8)
                        max_atp = custom_module.get_parameter_from_config(config, 'max_atp', 30)
                        cell_cycle_time = custom_module.get_parameter_from_config(config, 'cell_cycle_time', 240)

                        f.write(f"    Required Age: {cell_cycle_time}\n")
                        f.write(f"    ATP Threshold: {atp_threshold}\n")
                        f.write(f"    Max ATP: {max_atp}\n")
                        f.write(f"    Age Check: {'PASS' if cell.state.age >= cell_cycle_time else 'FAIL'}\n")

                        if hasattr(cell.state, 'metabolic_state') and 'atp_rate' in cell.state.metabolic_state:
                            atp_rate = cell.state.metabolic_state['atp_rate']
                            atp_rate_normalized = atp_rate / max_atp if max_atp > 0 else 0
                            f.write(f"    ATP Check: {'PASS' if atp_rate_normalized > atp_threshold else 'FAIL'}\n")
                        else:
                            f.write(f"    ATP Check: FAIL (no ATP data)\n")

                    except Exception as param_e:
                        f.write(f"    Parameter Error: {str(param_e)}\n")

                except Exception as e:
                    f.write(f"  Division Decision: ERROR ({str(e)})\n")

    def log_phenotype_update_end(self, phenotype_changes):
        """Log summary at end of phenotype update"""
        if not self.debug_enabled:
            return

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\nPHENOTYPE UPDATE SUMMARY:\n")
            if phenotype_changes:
                for change, count in phenotype_changes.items():
                    f.write(f"  {change}: {count} cells\n")
            else:
                f.write("  No phenotype changes\n")

    def log_simulation_status(self, cell_id, local_env, gene_states, phenotype, step=None):
        """Log structured simulation status for each cell"""
        if not self.simulation_status_logging:
            return

        # Use the step count from the logger if not provided
        if step is None:
            step = self.step_count

        # Extract required values
        oxygen = local_env.get('oxygen', 'N/A')
        glucose = local_env.get('glucose', 'N/A')
        lactate = local_env.get('lactate', 'N/A')
        tgfa = local_env.get('tgfa', 'N/A')

        # Extract gene node states
        oxygen_supply = gene_states.get('Oxygen_supply', 'N/A')
        glucose_supply = gene_states.get('Glucose_supply', 'N/A')
        mct1_stimulus = gene_states.get('MCT1_stimulus', 'N/A')
        egfr_stimulus = gene_states.get('EGFR_stimulus', 'N/A')

        apoptosis = gene_states.get('Apoptosis', 'N/A')
        proliferation = gene_states.get('Proliferation', 'N/A')
        necrosis = gene_states.get('Necrosis', 'N/A')
        growth_arrest = gene_states.get('Growth_Arrest', 'N/A')

        mito_atp = gene_states.get('mitoATP', 'N/A')
        glyco_atp = gene_states.get('glycoATP', 'N/A')

        # Write to status log file
        with open(self.status_log_file, 'a', encoding='utf-8') as f:
            f.write(f"{cell_id[:8]} | {oxygen} | {glucose} | {lactate} | {tgfa} | {oxygen_supply} | {glucose_supply} | {mct1_stimulus} | {egfr_stimulus} | {apoptosis} | {proliferation} | {necrosis} | {growth_arrest} | {mito_atp} | {glyco_atp} | {phenotype} | {step}\n")

@dataclass
class PopulationState:
    """Immutable population state representation"""
    cells: Dict[str, Cell] = field(default_factory=dict)
    spatial_grid: Dict[Union[Tuple[int, int], Tuple[int, int, int]], str] = field(default_factory=dict)  # position -> cell_id
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

class CellPopulation(ICellPopulation):
    """
    Spatial cell population management with immutable state tracking
    
    Manages cell positions, division, death, and migration on a spatial grid.
    All behaviors can be customized via the hook system.
    """
    
    def __init__(self, grid_size: Union[Tuple[int, int], Tuple[int, int, int]], gene_network: Optional[BooleanNetwork] = None,
                 custom_functions_module=None, config=None):

        self.grid_size = grid_size
        self.gene_network_template = gene_network or BooleanNetwork()  # Template for creating cell-specific networks
        self.custom_functions = self._load_custom_functions(custom_functions_module)
        self.config = config  # Store config for threshold calculations

        # Initialize phenotype logger
        output_dir = getattr(config, 'output_dir', 'logs') if config else 'logs'
        self.phenotype_logger = PhenotypeLogger(config, output_dir)

        # Initialize empty population state
        self.state = PopulationState()

        # Initialize step counter
        self.step_count = 0

        # Initialize gene network for population (will be used for new cells)
        self._initialize_population_gene_network()

        # Default parameters
        self.default_params = {
            'max_cells_per_position': 1,  # Spatial exclusion
            'migration_probability': 0.1,
            'division_success_rate': 0.8,
            'max_population_size': grid_size[0] * grid_size[1] * 2  # Prevent runaway growth
        }

    def _load_custom_functions(self, custom_functions_module):
        """Load custom functions from module"""
        if custom_functions_module is None:
            return None

        try:
            if isinstance(custom_functions_module, str):
                # Load from file path
                spec = importlib.util.spec_from_file_location("custom_functions", custom_functions_module)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    return module
            else:
                # Already a module
                return custom_functions_module
        except Exception as e:
            print(f"Warning: Could not load custom functions: {e}")
            return None

    def initialize_with_custom_placement(self, simulation_params: Optional[Dict] = None) -> int:
        """Initialize population using custom placement function"""
        simulation_params = simulation_params or {}

        if self.custom_functions and hasattr(self.custom_functions, 'initialize_cell_placement'):
            # Call custom placement function, passing config
            cell_placements = self.custom_functions.initialize_cell_placement(
                grid_size=self.grid_size,
                simulation_params=simulation_params,
                config=self.config
            )
        else:
            # Fail explicitly if custom function is not provided
            raise RuntimeError(
                f"❌ Custom function 'initialize_cell_placement' is required but not found!\n"
                f"   Please ensure your custom functions module defines this function.\n"
                f"   Custom functions module: {self.custom_functions}"
            )

            # Add cells according to custom placement
            cells_added = 0
            for placement in cell_placements:
                if isinstance(placement, dict):
                    position = placement.get('position')
                    phenotype = placement['phenotype'] if 'phenotype' in placement else 'normal'
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
    
    def add_cell(self, position: Union[Tuple[int, int], Tuple[int, int, int]], phenotype: str = "normal") -> bool:
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

        # Initialize gene network for new cell (NetLogo-style random initialization)
        self._initialize_cell_gene_network(cell)
        
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
        if self.custom_functions and hasattr(self.custom_functions, 'select_division_direction'):
            target_position = self.custom_functions.select_division_direction(
                parent_position=parent_cell.state.position,
                available_positions=self._get_available_neighbors(parent_cell.state.position)
            )
        else:
            # Fail explicitly if custom function is not provided
            raise RuntimeError(
                f"❌ Custom function 'select_division_direction' is required but not found!\n"
                f"   Please ensure your custom functions module defines this function.\n"
                f"   Custom functions module: {self.custom_functions}"
            )
        
        if target_position is None:
            return False  # No space available
        
        # Check division success rate
        if np.random.random() > self.default_params['division_success_rate']:
            return False
        
        # Create daughter cell
        daughter_cell = parent_cell.divide()
        daughter_cell.move_to(target_position)

        # Initialize gene network for daughter cell (NetLogo-style random initialization)
        self._initialize_cell_gene_network(daughter_cell)
        
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
    

    
    def _get_available_neighbors(self, position: Union[Tuple[int, int], Tuple[int, int, int]]) -> List[Union[Tuple[int, int], Tuple[int, int, int]]]:
        """Get available neighboring positions"""
        if len(position) == 2:
            # 2D neighbors
            x, y = position
            neighbors = [
                (x-1, y), (x+1, y), (x, y-1), (x, y+1),  # Von Neumann neighborhood
                (x-1, y-1), (x-1, y+1), (x+1, y-1), (x+1, y+1)  # Moore neighborhood
            ]
        else:
            # 3D neighbors
            x, y, z = position
            neighbors = []
            # 26-connected neighborhood in 3D
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for dz in [-1, 0, 1]:
                        if dx == 0 and dy == 0 and dz == 0:
                            continue  # Skip the center position
                        neighbors.append((x + dx, y + dy, z + dz))

        available = []
        for pos in neighbors:
            if self._is_valid_position(pos) and pos not in self.state.spatial_grid:
                available.append(pos)

        return available
    
    def _is_valid_position(self, position: Union[Tuple[int, int], Tuple[int, int, int]]) -> bool:
        """Check if position is within grid bounds"""
        if len(position) == 2:
            x, y = position
            return 0 <= x < self.grid_size[0] and 0 <= y < self.grid_size[1]
        else:
            x, y, z = position
            return (0 <= x < self.grid_size[0] and
                    0 <= y < self.grid_size[1] and
                    0 <= z < self.grid_size[2])
    
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

    def _initialize_cell_gene_network(self, cell):
        """
        Initialize gene network for a new cell (creation or division).

        This method implements NetLogo-style gene initialization:
        - Called ONLY during cell creation and division
        - NOT called during regular gene network updates
        - Provides each new cell with random initial gene states
        - Fate nodes (Apoptosis, Proliferation, etc.) always start as False
        - Each cell gets its own gene network instance
        """
        # Create a new gene network instance for this cell by copying the template
        cell_gene_network = self.gene_network_template.copy()

        # Use NetLogo-style random initialization if configured
        random_init = getattr(self.config.gene_network, 'random_initialization', False)

        # Reset gene network with random initialization for new cells only
        cell_gene_network.reset(random_init=random_init)

        # CRITICAL FIX: Initialize all nodes to match their logic rules after random reset
        # This ensures nodes start in states consistent with their logic, not just random
        cell_gene_network.initialize_logic_states(verbose=False)

        # Get initial gene states and store them in the cell along with the gene network
        initial_gene_states = cell_gene_network.get_all_states()
        cell.state = cell.state.with_updates(
            gene_states=initial_gene_states,
            gene_network=cell_gene_network  # Store the cell's own gene network instance
        )

    def _initialize_population_gene_network(self):
        """Initialize the population's gene network at simulation start"""
        # This ensures the gene network is properly set up before any cells are created
        # Individual cells will get their own random initialization when created
        pass  # Gene network is already initialized in constructor

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
            try:
                substance_conc = local_env[substance_name.lower()]
            except KeyError:
                raise ValueError(f"Substance '{substance_name}' not found in local environment - check configuration")

            # Get threshold configuration for this gene input
            if gene_input_name not in self.config.thresholds:
                raise ValueError(f"Threshold for '{gene_input_name}' not configured - no hardcoded thresholds allowed")

            threshold_config = self.config.thresholds[gene_input_name]
            # Gene input is TRUE if concentration exceeds threshold
            gene_inputs[gene_input_name] = substance_conc > threshold_config.threshold

            # Compact debug for gene inputs (only first call) - TURNED OFF
            # if not hasattr(self, '_gene_input_debug_shown'):
            #     print(f"🔍 Gene thresholds: {substance_name}>{threshold_config.threshold}={gene_inputs[gene_input_name]}")
            #     self._gene_input_debug_shown = True

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
    
    def get_substance_reactions(self, substance_concentrations: Optional[Dict[str, Dict[Tuple[int, int], float]]] = None) -> Dict[Tuple[float, float], Dict[str, float]]:
        """Get all cell reactions for substances"""

        reactions = {}

        for cell in self.state.cells.values():
            # Get local environment (initial values)
            local_env = self._get_local_environment(cell.state.position)

            # Update with current substance concentrations if provided
            if substance_concentrations:
                for substance_name, conc_field in substance_concentrations.items():
                    if cell.state.position in conc_field:
                        # Update both capitalized and lowercase keys for compatibility
                        local_env[substance_name.lower()] = conc_field[cell.state.position]
                        local_env[substance_name] = conc_field[cell.state.position]

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
            # Calculate metabolic state for ATP override in phenotype decisions
            local_env = self._get_local_environment(cell.state.position)

            # Update with current substance concentrations if provided
            if substance_concentrations:
                for substance_name, conc_field in substance_concentrations.items():
                    if cell.state.position in conc_field:
                        # Update both capitalized and lowercase keys for compatibility
                        local_env[substance_name.lower()] = conc_field[cell.state.position]
                        local_env[substance_name] = conc_field[cell.state.position]

            # Calculate and update metabolic state using custom functions
            if hasattr(cell.custom_functions, 'update_cell_metabolic_state'):
                cell.custom_functions.update_cell_metabolic_state(cell, local_env, self.config)
            else:
                # Fail explicitly if custom function is not provided
                raise RuntimeError(
                    f"❌ Custom function 'update_cell_metabolic_state' is required but not found!\n"
                    f"   Please ensure your custom functions module defines this function.\n"
                    f"   Custom functions module: {cell.custom_functions}\n"
                    f"   This function is CRITICAL for calculating ATP rates and metabolic state."
                )

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

            # DO NOT RESET gene network during regular updates - this destroys gene dynamics!
            # Gene network should only be reset during cell creation, not every update

            # Get this cell's own gene network instance
            cell_gene_network = cell.state.gene_network
            if cell_gene_network is None:
                # Fallback: create a new gene network for this cell if it doesn't have one
                print(f"⚠️  Cell {cell_id} missing gene network, creating new one")
                self._initialize_cell_gene_network(cell)
                cell_gene_network = cell.state.gene_network

            # Update gene network using configuration-based thresholds
            gene_inputs = self._calculate_gene_inputs(local_env)
            cell_gene_network.set_input_states(gene_inputs)

            # CRITICAL FIX: Initialize logic states after setting inputs
            # This ensures all nodes are in states consistent with their logic rules
            # Only needed on first update or when input states change significantly
            if self.step_count == 0:  # First update - initialize logic
                cell_gene_network.initialize_logic_states(verbose=False)

            # Get propagation steps from gene network configuration
            if not (self.config.gene_network and hasattr(self.config.gene_network, 'propagation_steps')):
                raise ValueError("gene_network.propagation_steps must be configured")

            steps = self.config.gene_network.propagation_steps

            gene_states = cell_gene_network.step(steps)

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

            # Get all gene network states for ATP analysis from this cell's gene network
            all_states = cell_gene_network.get_all_states()
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
            # if apoptosis:
            #     pos = cell.state.position
            #     oxygen = local_env.get('oxygen', 0.0)
            #     glucose = local_env.get('glucose', 0.0)
            #     print(f"🚨 APOPTOSIS CELL at {pos}: O2={oxygen:.3f}, Gluc={glucose:.3f}")
            #     print(f"   Gene inputs: {gene_inputs}")

            # Debug apoptosis pathway components - TURNED OFF
            if apoptosis and False:  # Disabled debug output
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
                apoptosis_node = cell_gene_network.nodes.get('Apoptosis')
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

            # Debug ATP gene outputs for first cell - TURNED OFF
            elif False:  # self._gene_output_debug_count == 1:
                atp_rate = gene_states.get('ATP_Production_Rate', False)
                mito_atp = gene_states.get('mitoATP', False)
                glyco_atp = gene_states.get('glycoATP', False)
                print(f"🔍 ATP Gene outputs: ATP_Rate={atp_rate}, mitoATP={mito_atp}, glycoATP={glyco_atp}")
                print(f"   Environmental: Oxygen_supply={gene_inputs.get('Oxygen_supply', False)}, Glucose_supply={gene_inputs.get('Glucose_supply', False)}")

            # NOTE: Debug logging moved to update_phenotypes() to log the correct final phenotype

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
                new_phenotype = cell.update_phenotype(cell._cached_local_env, cell._cached_gene_states, self.config)

                # Log detailed information for each phenotype update (with correct final phenotype)
                if self.phenotype_logger.debug_enabled:
                    # Re-calculate gene inputs for logging (since they're not cached)
                    gene_inputs = self._calculate_gene_inputs(cell._cached_local_env)
                    self.phenotype_logger.log_cell_substances_and_nodes(
                        cell_id, cell.state.position, cell._cached_local_env,
                        gene_inputs, cell._cached_gene_states, new_phenotype,  # Now logs the NEW phenotype
                        cell, self.config  # Add cell and config for division logging
                    )

                # Log structured simulation status
                if self.phenotype_logger.simulation_status_logging:
                    self.phenotype_logger.log_simulation_status(
                        cell_id, cell._cached_local_env, cell._cached_gene_states,
                        new_phenotype
                    )

                # Track phenotype changes compactly
                if old_phenotype != new_phenotype:
                    change_key = f"{old_phenotype}→{new_phenotype}"
                    phenotype_changes[change_key] = phenotype_changes[change_key] + 1 if change_key in phenotype_changes else 1

                # Clean up cache
                delattr(cell, '_cached_gene_states')
                delattr(cell, '_cached_local_env')

            updated_cells[cell_id] = cell

        # Log phenotype update summary
        self.phenotype_logger.log_phenotype_update_end(phenotype_changes)

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
            if self.custom_functions and hasattr(self.custom_functions, 'calculate_migration_probability'):
                migration_prob = self.custom_functions.calculate_migration_probability(
                    cell_state=cell.state.__dict__,
                    local_environment=self._get_local_environment(cell.state.position),
                    target_position=None  # Would be calculated for each neighbor
                )
            else:
                # Fail explicitly if custom function is not provided
                raise RuntimeError(
                    f"❌ Custom function 'calculate_migration_probability' is required but not found!\n"
                    f"   Please ensure your custom functions module defines this function.\n"
                    f"   Custom functions module: {self.custom_functions}"
                )
            
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
            phenotype_counts[phenotype] = phenotype_counts[phenotype] + 1 if phenotype in phenotype_counts else 1
            total_age += cell.state.age
        
        return {
            'total_cells': self.state.total_cells,
            'phenotype_counts': phenotype_counts,
            'average_age': total_age / self.state.total_cells,
            'generation_count': self.state.generation_count,
            'grid_occupancy': len(self.state.spatial_grid) / (self.grid_size[0] * self.grid_size[1])
        }
    
    def get_cell_positions(self) -> List[Tuple[Union[Tuple[int, int], Tuple[int, int, int]], str]]:
        """Get list of (position, phenotype) for all cells"""
        return [(cell.state.position, cell.state.phenotype)
                for cell in self.state.cells.values()]

    def get_cell_at_position(self, position: Union[Tuple[int, int], Tuple[int, int, int]]):
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
