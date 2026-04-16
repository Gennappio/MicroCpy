"""
Apply PhysiBoss Phenotype - Map BN output node probabilities to cell fate.

Reads the per-cell MaBoSS output probabilities stored by run_physiboss_step,
applies the output coupling (node → behaviour mapping), and uses the
PhysiBossPhenotypeMapper to make stochastic fate decisions (apoptosis,
necrosis, proliferation).

Supports two backends:
- CellContainer (NumPy SoA): fully vectorized — all cells processed at once
- Legacy Dict[str, Cell]: per-cell Python loop
"""

from typing import Dict, Any, Optional
import numpy as np
from src.workflow.decorators import register_function
from src.workflow.logging import log


@register_function(
    display_name="Apply PhysiBoss Phenotype",
    description=(
        "Map MaBoSS output node probabilities to cell phenotype changes "
        "(apoptosis, necrosis, proliferation) using PhysiBoss coupling"
    ),
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "verbose",
            "type": "BOOL",
            "description": "Enable detailed logging of fate decisions",
            "default": None,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def apply_physiboss_phenotype(
    context: Dict[str, Any],
    verbose: Optional[bool] = None,
    **kwargs,
) -> None:
    """
    Apply PhysiBoss coupling outputs to determine cell fate.

    Detects CellContainer and uses vectorized path, falling back to
    legacy per-cell loop.
    """
    from src.biology.cell_container import CellContainer

    container = context.get('cell_container')
    if isinstance(container, CellContainer):
        _apply_vectorized(context, container, verbose)
    else:
        _apply_legacy(context, verbose)


# ── Vectorized path ─────────────────────────────────────────────────────

def _apply_vectorized(context, container, verbose):
    """Fully vectorized phenotype mapping using CellContainer columns."""
    from src.biology.cell_container import phenotype_name

    coupling = context.get('physiboss_coupling')
    mapper = context.get('physiboss_phenotype_mapper')
    if coupling is None or mapper is None:
        return

    pb_config = context.get('physiboss_config')
    dt = pb_config.timing.dt_phenotype if pb_config else 6.0
    N = container.count

    # Build BN probability arrays from container columns
    bn_probs: Dict[str, np.ndarray] = {}
    for name in list(container._float_columns):
        if name.startswith("bn_prob_"):
            node_name = name[len("bn_prob_"):]
            bn_probs[node_name] = container.get_float(name)[:N]

    if not bn_probs:
        return  # No BN outputs stored yet

    # ── 1. Vectorized: BN probs → rates ─────────────────────────────
    cell_rates = coupling.apply_phenotype_outputs_vectorized(bn_probs, N)

    # ── 2. Vectorized: stochastic fate decisions ────────────────────
    old_phenos = container.phenotype_ids[:N].copy()
    new_phenos = mapper.apply_rates_vectorized(cell_rates, old_phenos, dt)

    # ── 3. Apply changes ────────────────────────────────────────────
    changed = old_phenos != new_phenos
    n_changed = int(changed.sum())
    container.phenotype_ids[:N] = new_phenos

    if n_changed > 0:
        # Count by phenotype
        fate_counts: Dict[str, int] = {}
        for pid in np.unique(new_phenos[changed]):
            name = phenotype_name(int(pid))
            fate_counts[name] = int((new_phenos[changed] == pid).sum())
        parts = ", ".join(f"{f}: {n}" for f, n in fate_counts.items())
        log(context, f"PhysiBoss phenotype changes: {parts}",
            prefix="[Fate]", node_verbose=verbose)


# ── Legacy path ─────────────────────────────────────────────────────────

def _apply_legacy(context, verbose):
    """Legacy per-cell loop for Dict[str, Cell] populations."""
    population = context.get('population')
    if population is None:
        return

    coupling = context.get('physiboss_coupling')
    mapper = context.get('physiboss_phenotype_mapper')
    if coupling is None or mapper is None:
        return

    pb_config = context.get('physiboss_config')
    dt = pb_config.timing.dt_phenotype if pb_config else 6.0

    fate_counts: Dict[str, int] = {}
    updated_cells = {}

    for cell_id, cell in population.state.cells.items():
        bn_outputs = getattr(cell, '_physiboss_bn_outputs', None)
        if bn_outputs is None:
            continue

        phenotype = getattr(cell.state, 'phenotype', '')
        if phenotype in ('apoptotic', 'necrotic', 'dead', 'removed'):
            continue

        cell_rates: Dict[str, float] = {}
        cell_rates = coupling.apply_phenotype_outputs(bn_outputs, cell_rates)
        new_phenotype = mapper.apply_rates(cell_rates, phenotype, dt)

        if new_phenotype != phenotype:
            cell.state = cell.state.with_updates(phenotype=new_phenotype)
            updated_cells[cell_id] = cell
            fate_counts[new_phenotype] = fate_counts.get(new_phenotype, 0) + 1

    if updated_cells:
        population.state = population.state.with_updates(cells=updated_cells)

    if fate_counts:
        parts = ", ".join(f"{fate}: {n}" for fate, n in fate_counts.items())
        log(context, f"PhysiBoss phenotype changes: {parts}",
            prefix="[Fate]", node_verbose=verbose)
