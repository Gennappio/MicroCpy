"""Diffuse CCL21 to steady state each step: endothelial source, Th17 sink, decay.

Solves the steady-state reaction-diffusion balance

    D * laplacian(c) - (k + u_Th17)*c + secretion(endothelial) = 0

on the shared FiPy mesh. Two things the generic ``run_diffusion_solver_coupled``
cannot do are handled here: (1) the endothelial source is **kind-gated** (that
cell has no gene network, so the gene-gated growth-factor path never fires), and
(2) the first-order decay ``k`` (from ``cfg.decay_rate``, now a first-class
``SubstanceConfig`` field) is added as a FiPy ``ImplicitSourceTerm``, together
with the Th17 uptake, applied as an implicit sink on the *current* concentration
(not the previous step's field) so a strong sink cannot set up the step-to-step
oscillation an explicit sink would. Runs once per step as a world behaviour (no
for_each).
"""
import numpy as np

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext

try:
    from fipy import CellVariable, DiffusionTerm, ImplicitSourceTerm
    # Direct LU: the mesh is small (~900 cells) and the CCL21 source magnitudes
    # are large, which makes the iterative GMRES solver hit its iteration cap
    # (a noisy DivergenceWarning). A direct solve is exact and warning-free here.
    from fipy.solvers.scipy import LinearLUSolver as Solver
    _HAVE_FIPY = True
except Exception:
    _HAVE_FIPY = False


@register_function(
    requires=["population", "simulator"],
    display_name="Diffuse CCL21",
    description="Steady-state CCL21 diffusion with endothelial secretion, Th17 uptake, "
                "and first-order decay read from the substance config.",
    category="DIFFUSION",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def diffuse_ccl21(env: BiologicalContext, **kwargs) -> bool:
    if not _HAVE_FIPY:
        print("[TCELL_CORRAL] FiPy unavailable; CCL21 diffusion skipped")
        return False

    ctx = env.raw_context
    config = env.config                      # typed accessor; simulator/population below
    simulator = ctx.get("simulator")         # need the low-level FiPy internals (no typed API)
    population = ctx.get("population")        # need per-cell metabolic_state (_kind / fate)
    if config is None or simulator is None or population is None:
        return False
    if "CCL21" not in simulator.state.substances:
        print("[TCELL_CORRAL] CCL21 not configured; run setup_ccl21_field first")
        return False

    cfg = simulator.state.substances["CCL21"].config
    secretion = float(getattr(cfg, "production_rate", 0.0) or 0.0)
    uptake = float(getattr(cfg, "uptake_rate", 0.0) or 0.0)
    decay = float(getattr(cfg, "decay_rate", 0.0) or 0.0)

    dom = config.domain
    gsx = dom.size_x.micrometers / dom.nx
    gsy = dom.size_y.micrometers / dom.ny
    cell_um = dom.cell_height.micrometers

    # Endothelial cells secrete a constant source (kind-gated: no gene network).
    # Th17 uptake is applied below as an implicit first-order sink coefficient,
    # not as a source term read from the previous field.
    reactions = {}
    n_src = n_sink = 0
    sink_coeff = np.full(dom.nx * dom.ny, decay, dtype=float)   # first-order decay everywhere
    for cell in population.state.cells.values():
        kind = cell.state.metabolic_state.get("_kind")
        pos = cell.state.position
        if kind == "endothelial_cell":
            reactions.setdefault(pos, {})["CCL21"] = secretion
            n_src += 1
        elif kind == "tcell" and cell.state.metabolic_state.get("fate") == "Th17":
            gx = max(0, min(dom.nx - 1, int(pos[0] * cell_um / gsx)))
            gy = max(0, min(dom.ny - 1, int(pos[1] * cell_um / gsy)))
            sink_coeff[gx * dom.ny + gy] += uptake     # FiPy 2D index x*ny+y; implicit on current c
            n_sink += 1

    # Reuse the simulator's bio-grid -> mesh mapping for the endothelial source, then
    # solve  D*laplacian(c) - (k + uptake_Th17)*c == -source.  Th17 uptake is an
    # ImplicitSourceTerm on the current concentration (as in PhysiCell/BioFVM), so the
    # strong sink is stable instead of oscillating with the previous step's field.
    source_field = simulator._create_source_field_from_reactions("CCL21", reactions)
    source_var = CellVariable(mesh=simulator.fipy_mesh, value=source_field)
    sink_var = CellVariable(mesh=simulator.fipy_mesh, value=sink_coeff)
    var = simulator.fipy_variables["CCL21"]
    D = float(cfg.diffusion_coeff)

    equation = DiffusionTerm(coeff=D) - ImplicitSourceTerm(coeff=sink_var) == -source_var
    try:
        equation.solve(var=var, solver=Solver())
    except Exception as e:
        print(f"[TCELL_CORRAL] CCL21 solve failed: {e}")
        return False

    field = np.array(var.value).reshape((dom.ny, dom.nx), order="F")
    simulator.state.substances["CCL21"].concentrations = field
    py, px = np.unravel_index(int(field.argmax()), field.shape)   # field is [ny, nx]
    print(f"[CCL21] {n_src} source(s), {n_sink} sink(s) | field min={field.min():.3e} "
          f"max={field.max():.3e} mean={field.mean():.3e} | peak at mesh (x={px}, y={py})")
    return True
