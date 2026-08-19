"""
Define the cell metabolism model: the constants of the Michaelis-Menten
consumption/production laws used by the coupled diffusion solver.

WHY THIS NODE EXISTS
    The metabolism itself is computed inside ``_recalculate_metabolism``, a
    private helper of ``run_diffusion_solver_coupled`` in the engine. It is not
    a node, so neither the equations nor their constants were visible or
    editable from the GUI -- a scientist could not see, let alone change, the
    metabolic model their tumour was running on. This node makes the constants
    a first-class, canvas-visible, Planner-tunable parameter, and states the
    equations here so they can be read alongside the values.

    (``setup_custom_parameters`` in the engine looks like it should do this, but
    it writes ``config.custom_parameters`` while the metabolism reads
    ``context['custom_parameters']``, and nothing mirrors one to the other -- so
    it has no effect on metabolism. This node writes both.)

THE EQUATIONS, exactly as the solver implements them
    Per cell, with the local concentrations at that cell's grid position and the
    saturation terms

        mm_O2  = C_O2  / (KO2 + C_O2)
        mm_Glc = C_Glc / (KG  + C_Glc)
        mm_Lac = C_Lac / (KL  + C_Lac)

    an OXPHOS cell (gene mitoATP ON) contributes

        O2  -= oxygen_vmax * mito_multiplier * mm_O2
        Glc -= (oxygen_vmax / 6) * mm_Glc * mm_O2
        Lac -= (oxygen_vmax * 2/6) * mm_Lac * mm_O2        (consumes lactate)

    a glycolytic cell (gene glycoATP ON) contributes

        O2  -= oxygen_vmax * glyco_oxygen_ratio * mm_O2
        g    = (oxygen_vmax / 6) * (max_atp / 2) * mm_Glc
        Glc -= g
        Lac += g * 3                                        (produces lactate)

    and every cell contributes protons

        H   += (oxygen_vmax * 2/6) * proton_coefficient * (max_atp / 2) * mm_Glc

    Oxygen therefore follows
        R_O2 = oxygen_vmax * mm_O2 * (mitoATP + glyco_oxygen_ratio * glycoATP)
    which is the standard form with glyco_oxygen_ratio as the K of that law.

    The three ``*_conversion_factor`` parameters on run_diffusion_solver_coupled
    scale the RESULTS of the above; the constants here shape the laws.

NOT INCLUDED, because the solver reads them and then never uses them:
    ``glucose_vmax`` -- glucose consumption is derived from oxygen_vmax/6, so
    this value has no effect. Listing it here would imply a control that does
    not exist.
"""

from typing import Any, Dict, Union

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


# The values the solver falls back to when nothing sets them, which is what
# MicroC has always effectively run with. Keeping these as the node defaults
# means adding the node to a workflow changes no results.
DEFAULTS: Dict[str, float] = {
    "oxygen_vmax": 3.0e-17,        # mol/s/cell; matches the Jayatilake reference
    "KO2": 0.005,                  # mM; NetLogo "the-optimal-oxygen"
    "KG": 0.5,                     # mM
    "KL": 1.0,                     # mM
    "max_atp": 30.0,               # ATP per glucose
    "glyco_oxygen_ratio": 0.5,     # O2 cost of glycolysis relative to OXPHOS
    "proton_coefficient": 0.001,
}


def resolve_metabolism_parameters(context: Dict[str, Any]) -> Dict[str, float]:
    """The metabolic constants in effect: DEFAULTS overlaid with whatever this
    node stored in ``context['custom_parameters']`` (unknown keys ignored).

    The single resolution rule (R2.2): ``compute_metabolism`` and every other
    reader of these constants (e.g. the ATP-gate snapshot published by
    ``mark_proliferating_cells_gated``) resolve through here, so the values a
    plot or checkpoint reports are provably the ones the solver ran with.
    """
    values = dict(DEFAULTS)
    values.update({k: v for k, v in (context.get('custom_parameters') or {}).items()
                   if k in DEFAULTS})
    return values


@register_function(
    requires=[],
    display_name="Set Metabolism Parameters",
    description="Constants of the Michaelis-Menten metabolism used by the coupled "
                "diffusion solver (oxygen_vmax, KO2, KG, KL, max_atp, "
                "glyco_oxygen_ratio, proton_coefficient). See the node source for "
                "the full equations.",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "metabolism_parameters",
            "type": "DICT",
            "description": "Metabolic constants. Any key omitted keeps its default. "
                           "oxygen_vmax (mol/s/cell), KO2/KG/KL (mM Michaelis "
                           "constants), max_atp (ATP per glucose), "
                           "glyco_oxygen_ratio (glycolysis O2 cost vs OXPHOS), "
                           "proton_coefficient.",
            "default": {},
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def set_metabolism_parameters(
    env: BiologicalContext,
    metabolism_parameters: Union[Dict[str, Any], None] = None,
    **kwargs
) -> bool:
    values = dict(DEFAULTS)
    for key, raw in dict(metabolism_parameters or {}).items():
        if key not in DEFAULTS:
            print(f"[METABOLISM] WARNING: '{key}' is not a metabolism constant the "
                  f"solver reads — ignoring. Known keys: {sorted(DEFAULTS)}")
            continue
        try:
            values[key] = float(raw)
        except (TypeError, ValueError):
            print(f"[METABOLISM] WARNING: '{key}={raw!r}' is not a number — "
                  f"keeping default {DEFAULTS[key]}")

    ctx = env.raw_context
    # The solver reads context['custom_parameters']; other functions
    # (update_cell_division) read config.custom_parameters. Write both so the
    # values are honoured wherever they are looked up.
    ctx.setdefault('custom_parameters', {}).update(values)
    config = ctx.get('config')
    if config is not None:
        existing = getattr(config, 'custom_parameters', None)
        if not isinstance(existing, dict):
            existing = {}
        existing.update(values)
        config.custom_parameters = existing

    changed = {k: v for k, v in values.items() if v != DEFAULTS[k]}
    print(f"[METABOLISM] Parameters set: {values}")
    if changed:
        print(f"   [+] non-default: {changed}")
    return True
