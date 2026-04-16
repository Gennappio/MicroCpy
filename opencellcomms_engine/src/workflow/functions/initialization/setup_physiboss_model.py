"""
Setup PhysiBoss Model - Load a PhysiCell/PhysiBoss XML configuration.

Parses a PhysiCell XML config file, initialises pyMaBoSS with the referenced
BND/CFG network files, and stores the PhysiBoss coupling configuration in the
workflow context so that subsequent functions (run_physiboss_step,
apply_physiboss_phenotype) can use them.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always


@register_function(
    display_name="Setup PhysiBoss Model",
    description=(
        "Load a PhysiCell/PhysiBoss XML config (domain, substrates, "
        "cell definitions, MaBoSS coupling) into the workflow context"
    ),
    category="INITIALIZATION",
    parameters=[
        {
            "name": "xml_config",
            "type": "STRING",
            "description": "Path to PhysiCell XML configuration file",
            "default": "1_Long_TNF.xml",
        },
        {
            "name": "sample_count",
            "type": "INT",
            "description": "Number of MaBoSS stochastic samples per cell update",
            "default": 1,
            "min_value": 1,
            "max_value": 10000,
        },
        {
            "name": "use_cell_container",
            "type": "BOOL",
            "description": "Use NumPy SoA CellContainer for vectorized operations (recommended for >100 cells)",
            "default": None,
        },
        {
            "name": "verbose",
            "type": "BOOL",
            "description": "Enable detailed logging",
            "default": None,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def setup_physiboss_model(
    context: Dict[str, Any],
    xml_config: str = "1_Long_TNF.xml",
    sample_count: int = 1,
    use_cell_container: Optional[bool] = None,
    verbose: Optional[bool] = None,
    **kwargs,
) -> bool:
    """
    Load a PhysiBoss model from XML and store everything in the context.

    Stores in context:
        physiboss_config:  PhysiBossConfig dataclass
        physiboss_coupling: PhysiBossSubstrateCoupling instance
        physiboss_phenotype_mapper: PhysiBossPhenotypeMapper instance
        maboss_sim:        pyMaBoSS simulation template
        maboss_config:     dict with BND/CFG paths and time params
        physiboss_maboss_networks: {} (populated later per-cell)

    Returns:
        True on success, False on error.
    """
    print("[WORKFLOW] Setting up PhysiBoss model")

    try:
        from src.adapters.physiboss.config_loader import PhysiBossConfigLoader
        from src.adapters.physiboss.coupling import PhysiBossSubstrateCoupling
        from src.adapters.physiboss.phenotype_mapper import PhysiBossPhenotypeMapper
    except ImportError as e:
        log_always(f"[ERROR] PhysiBoss adapter not available: {e}")
        return False

    # ── Resolve XML path ────────────────────────────────────────────────
    xml_path = _resolve_file(xml_config, context)
    if xml_path is None or not xml_path.exists():
        log_always(f"[ERROR] XML config file not found: {xml_config}")
        return False

    # ── Parse XML ───────────────────────────────────────────────────────
    try:
        loader = PhysiBossConfigLoader(str(xml_path))
        config = loader.load()
    except Exception as e:
        log_always(f"[ERROR] Failed to parse XML config: {e}")
        import traceback; traceback.print_exc()
        return False

    log(context, f"Parsed PhysiBoss config: {xml_path.name}", prefix="[+]", node_verbose=verbose)
    log(context, f"  Domain: {config.domain.x_min}..{config.domain.x_max} x "
                 f"{config.domain.y_min}..{config.domain.y_max}", prefix="[+]", node_verbose=verbose)
    log(context, f"  Substrates: {[s.name for s in config.substrates]}", prefix="[+]", node_verbose=verbose)
    log(context, f"  Cell types: {[cd.name for cd in config.cell_definitions]}", prefix="[+]", node_verbose=verbose)

    # ── Setup coupling ──────────────────────────────────────────────────
    coupling_obj = None
    if config.coupling:
        coupling_obj = PhysiBossSubstrateCoupling.from_config(config.coupling)
        log(context, f"  Coupling inputs: {[i.node_name for i in coupling_obj.inputs]}",
            prefix="[+]", node_verbose=verbose)
        log(context, f"  Coupling outputs: {[o.node_name for o in coupling_obj.outputs]}",
            prefix="[+]", node_verbose=verbose)

    # ── Setup phenotype mapper ──────────────────────────────────────────
    mapper = PhysiBossPhenotypeMapper(dt_phenotype=config.timing.dt_phenotype)

    # ── Load MaBoSS model ──────────────────────────────────────────────
    maboss_sim = None
    ic = config.intracellular
    if ic and ic.bnd_file and ic.cfg_file:
        try:
            import maboss
        except ImportError:
            log_always("[ERROR] pyMaBoSS is not installed. pip install maboss")
            return False

        bnd_path = _resolve_file(ic.bnd_file, context, xml_path.parent)
        cfg_path = _resolve_file(ic.cfg_file, context, xml_path.parent)

        if not bnd_path or not bnd_path.exists():
            log_always(f"[ERROR] BND file not found: {ic.bnd_file}")
            return False
        if not cfg_path or not cfg_path.exists():
            log_always(f"[ERROR] CFG file not found: {ic.cfg_file}")
            return False

        log(context, f"  Loading MaBoSS: {bnd_path.name} / {cfg_path.name}",
            prefix="[+]", node_verbose=verbose)

        maboss_sim = maboss.load(str(bnd_path), str(cfg_path))
        maboss_sim.param["sample_count"] = sample_count
        # Scale MaBoSS time to match intracellular_dt
        maboss_sim.param["max_time"] = ic.intracellular_dt / ic.scaling
        maboss_sim.param["time_tick"] = maboss_sim.param["max_time"] / 10.0

        node_names = list(maboss_sim.network.keys())
        log(context, f"  MaBoSS nodes: {node_names}", prefix="[+]", node_verbose=verbose)

    # ── Create CellContainer (NumPy SoA) if requested ─────────────────
    if use_cell_container:
        from src.biology.cell_container import CellContainer
        dims = 2 if config.domain.use_2D else 3
        container = CellContainer(capacity=4096, dimensions=dims)
        # Pre-register BN node columns
        if maboss_sim is not None:
            for node in maboss_sim.network.keys():
                container.add_float_column(f"bn_prob_{node}", default=0.0)
                container.add_bool_column(f"bn_state_{node}", default=False)
        context['cell_container'] = container
        log(context, f"  CellContainer created: {dims}D, capacity={container.capacity}",
            prefix="[+]", node_verbose=verbose)

    # ── Store in context ────────────────────────────────────────────────
    context['physiboss_config'] = config
    context['physiboss_coupling'] = coupling_obj
    context['physiboss_phenotype_mapper'] = mapper
    context['physiboss_maboss_networks'] = {}
    if maboss_sim is not None:
        context['maboss_sim'] = maboss_sim
        context['maboss_config'] = {
            'bnd_file': str(bnd_path),
            'cfg_file': str(cfg_path),
            'intracellular_dt': ic.intracellular_dt,
            'scaling': ic.scaling,
            'sample_count': sample_count,
        }

    print(f"[SETUP_PHYSIBOSS] Model loaded successfully from {xml_path.name}")
    return True


def _resolve_file(
    file_path: str,
    context: Dict[str, Any],
    extra_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Resolve a file path relative to the workflow, project root, or extra_dir."""
    path = Path(file_path)
    if path.is_absolute() and path.exists():
        return path

    # Strategy 1: context['resolve_path'] helper
    if 'resolve_path' in context:
        resolved = context['resolve_path'](file_path)
        if resolved and Path(resolved).exists():
            return Path(resolved)

    # Strategy 2: relative to extra_dir (e.g. XML parent)
    if extra_dir is not None:
        resolved = extra_dir / file_path
        if resolved.exists():
            return resolved

    # Strategy 3: relative to workflow file
    wf = context.get('workflow_file')
    if wf:
        resolved = Path(wf).parent / file_path
        if resolved.exists():
            return resolved

    # Strategy 4: relative to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    resolved = project_root / file_path
    if resolved.exists():
        return resolved

    return path if path.exists() else None
