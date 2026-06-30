"""diffuse_substances — env-style collective diffusion behaviour.

Drives the coupled diffusion-reaction solve over all substance resources on the
domain. The substances are ``DiffusingResource``s sharing one
``MultiSubstanceSimulator`` (see ``src/abm/resource.py``); this behaviour runs the
existing Picard coupling machinery (``run_diffusion_solver_coupled``) over them,
so the numerics are identical to the legacy diffusion path by construction.

This is the env-style entry the new ABM motor uses in place of the legacy
context-dict ``run_diffusion_solver_coupled`` node. (Stage 4 of the MicroC ABM
migration adapts the metabolism recompute inside the loop to read
``abm_population`` agents; until then it reuses the legacy ``population`` path
unchanged — see docs/MICROC_ABM_MIGRATION_PLAN.md.)
"""
from src.biology.context import BiologicalContext
from src.workflow.decorators import register_function
from src.workflow.functions.diffusion.run_diffusion_solver_coupled import (
    run_diffusion_solver_coupled,
)


@register_function(
    requires=["simulator"],
    display_name="Diffuse Substances",
    description="Coupled diffusion-reaction solve over all substance resources",
    category="DIFFUSION",
    parameters=[
        {"name": "max_coupling_iterations", "type": "INT", "default": 10, "min_value": 1},
        {"name": "coupling_tolerance", "type": "FLOAT", "default": 1e-4, "min_value": 0.0},
        {"name": "relaxation_factor", "type": "FLOAT", "default": 0.7,
         "min_value": 0.1, "max_value": 1.0},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["*"],
)
def diffuse_substances(env: BiologicalContext,
                       max_coupling_iterations: int = 10,
                       coupling_tolerance: float = 1e-4,
                       relaxation_factor: float = 0.7,
                       **kwargs) -> None:
    run_diffusion_solver_coupled(
        env.raw_context,
        max_coupling_iterations=int(max_coupling_iterations),
        coupling_tolerance=float(coupling_tolerance),
        relaxation_factor=float(relaxation_factor),
    )
