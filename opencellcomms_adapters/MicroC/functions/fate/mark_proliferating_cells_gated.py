"""
Mark cells as Proliferation only when the gene, the energy budget AND the cell
cycle clock all allow it.

This is the ATP-gated variant of ``mark_proliferating_cells``. The plain version
promotes a cell on the Proliferation gene alone; this one adds the two conditions
from the NetLogo original's -FATE-PROLIFERATION-102 rule:

    Proliferation gene ON
      AND  atp_rate > atp_threshold1 * atp_rate_max
      AND  age > cell_cycle_time

Both functions exist so microc.json and microc_p53_v2.json stay comparable. Pick
one per canvas -- do not run both.

WHERE THE NUMBERS COME FROM
    ``atp_rate`` and ``atp_rate_max`` are written per cell by the metabolism node
    (MicroC/functions/metabolism/calculate_cell_metabolism.py), recomputed at the
    current concentrations on every diffusion coupling iteration. That node owns
    the equations:

        R_ATP        = A0*(vmax/6)*mm_O2*mm_Glc (mitoATP) + A0*(vmax/6)*mm_Glc (glycoATP)
        atp_rate_max = A0 * vmax / 6            with A0 = max_atp, vmax = oxygen_vmax

    so a single saturated pathway scores a ratio of 1.0 and both score 2.0. The
    threshold is therefore a fraction of ONE saturated pathway. This node never
    re-derives the constants; it reads the two numbers the metabolism node
    published. Remove that node from the canvas and this gate has no ATP data --
    it says so loudly rather than silently rejecting every cell.

    ``age`` counts scheduler steps and is advanced by the ``advance_cell_age``
    node. ``update_cell_division`` resets it to 0 on parent and daughter, so it
    is the number of steps since the cell last divided.

WHAT IT DOES NOT DO
    Division itself is still ``update_cell_division``, which divides purely on
    ``phenotype == 'Proliferation'``. This node is the sole arbiter of that
    phenotype, so the gate here is the gate on division.

FATE PRECEDENCE
    Same as the plain version: cells already marked Apoptosis or Growth_Arrest by
    an earlier marker in this cycle keep that phenotype; everything else that
    fails the gate resets to Quiescent. The Quiescent reset is what stops stale
    phenotypes from previous iterations keeping a cell dividing.
"""

from typing import Any, Dict, Mapping, Tuple, Union

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext, Phenotype

from opencellcomms_adapters.MicroC.functions.metabolism.set_metabolism_parameters import (
    resolve_metabolism_parameters,
)


_PROTECTED_FATES = {Phenotype.APOPTOSIS.value, Phenotype.GROWTH_ARREST.value,
                    Phenotype.NECROSIS.value}

DEFAULTS: Dict[str, float] = {
    "atp_threshold1": 0.8,   # fraction of one saturated ATP pathway
    "cell_cycle_time": 2.0,  # scheduler steps a cell must wait between divisions
}


def _resolve(proliferation_gate: Union[Dict[str, Any], None]) -> Dict[str, float]:
    values = dict(DEFAULTS)
    for key, raw in dict(proliferation_gate or {}).items():
        if key not in DEFAULTS:
            print(f"[PROLIF_GATE] WARNING: '{key}' is not a gate parameter — "
                  f"ignoring. Known keys: {sorted(DEFAULTS)}")
            continue
        try:
            values[key] = float(raw)
        except (TypeError, ValueError):
            print(f"[PROLIF_GATE] WARNING: '{key}={raw!r}' is not a number — "
                  f"keeping default {DEFAULTS[key]}")
    return values


def atp_gate_passes(metabolic_state: Mapping[str, Any],
                    atp_threshold1: float) -> Tuple[bool, bool]:
    """The ATP half of the proliferation gate, as ``(has_atp, atp_ok)``.

    The one implementation (docs/READABILITY.md R2.1) of the energy test in
    NetLogo's -FATE-PROLIFERATION-102 rule:

        atp_ok = atp_rate > atp_threshold1 * atp_rate_max

    ``atp_rate`` and ``atp_rate_max`` are the per-cell numbers Calculate Cell
    Metabolism publishes in ``metabolic_state``. ``atp_threshold1`` is owned by
    this node's Proliferation Gate table, which it also publishes to
    ``results['proliferation_gate']`` for read-only consumers such as Record
    Sensitivity Metrics. ``has_atp`` is False when the cell carries no usable ATP
    data (no metabolism node ran, or the cell was zeroed as necrotic); the gate
    then fails closed.
    """
    atp_rate = metabolic_state.get('atp_rate')
    atp_rate_max = metabolic_state.get('atp_rate_max')
    has_atp = atp_rate is not None and bool(atp_rate_max)
    atp_ok = has_atp and atp_rate > atp_threshold1 * atp_rate_max
    return has_atp, atp_ok


_COUNTERS = ('cells', 'gene_on', 'atp_ok', 'age_ok', 'prolif', 'has_atp')


def _tally(env: BiologicalContext) -> Dict[str, int]:
    """Per-pass counters in context scratch, so the gate can be debugged.

    Under a per-agent ask this function sees one cell at a time, so the counts
    are accumulated in the context and reported once the whole population has
    been seen. Deliberately NOT keyed on env.step: this workflow drives the
    scheduler without a clock, so env.step stays 0 for the whole run and a
    step-keyed tally would never reset.
    """
    ctx = env.raw_context
    tally = ctx.get('_prolif_gate_tally')
    if tally is None:
        tally = {'pass': 0}
        tally.update({k: 0 for k in _COUNTERS})
        ctx['_prolif_gate_tally'] = tally
    return tally


def _flush(env: BiologicalContext, tally: Dict[str, int]) -> None:
    tally['pass'] += 1
    print(f"[PROLIF_GATE] pass {tally['pass']}: {tally['cells']} cells, "
          f"gene_on={tally['gene_on']}, atp_ok={tally['atp_ok']}, "
          f"age_ok={tally['age_ok']} -> proliferating={tally['prolif']}")

    # No cell at all had ATP data: that is the metabolism node missing, not
    # biology. Say so once -- otherwise the gate rejects everything in silence.
    if tally['cells'] and not tally['has_atp']:
        _warn_no_atp(env)


@register_function(
    requires=['population'],
    display_name="Mark Proliferating Cells (ATP + cell cycle gated)",
    description="Mark a cell as proliferating only if its Proliferation gene is ON, "
                "its ATP production rate exceeds atp_threshold1 x atp_rate_max, and it "
                "has aged past cell_cycle_time steps since its last division. Requires "
                "the Calculate Cell Metabolism and Advance Cell Age nodes. Publishes "
                "the resolved gate to results['proliferation_gate'] so the plots' "
                "ATP-gate isolines draw the threshold actually in effect.",
    category="INTERCELLULAR",
    parameters=[
        {"name": "proliferation_gate", "type": "DICT",
         "description": "atp_threshold1 (fraction of one saturated ATP pathway, 0-2) "
                        "and cell_cycle_time (scheduler steps between divisions)",
         "default": {}},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def mark_proliferating_cells_gated(
    env: BiologicalContext,
    proliferation_gate: Union[Dict[str, Any], None] = None,
    **kwargs
) -> None:
    gate = _resolve(proliferation_gate)
    atp_threshold1 = gate['atp_threshold1']
    cell_cycle_time = gate['cell_cycle_time']

    # Publish the gate actually in effect so the plots can draw the ATP-gate
    # isolines and the checkpoints can replay them (same pattern as
    # necrosis_thresholds). The metabolic constants are NOT owned here — they
    # are a run-time snapshot of the Set Metabolism Parameters owner, included
    # so the record is self-contained for offline replay. Idempotent under a
    # per-agent ask.
    metab = resolve_metabolism_parameters(env.raw_context)
    env.results.store('proliferation_gate', {
        **gate,
        'KO2': metab['KO2'], 'KG': metab['KG'],
        'max_atp': metab['max_atp'], 'oxygen_vmax': metab['oxygen_vmax'],
    })

    # Per-cell when the executor's per-cell ask bound a cell (env.cell); else
    # fall back to the whole-population loop.
    targets = [env.cell] if env.cell is not None else list(env.cells)
    tally = _tally(env)

    for cell in targets:
        # Count every cell seen, so the end-of-pass flush below still fires
        # under a per-agent ask, then skip necrotic cells: Necrosis is terminal
        # (and a necrotic cell can still carry stale atp_rate values from
        # before it died, so the gate alone is not enough to keep it out).
        tally['cells'] += 1
        if cell.is_necrotic:
            continue

        # A cell can legitimately lack ATP data: calculate_cell_metabolism
        # zeroes a necrotic cell (atp_rate 0, no atp_rate_max) and a cell born
        # since the last metabolism pass has none yet. So judge it per cell as
        # simply "cannot afford to divide", and diagnose a missing metabolism
        # node from the whole pass instead (see _flush).
        has_atp, atp_ok = atp_gate_passes(cell.metabolic_state, atp_threshold1)

        gene_on = cell.gene_states.get(Phenotype.PROLIFERATION.value, False)
        age_ok = cell.age > cell_cycle_time

        tally['has_atp'] += bool(has_atp)
        tally['gene_on'] += bool(gene_on)
        tally['atp_ok'] += bool(atp_ok)
        tally['age_ok'] += bool(age_ok)

        if gene_on and atp_ok and age_ok:
            if not cell.is_proliferating:
                cell.mark_proliferating()
            tally['prolif'] += 1
        elif cell.phenotype not in _PROTECTED_FATES:
            if not cell.is_quiescent:
                cell.mark_quiescent()

    if tally['cells'] >= len(env.cells):
        _flush(env, tally)
        env.results.record_change('proliferation', {
            'proliferating': tally['prolif'],
            'quiescent': tally['cells'] - tally['prolif'],
            'gene_on': tally['gene_on'],
            'atp_ok': tally['atp_ok'],
            'age_ok': tally['age_ok'],
        })
        for key in _COUNTERS:
            tally[key] = 0


def _warn_no_atp(env: BiologicalContext) -> None:
    """Say it once per run: without ATP data the gate rejects every cell."""
    ctx = env.raw_context
    if ctx.get('_prolif_gate_warned_no_atp'):
        return
    ctx['_prolif_gate_warned_no_atp'] = True
    print("[PROLIF_GATE] ERROR: no 'atp_rate'/'atp_rate_max' on cell.metabolic_state. "
          "The Calculate Cell Metabolism node must run before this one (it is what "
          "computes them). Until it does, NO cell can pass the ATP gate.")
