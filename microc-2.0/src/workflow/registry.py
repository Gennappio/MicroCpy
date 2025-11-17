"""
Function registry for MicroC workflow system.

Catalogs all available simulation functions with metadata for the UI and executor.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Optional
from enum import Enum


class FunctionCategory(Enum):
    """Categories of workflow functions."""
    INITIALIZATION = "initialization"
    INTRACELLULAR = "intracellular"
    DIFFUSION = "diffusion"
    INTERCELLULAR = "intercellular"
    FINALIZATION = "finalization"
    UTILITY = "utility"


class ParameterType(Enum):
    """Types of function parameters."""
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    DICT = "dict"
    LIST = "list"


@dataclass
class ParameterDefinition:
    """Definition of a function parameter."""
    name: str
    type: ParameterType
    description: str
    default: Any = None
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Optional[List[Any]] = None  # For enum-like parameters


@dataclass
class FunctionMetadata:
    """Metadata for a registered function."""
    name: str
    display_name: str
    description: str
    category: FunctionCategory
    parameters: List[ParameterDefinition] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)  # What data this function needs
    outputs: List[str] = field(default_factory=list)  # What data this function produces
    cloneable: bool = False  # Can this function be cloned/customized?
    module_path: str = ""  # Where to find this function
    source_file: str = ""  # Path to source file (for GUI code viewer)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "default": p.default,
                    "required": p.required,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "options": p.options
                }
                for p in self.parameters
            ],
            "inputs": self.inputs,
            "outputs": self.outputs,
            "cloneable": self.cloneable,
            "module_path": self.module_path,
            "source_file": self.source_file
        }


class FunctionRegistry:
    """Registry of all available workflow functions."""
    
    def __init__(self):
        self.functions: Dict[str, FunctionMetadata] = {}
    
    def register(self, metadata: FunctionMetadata):
        """Register a function with its metadata."""
        self.functions[metadata.name] = metadata
    
    def get(self, function_name: str) -> Optional[FunctionMetadata]:
        """Get metadata for a function by name."""
        return self.functions.get(function_name)
    
    def get_by_category(self, category: FunctionCategory) -> List[FunctionMetadata]:
        """Get all functions in a category."""
        return [f for f in self.functions.values() if f.category == category]
    
    def list_all(self) -> List[FunctionMetadata]:
        """Get all registered functions."""
        return list(self.functions.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary for JSON export."""
        return {
            "functions": {
                name: metadata.to_dict()
                for name, metadata in self.functions.items()
            }
        }


def get_default_registry() -> FunctionRegistry:
    """
    Create and populate the default function registry with Jayatilake experiment functions.
    
    This registry catalogs all functions from jayatilake_experiment_cell_functions.py
    """
    registry = FunctionRegistry()
    
    # =========================================================================
    # STANDARD WORKFLOW ORCHESTRATOR FUNCTIONS
    # =========================================================================

    registry.register(FunctionMetadata(
        name="standard_intracellular_update",
        display_name="Standard Intracellular Update",
        description="Default intracellular workflow: metabolism → gene networks → phenotypes → death",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["population", "simulator", "gene_network", "config", "dt", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    registry.register(FunctionMetadata(
        name="standard_diffusion_update",
        display_name="Standard Diffusion Update",
        description="Default diffusion workflow: run diffusion solver with cell reactions",
        category=FunctionCategory.DIFFUSION,
        parameters=[],
        inputs=["population", "simulator", "gene_network", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    registry.register(FunctionMetadata(
        name="standard_intercellular_update",
        display_name="Standard Intercellular Update",
        description="Default intercellular workflow: division and migration",
        category=FunctionCategory.INTERCELLULAR,
        parameters=[],
        inputs=["population", "simulator", "gene_network", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    # =========================================================================
    # GRANULAR WORKFLOW FUNCTIONS (for GUI customization)
    # =========================================================================

    # --- Granular Intracellular Functions ---

    registry.register(FunctionMetadata(
        name="update_metabolism",
        display_name="Update Metabolism",
        description="Update intracellular metabolism (ATP, metabolites)",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["population", "simulator", "gene_network", "config", "dt", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.functions.intracellular.update_metabolism",
        source_file="src/workflow/functions/intracellular/update_metabolism.py"
    ))

    registry.register(FunctionMetadata(
        name="update_gene_networks",
        display_name="Update Gene Networks",
        description="Update gene networks based on environment (hypoxia, glycolysis genes)",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["population", "simulator", "gene_network", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.functions.intracellular.update_gene_networks",
        source_file="src/workflow/functions/intracellular/update_gene_networks.py"
    ))

    registry.register(FunctionMetadata(
        name="update_phenotypes",
        display_name="Update Phenotypes",
        description="Update cell phenotypes based on gene states (glycolytic vs oxidative)",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["population", "simulator", "gene_network", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.functions.intracellular.update_phenotypes",
        source_file="src/workflow/functions/intracellular/update_phenotypes.py"
    ))

    registry.register(FunctionMetadata(
        name="remove_dead_cells",
        display_name="Remove Dead Cells",
        description="Remove cells with ATP below death threshold",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["population", "simulator", "gene_network", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.functions.intracellular.remove_dead_cells",
        source_file="src/workflow/functions/intracellular/remove_dead_cells.py"
    ))

    # --- Granular Diffusion Functions ---

    registry.register(FunctionMetadata(
        name="run_diffusion_solver",
        display_name="Run Diffusion Solver",
        description="Run diffusion PDE solver (oxygen, glucose, lactate, H+, pH). Connect individual substance parameter nodes (with name, diffusion_coeff, etc.) and solver parameter nodes.",
        category=FunctionCategory.DIFFUSION,
        parameters=[
            ParameterDefinition(
                name="max_iterations",
                display_name="Max Iterations",
                description="Maximum iterations for diffusion solver",
                type="int",
                default=1000,
                required=False
            ),
            ParameterDefinition(
                name="tolerance",
                display_name="Tolerance",
                description="Convergence tolerance for diffusion solver",
                type="float",
                default=1e-6,
                required=False
            ),
            ParameterDefinition(
                name="solver_type",
                display_name="Solver Type",
                description="Type of solver (steady_state or transient)",
                type="str",
                default="steady_state",
                required=False
            ),
        ],
        inputs=["population", "simulator", "gene_network", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.functions.diffusion.run_diffusion_solver",
        source_file="src/workflow/functions/diffusion/run_diffusion_solver.py"
    ))

    # --- Granular Intercellular Functions ---

    registry.register(FunctionMetadata(
        name="update_cell_division",
        display_name="Update Cell Division",
        description="ATP-based cell division (divide when ATP > threshold)",
        category=FunctionCategory.INTERCELLULAR,
        parameters=[],
        inputs=["population", "simulator", "gene_network", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.functions.intercellular.update_cell_division",
        source_file="src/workflow/functions/intercellular/update_cell_division.py"
    ))

    registry.register(FunctionMetadata(
        name="update_cell_migration",
        display_name="Update Cell Migration",
        description="Cell migration (placeholder for custom migration logic)",
        category=FunctionCategory.INTERCELLULAR,
        parameters=[],
        inputs=["population", "simulator", "gene_network", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.functions.intercellular.update_cell_migration",
        source_file="src/workflow/functions/intercellular/update_cell_migration.py"
    ))

    registry.register(FunctionMetadata(
        name="minimal_intracellular",
        display_name="Minimal Intracellular (No Phenotype Update)",
        description="Intracellular update without phenotype changes",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    registry.register(FunctionMetadata(
        name="no_death_intracellular",
        display_name="Intracellular Without Death",
        description="Intracellular update that prevents cell death",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    # =========================================================================
    # INITIALIZATION STAGE FUNCTIONS
    # =========================================================================

    registry.register(FunctionMetadata(
        name="load_config_file",
        display_name="Load Configuration File",
        description="Load YAML configuration file and initialize simulation infrastructure",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="config_file",
                type=ParameterType.STRING,
                description="Path to YAML configuration file",
                default="tests/jayatilake_experiment/jayatilake_experiment_config.yaml",
                required=True
            )
        ],
        inputs=["context"],
        outputs=["config", "simulator", "population", "gene_network"],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    registry.register(FunctionMetadata(
        name="load_cells_from_vtk",
        display_name="Load Cells from VTK File",
        description="Load initial cell state from a VTK file",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="file_path",
                type=ParameterType.STRING,
                description="Path to VTK file (relative to microc-2.0 root or absolute)",
                default="tools/generated_h5/cells_200um_domain_domain.vtk",
                required=True
            )
        ],
        inputs=["context"],
        outputs=["loaded_cells"],
        cloneable=False,
        module_path="src.workflow.functions.initialization",
        source_file="src/workflow/functions/initialization/load_cells_from_vtk.py"
    ))

    registry.register(FunctionMetadata(
        name="load_cells_from_csv",
        display_name="Load Cells from CSV File",
        description="Load initial cell state from a CSV file (2D only)",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="file_path",
                type=ParameterType.STRING,
                description="Path to CSV file (relative to microc-2.0 root or absolute)",
                default="initial_state.csv",
                required=True
            )
        ],
        inputs=["context"],
        outputs=["loaded_cells"],
        cloneable=False,
        module_path="src.workflow.functions.initialization",
        source_file="src/workflow/functions/initialization/load_cells_from_csv.py"
    ))

    # =========================================================================
    # NEW GRANULAR INITIALIZATION FUNCTIONS (NO YAML)
    # =========================================================================

    registry.register(FunctionMetadata(
        name="setup_simulation",
        display_name="Setup Simulation Parameters",
        description="Initialize simulation parameters (name, duration, timestep, output directory)",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="name",
                type=ParameterType.STRING,
                description="Simulation name",
                default="MicroCpy Simulation",
                required=True
            ),
            ParameterDefinition(
                name="duration",
                type=ParameterType.FLOAT,
                description="Total simulation time",
                default=10.0,
                min_value=0.0,
                required=True
            ),
            ParameterDefinition(
                name="dt",
                type=ParameterType.FLOAT,
                description="Timestep size",
                default=0.1,
                min_value=0.001,
                required=True
            ),
            ParameterDefinition(
                name="output_dir",
                type=ParameterType.STRING,
                description="Base output directory",
                default="results",
                required=True
            ),
            ParameterDefinition(
                name="save_interval",
                type=ParameterType.INT,
                description="Save data every N steps",
                default=10,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="diffusion_step",
                type=ParameterType.INT,
                description="Run diffusion every N steps",
                default=1,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="intracellular_step",
                type=ParameterType.INT,
                description="Run intracellular updates every N steps",
                default=1,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="intercellular_step",
                type=ParameterType.INT,
                description="Run intercellular updates every N steps",
                default=1,
                min_value=1,
                required=False
            )
        ],
        inputs=["context"],
        outputs=["simulation_params", "results"],
        cloneable=False,
        module_path="src.workflow.functions.initialization",
        source_file="src/workflow/functions/initialization/setup_simulation.py"
    ))

    registry.register(FunctionMetadata(
        name="setup_domain",
        display_name="Setup Domain and Mesh",
        description="Initialize spatial domain and mesh configuration",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="dimensions",
                type=ParameterType.INT,
                description="2 or 3 for 2D/3D simulation",
                default=3,
                options=[2, 3],
                required=True
            ),
            ParameterDefinition(
                name="size_x",
                type=ParameterType.FLOAT,
                description="Domain size in X direction (micrometers)",
                default=400.0,
                min_value=1.0,
                required=True
            ),
            ParameterDefinition(
                name="size_y",
                type=ParameterType.FLOAT,
                description="Domain size in Y direction (micrometers)",
                default=400.0,
                min_value=1.0,
                required=True
            ),
            ParameterDefinition(
                name="size_z",
                type=ParameterType.FLOAT,
                description="Domain size in Z direction (micrometers)",
                default=400.0,
                min_value=1.0,
                required=False
            ),
            ParameterDefinition(
                name="nx",
                type=ParameterType.INT,
                description="Number of mesh cells in X direction",
                default=25,
                min_value=1,
                required=True
            ),
            ParameterDefinition(
                name="ny",
                type=ParameterType.INT,
                description="Number of mesh cells in Y direction",
                default=25,
                min_value=1,
                required=True
            ),
            ParameterDefinition(
                name="nz",
                type=ParameterType.INT,
                description="Number of mesh cells in Z direction",
                default=25,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="cell_height",
                type=ParameterType.FLOAT,
                description="Biological cell height/thickness (micrometers)",
                default=5.0,
                min_value=0.1,
                required=False
            )
        ],
        inputs=["context"],
        outputs=["config", "mesh_manager"],
        cloneable=False,
        module_path="src.workflow.functions.initialization",
        source_file="src/workflow/functions/initialization/setup_domain.py"
    ))

    registry.register(FunctionMetadata(
        name="setup_substances",
        display_name="Setup Substances and Diffusion",
        description="Initialize substances and create diffusion simulator",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="substances",
                type=ParameterType.LIST,
                description="List of substance definitions (each with name, diffusion_coeff, production_rate, uptake_rate, initial_value, boundary_value, boundary_type, unit)",
                default=[],
                required=True
            ),
            ParameterDefinition(
                name="associations",
                type=ParameterType.DICT,
                description="Dict mapping substance names to gene network inputs",
                default={},
                required=False
            )
        ],
        inputs=["context"],
        outputs=["config.substances", "simulator"],
        cloneable=False,
        module_path="src.workflow.functions.initialization",
        source_file="src/workflow/functions/initialization/setup_substances.py"
    ))

    registry.register(FunctionMetadata(
        name="setup_population",
        display_name="Setup Cell Population",
        description="Initialize cell population and gene network",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="enable_gene_network",
                type=ParameterType.BOOL,
                description="Whether to enable the gene network",
                default=True,
                required=False
            ),
            ParameterDefinition(
                name="custom_functions_module",
                type=ParameterType.STRING,
                description="Path to custom functions module",
                default="src/config/custom_functions.py",
                required=False
            )
        ],
        inputs=["context"],
        outputs=["population", "gene_network"],
        cloneable=False,
        module_path="src.workflow.functions.initialization",
        source_file="src/workflow/functions/initialization/setup_population.py"
    ))

    registry.register(FunctionMetadata(
        name="setup_output",
        display_name="Setup Output Configuration",
        description="Configure output settings for plots and data saving",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="save_data_interval",
                type=ParameterType.INT,
                description="Save data every N steps",
                default=10,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="save_plots_interval",
                type=ParameterType.INT,
                description="Generate plots every N steps",
                default=10,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="save_final_plots",
                type=ParameterType.BOOL,
                description="Generate plots at the end",
                default=True,
                required=False
            ),
            ParameterDefinition(
                name="save_initial_plots",
                type=ParameterType.BOOL,
                description="Generate plots at the beginning",
                default=True,
                required=False
            ),
            ParameterDefinition(
                name="status_print_interval",
                type=ParameterType.INT,
                description="Print status every N steps",
                default=10,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="save_cellstate_interval",
                type=ParameterType.INT,
                description="Save cell states every N steps (0 = disabled)",
                default=0,
                min_value=0,
                required=False
            )
        ],
        inputs=["context"],
        outputs=["config.output"],
        cloneable=False,
        module_path="src.workflow.functions.initialization",
        source_file="src/workflow/functions/initialization/setup_output.py"
    ))

    registry.register(FunctionMetadata(
        name="initialize_cell_placement",
        display_name="Initialize Cell Placement",
        description="Place cells in a spheroid configuration at simulation start",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="initial_cell_count",
                type=ParameterType.INT,
                description="Number of cells to place initially",
                default=50,
                min_value=1,
                max_value=10000
            ),
            ParameterDefinition(
                name="placement_pattern",
                type=ParameterType.STRING,
                description="Pattern for cell placement",
                default="spheroid",
                options=["spheroid", "grid", "random"]
            )
        ],
        inputs=["grid_size", "config"],
        outputs=["cell_placements"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))
    
    registry.register(FunctionMetadata(
        name="initialize_cell_ages",
        display_name="Initialize Cell Ages",
        description="Set initial cell ages with random distribution",
        category=FunctionCategory.INITIALIZATION,
        parameters=[
            ParameterDefinition(
                name="max_cell_age",
                type=ParameterType.FLOAT,
                description="Maximum cell age in hours",
                default=500.0,
                min_value=0.0
            ),
            ParameterDefinition(
                name="cell_cycle_time",
                type=ParameterType.FLOAT,
                description="Cell cycle time in hours",
                default=240.0,
                min_value=0.0
            )
        ],
        inputs=["population", "config"],
        outputs=["updated_population"],
        cloneable=False,
        module_path="jayatilake_experiment_cell_functions"
    ))
    
    # =========================================================================
    # INTRACELLULAR STAGE FUNCTIONS
    # =========================================================================
    
    registry.register(FunctionMetadata(
        name="calculate_cell_metabolism",
        display_name="Calculate Cell Metabolism",
        description="Calculate substance consumption/production using Michaelis-Menten kinetics",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[
            ParameterDefinition(
                name="oxygen_vmax",
                type=ParameterType.FLOAT,
                description="Maximum oxygen consumption rate (mol/cell/s)",
                default=1.0e-16
            ),
            ParameterDefinition(
                name="glucose_vmax",
                type=ParameterType.FLOAT,
                description="Maximum glucose consumption rate (mol/cell/s)",
                default=3.0e-15
            ),
            ParameterDefinition(
                name="KO2",
                type=ParameterType.FLOAT,
                description="Michaelis constant for oxygen (mM)",
                default=0.01
            ),
            ParameterDefinition(
                name="KG",
                type=ParameterType.FLOAT,
                description="Michaelis constant for glucose (mM)",
                default=0.5
            ),
            ParameterDefinition(
                name="KL",
                type=ParameterType.FLOAT,
                description="Michaelis constant for lactate (mM)",
                default=1.0
            )
        ],
        inputs=["local_environment", "cell_state", "config"],
        outputs=["substance_reactions"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))
    
    registry.register(FunctionMetadata(
        name="update_cell_metabolic_state",
        display_name="Update Cell Metabolic State",
        description="Update cell's metabolic state with calculated ATP and metabolic rates",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["cell", "local_environment", "config"],
        outputs=["updated_cell"],
        cloneable=False,
        module_path="jayatilake_experiment_cell_functions"
    ))
    
    registry.register(FunctionMetadata(
        name="should_divide",
        display_name="Check Division (ATP-based)",
        description="Determine if cell should divide based on ATP rate and cell cycle",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[
            ParameterDefinition(
                name="atp_threshold",
                type=ParameterType.FLOAT,
                description="ATP threshold for proliferation (normalized 0-1)",
                default=0.8,
                min_value=0.0,
                max_value=1.0
            ),
            ParameterDefinition(
                name="cell_cycle_time",
                type=ParameterType.FLOAT,
                description="Minimum cell cycle time (hours)",
                default=240.0,
                min_value=0.0
            ),
            ParameterDefinition(
                name="max_atp",
                type=ParameterType.FLOAT,
                description="Maximum ATP per glucose molecule",
                default=30.0
            )
        ],
        inputs=["cell", "config"],
        outputs=["division_decision"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))

    registry.register(FunctionMetadata(
        name="update_cell_phenotype",
        display_name="Update Cell Phenotype",
        description="Determine cell phenotype based on gene network states",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[
            ParameterDefinition(
                name="necrosis_threshold_oxygen",
                type=ParameterType.FLOAT,
                description="Oxygen threshold for necrosis (mM)",
                default=0.011
            ),
            ParameterDefinition(
                name="necrosis_threshold_glucose",
                type=ParameterType.FLOAT,
                description="Glucose threshold for necrosis (mM)",
                default=0.23
            )
        ],
        inputs=["cell_state", "local_environment", "gene_states", "config"],
        outputs=["phenotype"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))

    registry.register(FunctionMetadata(
        name="age_cell",
        display_name="Age Cell",
        description="Update cell age by time step",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["cell", "dt"],
        outputs=["updated_cell"],
        cloneable=False,
        module_path="jayatilake_experiment_cell_functions"
    ))

    registry.register(FunctionMetadata(
        name="check_cell_death",
        display_name="Check Cell Death",
        description="Determine if cell should die based on phenotype",
        category=FunctionCategory.INTRACELLULAR,
        parameters=[],
        inputs=["cell_state", "local_environment"],
        outputs=["death_decision"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))

    # =========================================================================
    # INTERCELLULAR STAGE FUNCTIONS
    # =========================================================================

    registry.register(FunctionMetadata(
        name="select_division_direction",
        display_name="Select Division Direction",
        description="Choose direction for cell division from available positions",
        category=FunctionCategory.INTERCELLULAR,
        parameters=[],
        inputs=["parent_position", "available_positions"],
        outputs=["division_position"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))

    registry.register(FunctionMetadata(
        name="calculate_migration_probability",
        display_name="Calculate Migration Probability",
        description="Calculate probability of cell migration",
        category=FunctionCategory.INTERCELLULAR,
        parameters=[
            ParameterDefinition(
                name="base_migration_rate",
                type=ParameterType.FLOAT,
                description="Base migration probability",
                default=0.0,
                min_value=0.0,
                max_value=1.0
            )
        ],
        inputs=["cell_state", "local_environment", "target_position"],
        outputs=["migration_probability"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))

    # =========================================================================
    # FINALIZATION STAGE FUNCTIONS
    # =========================================================================

    registry.register(FunctionMetadata(
        name="final_report",
        display_name="Generate Final Report",
        description="Print comprehensive final report of all cells",
        category=FunctionCategory.FINALIZATION,
        parameters=[],
        inputs=["population", "local_environments", "config"],
        outputs=["report"],
        cloneable=False,
        module_path="jayatilake_experiment_cell_functions"
    ))

    # =========================================================================
    # TIMING ORCHESTRATION FUNCTIONS
    # =========================================================================

    registry.register(FunctionMetadata(
        name="should_update_intracellular",
        display_name="Should Update Intracellular",
        description="Determine if intracellular processes should update this step",
        category=FunctionCategory.UTILITY,
        parameters=[],
        inputs=["current_step", "last_update", "interval", "state"],
        outputs=["should_update"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))

    registry.register(FunctionMetadata(
        name="should_update_diffusion",
        display_name="Should Update Diffusion",
        description="Determine if diffusion should update this step",
        category=FunctionCategory.UTILITY,
        parameters=[],
        inputs=["current_step", "last_update", "interval", "state"],
        outputs=["should_update"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))

    registry.register(FunctionMetadata(
        name="should_update_intercellular",
        display_name="Should Update Intercellular",
        description="Determine if intercellular processes should update this step",
        category=FunctionCategory.UTILITY,
        parameters=[],
        inputs=["current_step", "last_update", "interval", "state"],
        outputs=["should_update"],
        cloneable=True,
        module_path="jayatilake_experiment_cell_functions"
    ))

    # =========================================================================
    # FINALIZATION STAGE FUNCTIONS
    # =========================================================================

    registry.register(FunctionMetadata(
        name="standard_data_collection",
        display_name="Standard Data Collection",
        description="Collect final simulation statistics (cell counts, substance stats, phenotype distribution)",
        category=FunctionCategory.FINALIZATION,
        parameters=[],
        inputs=["population", "simulator", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    registry.register(FunctionMetadata(
        name="export_final_state",
        display_name="Export Final State",
        description="Export final simulation state for analysis",
        category=FunctionCategory.FINALIZATION,
        parameters=[],
        inputs=["population", "simulator", "config", "helpers"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    registry.register(FunctionMetadata(
        name="generate_summary_plots",
        display_name="Generate Summary Plots",
        description="Generate all automatic plots (substance heatmaps, etc.)",
        category=FunctionCategory.FINALIZATION,
        parameters=[],
        inputs=["context"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    registry.register(FunctionMetadata(
        name="save_simulation_data",
        display_name="Save Simulation Data",
        description="Save simulation results to files (config, time series, substance stats)",
        category=FunctionCategory.FINALIZATION,
        parameters=[
            ParameterDefinition(
                name="save_config",
                type=ParameterType.BOOL,
                description="Save simulation configuration to JSON",
                default=True,
                required=False
            ),
            ParameterDefinition(
                name="save_timeseries",
                type=ParameterType.BOOL,
                description="Save time series data to NPY files",
                default=True,
                required=False
            ),
            ParameterDefinition(
                name="save_substances",
                type=ParameterType.BOOL,
                description="Save substance statistics to JSON",
                default=True,
                required=False
            )
        ],
        inputs=["context"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    registry.register(FunctionMetadata(
        name="print_simulation_summary",
        display_name="Print Simulation Summary",
        description="Print final simulation summary (completion message, statistics)",
        category=FunctionCategory.FINALIZATION,
        parameters=[],
        inputs=["context"],
        outputs=[],
        cloneable=False,
        module_path="src.workflow.standard_functions"
    ))

    return registry

