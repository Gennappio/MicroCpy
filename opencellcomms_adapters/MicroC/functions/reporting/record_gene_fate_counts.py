"""
Record and plot MicroC gene-fate counts over scheduler iterations.

This is a reporting-only helper for test workflows. It does not update the
gene network or cell phenotypes; it summarizes the state produced upstream by
gene_update and fate_update.
"""

import csv
from pathlib import Path
from typing import Dict, Any

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
]


@register_function(
    requires=["population"],
    display_name="Record Gene Fate Counts",
    description="Log and plot Apoptosis/Growth_Arrest/Proliferation counts over iterations",
    category="FINALIZATION",
    parameters=[
        {
            "name": "plot_filename",
            "type": "STRING",
            "description": "Filename for the fate-count line plot",
            "default": "gene_fate_counts_over_time.png",
        },
        {
            "name": "csv_filename",
            "type": "STRING",
            "description": "Filename for the fate-count CSV history",
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
    history = ctx.setdefault("gene_fate_history", [])

    iteration = ctx.get("loop_iteration")
    if iteration is None:
        iteration = len(history) + 1
    try:
        iteration = int(iteration)
    except (TypeError, ValueError):
        iteration = len(history) + 1

    row: Dict[str, Any] = {
        "iteration": iteration,
        "total_cells": len(env.cells),
    }

    gene_counts = {name: 0 for name in FATE_GENES}
    phenotype_counts = {name: 0 for name in PHENOTYPES}
    phenotype_counts["Other"] = 0

    for cell in env.cells:
        states = cell.gene_states
        for name in FATE_GENES:
            if bool(states.get(name, False)):
                gene_counts[name] += 1

        phenotype = cell.phenotype or "Other"
        if phenotype not in phenotype_counts:
            phenotype = "Other"
        phenotype_counts[phenotype] += 1

    for name, count in gene_counts.items():
        row[f"gene_{name}"] = count
    for name, count in phenotype_counts.items():
        row[f"phenotype_{name}"] = count

    history.append(row)

    print(
        "[FATE_SUMMARY] "
        f"Iteration {iteration}: "
        f"gene Apoptosis={gene_counts[Phenotype.APOPTOSIS.value]}, "
        f"Growth_Arrest={gene_counts[Phenotype.GROWTH_ARREST.value]}, "
        f"Proliferation={gene_counts[Phenotype.PROLIFERATION.value]}, "
        f"Necrosis={gene_counts[Phenotype.NECROSIS.value]} | "
        f"phenotype Apoptosis={phenotype_counts[Phenotype.APOPTOSIS.value]}, "
        f"Growth_Arrest={phenotype_counts[Phenotype.GROWTH_ARREST.value]}, "
        f"Proliferation={phenotype_counts[Phenotype.PROLIFERATION.value]}, "
        f"Necrosis={phenotype_counts[Phenotype.NECROSIS.value]}, "
        f"Quiescent={phenotype_counts[Phenotype.QUIESCENT.value]}"
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
    colors = {
        "Apoptosis": "#d62728",
        "Growth_Arrest": "#ff7f0e",
        "Proliferation": "#2ca02c",
        "Necrosis": "#4d4d4d",
        "Quiescent": "#7f7f7f",
    }

    fig, (ax_gene, ax_pheno) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

    for name in FATE_GENES:
        ax_gene.plot(
            iterations,
            [row[f"gene_{name}"] for row in history],
            marker="o",
            linewidth=2,
            label=name,
            color=colors.get(name),
        )
    ax_gene.set_ylabel("Cells")
    ax_gene.set_title("Gene Fate Outputs")
    ax_gene.grid(True, alpha=0.3)
    ax_gene.legend(loc="upper right")

    for name in PHENOTYPES:
        ax_pheno.plot(
            iterations,
            [row[f"phenotype_{name}"] for row in history],
            marker="o",
            linewidth=2,
            label=name,
            color=colors.get(name),
        )
    ax_pheno.set_xlabel("Scheduler Iteration")
    ax_pheno.set_ylabel("Cells")
    ax_pheno.set_title("Marked Phenotypes After fate_update")
    ax_pheno.grid(True, alpha=0.3)
    ax_pheno.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
