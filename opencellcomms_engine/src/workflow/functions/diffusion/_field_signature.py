"""
Discrete-state signatures for event-driven steady-state solves.

A steady-state field solve is a fixed point: given the discrete cell state
(who exists, where, with which fate and which field-relevant gene values) and
the solver/model parameters, the converged fields are fully determined — the
concentration dependence of the reaction laws is *part of* the fixed point,
not an extra input. So if none of those discrete inputs changed since the
last converged solve, the fields already hold the exact answer and the solve
can be skipped without approximation.

This module owns the signature representation and its comparison (R2.1: one
implementation, shared by the metabolic and growth-factor ON-CHANGE nodes).

The per-cell entry is (position, phenotype, watched-gene booleans):

- ``position`` / membership — sources are deposited per cell voxel, so
  division, removal, and movement all change the equations.
- ``phenotype`` — a conservative stand-in for the fate weight the reaction
  collectors apply (1.0 normal / 0.5 Growth_Arrest / 0.0 Necrosis). Using the
  phenotype itself avoids duplicating that mapping here (R2.1); the cost is
  an occasional redundant re-solve on a weight-neutral phenotype change
  (e.g. Quiescent -> Proliferation), never a wrongly skipped one.
- ``watched genes`` — exactly the gene nodes the group's reaction laws read:
  mitoATP/glycoATP gate every metabolic consumption/production branch
  (calculate_cell_metabolism), and each signalling substance's own gene node
  gates its production (_add_growth_factor_reactions). All other gene nodes
  never enter the PDEs, so their flips must not trigger a solve.
"""

from typing import Any, Dict, Iterable, Optional


def collect_field_signature(population, watched_genes: Iterable[str],
                            params: Iterable[Any]) -> Dict[str, Any]:
    """Snapshot the discrete state that determines one field group's fixed point."""
    cells = {}
    for cell_id, cell in population.state.cells.items():
        state = cell.state
        genes = state.gene_states or {}
        cells[cell_id] = (
            tuple(state.position),
            state.phenotype,
            tuple(bool(genes.get(g, False)) for g in watched_genes),
        )
    return {"cells": cells, "params": tuple(params)}


def describe_change(previous: Optional[Dict[str, Any]],
                    current: Dict[str, Any]) -> Optional[str]:
    """Why the fixed point moved — or None when a skip is exact.

    Returns a human-readable trigger summary (used verbatim in the R1.5 solve
    log line), or None when ``current`` equals ``previous`` and the previous
    converged fields are still the exact steady state.
    """
    if previous is None:
        return "first solve of the run"
    if previous["params"] != current["params"]:
        return "solver/model parameters changed"
    old, new = previous["cells"], current["cells"]
    if old == new:
        return None

    added = len(new.keys() - old.keys())
    removed = len(old.keys() - new.keys())
    flips = moved = fates = 0
    for cell_id, entry in new.items():
        prev_entry = old.get(cell_id)
        if prev_entry is None or prev_entry == entry:
            continue
        if prev_entry[0] != entry[0]:
            moved += 1
        if prev_entry[1] != entry[1]:
            fates += 1
        if prev_entry[2] != entry[2]:
            flips += sum(a != b for a, b in zip(prev_entry[2], entry[2]))

    parts = []
    if flips:
        parts.append(f"{flips} watched-gene flip(s)")
    if fates:
        parts.append(f"{fates} phenotype change(s)")
    if added:
        parts.append(f"+{added} cell(s)")
    if removed:
        parts.append(f"-{removed} cell(s)")
    if moved:
        parts.append(f"{moved} cell(s) moved")
    return ", ".join(parts) or "cell state changed"
