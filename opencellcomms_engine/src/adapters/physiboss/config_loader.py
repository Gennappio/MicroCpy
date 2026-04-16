"""
PhysiBoss Config Loader - Parse PhysiCell XML configuration into Python dataclasses.

Reads a PhysiCell/PhysiBoss XML config file (e.g. 1_Long_TNF.xml) and produces
a PhysiBossConfig object containing domain, timing, substrates, cell definitions,
intracellular coupling, initial cell placement, and treatment schedule.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DomainConfig:
    """Spatial domain configuration."""
    x_min: float = -500.0
    x_max: float = 500.0
    y_min: float = -500.0
    y_max: float = 500.0
    z_min: float = -10.0
    z_max: float = 10.0
    dx: float = 20.0
    dy: float = 20.0
    dz: float = 20.0
    use_2D: bool = True


@dataclass
class TimingConfig:
    """Multi-timescale timing configuration."""
    max_time: float = 10080.0       # minutes
    dt_diffusion: float = 0.01      # finest timescale
    dt_mechanics: float = 0.1
    dt_phenotype: float = 6.0
    intracellular_dt: float = 12.0  # MaBoSS update interval


@dataclass
class DirichletConfig:
    """Dirichlet boundary condition for a substrate."""
    enabled: bool = False
    value: float = 0.0
    xmin: bool = True
    xmax: bool = True
    ymin: bool = True
    ymax: bool = True
    zmin: bool = True
    zmax: bool = True


@dataclass
class SubstrateConfig:
    """Configuration for a single diffusing substrate."""
    name: str = ""
    diffusion_coefficient: float = 0.0   # µm²/min
    decay_rate: float = 0.0              # 1/min
    initial_condition: float = 0.0
    dirichlet: DirichletConfig = field(default_factory=DirichletConfig)


@dataclass
class InputMapping:
    """Maps a substance concentration to a MaBoSS input node."""
    substance_name: str = ""
    node_name: str = ""
    threshold: float = 0.0
    action: str = "activation"   # activation | inhibition
    inact_threshold: float = 0.0
    smoothing: float = 0.0


@dataclass
class OutputMapping:
    """Maps a MaBoSS output node to a PhysiCell phenotype behaviour."""
    node_name: str = ""
    behaviour_name: str = ""     # e.g. "apoptosis", "necrosis"
    value: float = 0.0           # rate when node is ON
    base_value: float = 0.0      # rate when node is OFF
    action: str = "activation"
    smoothing: float = 0.0


@dataclass
class CouplingConfig:
    """Input/output coupling between BN and cell phenotype."""
    inputs: List[InputMapping] = field(default_factory=list)
    outputs: List[OutputMapping] = field(default_factory=list)


@dataclass
class IntracellularConfig:
    """MaBoSS intracellular model configuration."""
    bnd_file: str = ""
    cfg_file: str = ""
    intracellular_dt: float = 12.0
    scaling: float = 1.0
    time_stochasticity: float = 0.0
    inheritance_global: float = 1.0   # fraction of BN state inherited on division
    coupling: CouplingConfig = field(default_factory=CouplingConfig)


@dataclass
class SecretionConfig:
    """Per-substrate secretion parameters for a cell definition."""
    substrate_name: str = ""
    secretion_rate: float = 0.0
    uptake_rate: float = 0.0
    net_export_rate: float = 0.0


@dataclass
class DeathModelConfig:
    """Death model (apoptosis or necrosis) parameters."""
    model_name: str = ""      # "apoptosis" or "necrosis"
    death_rate: float = 0.0   # 1/min
    phase_durations: List[float] = field(default_factory=list)
    phase_transition_rates: List[float] = field(default_factory=list)


@dataclass
class CycleConfig:
    """Cell cycle configuration."""
    model: str = "flow_cytometry_separated_cycle_model"
    phase_durations: List[float] = field(default_factory=list)
    phase_transition_rates: List[float] = field(default_factory=list)


@dataclass
class VolumeConfig:
    """Cell volume parameters."""
    total: float = 2494.0
    fluid_fraction: float = 0.75
    nuclear: float = 540.0
    fluid_change_rate: float = 0.05
    cytoplasmic_biomass_change_rate: float = 0.0045
    nuclear_biomass_change_rate: float = 0.0055
    calcified_fraction: float = 0.0
    calcification_rate: float = 0.0
    target_solid_cytoplasmic: float = 486.0
    target_solid_nuclear: float = 135.0
    target_fluid_fraction: float = 0.75


@dataclass
class MechanicsConfig:
    """Cell mechanics parameters."""
    cell_cell_adhesion_strength: float = 0.4
    cell_cell_repulsion_strength: float = 10.0
    relative_maximum_adhesion_distance: float = 1.25
    cell_BM_adhesion_strength: float = 4.0
    cell_BM_repulsion_strength: float = 10.0
    attachment_elastic_constant: float = 0.01
    attachment_rate: float = 0.0
    detachment_rate: float = 0.0


@dataclass
class MotilityConfig:
    """Cell motility parameters."""
    speed: float = 1.0
    persistence_time: float = 1.0
    migration_bias: float = 0.0
    motility_enabled: bool = False
    use_2D: bool = True
    chemotaxis_enabled: bool = False
    chemotaxis_substrate: str = ""
    chemotaxis_direction: int = 1  # 1 = up gradient, -1 = down


@dataclass
class CellDefinitionConfig:
    """Configuration for a cell type."""
    name: str = "default"
    cycle: CycleConfig = field(default_factory=CycleConfig)
    death_models: List[DeathModelConfig] = field(default_factory=list)
    volume: VolumeConfig = field(default_factory=VolumeConfig)
    mechanics: MechanicsConfig = field(default_factory=MechanicsConfig)
    motility: MotilityConfig = field(default_factory=MotilityConfig)
    secretion: List[SecretionConfig] = field(default_factory=list)
    intracellular: Optional[IntracellularConfig] = None
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InitialCellsConfig:
    """Initial cell placement configuration."""
    csv_file: Optional[str] = None
    random_count: int = 0


@dataclass
class TreatmentConfig:
    """Treatment schedule (e.g. periodic TNF application)."""
    enabled: bool = False
    substrate: str = ""
    start_time: float = 0.0
    period: float = 0.0       # on+off duration
    duration: float = 0.0     # on duration within period
    concentration: float = 0.0


@dataclass
class SaveConfig:
    """Output save configuration."""
    folder: str = "output"
    interval: float = 60.0   # minutes between saves


@dataclass
class PhysiBossConfig:
    """Top-level configuration parsed from a PhysiCell XML file."""
    domain: DomainConfig = field(default_factory=DomainConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    substrates: List[SubstrateConfig] = field(default_factory=list)
    cell_definitions: List[CellDefinitionConfig] = field(default_factory=list)
    initial_cells: InitialCellsConfig = field(default_factory=InitialCellsConfig)
    treatment: TreatmentConfig = field(default_factory=TreatmentConfig)
    save: SaveConfig = field(default_factory=SaveConfig)

    # Convenience accessors
    @property
    def intracellular(self) -> Optional[IntracellularConfig]:
        """Return the first cell definition's intracellular config, if any."""
        for cd in self.cell_definitions:
            if cd.intracellular is not None:
                return cd.intracellular
        return None

    @property
    def coupling(self) -> Optional[CouplingConfig]:
        """Return the first coupling config found."""
        ic = self.intracellular
        return ic.coupling if ic else None


# ---------------------------------------------------------------------------
# XML Parser
# ---------------------------------------------------------------------------

def _text(el: Optional[ET.Element], default: str = "") -> str:
    """Get text content of an element, stripping whitespace."""
    if el is None:
        return default
    return (el.text or "").strip()


def _float(el: Optional[ET.Element], default: float = 0.0) -> float:
    t = _text(el)
    return float(t) if t else default


def _bool_text(el: Optional[ET.Element], default: bool = False) -> bool:
    t = _text(el).lower()
    if t in ("true", "1", "yes"):
        return True
    if t in ("false", "0", "no"):
        return False
    return default


class PhysiBossConfigLoader:
    """Parses a PhysiCell/PhysiBoss XML config file into a PhysiBossConfig."""

    def __init__(self, xml_path: str, base_dir: Optional[str] = None):
        self.xml_path = Path(xml_path)
        self.base_dir = Path(base_dir) if base_dir else self.xml_path.parent
        self.tree = ET.parse(str(self.xml_path))
        self.root = self.tree.getroot()

    def load(self) -> PhysiBossConfig:
        """Parse the XML and return a PhysiBossConfig."""
        return PhysiBossConfig(
            domain=self._parse_domain(),
            timing=self._parse_timing(),
            substrates=self._parse_substrates(),
            cell_definitions=self._parse_cell_definitions(),
            initial_cells=self._parse_initial_cells(),
            treatment=self._parse_treatment(),
            save=self._parse_save(),
        )

    # -- Domain ---------------------------------------------------------------

    def _parse_domain(self) -> DomainConfig:
        d = self.root.find(".//domain")
        if d is None:
            return DomainConfig()
        return DomainConfig(
            x_min=_float(d.find("x_min"), -500),
            x_max=_float(d.find("x_max"), 500),
            y_min=_float(d.find("y_min"), -500),
            y_max=_float(d.find("y_max"), 500),
            z_min=_float(d.find("z_min"), -10),
            z_max=_float(d.find("z_max"), 10),
            dx=_float(d.find("dx"), 20),
            dy=_float(d.find("dy"), 20),
            dz=_float(d.find("dz"), 20),
            use_2D=_bool_text(d.find("use_2D"), True),
        )

    # -- Timing ---------------------------------------------------------------

    def _parse_timing(self) -> TimingConfig:
        overall = self.root.find(".//overall")
        tc = TimingConfig()
        if overall is not None:
            tc.max_time = _float(overall.find("max_time"), tc.max_time)
            tc.dt_diffusion = _float(overall.find("dt_diffusion"), tc.dt_diffusion)
            tc.dt_mechanics = _float(overall.find("dt_mechanics"), tc.dt_mechanics)
            tc.dt_phenotype = _float(overall.find("dt_phenotype"), tc.dt_phenotype)
        # intracellular_dt is set later from cell_definition/intracellular
        return tc

    # -- Substrates -----------------------------------------------------------

    def _parse_substrates(self) -> List[SubstrateConfig]:
        substrates = []
        for var in self.root.findall(".//microenvironment_setup/variable"):
            name = var.get("name", "")
            pd = var.find("physical_parameter_set")
            dc = var.find("Dirichlet_boundary_condition")
            do = var.find("Dirichlet_options")

            dirichlet = DirichletConfig()
            if dc is not None:
                dirichlet.enabled = dc.get("enabled", "false").lower() == "true"
                dirichlet.value = float(_text(dc, "0"))
            if do is not None:
                for bnd in do.findall("boundary_value"):
                    bid = bnd.get("ID", "")
                    enabled = bnd.get("enabled", "true").lower() == "true"
                    if bid == "xmin":
                        dirichlet.xmin = enabled
                    elif bid == "xmax":
                        dirichlet.xmax = enabled
                    elif bid == "ymin":
                        dirichlet.ymin = enabled
                    elif bid == "ymax":
                        dirichlet.ymax = enabled
                    elif bid == "zmin":
                        dirichlet.zmin = enabled
                    elif bid == "zmax":
                        dirichlet.zmax = enabled

            sc = SubstrateConfig(
                name=name,
                diffusion_coefficient=_float(pd.find("diffusion_coefficient") if pd is not None else None),
                decay_rate=_float(pd.find("decay_rate") if pd is not None else None),
                initial_condition=_float(var.find("initial_condition")),
                dirichlet=dirichlet,
            )
            substrates.append(sc)
        return substrates

    # -- Cell definitions -----------------------------------------------------

    def _parse_cell_definitions(self) -> List[CellDefinitionConfig]:
        defs = []
        for cd_el in self.root.findall(".//cell_definitions/cell_definition"):
            cd = CellDefinitionConfig(name=cd_el.get("name", "default"))
            phenotype = cd_el.find("phenotype")
            if phenotype is not None:
                cd.cycle = self._parse_cycle(phenotype.find("cycle"))
                cd.death_models = self._parse_death(phenotype.find("death"))
                cd.volume = self._parse_volume(phenotype.find("volume"))
                cd.mechanics = self._parse_mechanics(phenotype.find("mechanics"))
                cd.motility = self._parse_motility(phenotype.find("motility"))
                cd.secretion = self._parse_secretion(phenotype.find("secretion"))
                cd.intracellular = self._parse_intracellular(phenotype.find("intracellular"))
            # Custom data
            custom = cd_el.find("custom_data")
            if custom is not None:
                for child in custom:
                    cd.custom_data[child.tag] = _text(child)
            defs.append(cd)
        return defs

    def _parse_cycle(self, el: Optional[ET.Element]) -> CycleConfig:
        cc = CycleConfig()
        if el is None:
            return cc
        cc.model = el.get("name", cc.model)
        durations = []
        rates = []
        for pr in el.findall(".//phase_transition_rates/rate"):
            rates.append(float(_text(pr, "0")))
        for pd in el.findall(".//phase_durations/duration"):
            durations.append(float(_text(pd, "0")))
        cc.phase_durations = durations
        cc.phase_transition_rates = rates
        return cc

    def _parse_death(self, el: Optional[ET.Element]) -> List[DeathModelConfig]:
        models = []
        if el is None:
            return models
        for model_el in el.findall("model"):
            dm = DeathModelConfig(
                model_name=model_el.get("name", ""),
                death_rate=_float(model_el.find("death_rate")),
            )
            for pd in model_el.findall(".//phase_durations/duration"):
                dm.phase_durations.append(float(_text(pd, "0")))
            for pr in model_el.findall(".//phase_transition_rates/rate"):
                dm.phase_transition_rates.append(float(_text(pr, "0")))
            models.append(dm)
        return models

    def _parse_volume(self, el: Optional[ET.Element]) -> VolumeConfig:
        vc = VolumeConfig()
        if el is None:
            return vc
        vc.total = _float(el.find("total"), vc.total)
        vc.fluid_fraction = _float(el.find("fluid_fraction"), vc.fluid_fraction)
        vc.nuclear = _float(el.find("nuclear"), vc.nuclear)
        vc.fluid_change_rate = _float(el.find("fluid_change_rate"), vc.fluid_change_rate)
        vc.cytoplasmic_biomass_change_rate = _float(
            el.find("cytoplasmic_biomass_change_rate"), vc.cytoplasmic_biomass_change_rate
        )
        vc.nuclear_biomass_change_rate = _float(
            el.find("nuclear_biomass_change_rate"), vc.nuclear_biomass_change_rate
        )
        vc.calcified_fraction = _float(el.find("calcified_fraction"), vc.calcified_fraction)
        vc.calcification_rate = _float(el.find("calcification_rate"), vc.calcification_rate)
        vc.target_solid_cytoplasmic = _float(
            el.find("target_solid_cytoplasmic"), vc.target_solid_cytoplasmic
        )
        vc.target_solid_nuclear = _float(el.find("target_solid_nuclear"), vc.target_solid_nuclear)
        vc.target_fluid_fraction = _float(
            el.find("target_fluid_fraction"), vc.target_fluid_fraction
        )
        return vc

    def _parse_mechanics(self, el: Optional[ET.Element]) -> MechanicsConfig:
        mc = MechanicsConfig()
        if el is None:
            return mc
        mc.cell_cell_adhesion_strength = _float(
            el.find("cell_cell_adhesion_strength"), mc.cell_cell_adhesion_strength
        )
        mc.cell_cell_repulsion_strength = _float(
            el.find("cell_cell_repulsion_strength"), mc.cell_cell_repulsion_strength
        )
        mc.relative_maximum_adhesion_distance = _float(
            el.find("relative_maximum_adhesion_distance"),
            mc.relative_maximum_adhesion_distance,
        )
        return mc

    def _parse_motility(self, el: Optional[ET.Element]) -> MotilityConfig:
        mot = MotilityConfig()
        if el is None:
            return mot
        mot.speed = _float(el.find("speed"), mot.speed)
        mot.persistence_time = _float(el.find("persistence_time"), mot.persistence_time)
        mot.migration_bias = _float(el.find("migration_bias"), mot.migration_bias)
        options = el.find("options")
        if options is not None:
            mot.motility_enabled = _bool_text(options.find("enabled"), False)
            mot.use_2D = _bool_text(options.find("use_2D"), True)
            chem = options.find("chemotaxis")
            if chem is not None:
                mot.chemotaxis_enabled = _bool_text(chem.find("enabled"), False)
                mot.chemotaxis_substrate = _text(chem.find("substrate"), "")
                mot.chemotaxis_direction = int(_float(chem.find("direction"), 1))
        return mot

    def _parse_secretion(self, el: Optional[ET.Element]) -> List[SecretionConfig]:
        secs = []
        if el is None:
            return secs
        for sub in el.findall("substrate"):
            secs.append(SecretionConfig(
                substrate_name=sub.get("name", ""),
                secretion_rate=_float(sub.find("secretion_rate")),
                uptake_rate=_float(sub.find("uptake_rate")),
                net_export_rate=_float(sub.find("net_export_rate")),
            ))
        return secs

    def _parse_intracellular(self, el: Optional[ET.Element]) -> Optional[IntracellularConfig]:
        if el is None:
            return None
        ic_type = el.get("type", "")
        if ic_type.lower() != "maboss":
            return None  # only MaBoSS supported

        ic = IntracellularConfig()
        ic.bnd_file = _text(el.find("bnd_file"))
        ic.cfg_file = _text(el.find("cfg_file"))
        ic.intracellular_dt = _float(el.find("time_step"), 12.0)
        ic.scaling = _float(el.find("scaling"), 1.0)
        ic.time_stochasticity = _float(el.find("time_stochasticity"), 0.0)

        # Inheritance
        inh = el.find(".//inheritance")
        if inh is not None:
            ic.inheritance_global = _float(inh.find("global"), 1.0)

        # Coupling mappings
        mapping = el.find(".//mapping")
        if mapping is not None:
            for inp in mapping.findall("input"):
                im = InputMapping(
                    substance_name=inp.get("intracellular", ""),
                    node_name=inp.get("intracellular", ""),
                    threshold=float(inp.get("threshold", "0")),
                    action=inp.get("action", "activation"),
                    inact_threshold=float(inp.get("inact_threshold", "0")),
                    smoothing=float(inp.get("smoothing", "0")),
                )
                # PhysiBoss XML: physicell_name is the substance
                physicell_name = inp.get("physicell_name", "")
                if physicell_name:
                    im.substance_name = physicell_name
                ic.coupling.inputs.append(im)

            for out in mapping.findall("output"):
                om = OutputMapping(
                    node_name=out.get("intracellular", ""),
                    behaviour_name=out.get("physicell_name", ""),
                    value=float(out.get("value", "0")),
                    base_value=float(out.get("base_value", "0")),
                    action=out.get("action", "activation"),
                    smoothing=float(out.get("smoothing", "0")),
                )
                ic.coupling.outputs.append(om)

        return ic

    # -- Initial cells --------------------------------------------------------

    def _parse_initial_cells(self) -> InitialCellsConfig:
        ic = InitialCellsConfig()
        el = self.root.find(".//initial_conditions/cell_positions")
        if el is not None:
            csv_el = el.find("filename")
            if csv_el is not None:
                ic.csv_file = _text(csv_el)
        return ic

    # -- Treatment (user_parameters) ------------------------------------------

    def _parse_treatment(self) -> TreatmentConfig:
        """Parse treatment from user_parameters (PhysiBoss convention)."""
        tc = TreatmentConfig()
        up = self.root.find(".//user_parameters")
        if up is None:
            return tc

        # Look for common treatment parameters
        for param in up:
            tag = param.tag.lower()
            val = _text(param)
            if "treatment" in tag and "duration" in tag:
                tc.duration = float(val) if val else 0.0
                tc.enabled = True
            elif "treatment" in tag and "period" in tag:
                tc.period = float(val) if val else 0.0
            elif "treatment" in tag and "start" in tag:
                tc.start_time = float(val) if val else 0.0
            elif "treatment" in tag and "concentration" in tag:
                tc.concentration = float(val) if val else 0.0
            elif "treatment" in tag and "substrate" in tag:
                tc.substrate = val

        return tc

    # -- Save -----------------------------------------------------------------

    def _parse_save(self) -> SaveConfig:
        sc = SaveConfig()
        save_el = self.root.find(".//save")
        if save_el is not None:
            sc.folder = _text(save_el.find("folder"), sc.folder)
            sc.interval = _float(save_el.find(".//interval"), sc.interval)
        return sc
