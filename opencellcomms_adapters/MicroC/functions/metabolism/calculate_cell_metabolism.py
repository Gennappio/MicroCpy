"""
Cell metabolism: how each cell consumes oxygen and glucose and produces lactate
and protons, given its ATP mode and the concentrations where it sits.

This is the MicroC metabolic model. It is experiment-specific biology, not
generic ABM infrastructure, so it lives here as an editable node rather than
inside the engine's diffusion solver. Change the equations in this file and the
model changes; the constants are set separately by ``set_metabolism_parameters``.

HOW IT IS DRIVEN
    ``run_diffusion_solver_coupled`` needs the metabolic rates recomputed at the
    *current* concentrations on every Picard coupling iteration -- that inner
    recomputation is what lets Michaelis-Menten saturation pull consumption down
    as a substance approaches zero, and it is why this cannot simply be a
    once-per-tick node in the scheduler.

    So this node does two things when it runs. It computes one pass immediately,
    and it publishes itself on the context as the metabolism the solver should
    call. The solver then invokes THIS function once per coupling iteration
    instead of its own built-in copy. Placing the node on the diffusion_step
    canvas is what activates it; remove the node and the solver falls back to
    its internal default.

WHO IS SKIPPED
    Fate weighting follows the NetLogo patch count n_cell − 0.5·n_growth_arrest
    − n_necrosis: necrotic cells get an all-zero metabolic_state (written, not
    skipped — stale rates would otherwise keep feeding the solver) and
    growth-arrested cells exchange at half rate.

THE MODEL
    With local concentrations at the cell's grid position, the saturation terms

        mm_O2  = C_O2  / (KO2 + C_O2)
        mm_Glc = C_Glc / (KG  + C_Glc)
        mm_Lac = C_Lac / (KL  + C_Lac)

    OXPHOS (gene mitoATP ON) -- burns oxygen, and can consume lactate:

        O2  -= oxygen_vmax * mito_multiplier * mm_O2
        Glc -= (oxygen_vmax / 6) * mm_Glc * mm_O2
        Lac -= (oxygen_vmax * 2/6) * mm_Lac * mm_O2

    Glycolysis (gene glycoATP ON) -- cheap in oxygen, produces lactate:

        O2  -= oxygen_vmax * glyco_oxygen_ratio * mm_O2
        g    = (oxygen_vmax / 6) * (max_atp / 2) * mm_Glc
        Glc -= g
        Lac += 3 * g

    Protons, from glycolytic flux, independent of ATP mode:

        H   += (oxygen_vmax * 2/6) * proton_coefficient * (max_atp / 2) * mm_Glc

    Oxygen therefore obeys
        R_O2 = oxygen_vmax * mm_O2 * (mitoATP + glyco_oxygen_ratio * glycoATP)

    The three *_conversion_factor parameters on run_diffusion_solver_coupled
    scale the results of the above.

ATP PRODUCTION RATE
    With A0 = max_atp (ATP yield per glucose through OXPHOS):

        R_ATP = A0 * (oxygen_vmax/6) * mm_O2 * mm_Glc   (mitoATP)
              + A0 * (oxygen_vmax/6) * mm_Glc           (glycoATP)

    The two terms are consistent with the consumption laws above. OXPHOS burns
    (oxygen_vmax/6)*mm_Glc*mm_O2 glucose at A0 ATP per glucose; glycolysis burns
    A0/2 times more glucose at 2 ATP per glucose, which is the same A0*vmax/6.

    NOT MODELLED: lactate-fuelled OXPHOS produces no ATP here. Lactate is still
    consumed (mm_Lac term above), it just does not feed R_ATP. The NetLogo
    original and the legacy port do add an MCT1 ATP term; this model omits it
    deliberately.

    The saturation ceiling of a single pathway,

        atp_rate_max = A0 * oxygen_vmax / 6

    is stored alongside R_ATP so consumers compare against one derived number
    instead of re-deriving it from the constants. A cell running both pathways
    at full saturation reaches 2 * atp_rate_max. This is the derivation the
    NetLogo source intended for `the-cell-atp-rate-max`
    (microC_Metabolic_Symbiosis.nlogo3d:2856-2858), where the assignment is
    commented out and the global therefore stays at 0.

    R_ATP is deliberately NOT scaled by the *_conversion_factor arguments:
    those are solver-side scalings of the PDE source terms, not biology.
"""

from typing import Any, Dict, Optional

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext

from opencellcomms_adapters.MicroC.functions.metabolism.set_metabolism_parameters import DEFAULTS
from src.core.coords import cell_to_solver_index

# NetLogo patch weighting (n_cell − 0.5·n_growth_arrest − n_necrosis):
# necrotic cells contribute NOTHING to consumption/production, growth-arrested
# cells contribute at HALF rate.
_FATE_WEIGHTS = {'Necrosis': 0.0, 'Growth_Arrest': 0.5}

# Written to necrotic cells. Overwriting matters: skipping the cell would
# leave its last pre-necrosis rates in metabolic_state, and the reaction
# collector (which reads metabolic_state with no phenotype check) would keep
# the dead cell consuming and producing forever.
_ZERO_METABOLISM = {
    'oxygen_consumption': 0.0,
    'glucose_consumption': 0.0,
    'lactate_production': 0.0,
    'lactate_consumption': 0.0,
    'h_production': 0.0,
    'atp_rate': 0.0,
}


def compute_metabolism(context: Dict[str, Any], simulator, population, config,
                       oxygen_conversion_factor: float = 1.0,
                       glucose_conversion_factor: float = 1.0,
                       lactate_conversion_factor: float = 1.0,
                       oxygen_consumption_multiplier: float = 1.0,
                       verbose: Optional[bool] = None) -> None:
    """Recompute every cell's metabolic_state at the current concentrations.

    Signature matches what run_diffusion_solver_coupled calls each coupling
    iteration. Keep it that way if you edit this file.
    """
    try:
        conc = simulator.get_substance_concentrations()
    except Exception as exc:
        print(f"[METABOLISM] could not read concentrations: {exc}")
        return

    p = dict(DEFAULTS)
    p.update({k: v for k, v in (context.get('custom_parameters') or {}).items() if k in DEFAULTS})

    has_domain = config is not None and getattr(config, 'domain', None) is not None
    cell_size_um = 20.0

    updated, n_mito, n_glyco = {}, 0, 0

    for cell_id, cell in population.state.cells.items():
        phenotype = cell.state.phenotype
        name = phenotype.name if hasattr(phenotype, 'name') else (str(phenotype) if phenotype else None)
        weight = _FATE_WEIGHTS.get(name, 1.0)
        if weight == 0.0:
            cell.state = cell.state.with_updates(metabolic_state=dict(_ZERO_METABOLISM))
            updated[cell_id] = cell
            continue

        pos = cell.state.position
        if has_domain:
            # Shared bio-grid -> solver-voxel law; (gx, gy) in 2D,
            # (gx, gy, gz) in 3D, matching the concentrations dict keys.
            key = cell_to_solver_index(config, pos)
        else:
            key = (int((pos[0] * cell_size_um) / 30.0),
                   int((pos[1] * cell_size_um) / 30.0))

        o2 = max(0.0, conc.get('Oxygen', {}).get(key, 0.0))
        glc = max(0.0, conc.get('Glucose', {}).get(key, 0.0))
        lac = max(0.0, conc.get('Lactate', {}).get(key, 0.0))

        genes = cell.state.gene_states or {}
        mito = bool(genes.get('mitoATP', False))
        glyco = bool(genes.get('glycoATP', False))
        n_mito += mito
        n_glyco += glyco

        mm_o2 = o2 / (p['KO2'] + o2) if (p['KO2'] + o2) > 0 else 0.0
        mm_glc = glc / (p['KG'] + glc) if (p['KG'] + glc) > 0 else 0.0
        mm_lac = lac / (p['KL'] + lac) if (p['KL'] + lac) > 0 else 0.0

        vmax = p['oxygen_vmax']
        o2_use = glc_use = lac_prod = lac_use = 0.0

        if mito:
            o2_use += vmax * oxygen_consumption_multiplier * mm_o2
            glc_use += (vmax / 6.0) * mm_glc * mm_o2
            lac_use += (vmax * 2.0 / 6.0) * mm_lac * mm_o2

        if glyco:
            o2_use += vmax * p['glyco_oxygen_ratio'] * mm_o2
            g = (vmax / 6.0) * (p['max_atp'] / 2.0) * mm_glc
            glc_use += g
            lac_prod += g * 3.0

        h_prod = (vmax * 2.0 / 6.0) * p['proton_coefficient'] * (p['max_atp'] / 2.0) * mm_glc

        atp_rate = 0.0
        if mito:
            atp_rate += p['max_atp'] * (vmax / 6.0) * mm_o2 * mm_glc
        if glyco:
            atp_rate += p['max_atp'] * (vmax / 6.0) * mm_glc

        # Exchange rates carry the fate weight (0.5 for Growth_Arrest, per the
        # NetLogo patch weighting); atp_rate stays per-cell — it feeds the
        # proliferation gate, not the PDE.
        cell.state = cell.state.with_updates(metabolic_state={
            'oxygen_consumption': o2_use * oxygen_conversion_factor * weight,
            'glucose_consumption': glc_use * glucose_conversion_factor * weight,
            'lactate_production': lac_prod * lactate_conversion_factor * weight,
            'lactate_consumption': lac_use * weight,
            'h_production': h_prod * weight,
            'atp_rate': atp_rate,
            'atp_rate_max': p['max_atp'] * vmax / 6.0,
        })
        updated[cell_id] = cell

    population.state = population.state.with_updates(cells=updated)

    if verbose:
        print(f"[METABOLISM] node: {len(updated)} cells, mitoATP={n_mito}, "
              f"glycoATP={n_glyco}, KO2={p['KO2']}, oxygen_vmax={p['oxygen_vmax']:.2e}")


@register_function(
    requires=['population'],
    display_name="Calculate Cell Metabolism",
    description="MicroC metabolic model: per-cell oxygen/glucose consumption, "
                "lactate/proton production and ATP production rate from the mitoATP "
                "and glycoATP gene states, with Michaelis-Menten saturation. Place it "
                "before the diffusion solver; the solver then calls it once per "
                "coupling iteration.",
    category="INTRACELLULAR",
    parameters=[
        {"name": "verbose", "type": "BOOL",
         "description": "Log per-iteration cell counts and the constants in use",
         "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True,
    compatible_kernels=["biophysics"],
)
def calculate_cell_metabolism(env: BiologicalContext, verbose: bool = False, **kwargs) -> bool:
    ctx = env.raw_context
    # Publish this function as the metabolism the coupled solver must call each
    # Picard iteration. The solver looks for this key and falls back to its own
    # built-in copy when the node is absent from the canvas.
    ctx['metabolism_fn'] = compute_metabolism
    ctx['metabolism_fn_verbose'] = verbose

    simulator = ctx.get('simulator')
    population = env.cells.raw
    if simulator is None or population is None:
        # Nothing to compute yet at init time; the solver will drive it.
        print("[METABOLISM] node registered (no simulator/population yet — "
              "the diffusion solver will drive it)")
        return True

    compute_metabolism(ctx, simulator, population, env.config, verbose=verbose)
    return True
