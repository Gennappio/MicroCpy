"""
Record and plot MicroC gene-fate statistics over scheduler iterations.

This is a reporting-only helper for test workflows. It does not update the
gene network or cell phenotypes; it summarizes the state produced upstream by
gene_update and fate_update.

Per scheduler iteration it records, across the whole population:
- fate-gene ON counts and % of population (NetLogo "fate node Boolean state"),
- marked-phenotype counts and % of population (NetLogo "my-fate" distribution),
- fate fires and fate reverts this iteration (NetLogo "fate fires / reverts"),
  derived from the cumulative per-cell counters maintained by
  propagate_gene_networks_netlogo.

The population-over-time analogue of gene_network_netlogo_faithful.py, whose
distributions are over independent runs.
"""

import csv
from pathlib import Path
from typing import Dict, Any, List

from src.biology.context import BiologicalContext, Phenotype
from src.workflow.decorators import register_function


FATE_GENES = [
    Phenotype.APOPTOSIS.value,
    Phenotype.GROWTH_ARREST.value,
    Phenotype.PROLIFERATION.value,
    Phenotype.NECROSIS.value,
]

PHENOTYPES = [
    Phenotype.APOPTOSIS.value,
    Phenotype.GROWTH_ARREST.value,
    Phenotype.PROLIFERATION.value,
    Phenotype.NECROSIS.value,
    Phenotype.QUIESCENT.value,
    "Other",
]

COLORS = {
    "Apoptosis": "#d62728",
    "Growth_Arrest": "#ff7f0e",
    "Proliferation": "#2ca02c",
    "Necrosis": "#4d4d4d",
    "Quiescent": "#7f7f7f",
    "Other": "#c7c7c7",
}


@register_function(
    requires=["population", "gene_networks"],
    display_name="Record Gene Fate Counts",
    description="Log and plot fate-gene/phenotype counts, %, and fate fires/reverts over iterations",
    category="FINALIZATION",
    parameters=[
        {
            "name": "plot_filename",
            "type": "STRING",
            "description": "Filename for the fate-statistics line plot",
            "default": "gene_fate_counts_over_time.png",
        },
        {
            "name": "csv_filename",
            "type": "STRING",
            "description": "Filename for the fate-statistics CSV history",
            "default": "gene_fate_counts_over_time.csv",
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def record_gene_fate_counts(
    env: BiologicalContext,
    plot_filename: str = "gene_fate_counts_over_time.png",
    csv_filename: str = "gene_fate_counts_over_time.csv",
    **kwargs,
) -> bool:
    ctx = env.raw_context
    history: List[Dict[str, Any]] = ctx.setdefault("gene_fate_history", [])
    prev = history[-1] if history else None

    iteration = ctx.get("loop_iteration")
    if iteration is None:
        iteration = len(history) + 1
    try:
        iteration = int(iteration)
    except (TypeError, ValueError):
        iteration = len(history) + 1

    total_cells = len(env.cells)
    row: Dict[str, Any] = {
        "iteration": iteration,
        "total_cells": total_cells,
    }

    gene_counts = {name: 0 for name in FATE_GENES}
    phenotype_counts = {name: 0 for name in PHENOTYPES}
    # Cumulative fire/revert counters summed across the live population.
    fires_cum = {name: 0 for name in FATE_GENES}
    reverts_cum = {name: 0 for name in FATE_GENES}

    for cell in env.cells:
        states = cell.gene_states
        for name in FATE_GENES:
            if bool(states.get(name, False)):
                gene_counts[name] += 1

        phenotype = cell.phenotype or "Other"
        if phenotype not in phenotype_counts:
            phenotype = "Other"
        phenotype_counts[phenotype] += 1

        gn = env.gene_network(cell)
        if gn is not None:
            fires = getattr(gn, "_fate_fires", None)
            reverts = getattr(gn, "_fate_reverts", None)
            for name in FATE_GENES:
                if fires:
                    fires_cum[name] += fires.get(name, 0)
                if reverts:
                    reverts_cum[name] += reverts.get(name, 0)

    denom = total_cells or 1
    for name in FATE_GENES:
        row[f"gene_{name}"] = gene_counts[name]
        row[f"gene_{name}_pct"] = round(100.0 * gene_counts[name] / denom, 2)
    for name in PHENOTYPES:
        row[f"phenotype_{name}"] = phenotype_counts[name]
        row[f"phenotype_{name}_pct"] = round(100.0 * phenotype_counts[name] / denom, 2)

    # Per-iteration fires/reverts = delta of cumulative since the previous record.
    # Guarded at >=0 because cells removed (apoptosis/necrosis) can shrink the
    # cumulative sum across the population.
    for name in FATE_GENES:
        prev_fires = prev.get(f"fires_{name}_cum", 0) if prev else 0
        prev_reverts = prev.get(f"reverts_{name}_cum", 0) if prev else 0
        row[f"fires_{name}_cum"] = fires_cum[name]
        row[f"reverts_{name}_cum"] = reverts_cum[name]
        row[f"fires_{name}"] = max(0, fires_cum[name] - prev_fires)
        row[f"reverts_{name}"] = max(0, reverts_cum[name] - prev_reverts)

    history.append(row)

    fires_total = sum(row[f"fires_{n}"] for n in FATE_GENES)
    reverts_total = sum(row[f"reverts_{n}"] for n in FATE_GENES)
    print(
        "[FATE_SUMMARY] "
        f"Iteration {iteration} (n={total_cells}): "
        f"gene Apo={gene_counts[Phenotype.APOPTOSIS.value]}, "
        f"GA={gene_counts[Phenotype.GROWTH_ARREST.value]}, "
        f"Prolif={gene_counts[Phenotype.PROLIFERATION.value]}, "
        f"Necro={gene_counts[Phenotype.NECROSIS.value]} | "
        f"pheno Apo={phenotype_counts[Phenotype.APOPTOSIS.value]}, "
        f"GA={phenotype_counts[Phenotype.GROWTH_ARREST.value]}, "
        f"Prolif={phenotype_counts[Phenotype.PROLIFERATION.value]}, "
        f"Necro={phenotype_counts[Phenotype.NECROSIS.value]}, "
        f"Quiesc={phenotype_counts[Phenotype.QUIESCENT.value]} | "
        f"fires={fires_total}, reverts={reverts_total}"
    )

    output_dir = Path(ctx.get("plots_dir") or "results/plots") / "timeseries"
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(output_dir / csv_filename, history)
    _write_plot(output_dir / plot_filename, history)
    return True


def _write_csv(path: Path, history) -> None:
    if not history:
        return
    fieldnames = list(history[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(history)


def _write_plot(path: Path, history) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[FATE_SUMMARY] matplotlib unavailable; wrote CSV only")
        return

    iterations = [row["iteration"] for row in history]

    fig, (ax_gene, ax_pheno, ax_events) = plt.subplots(
        3, 1, figsize=(9, 10), sharex=True
    )

    for name in FATE_GENES:
        ax_gene.plot(
            iterations,
            [row[f"gene_{name}"] for row in history],
            marker="o", linewidth=2, label=name, color=COLORS.get(name),
        )
    ax_gene.set_ylabel("Cells")
    ax_gene.set_title("Fate Gene Outputs (ON cells)")
    ax_gene.grid(True, alpha=0.3)
    ax_gene.legend(loc="upper right", fontsize=8)

    for name in PHENOTYPES:
        ax_pheno.plot(
            iterations,
            [row[f"phenotype_{name}"] for row in history],
            marker="o", linewidth=2, label=name, color=COLORS.get(name),
        )
    ax_pheno.set_ylabel("Cells")
    ax_pheno.set_title("Marked Phenotypes After fate_update")
    ax_pheno.grid(True, alpha=0.3)
    ax_pheno.legend(loc="upper right", fontsize=8)

    for name in FATE_GENES:
        ax_events.plot(
            iterations,
            [row[f"fires_{name}"] for row in history],
            marker="o", linewidth=2, label=f"{name} fires", color=COLORS.get(name),
        )
    reverts_total = [sum(row[f"reverts_{n}"] for n in FATE_GENES) for row in history]
    ax_events.plot(
        iterations, reverts_total,
        marker="x", linewidth=1.5, linestyle="--", color="#9467bd",
        label="reverts (all fates)",
    )
    ax_events.set_xlabel("Scheduler Iteration")
    ax_events.set_ylabel("Events / iteration")
    ax_events.set_title("Fate Fires & Reverts per Iteration")
    ax_events.grid(True, alpha=0.3)
    ax_events.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
