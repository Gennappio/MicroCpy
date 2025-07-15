from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from core.units import Length, Concentration

@dataclass
class DomainConfig:
    """Domain configuration with unit validation"""
    size_x: Length
    size_y: Length
    nx: int
    ny: int
    dimensions: int = 2
    cell_height: Length = field(default_factory=lambda: Length(20.0, "μm"))  # Biological cell height/thickness
    
    def __post_init__(self):
        # Validate grid spacing consistency (flexible)
        actual_dx = Length(self.size_x.meters / self.nx, "m")
        actual_dy = Length(self.size_y.meters / self.ny, "m")

        # Check that grid is square (dx = dy)
        if abs(actual_dx.micrometers - actual_dy.micrometers) > 0.1:
            raise ValueError(f"Grid must be square! "
                           f"dx = {actual_dx}, dy = {actual_dy}")

        # Check reasonable grid spacing (1-50 μm)
        if actual_dx.micrometers < 1.0 or actual_dx.micrometers > 50.0:
            raise ValueError(f"Grid spacing {actual_dx} outside reasonable range (1-50 μm)")
    
    @property
    def cell_volume_um3(self) -> float:
        """Cell volume in μm³ - single source of truth"""
        dx_um = self.size_x.micrometers / self.nx
        dy_um = self.size_y.micrometers / self.ny
        height_um = self.cell_height.micrometers  # Configurable cell height
        return dx_um * dy_um * height_um

@dataclass
class TimeConfig:
    dt: float
    end_time: float
    diffusion_step: int = 5
    intracellular_step: int = 1
    intercellular_step: int = 10

@dataclass
class DiffusionConfig:
    """Configuration for steady state diffusion solver"""
    max_iterations: int = 1000      # Maximum iterations for convergence
    tolerance: float = 1e-6         # Convergence tolerance
    solver_type: str = "steady_state"  # "steady_state" or "transient"
    twodimensional_adjustment_coefficient: float = 1.0  # No adjustment needed (mesh volume already includes thickness)

@dataclass
class OutputConfig:
    save_data_interval: int = 1        # Save data every N steps (1 = every step)
    save_plots_interval: int = 50      # Generate plots every N steps
    save_final_plots: bool = True      # Always save plots at the end
    save_initial_plots: bool = True    # Always save plots at the beginning
    status_print_interval: int = 10    # Print detailed status every N steps
    
@dataclass
class SubstanceConfig:
    name: str
    diffusion_coeff: float  # m²/s
    production_rate: float  # mol/s/cell
    uptake_rate: float      # mol/s/cell
    initial_value: Concentration
    boundary_value: Concentration
    boundary_type: str = "fixed"

@dataclass
class ThresholdConfig:
    name: str
    initial: float
    threshold: float

@dataclass
class AssociationConfig:
    substance: str
    gene_input: str

@dataclass
class GeneNodeConfig:
    name: str
    inputs: List[str] = field(default_factory=list)
    logic: str = ""  # Boolean expression as string
    is_input: bool = False
    is_output: bool = False
    default_state: bool = False

@dataclass
class GeneNetworkConfig:
    nodes: Dict[str, GeneNodeConfig] = field(default_factory=dict)
    input_nodes: List[str] = field(default_factory=list)
    output_nodes: List[str] = field(default_factory=list)
    propagation_steps: int = 3  # Number of steps for signal propagation
    bnd_file: Optional[str] = None  # Path to .bnd file for Boolean network definition
    random_initialization: bool = True  # NetLogo-style random gene initialization (default: True to match NetLogo)

@dataclass
class CompositeGeneConfig:
    """Configuration for composite gene inputs (derived from other gene inputs)"""
    name: str
    inputs: List[str]  # List of input gene names
    logic: str         # Logic expression: "AND", "OR", "NOT input1", etc.

@dataclass
class EnvironmentConfig:
    """Configuration for environmental parameters"""
    ph: float = 7.4

@dataclass
class MicroCConfig:
    """Master configuration - single source of truth"""
    domain: DomainConfig
    time: TimeConfig
    diffusion: DiffusionConfig
    substances: Dict[str, SubstanceConfig]
    associations: Dict[str, str] = field(default_factory=dict)  # substance -> gene_input
    thresholds: Dict[str, ThresholdConfig] = field(default_factory=dict)
    composite_genes: List[CompositeGeneConfig] = field(default_factory=list)  # composite gene logic
    gene_network: Optional[GeneNetworkConfig] = None
    gene_network_steps: int = 3  # Default propagation steps if no full gene network config
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    output: OutputConfig = field(default_factory=OutputConfig)  # Output and saving configuration
    output_dir: Path = Path("results")
    plots_dir: Path = Path("plots")
    data_dir: Path = Path("data")
    custom_functions_path: Optional[str] = None
    custom_parameters: Dict[str, Any] = field(default_factory=dict)  # Custom parameters for user functions
    debug_phenotype_detailed: bool = False  # Flag to enable detailed phenotype debugging
    log_simulation_status: bool = False  # Flag to enable structured simulation status logging
    
    @classmethod
    def load_from_yaml(cls, config_file: Path) -> 'MicroCConfig':
        with open(config_file) as f:
            data = yaml.safe_load(f)
        
        # Convert to proper types with validation
        domain = DomainConfig(
            size_x=Length(data['domain']['size_x'], data['domain']['size_x_unit']),
            size_y=Length(data['domain']['size_y'], data['domain']['size_y_unit']),
            nx=data['domain']['nx'],
            ny=data['domain']['ny'],
            cell_height=Length(
                data['domain'].get('cell_height', 20.0),
                data['domain'].get('cell_height_unit', 'μm')
            )
        )
        
        time = TimeConfig(
            dt=data['time']['dt'],
            end_time=data['time']['end_time'],
            diffusion_step=data['time']['diffusion_step'],
            intracellular_step=data['time']['intracellular_step'],
            intercellular_step=data['time']['intercellular_step']
        )

        # Diffusion configuration (optional, with defaults)
        diffusion = DiffusionConfig()
        if 'diffusion' in data:
            diffusion = DiffusionConfig(
                max_iterations=data['diffusion'].get('max_iterations', 1000),
                tolerance=data['diffusion'].get('tolerance', 1e-6),
                solver_type=data['diffusion'].get('solver_type', 'steady_state'),
                twodimensional_adjustment_coefficient=data['diffusion'].get('twodimensional_adjustment_coefficient', 1.0)
            )

        # Output configuration (optional)
        output = OutputConfig()
        if 'output' in data:
            output = OutputConfig(
                save_data_interval=data['output'].get('save_data_interval', 1),
                save_plots_interval=data['output'].get('save_plots_interval', 50),
                save_final_plots=data['output'].get('save_final_plots', True),
                save_initial_plots=data['output'].get('save_initial_plots', True),
                status_print_interval=data['output'].get('status_print_interval', 10)
            )
        
        substances = {}
        for name, sub_data in data['substances'].items():
            substances[name] = SubstanceConfig(
                name=name,
                diffusion_coeff=sub_data['diffusion_coeff'],
                production_rate=sub_data['production_rate'],
                uptake_rate=sub_data['uptake_rate'],
                initial_value=Concentration(sub_data['initial_value'], "mM"),
                boundary_value=Concentration(sub_data['boundary_value'], "mM"),
                boundary_type=sub_data['boundary_type']
            )

        # Load associations (substance -> gene_input mapping)
        associations = data.get('associations', {})

        # Load thresholds
        thresholds = {}
        for name, thresh_data in data.get('thresholds', {}).items():
            thresholds[name] = ThresholdConfig(
                name=name,
                initial=thresh_data['initial'],
                threshold=thresh_data['threshold']
            )

        # Load gene network configuration
        gene_network = None
        if 'gene_network' in data:
            gene_net_data = data['gene_network']
            nodes = {}
            for name, node_data in gene_net_data.get('nodes', {}).items():
                nodes[name] = GeneNodeConfig(
                    name=name,
                    inputs=node_data.get('inputs', []),
                    logic=node_data.get('logic', ''),
                    is_input=node_data.get('is_input', False),
                    is_output=node_data.get('is_output', False),
                    default_state=node_data.get('default_state', False)
                )

            gene_network = GeneNetworkConfig(
                nodes=nodes,
                input_nodes=gene_net_data.get('input_nodes', []),
                output_nodes=gene_net_data.get('output_nodes', []),
                propagation_steps=gene_net_data.get('propagation_steps', 3),
                bnd_file=gene_net_data.get('bnd_file', None)
            )

        # Load environment configuration
        environment = EnvironmentConfig()
        if 'environment' in data:
            env_data = data['environment']
            environment = EnvironmentConfig(
                ph=env_data.get('ph', 7.4)
            )

        # Load composite gene configurations
        composite_genes = []
        if 'composite_genes' in data:
            for comp_data in data['composite_genes']:
                composite_genes.append(CompositeGeneConfig(
                    name=comp_data['name'],
                    inputs=comp_data['inputs'],
                    logic=comp_data['logic']
                ))

        return cls(
            domain=domain,
            time=time,
            diffusion=diffusion,
            substances=substances,
            associations=associations,
            thresholds=thresholds,
            composite_genes=composite_genes,
            gene_network=gene_network,
            gene_network_steps=data.get('gene_network_steps', 3),
            environment=environment,
            output=output,
            output_dir=Path(data.get('output_dir', 'results')),
            plots_dir=Path(data.get('plots_dir', 'plots')),
            data_dir=Path(data.get('data_dir', 'data')),
            custom_functions_path=data.get('custom_functions_path'),
            custom_parameters=data.get('custom_parameters', {}),
            debug_phenotype_detailed=data.get('debug_phenotype_detailed', False),
            log_simulation_status=data.get('log_simulation_status', False)
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MicroCConfig':
        """Create configuration from dictionary (same as from_yaml but for dict input)"""
        # Domain configuration
        domain_data = data['domain']
        domain = DomainConfig(
            size_x=Length(domain_data['size_x'], domain_data['size_x_unit']),
            size_y=Length(domain_data['size_y'], domain_data['size_y_unit']),
            nx=domain_data['nx'],
            ny=domain_data['ny'],
            dimensions=domain_data['dimensions'],
            cell_height=Length(
                domain_data.get('cell_height', 20.0),
                domain_data.get('cell_height_unit', 'μm')
            )
        )

        # Time configuration
        time_data = data['time']
        time = TimeConfig(
            dt=time_data['dt'],
            end_time=time_data['end_time'],
            diffusion_step=time_data['diffusion_step'],
            intracellular_step=time_data['intracellular_step'],
            intercellular_step=time_data['intercellular_step']
        )

        # Diffusion configuration (optional, with defaults)
        diffusion = DiffusionConfig()
        if 'diffusion' in data:
            diffusion = DiffusionConfig(
                max_iterations=data['diffusion'].get('max_iterations', 1000),
                tolerance=data['diffusion'].get('tolerance', 1e-6),
                solver_type=data['diffusion'].get('solver_type', 'steady_state'),
                twodimensional_adjustment_coefficient=data['diffusion'].get('twodimensional_adjustment_coefficient', 1.0)
            )

        # Substances
        substances = {}
        for name, sub_data in data['substances'].items():
            substances[name] = SubstanceConfig(
                name=name,
                diffusion_coeff=sub_data['diffusion_coeff'],
                production_rate=sub_data['production_rate'],
                uptake_rate=sub_data['uptake_rate'],
                initial_value=Concentration(sub_data['initial_value'], "mM"),
                boundary_value=Concentration(sub_data['boundary_value'], "mM"),
                boundary_type=sub_data['boundary_type']
            )

        # Associations and thresholds
        associations = data.get('associations', {})
        thresholds = {}
        for name, thresh_data in data.get('thresholds', {}).items():
            thresholds[name] = ThresholdConfig(
                name=name,
                initial=thresh_data['initial'],
                threshold=thresh_data['threshold']
            )

        # Gene network (same as load_from_yaml)
        gene_network = None
        if 'gene_network' in data:
            gene_net_data = data['gene_network']
            nodes = {}
            for name, node_data in gene_net_data.get('nodes', {}).items():
                nodes[name] = GeneNodeConfig(
                    name=name,
                    inputs=node_data.get('inputs', []),
                    logic=node_data.get('logic', ''),
                    is_input=node_data.get('is_input', False),
                    is_output=node_data.get('is_output', False),
                    default_state=node_data.get('default_state', False)
                )

            gene_network = GeneNetworkConfig(
                nodes=nodes,
                input_nodes=gene_net_data.get('input_nodes', []),
                output_nodes=gene_net_data.get('output_nodes', []),
                propagation_steps=gene_net_data.get('propagation_steps', 3),
                bnd_file=gene_net_data.get('bnd_file', None)
            )

        # Output configuration (same as load_from_yaml)
        output = OutputConfig()
        if 'output' in data:
            output = OutputConfig(
                save_data_interval=data['output'].get('save_data_interval', 1),
                save_plots_interval=data['output'].get('save_plots_interval', 50),
                save_final_plots=data['output'].get('save_final_plots', True),
                save_initial_plots=data['output'].get('save_initial_plots', True),
                status_print_interval=data['output'].get('status_print_interval', 10)
            )

        return cls(
            domain=domain,
            time=time,
            diffusion=diffusion,
            substances=substances,
            associations=associations,
            thresholds=thresholds,
            gene_network=gene_network,
            gene_network_steps=data.get('gene_network_steps', 3),
            output=output,
            output_dir=Path(data.get('output_dir', 'results')),
            plots_dir=Path(data.get('plots_dir', 'plots')),
            data_dir=Path(data.get('data_dir', 'data')),
            custom_functions_path=data.get('custom_functions_path'),
            debug_phenotype_detailed=data.get('debug_phenotype_detailed', False),
            log_simulation_status=data.get('log_simulation_status', False)
        )
    
    def validate(self) -> bool:
        """Comprehensive validation to catch our previous errors"""
        # 1. Check grid spacing is reasonable
        actual_spacing = Length(self.domain.size_x.meters / self.domain.nx, "m")
        assert 1.0 <= actual_spacing.micrometers <= 50.0, f"Grid spacing {actual_spacing} outside reasonable range"
        
        # 2. Check domain size consistency
        if abs(self.domain.size_x.micrometers - 800.0) > 1.0 and abs(self.domain.size_x.micrometers - 500.0) > 1.0:
            raise ValueError(f"Unexpected domain size: {self.domain.size_x.micrometers} μm (expected 500 or 800 μm)")
        
        # 3. Check volume calculation consistency
        expected_volume = 8000.0  # μm³ for 20×20×20 cell
        actual_volume = self.domain.cell_volume_um3
        assert abs(actual_volume - expected_volume) < 100, f"Volume wrong: {actual_volume} vs {expected_volume}"
        
        return True
