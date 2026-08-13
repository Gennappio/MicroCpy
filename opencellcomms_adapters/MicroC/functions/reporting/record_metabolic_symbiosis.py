"""Per-iteration CSV for the metabolic-symbiosis figures.

Writes one row per scheduler iteration with everything needed to draw the three
panels of the symbiosis figure, so the plotting is done outside the engine:

    panel A  total_cells, n_glycoATP, n_mitoATP        (cells by ATP pathway)
    panel B  n_oxygenated, n_hypoxic                   (cells by region)
    panel C  msi_mct1, msi_mito                        (metabolic symbiosis index)

METABOLIC SYMBIOSIS INDEX
    MSI = [phi_L(A_oxy) - phi_G(A_oxy)] / [phi_L(A_oxy) + phi_G(A_oxy)]
          if phi_L(A_oxy) > phi_G(A_oxy) and phi_L(A_hypo) < phi_G(A_hypo)
    MSI = 0 otherwise

    phi_L(A) and phi_G(A) are the lactate-metabolic and glycolytic cell
    fractions of tumour region A; A_oxy and A_hypo are the oxygenated and
    hypoxic regions. Both terms share one denominator, so MSI is a normalised
    difference on [-1, 1] that the gate clips to [0, 1].

    The region fractions divide by the cell count of that region, but the choice
    of denominator does not matter: any denominator common to phi_L and phi_G
    cancels in the ratio. What the gate encodes is the shape of a symbiotic
    tumour -- lactate consumers concentrated in the oxygenated rim, lactate
    producers in the hypoxic core. When there is no hypoxic region yet, the
    hypoxic fractions are both 0, `phi_L < phi_G` is false, and MSI is 0. That
    is why the index sits flat at zero early in a run and only lifts once a
    hypoxic core forms.

WHAT COUNTS AS A LACTATE-METABOLIC CELL: TWO COLUMNS, YOU CHOOSE
    jaya.bnd makes the distinction sharp, and the two readings are not the same
    cell set, so this node emits MSI both ways rather than picking for you:

      msi_mct1  phi_L = MCT1 ON. MCT1 = Oxygen_supply & MCT1_stimulus & !MCT1I
                is the lactate importer, so this counts only cells actually
                taking lactate up. LDHB = MCT1 and glycoATP = PEP & !LDHB, so
                this phi_L and phi_G are mutually exclusive by construction.

      msi_mito  phi_L = mitoATP ON. mitoATP = ETC = TCA & Oxygen_supply is
                oxidative ATP from ANY carbon source, so it also counts cells
                burning glucose with no lactate involved. Broader than
                "lactate metabolic", but it matches the mitoATP series in
                panel A exactly.

    phi_G is glycoATP ON in both cases. `*_raw` columns carry the ungated
    normalised difference and `gate_*` carries the condition, so a zero in the
    MSI column can be read as "gate closed" rather than "no signal".

WHY raw_context FOR THE ITERATION NUMBER
    `env.step` is the engine clock, which MicroC's workflow scheduler does not
    advance -- the loop counter is `loop_iteration`, set by the executor. The
    sibling reporter record_gene_fate_counts reads it the same way. `dt_hours`
    is emitted alongside `time_hours` so a dt that never reached the clock is
    visible in the data instead of silently scaling the time axis.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    requires=['population'],
    display_name="Record Metabolic Symbiosis",
    description="Per-iteration CSV of cells by ATP pathway, cells by oxygen region, "
                "and the metabolic symbiosis index (MSI)",
    category="FINALIZATION",
    parameters=[
        {"name": "hypoxia_threshold", "type": "FLOAT",
         "description": "Oxygen concentration (mM) separating hypoxic from oxygenated "
                        "cells. Defaults to 0.022, the Oxygen_supply association "
                        "threshold, so a cell is hypoxic exactly when its "
                        "Oxygen_supply gene input is OFF.",
         "default": 0.022},
        {"name": "csv_filename", "type": "STRING",
         "description": "Output file, written under plots_dir/timeseries",
         "default": "metabolic_symbiosis_over_time.csv"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def record_metabolic_symbiosis(
    env: BiologicalContext,
    hypoxia_threshold: float = 0.022,
    csv_filename: str = "metabolic_symbiosis_over_time.csv",
    **kwargs,
) -> bool:
    # Whole-population reporter: one row per iteration, not per cell. Bail out if
    # a per-agent ask bound a cell, so a stray for_each on the calling node cannot
    # multiply the CSV by the population size.
    if env.cell is not None:
        return True

    ctx = env.raw_context
    history: List[Dict[str, Any]] = ctx.setdefault("symbiosis_history", [])

    iteration = ctx.get("loop_iteration")
    try:
        iteration = int(iteration)
    except (TypeError, ValueError):
        iteration = len(history) + 1

    counts = {
        ('oxy', 'glyco'): 0, ('oxy', 'mito'): 0, ('oxy', 'mct1'): 0,
        ('hypo', 'glyco'): 0, ('hypo', 'mito'): 0, ('hypo', 'mct1'): 0,
    }
    n_region = {'oxy': 0, 'hypo': 0}
    n_glyco = n_mito = n_mct1 = n_mct4 = 0

    for cell in env.cells:
        oxygen = env.concentration('Oxygen', cell)
        region = 'oxy' if oxygen >= hypoxia_threshold else 'hypo'
        n_region[region] += 1

        states = cell.gene_states
        if states.get('glycoATP', False):
            counts[(region, 'glyco')] += 1
            n_glyco += 1
        if states.get('mitoATP', False):
            counts[(region, 'mito')] += 1
            n_mito += 1
        if states.get('MCT1', False):
            counts[(region, 'mct1')] += 1
            n_mct1 += 1
        if states.get('MCT4', False):
            n_mct4 += 1

    dt_hours = env.dt
    row: Dict[str, Any] = {
        "iteration": iteration,
        "time_hours": round(iteration * dt_hours, 6),
        "dt_hours": dt_hours,
        "total_cells": n_region['oxy'] + n_region['hypo'],
        # panel A
        "n_glycoATP": n_glyco,
        "n_mitoATP": n_mito,
        "n_MCT1": n_mct1,
        "n_MCT4": n_mct4,
        # panel B
        "n_oxygenated": n_region['oxy'],
        "n_hypoxic": n_region['hypo'],
        "hypoxia_threshold": hypoxia_threshold,
        # region breakdown
        "oxy_glycoATP": counts[('oxy', 'glyco')],
        "oxy_mitoATP": counts[('oxy', 'mito')],
        "oxy_MCT1": counts[('oxy', 'mct1')],
        "hypo_glycoATP": counts[('hypo', 'glyco')],
        "hypo_mitoATP": counts[('hypo', 'mito')],
        "hypo_MCT1": counts[('hypo', 'mct1')],
    }

    # panel C, both readings of phi_L
    for label, key in (("mct1", "mct1"), ("mito", "mito")):
        msi, raw, gate, phis = _symbiosis_index(
            l_oxy=counts[('oxy', key)], g_oxy=counts[('oxy', 'glyco')],
            l_hypo=counts[('hypo', key)], g_hypo=counts[('hypo', 'glyco')],
            n_oxy=n_region['oxy'], n_hypo=n_region['hypo'],
        )
        row[f"msi_{label}"] = round(msi, 6)
        row[f"msi_{label}_raw"] = round(raw, 6)
        row[f"gate_{label}"] = int(gate)
        row[f"phi_L_{label}_oxy"] = round(phis[0], 6)
        row[f"phi_G_{label}_oxy"] = round(phis[1], 6)
        row[f"phi_L_{label}_hypo"] = round(phis[2], 6)
        row[f"phi_G_{label}_hypo"] = round(phis[3], 6)

    history.append(row)

    output_dir = env.plots_dir / "timeseries"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / csv_filename, history)

    print(
        f"[SYMBIOSIS] Iteration {iteration} (n={row['total_cells']}): "
        f"oxygenated={row['n_oxygenated']}, hypoxic={row['n_hypoxic']} | "
        f"glycoATP={n_glyco}, mitoATP={n_mito}, MCT1={n_mct1} | "
        f"MSI(mct1)={row['msi_mct1']}, MSI(mito)={row['msi_mito']}"
    )
    return True


def _symbiosis_index(l_oxy: int, g_oxy: int, l_hypo: int, g_hypo: int,
                     n_oxy: int, n_hypo: int):
    """MSI plus the fractions and gate that produced it.

    Returns (msi, raw, gate, (phi_L_oxy, phi_G_oxy, phi_L_hypo, phi_G_hypo)).
    """
    phi_l_oxy = l_oxy / n_oxy if n_oxy else 0.0
    phi_g_oxy = g_oxy / n_oxy if n_oxy else 0.0
    phi_l_hypo = l_hypo / n_hypo if n_hypo else 0.0
    phi_g_hypo = g_hypo / n_hypo if n_hypo else 0.0

    denom = phi_l_oxy + phi_g_oxy
    raw = (phi_l_oxy - phi_g_oxy) / denom if denom > 0 else 0.0

    # Both halves are required: lactate consumers must dominate the oxygenated
    # region AND be outnumbered by glycolytic cells in the hypoxic one. With no
    # hypoxic cells both hypoxic fractions are 0, the strict `<` fails, and MSI
    # is 0 -- the flat stretch before a hypoxic core forms.
    gate = (phi_l_oxy > phi_g_oxy) and (phi_l_hypo < phi_g_hypo)

    return (raw if gate else 0.0), raw, gate, (phi_l_oxy, phi_g_oxy,
                                               phi_l_hypo, phi_g_hypo)


def _write_csv(path: Path, history: List[Dict[str, Any]]) -> None:
    if not history:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)
