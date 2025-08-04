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
    size_z: Optional[Length] = None  # Z dimension for 3D simulations
    nz: Optional[int] = None  # Z grid points for 3D simulations
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
        """Cell volume in μm³ - handles both 2D and 3D simulations"""
        dx_um = self.size_x.micrometers / self.nx
        dy_um = self.size_y.micrometers / self.ny

        if self.dimensions == 3 and self.size_z is not None and self.nz is not None:
            # For 3D simulations: dx × dy × dz
            dz_um = self.size_z.micrometers / self.nz
            return dx_um * dy_um * dz_um
        else:
            # For 2D simulations: area × height
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
    threshold: float
    initial: Optional[float] = None  # Optional - can be derived from substance initial_value

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
        config_dir = config_file.parent
        with open(config_file) as f:
            data = yaml.safe_load(f)

        # Resolve paths relative to the config file directory
        if 'gene_network' in data and 'bnd_file' in data['gene_network']:
            bnd_file_path = config_dir / data['gene_network']['bnd_file']
            if not bnd_file_path.exists():
                raise FileNotFoundError(f"bnd_file not found at resolved path: {bnd_file_path}")
            data['gene_network']['bnd_file'] = str(bnd_file_path)

        if 'custom_functions_path' in data and data['custom_functions_path']:
            custom_functions_path = config_dir / data['custom_functions_path']
            if not custom_functions_path.exists():
                raise FileNotFoundError(f"custom_functions_path not found at resolved path: {custom_functions_path}")
            data['custom_functions_path'] = str(custom_functions_path)

        # Convert to proper types with validation
        domain_data = data['domain']
        domain = DomainConfig(
            size_x=Length(domain_data['size_x'], domain_data['size_x_unit']),
            size_y=Length(domain_data['size_y'], domain_data['size_y_unit']),
            size_z=Length(domain_data['size_z'], domain_data['size_z_unit']) if 'size_z' in domain_data else None,
            nx=domain_data['nx'],
            ny=domain_data['ny'],
            nz=domain_data.get('nz', None),
            dimensions=domain_data.get('dimensions', 2),
            cell_height=Length(
                domain_data['cell_height'],
                domain_data['cell_height_unit']
            )
        )
        
        time = TimeConfig(
            dt=data['time']['dt'],
            end_time=data['time']['end_time'],
            diffusion_step=data['time']['diffusion_step'],
            intracellular_step=data['time']['intracellular_step'],
            intercellular_step=data['time']['intercellular_step']
        )

        # Diffusion configuration (required)
        diffusion = DiffusionConfig(
            max_iterations=data['diffusion']['max_iterations'],
            tolerance=data['diffusion']['tolerance'],
            solver_type=data['diffusion']['solver_type'],
            twodimensional_adjustment_coefficient=data['diffusion']['twodimensional_adjustment_coefficient']
        )

        # Output configuration (required)
        output = OutputConfig(
            save_data_interval=data['output']['save_data_interval'],
            save_plots_interval=data['output']['save_plots_interval'],
            save_final_plots=data['output']['save_final_plots'],
            save_initial_plots=data['output']['save_initial_plots'],
            status_print_interval=data['output']['status_print_interval']
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
        associations = data['associations']

        # Load thresholds
        thresholds = {}
        for name, thresh_data in data['thresholds'].items():
            thresholds[name] = ThresholdConfig(
                name=name,
                threshold=thresh_data['threshold'],
                initial=thresh_data.get('initial')  # Optional field
            )

        # Load gene network configuration
        gene_network = None
        if 'gene_network' in data:
            gene_net_data = data['gene_network']
            nodes = {}
            for name, node_data in gene_net_data['nodes'].items():
                # For nodes defined in .bnd files, inputs and logic are optional in YAML
                inputs = node_data.get('inputs', []) if 'bnd_file' in gene_net_data else node_data['inputs']
                logic = node_data.get('logic', '') if 'bnd_file' in gene_net_data else node_data['logic']
                # is_output defaults to False if not specified (most nodes are not output nodes)
                is_output = node_data.get('is_output', False)

                nodes[name] = GeneNodeConfig(
                    name=name,
                    inputs=inputs,
                    logic=logic,
                    is_input=node_data['is_input'],
                    is_output=is_output,
                    default_state=node_data['default_state']
                )

            # Derive input_nodes from nodes marked as is_input=True if not explicitly specified
            input_nodes = gene_net_data.get('input_nodes', [name for name, node in nodes.items() if node.is_input])

            gene_network = GeneNetworkConfig(
                nodes=nodes,
                input_nodes=input_nodes,
                output_nodes=gene_net_data['output_nodes'],
                propagation_steps=gene_net_data['propagation_steps'],
                bnd_file=gene_net_data['bnd_file']
            )

        # Load environment configuration
        environment = EnvironmentConfig(
            ph=data['environment']['ph']
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
            gene_network_steps=data.get('gene_network_steps', gene_network.propagation_steps if gene_network else 3),
            environment=environment,
            output=output,
            output_dir=Path(data['output_dir']),
            plots_dir=Path(data['plots_dir']),
            data_dir=Path(data['data_dir']),
            custom_functions_path=data['custom_functions_path'],
            custom_parameters=data['custom_parameters'],
            debug_phenotype_detailed=data['debug_phenotype_detailed'],
            log_simulation_status=data['log_simulation_status']
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MicroCConfig':
        """Create configuration from dictionary (same as from_yaml but for dict input)"""
        # Domain configuration
        domain_data = data['domain']
        domain = DomainConfig(
            size_x=Length(domain_data['size_x'], domain_data['size_x_unit']),
            size_y=Length(domain_data['size_y'], domain_data['size_y_unit']),
            size_z=Length(domain_data['size_z'], domain_data['size_z_unit']) if 'size_z' in domain_data else None,
            nx=domain_data['nx'],
            ny=domain_data['ny'],
            nz=domain_data.get('nz', None),
            dimensions=domain_data.get('dimensions', 2),
            cell_height=Length(
                domain_data['cell_height'],
                domain_data['cell_height_unit']
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

        # Diffusion configuration (required)
        diffusion = DiffusionConfig(
            max_iterations=data['diffusion']['max_iterations'],
            tolerance=data['diffusion']['tolerance'],
            solver_type=data['diffusion']['solver_type'],
            twodimensional_adjustment_coefficient=data['diffusion']['twodimensional_adjustment_coefficient']
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
        associations = data['associations']
        thresholds = {}
        for name, thresh_data in data['thresholds'].items():
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
            for name, node_data in gene_net_data['nodes'].items():
                # For nodes defined in .bnd files, inputs and logic are optional in YAML
                inputs = node_data.get('inputs', []) if 'bnd_file' in gene_net_data else node_data['inputs']
                logic = node_data.get('logic', '') if 'bnd_file' in gene_net_data else node_data['logic']
                # is_output defaults to False if not specified (most nodes are not output nodes)
                is_output = node_data.get('is_output', False)

                nodes[name] = GeneNodeConfig(
                    name=name,
                    inputs=inputs,
                    logic=logic,
                    is_input=node_data['is_input'],
                    is_output=is_output,
                    default_state=node_data['default_state']
                )

            # Derive input_nodes from nodes marked as is_input=True if not explicitly specified
            input_nodes = gene_net_data.get('input_nodes', [name for name, node in nodes.items() if node.is_input])

            gene_network = GeneNetworkConfig(
                nodes=nodes,
                input_nodes=input_nodes,
                output_nodes=gene_net_data['output_nodes'],
                propagation_steps=gene_net_data['propagation_steps'],
                bnd_file=gene_net_data['bnd_file']
            )

        # Output configuration (required)
        output = OutputConfig(
            save_data_interval=data['output']['save_data_interval'],
            save_plots_interval=data['output']['save_plots_interval'],
            save_final_plots=data['output']['save_final_plots'],
            save_initial_plots=data['output']['save_initial_plots'],
            status_print_interval=data['output']['status_print_interval']
        )

        return cls(
            domain=domain,
            time=time,
            diffusion=diffusion,
            substances=substances,
            associations=associations,
            thresholds=thresholds,
            gene_network=gene_network,
            gene_network_steps=data.get('gene_network_steps', gene_network.propagation_steps if gene_network else 3),
            output=output,
            output_dir=Path(data['output_dir']),
            plots_dir=Path(data['plots_dir']),
            data_dir=Path(data['data_dir']),
            custom_functions_path=data['custom_functions_path'],
            debug_phenotype_detailed=data['debug_phenotype_detailed'],
            log_simulation_status=data['log_simulation_status']
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
