from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional, Union
from pathlib import Path
import numpy as np


class ISubstanceSimulator(ABC):
    """Interface for multi-substance diffusion-reaction simulators.

    This defines the complete public API for substance simulators.
    Use this type for IDE discoverability when accessing the simulator from context.

    Example usage in workflow functions::

        from interfaces.base import ISubstanceSimulator

        simulator: Optional[ISubstanceSimulator] = context.get('simulator')
        if simulator:
            simulator.update(substance_reactions)
            concentrations = simulator.get_substance_concentrations()
            stats = simulator.get_summary_statistics()
    """

    @abstractmethod
    def initialize_substances(self, substances: Dict[str, Any]) -> None:
        """(Re)initialize substances from a provided config dict.

        Called by workflow initialization functions after the simulator
        has been constructed to bring internal state in sync with
        workflow-defined substances.

        Args:
            substances: Dict mapping substance names to SubstanceConfig objects
        """
        pass

    @abstractmethod
    def update(self, substance_reactions: Dict[Tuple[float, float], Dict[str, float]]) -> None:
        """Solve diffusion PDE for all substances using cell reactions as source/sink terms.

        Args:
            substance_reactions: Dict mapping cell positions ``(x, y)`` to
                per-substance reaction rates ``{substance_name: rate}``
        """
        pass

    @abstractmethod
    def solve_steady_state(self, cell_reactions: Dict[Tuple[float, float], float]) -> bool:
        """Solve diffusion-reaction to steady state.

        Args:
            cell_reactions: Dict mapping cell positions to reaction rates

        Returns:
            True if solver converged
        """
        pass

    @abstractmethod
    def evaluate_at_point(self, position: Tuple[float, float]) -> float:
        """Get concentration at specific position.

        Args:
            position: ``(x, y)`` coordinates

        Returns:
            Concentration value at the given position
        """
        pass

    @abstractmethod
    def get_field_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get X, Y, Z arrays for visualization.

        Returns:
            Tuple of ``(X, Y, Z)`` numpy arrays
        """
        pass

    @abstractmethod
    def get_substance_concentrations(self) -> Dict[str, Dict[Tuple[int, int], float]]:
        """Get all substance concentrations for cell updates.

        Returns:
            Dict mapping substance names to position→concentration dicts,
            e.g. ``{'Oxygen': {(0,0): 0.28, (1,0): 0.27, ...}}``
        """
        pass

    @abstractmethod
    def get_gene_network_inputs_for_position(self, position: Tuple[int, int]) -> Dict[str, float]:
        """Get gene network inputs for a specific cell position.

        Converts substance concentrations to gene network input values
        using configured associations and thresholds.

        Args:
            position: ``(x, y)`` grid position

        Returns:
            Dict mapping gene input names to float values
        """
        pass

    @abstractmethod
    def get_summary_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get summary statistics for all substances.

        Returns:
            Dict mapping substance names to stats dicts with keys
            ``'min'``, ``'max'``, ``'mean'``, ``'std'``
        """
        pass

class ICell(ABC):
    """Interface for individual cell behavior"""

    @abstractmethod
    def update_phenotype(self, local_environment: Dict[str, float],
                        gene_states: Dict[str, bool]) -> str:
        """Update cell phenotype based on environment and genes"""
        pass

    @abstractmethod
    def calculate_metabolism(self, local_environment: Dict[str, float]) -> Dict[str, float]:
        """Calculate metabolic production/consumption rates"""
        pass

    @abstractmethod
    def should_divide(self) -> bool:
        """Check if cell should attempt division"""
        pass

    @abstractmethod
    def should_die(self, local_environment: Dict[str, float]) -> bool:
        """Check if cell should die"""
        pass

class ICellPopulation(ABC):
    """Interface for cell population management.

    This defines the complete public API for cell population implementations.
    Use this type for IDE discoverability when accessing the population from context.

    Example usage in workflow functions::

        from interfaces.base import ICellPopulation

        population: Optional[ICellPopulation] = context.get('population')
        if population:
            cells = population.state.cells
            stats = population.get_population_statistics()
            positions = population.get_cell_positions()
    """

    @abstractmethod
    def initialize_with_custom_placement(self, simulation_params: Optional[Dict] = None) -> int:
        """Initialize population using custom placement function.

        Args:
            simulation_params: Optional simulation parameters dict

        Returns:
            Number of cells placed
        """
        pass

    @abstractmethod
    def initialize_cells(self, cell_data: List[Dict[str, Any]]) -> int:
        """Batch initialize cells with a single state update for efficiency.

        Args:
            cell_data: List of dicts, each with keys like 'position', 'phenotype', etc.

        Returns:
            Number of cells successfully initialized
        """
        pass

    @abstractmethod
    def add_cell(self, position: Union[Tuple[int, int], Tuple[int, int, int]], phenotype: str = "normal") -> bool:
        """Add a single cell at a lattice position.

        Args:
            position: ``(x, y)`` or ``(x, y, z)`` grid position
            phenotype: Initial cell phenotype (default ``"normal"``)

        Returns:
            True if cell was added, False if position was occupied or invalid
        """
        pass

    @abstractmethod
    def attempt_division(self, parent_id: str) -> bool:
        """Attempt to divide a single cell.

        Args:
            parent_id: ID of the parent cell

        Returns:
            True if division succeeded, False otherwise
        """
        pass

    @abstractmethod
    def attempt_divisions(self) -> int:
        """Attempt cell divisions in batch with a single state update.

        Returns:
            Number of successful divisions
        """
        pass

    @abstractmethod
    def remove_dead_cells(self) -> List[str]:
        """Remove dead cells and return their IDs.

        Returns:
            List of removed cell IDs
        """
        pass

    @abstractmethod
    def get_substance_reactions(self, substance_concentrations: Optional[Dict[str, Dict[Tuple[int, int], float]]] = None) -> Dict[Tuple[float, float], Dict[str, float]]:
        """Get all cell reactions for substances.

        Args:
            substance_concentrations: Optional pre-computed substance concentrations

        Returns:
            Dict mapping cell positions to per-substance reaction rate dicts
        """
        pass

    @abstractmethod
    def update_cells(self, dt: float, substance_concentrations: Optional[Dict[str, Dict[Tuple[int, int], float]]] = None) -> None:
        """DEPRECATED: Use update_intracellular_processes() instead.

        Args:
            dt: Time step in hours
            substance_concentrations: Optional substance concentrations
        """
        pass

    @abstractmethod
    def update_intracellular_processes(self, dt: float, substance_concentrations: Optional[Dict[str, Dict[Tuple[int, int], float]]] = None) -> None:
        """Update intracellular processes: aging, metabolism, division, death.

        Should be called every intracellular_step (fast timescale).

        Args:
            dt: Time step in hours
            substance_concentrations: Optional substance concentrations
        """
        pass

    @abstractmethod
    def update_gene_networks(self, substance_concentrations: Optional[Dict[str, Dict[Tuple[int, int], float]]] = None) -> None:
        """Update gene networks based on current environment.

        Args:
            substance_concentrations: Optional substance concentrations
        """
        pass

    @abstractmethod
    def update_phenotypes(self) -> None:
        """Update cell phenotypes based on cached gene states.

        Should be called every intracellular_step (phenotype changes follow gene expression).
        """
        pass

    @abstractmethod
    def update_intercellular_processes(self) -> Dict[str, Any]:
        """Update intercellular processes: migration, cell-cell interactions, signaling.

        Should be called every intercellular_step (slower than intracellular processes).

        Returns:
            Dict with keys ``'migrations'`` and ``'divisions'`` containing counts
        """
        pass

    @abstractmethod
    def get_population_statistics(self) -> Dict[str, Any]:
        """Get population statistics.

        Returns:
            Dict with keys ``'total_cells'``, ``'phenotype_counts'``,
            ``'average_age'``, ``'generation_count'``, ``'grid_occupancy'``
        """
        pass

    @abstractmethod
    def get_cell_positions(self) -> List[Tuple[Union[Tuple[int, int], Tuple[int, int, int]], str]]:
        """Get list of (position, phenotype) for all cells.

        Returns:
            List of ``(position, phenotype)`` tuples
        """
        pass

    @abstractmethod
    def get_cell_at_position(self, position: Union[Tuple[int, int], Tuple[int, int, int]]) -> Optional[Any]:
        """Get cell at specific position, if any.

        Args:
            position: ``(x, y)`` or ``(x, y, z)`` grid position

        Returns:
            Cell object or None
        """
        pass

    @abstractmethod
    def get_state(self) -> Any:
        """Get current population state (immutable).

        Returns:
            PopulationState object
        """
        pass

    @abstractmethod
    def print_atp_statistics(self) -> None:
        """Print ATP statistics — called only at status_print_interval."""
        pass

class IGeneNetwork(ABC):
    """Interface for gene regulatory networks.

    This defines the complete public API for gene network implementations.
    Use this type for IDE discoverability when accessing gene networks from context.

    Example usage in workflow functions::

        from interfaces.base import IGeneNetwork

        cell_gn: Optional[IGeneNetwork] = gene_networks.get(cell_id)
        if cell_gn:
            cell_gn.step(500, mode="netlogo")       # propagate
            states = cell_gn.get_all_states()        # read all node states
            outputs = cell_gn.get_output_states()    # read fate nodes only
    """

    @abstractmethod
    def fix_node(self, node_name: str, state: bool) -> None:
        """Fix a node to a specific state (permanently pinned during propagation).

        Args:
            node_name: Name of the node to fix
            state: Boolean state to fix the node to
        """
        pass

    @abstractmethod
    def set_input_states(self, inputs: Dict[str, bool]) -> None:
        """Set input node states. Input nodes stay FIXED during propagation.

        Args:
            inputs: Dict mapping input node names to boolean states
        """
        pass

    @abstractmethod
    def initialize_logic_states(self, verbose: bool = False) -> int:
        """Initialize all non-input nodes to match their logic rules.

        Args:
            verbose: If True, print details of each node initialization

        Returns:
            Number of nodes that were updated
        """
        pass

    @abstractmethod
    def initialize_random(self) -> None:
        """Initialize ALL nodes with random states (except fixed nodes)."""
        pass

    @abstractmethod
    def step(self, num_steps: int = 1, mode: str = "synchronous") -> Dict[str, bool]:
        """Run network for specified steps.

        Args:
            num_steps: Number of update steps to run
            mode: Update mode:
                - "synchronous": All genes update together each step
                - "netlogo": Random single gene per step (NetLogo-style)

        Returns:
            Dictionary of all gene states after propagation
        """
        pass

    @abstractmethod
    def get_output_states(self) -> Dict[str, bool]:
        """Get current output/fate node states (e.g. Proliferation, Apoptosis).

        Returns:
            Dict mapping output node names to their boolean states
        """
        pass

    @abstractmethod
    def get_all_states(self) -> Dict[str, bool]:
        """Get all node states (inputs, internal, and outputs).

        Returns:
            Dict mapping all node names to their boolean states
        """
        pass

    @abstractmethod
    def reset(self, random_init: bool = False) -> None:
        """Reset network: fate nodes to False, others to random by default.

        Args:
            random_init: If True, randomize non-input, non-fate nodes
        """
        pass

    @abstractmethod
    def copy(self) -> 'IGeneNetwork':
        """Create a deep copy of this gene network.

        Returns:
            A new IGeneNetwork instance with identical state
        """
        pass

    @abstractmethod
    def get_network_info(self) -> Dict[str, Any]:
        """Get network metadata (node counts, input/output node names, etc.).

        Returns:
            Dict with network information
        """
        pass

class IVisualization(ABC):
    """Interface for visualization components"""

    @abstractmethod
    def plot_substance_field(self, substance_name: str, data: np.ndarray,
                           metadata: Dict[str, Any]) -> str:
        """Plot substance concentration field"""
        pass

    @abstractmethod
    def plot_cell_population(self, cell_positions: List[Tuple[int, int]],
                           cell_phenotypes: List[str], metadata: Dict[str, Any]) -> str:
        """Plot cell population distribution"""
        pass

class IDataExporter(ABC):
    """Interface for data export components"""

    @abstractmethod
    def export_simulation_data(self, timestep: int, substance_data: Dict[str, np.ndarray],
                             cell_data: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
        """Export simulation data for a timestep"""
        pass

    @abstractmethod
    def finalize_export(self) -> str:
        """Finalize export and return output path"""
        pass

class ITimescaleOrchestrator(ABC):
    """Interface for multi-timescale coordination"""

    @abstractmethod
    def should_update_diffusion(self, current_step: int) -> bool:
        """Check if diffusion should be updated this step"""
        pass

    @abstractmethod
    def should_update_intracellular(self, current_step: int) -> bool:
        """Check if intracellular processes should be updated"""
        pass

    @abstractmethod
    def should_update_intercellular(self, current_step: int) -> bool:
        """Check if intercellular processes should be updated"""
        pass

class IPerformanceProfiler(ABC):
    """Interface for performance monitoring"""

    @abstractmethod
    def start_timer(self, operation_name: str):
        """Start timing an operation"""
        pass

    @abstractmethod
    def end_timer(self, operation_name: str) -> float:
        """End timing and return duration"""
        pass

    @abstractmethod
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        pass


class IConfig(ABC):
    """Interface for OpenCellCommsConfig — the master simulation configuration.

    This defines all public fields and methods of the configuration dataclass.
    Use this type for IDE discoverability when accessing config from context.

    Example usage in workflow functions::

        from interfaces.base import IConfig

        config: Optional[IConfig] = context.get('config')
        if config:
            dt = config.time.dt
            substances = config.substances
            output_dir = config.output_dir
    """

    # ── Core simulation parameters ───────────────────────────────
    @property
    @abstractmethod
    def domain(self) -> Any:
        """Domain configuration (DomainConfig): size_x, size_y, nx, ny, dimensions, cell_height, …"""
        pass

    @property
    @abstractmethod
    def time(self) -> Any:
        """Time configuration (TimeConfig): dt, end_time, diffusion_step, intracellular_step, intercellular_step"""
        pass

    @property
    @abstractmethod
    def diffusion(self) -> Any:
        """Diffusion solver configuration (DiffusionConfig): max_iterations, tolerance, solver_type, twodimensional_adjustment_coefficient"""
        pass

    @property
    @abstractmethod
    def substances(self) -> Dict[str, Any]:
        """Substance configurations: Dict mapping substance names to SubstanceConfig objects.

        Each SubstanceConfig has: name, diffusion_coeff, production_rate, uptake_rate,
        initial_value, boundary_value, boundary_type.
        """
        pass

    # ── Gene network configuration ───────────────────────────────
    @property
    @abstractmethod
    def associations(self) -> Dict[str, str]:
        """Substance-to-gene input mapping: e.g. ``{'Oxygen': 'Oxygen_supply'}``"""
        pass

    @property
    @abstractmethod
    def thresholds(self) -> Dict[str, Any]:
        """Gene activation thresholds: Dict mapping threshold names to ThresholdConfig (name, threshold, initial)"""
        pass

    @property
    @abstractmethod
    def composite_genes(self) -> List[Any]:
        """Composite gene configurations: List of CompositeGeneConfig (name, inputs, logic)"""
        pass

    @property
    @abstractmethod
    def gene_network(self) -> Optional[Any]:
        """Gene network configuration (GeneNetworkConfig or None): nodes, input_nodes, output_nodes, propagation_steps, bnd_file, random_initialization"""
        pass

    @property
    @abstractmethod
    def gene_network_steps(self) -> int:
        """Number of propagation steps for gene network updates (default 3)"""
        pass

    # ── Environment and output ───────────────────────────────────
    @property
    @abstractmethod
    def environment(self) -> Any:
        """Environment configuration (EnvironmentConfig)"""
        pass

    @property
    @abstractmethod
    def output(self) -> Any:
        """Output configuration (OutputConfig): save_data_interval, save_plots_interval, status_print_interval, cell_size_um, …"""
        pass

    @property
    @abstractmethod
    def initial_state(self) -> Any:
        """Initial state configuration (InitialStateConfig): file_path"""
        pass

    # ── Paths ────────────────────────────────────────────────────
    @property
    @abstractmethod
    def output_dir(self) -> Path:
        """Output directory path (default ``Path('results')``)"""
        pass

    @property
    @abstractmethod
    def plots_dir(self) -> Path:
        """Plots directory path (default ``Path('plots')``)"""
        pass

    @property
    @abstractmethod
    def data_dir(self) -> Path:
        """Data directory path (default ``Path('data')``)"""
        pass

    # ── Customization ────────────────────────────────────────────
    @property
    @abstractmethod
    def custom_functions_path(self) -> Optional[str]:
        """Path to custom workflow functions file (or None)"""
        pass

    @property
    @abstractmethod
    def custom_parameters(self) -> Dict[str, Any]:
        """User-defined custom parameters dict"""
        pass

    # ── Debug flags ──────────────────────────────────────────────
    @property
    @abstractmethod
    def debug_phenotype_detailed(self) -> bool:
        """Enable detailed phenotype debugging output"""
        pass

    @property
    @abstractmethod
    def log_simulation_status(self) -> bool:
        """Enable structured simulation status logging"""
        pass

    # ── Factory methods ──────────────────────────────────────────
    @classmethod
    @abstractmethod
    def load_from_yaml(cls, config_file: Path) -> 'IConfig':
        """Load configuration from a YAML file.

        Args:
            config_file: Path to the YAML configuration file

        Returns:
            A fully populated IConfig instance
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IConfig':
        """Create configuration from a dictionary.

        Args:
            data: Dict with all configuration keys

        Returns:
            A fully populated IConfig instance
        """
        pass



class IMeshManager(ABC):
    """Interface for spatial mesh management (FiPy solver mesh).

    This defines the complete public API for MeshManager.
    Use this type for IDE discoverability when accessing the mesh manager from context.

    Example usage in workflow functions::

        from interfaces.base import IMeshManager

        mesh_manager: Optional[IMeshManager] = context.get('mesh_manager')
        if mesh_manager:
            metadata = mesh_manager.get_metadata()
            vol = mesh_manager.cell_volume_um3
    """

    @property
    @abstractmethod
    def config(self) -> Any:
        """Domain configuration (DomainConfig) used to build this mesh."""
        pass

    @property
    @abstractmethod
    def solver_mesh(self) -> Any:
        """The FiPy solver mesh (Grid2D or Grid3D). Used by the diffusion solver."""
        pass

    @property
    @abstractmethod
    def mesh(self) -> Any:
        """Backward-compatible alias for ``solver_mesh``."""
        pass

    @property
    @abstractmethod
    def verbose(self) -> bool:
        """Whether to print diagnostic messages."""
        pass

    @property
    @abstractmethod
    def cell_volume_m3(self) -> float:
        """Cell (voxel) volume in m³ — handles both 2D and 3D."""
        pass

    @property
    @abstractmethod
    def cell_volume_um3(self) -> float:
        """Cell (voxel) volume in μm³ for easier reading."""
        pass

    @abstractmethod
    def center_solver_mesh_at_origin(self) -> None:
        """Center the solver mesh at origin after FiPy variables are created.

        Should be called after all FiPy setup is complete.
        """
        pass

    @abstractmethod
    def center_mesh_at_origin(self) -> None:
        """Backward-compatible alias for ``center_solver_mesh_at_origin()``."""
        pass

    @abstractmethod
    def get_metadata(self) -> dict:
        """Return mesh metadata as a dictionary.

        Returns:
            Dict with keys: ``dimensions``, ``nx``, ``ny``, ``dx_um``, ``dy_um``,
            ``domain_x_um``, ``domain_y_um``, ``cell_volume_um3``, ``total_cells``
            (plus ``nz``, ``dz_um``, ``domain_z_um`` for 3D).
        """
        pass

    @abstractmethod
    def validate_against_expected(self, expected_spacing_um: float = None,
                                  expected_volume_um3: float = None) -> None:
        """Validate mesh against expected values.

        Args:
            expected_spacing_um: Expected grid spacing in μm (uses config if None)
            expected_volume_um3: Expected cell volume in μm³ (uses config if None)

        Raises:
            DomainError: If validation fails
        """
        pass


class IWorkflowHelpers(ABC):
    """Interface for workflow helper functions provided by SimulationEngine.

    In full simulation mode, helpers is a dict of convenience lambdas built by
    ``SimulationEngine._build_context()``. This interface documents the available
    helper keys for IDE discoverability.

    Example usage in workflow functions::

        from interfaces.base import IWorkflowHelpers

        helpers: Optional[IWorkflowHelpers] = context.get('helpers')
        if helpers:
            helpers.run_diffusion()
            helpers.update_phenotypes()

    Note:
        In the default engine, helpers is a ``Dict[str, Callable]`` accessed via
        ``helpers['run_diffusion']()``.  This interface exists for documentation
        and discoverability purposes.
    """

    @abstractmethod
    def update_intracellular(self) -> None:
        """Run intracellular update: ``population.update_intracellular_processes(dt)``"""
        pass

    @abstractmethod
    def update_gene_networks(self) -> None:
        """Run gene network update: ``population.update_gene_networks(concentrations)``"""
        pass

    @abstractmethod
    def update_phenotypes(self) -> None:
        """Run phenotype update: ``population.update_phenotypes()``"""
        pass

    @abstractmethod
    def remove_dead_cells(self) -> None:
        """Remove dead cells: ``population.remove_dead_cells()``"""
        pass

    @abstractmethod
    def run_diffusion(self) -> None:
        """Run one diffusion solver step."""
        pass

    @abstractmethod
    def get_substance_reactions(self) -> Dict[Tuple[float, float], Dict[str, float]]:
        """Get substance reactions from all cells.

        Returns:
            Dict mapping cell positions to per-substance reaction rates
        """
        pass

    @abstractmethod
    def update_intercellular(self) -> None:
        """Run intercellular update: ``population.update_intercellular_processes()``"""
        pass