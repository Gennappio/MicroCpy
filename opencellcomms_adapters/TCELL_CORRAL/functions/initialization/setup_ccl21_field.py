"""Register CCL21 as a diffusing chemokine for the Corral model.

CCL21 is the endothelial-secreted chemokine that dendritic cells climb. It lives
as a FiPy substance on the shared MultiSubstanceSimulator: a diffusion
coefficient, a per-kind secretion (endothelial) / uptake (Th17) rate, and a
first-order decay.

Decay has no slot on ``SubstanceConfig``, so it is stashed in
``context['ccl21_decay_rate']`` for ``diffuse_ccl21`` to apply as a FiPy implicit
sink. All rates are SI (metres, seconds) to match the diffusion solver — the
PhysiCell values (1000 um^2/min, 0.005/min) are pre-converted in the defaults.
"""
from typing import Any, Dict, Optional

from src.workflow.decorators import register_function
from src.interfaces.base import IConfig


@register_function(
    typed_env_exempt=True,
    requires=["simulator"],
    display_name="Setup CCL21 Field",
    description="Register CCL21 as a diffusing chemokine (endothelial source, Th17 sink, "
                "first-order decay) on the shared diffusion simulator.",
    category="INITIALIZATION",
    parameters=[
        {"name": "diffusion_coeff", "type": "FLOAT",
         "description": "CCL21 diffusion coefficient, m^2/s (PhysiCell 1000 um^2/min = 1.667e-11)",
         "default": 1.667e-11},
        {"name": "decay_rate", "type": "FLOAT",
         "description": "First-order decay, 1/s (PhysiCell 0.005/min = 8.333e-5)",
         "default": 8.333e-5},
        {"name": "secretion_rate", "type": "FLOAT",
         "description": "Endothelial CCL21 secretion rate (source magnitude)",
         "default": 10.0},
        {"name": "uptake_rate", "type": "FLOAT",
         "description": "Th17 CCL21 uptake, 1/s first-order sink (PhysiCell 0.5/min = 8.333e-3)",
         "default": 8.333e-3},
        {"name": "initial_value", "type": "FLOAT",
         "description": "Initial uniform CCL21 concentration",
         "default": 0.0},
    ],
    inputs=["context"],
    outputs=["simulator"],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def setup_ccl21_field(
    context: Dict[str, Any],
    diffusion_coeff: float = 1.667e-11,
    decay_rate: float = 8.333e-5,
    secretion_rate: float = 10.0,
    uptake_rate: float = 8.333e-3,
    initial_value: float = 0.0,
    **kwargs,
) -> bool:
    config: Optional[IConfig] = context.get("config")
    simulator = context.get("simulator")
    if not config or not simulator:
        print("[TCELL_CORRAL] Config and simulator must be set up before CCL21")
        return False

    from src.workflow.functions.diffusion.run_diffusion_solver import _configure_substances

    # production_rate / uptake_rate are carried on the SubstanceConfig and read
    # back per-kind by diffuse_ccl21 (endothelial secretes, Th17 takes up).
    ccl21 = {
        "name": "CCL21",
        "diffusion_coeff": diffusion_coeff,
        "production_rate": secretion_rate,
        "uptake_rate": uptake_rate,
        "initial_value": initial_value,
        "boundary_value": 0.0,
        "boundary_type": "neumann",     # Dirichlet off -> no-flux edges (PhysiCell)
        "unit": "mM",
    }
    _configure_substances(config, simulator, [ccl21])
    context["ccl21_decay_rate"] = float(decay_rate)
    print(f"[TCELL_CORRAL] CCL21 field ready (D={diffusion_coeff:.3e} m^2/s, "
          f"decay={decay_rate:.3e}/s, secretion={secretion_rate}, uptake={uptake_rate})")
    return True
