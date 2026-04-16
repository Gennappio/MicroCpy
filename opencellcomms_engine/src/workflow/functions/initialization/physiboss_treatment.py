"""
PhysiBoss Treatment - Toggle Dirichlet boundary conditions for treatment.

Applies or removes a substrate treatment (e.g. TNF) on a periodic schedule
by enabling/disabling Dirichlet boundary conditions on the diffusion solver.

This implements PhysiCell's pulsed-treatment protocol where a substance is
applied at its boundary value for a set duration, then removed.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always


@register_function(
    display_name="PhysiBoss Treatment",
    description=(
        "Toggle Dirichlet boundary conditions for pulsed substance "
        "treatment (e.g. periodic TNF application)"
    ),
    category="INITIALIZATION",
    parameters=[
        {
            "name": "substrate",
            "type": "STRING",
            "description": "Name of the substrate to toggle (e.g. 'tnf')",
            "default": "tnf",
        },
        {
            "name": "start_time",
            "type": "FLOAT",
            "description": "Time (minutes) when treatment begins",
            "default": 0.0,
        },
        {
            "name": "period",
            "type": "FLOAT",
            "description": "Total period (on + off) in minutes. 0 = always on.",
            "default": 0.0,
        },
        {
            "name": "duration",
            "type": "FLOAT",
            "description": "Duration within each period that treatment is active (minutes)",
            "default": 0.0,
        },
        {
            "name": "concentration",
            "type": "FLOAT",
            "description": "Dirichlet boundary value when treatment is ON",
            "default": 0.5,
        },
        {
            "name": "use_physiboss_config",
            "type": "BOOL",
            "description": "If True, read treatment parameters from loaded PhysiBoss config",
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
def physiboss_treatment(
    context: Dict[str, Any],
    substrate: str = "tnf",
    start_time: float = 0.0,
    period: float = 0.0,
    duration: float = 0.0,
    concentration: float = 0.5,
    use_physiboss_config: Optional[bool] = None,
    verbose: Optional[bool] = None,
    **kwargs,
) -> None:
    """
    Toggle Dirichlet BCs for pulsed treatment.

    Called each step; decides whether treatment is ON or OFF based on
    the current simulation time and the periodic schedule.
    """
    current_step = context.get('current_step', 0)
    dt = context.get('dt', 1.0)
    current_time = current_step * dt  # in simulation time units

    # Optionally pull params from PhysiBoss config
    if use_physiboss_config:
        pb_config = context.get('physiboss_config')
        if pb_config and pb_config.treatment.enabled:
            treatment = pb_config.treatment
            substrate = treatment.substrate or substrate
            start_time = treatment.start_time
            period = treatment.period
            duration = treatment.duration
            concentration = treatment.concentration

    # Determine if treatment is ON this step
    treatment_on = False
    if current_time >= start_time:
        if period > 0:
            time_in_cycle = (current_time - start_time) % period
            treatment_on = time_in_cycle < duration
        else:
            # No period = always on after start_time
            treatment_on = True

    # Store state for logging/inspection (always, even without simulator)
    context.setdefault('physiboss_treatment_state', {})[substrate] = treatment_on
    if treatment_on:
        context['physiboss_treatment_state'][f'{substrate}_concentration'] = concentration

    # Apply to simulator if available
    simulator = context.get('simulator')
    if simulator is not None:
        try:
            if treatment_on:
                simulator.set_dirichlet_bc(substrate, concentration, enabled=True)
            else:
                simulator.set_dirichlet_bc(substrate, 0.0, enabled=False)
        except AttributeError:
            pass  # Simulator doesn't support set_dirichlet_bc — state already stored

    if current_step % 100 == 0:
        state_str = "ON" if treatment_on else "OFF"
        log(context, f"Treatment [{substrate}] = {state_str} at t={current_time:.1f} min",
            prefix="[Tx]", node_verbose=verbose)
