"""
Record and plot MicroC fate statistics over scheduler iterations.

This is a reporting-only helper for test workflows. It does not update the
gene network or cell phenotypes; it summarizes the state produced upstream by
gene_update and fate_update.

Per scheduler iteration it records, across the whole population:
- marked-phenotype counts and % of population (NetLogo "my-fate" distribution),
- fate-gene ON counts and % of population as CSV/log diagnostics only,
- fate fires and fate reverts this iteration (NetLogo "fate fires / reverts"),
  derived from the cumulative per-cell counters maintained by
  propagate_gene_networks_netlogo.

The PNG deliberately plots actual cell phenotypes, not Boolean fate-node
states. This matches the phenotype borders in the iteration plots: a Necrosis
node that is ON does not count as necrosis until fate_update applies the
environmental gate and marks the cell's phenotype.

Time axis: each row also carries ``gene_steps`` = iteration x propagation
steps, read from what the gene updater published (see
gene_propagation_record), and the plot uses it as its x axis so runs with
different propagation step counts line up on the number of gene-network
updates. When no updater published a step count the plot falls back to
scheduler iterations and its axis label says so.
"""

import csv
from pathlib import Path
from typing import Dict, Any, List

from src.biology.context import BiologicalContext, Phenotype
from src.workflow.decorators import register_function

from opencellcomms_adapters.MicroC.functions.gene_network.gene_propagation_record import (
    gene_steps,
)


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

# Colour follows the entity, never its position in the legend: a phenotype or
# gene keeps its hue whichever series happen to be drawn. Categorical slots are
# ordered so adjacent hues stay distinct under colour-vision deficiency.
COLORS = {
    "Quiescent": "#2a78d6",
    "Proliferation": "#008300",
    "Apoptosis": "#e34948",
    "Growth_Arrest": "#eda100",
    "Necrosis": "#4a3aa7",
    "Other": "#898781",
    "total_cells": "#52514e",
    "glycoATP": "#eb6834",
    "mitoATP": "#1baf7a",
}
# Fallback hues for extra plotted genes without a fixed colour above.
EXTRA_GENE_COLORS = ["#e87ba4", "#4a3aa7", "#eda100", "#e34948"]

INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"

DEFAULT_METABOLIC_GENES = "glycoATP,mitoATP"
DEFAULT_PLOT_GENES = "glycoATP,mitoATP"


@register_function(
    requires=["population", "gene_networks"],
    display_name="Record Actual Fate Counts",
    description=(
        "Plot actual marked phenotypes over time; retain gene-node counts as "
        "CSV diagnostics"
    ),
    category="FINALIZATION",
    parameters=[
        {
            "name": "plot_filename",
            "type": "STRING",
            "description": "Filename for the actual-phenotype line plot",
            "default": "gene_fate_counts_over_time.png",
        },
        {
            "name": "csv_filename",
            "type": "STRING",
            "description": "Filename for the fate-statistics CSV history",
            "default": "gene_fate_counts_over_time.csv",
        },
        {
            "name": "metabolic_genes",
            "type": "STRING",
            "description": "Comma-separated gene names to track ON-cell counts over time (CSV and log)",
            "default": DEFAULT_METABOLIC_GENES,
        },
        {
            "name": "plot_genes",
            "type": "STRING",
            "description": (
                "Comma-separated subset of metabolic_genes drawn in the plot with "
                "total cells (the others stay CSV-only diagnostics)"
            ),
            "default": DEFAULT_PLOT_GENES,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    collective=True,
)
def record_gene_fate_counts(
    env: BiologicalContext,
    plot_filename: str = "gene_fate_counts_over_time.png",
    csv_filename: str = "gene_fate_counts_over_time.csv",
    metabolic_genes: str = DEFAULT_METABOLIC_GENES,
    plot_genes: str = DEFAULT_PLOT_GENES,
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

    # One row per iteration, whatever the calling convention. This node is a
    # whole-population census, but the GUI gives every behavior owned by an agent
    # kind a per-agent for_each, so it is called once per cell. env.cells is the
    # full population either way, so the first call of a tick writes the row and
    # the rest return here rather than writing N identical ones (which would also
    # zero the fires/reverts deltas, since each would diff against its twin).
    if history and history[-1]["iteration"] == iteration:
        return True

    total_cells = len(env.cells)
    steps_total = gene_steps(env, iteration)
    row: Dict[str, Any] = {
        "iteration": iteration,
        "gene_steps": steps_total if steps_total is not None else "",
        "total_cells": total_cells,
    }

    met_genes = [g.strip() for g in metabolic_genes.split(",") if g.strip()]

    gene_counts = {name: 0 for name in FATE_GENES}
    met_counts = {name: 0 for name in met_genes}
    phenotype_counts = {name: 0 for name in PHENOTYPES}
    # Cumulative fire/revert counters summed across the live population.
    fires_cum = {name: 0 for name in FATE_GENES}
    reverts_cum = {name: 0 for name in FATE_GENES}

    for cell in env.cells:
        states = cell.gene_states
        for name in FATE_GENES:
            if bool(states.get(name, False)):
                gene_counts[name] += 1
        for name in met_genes:
            if bool(states.get(name, False)):
                met_counts[name] += 1

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
    for name in met_genes:
        row[f"gene_{name}"] = met_counts[name]
        row[f"gene_{name}_pct"] = round(100.0 * met_counts[name] / denom, 2)
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
        + (
            " | " + ", ".join(f"{n}={met_counts[n]}" for n in met_genes)
            if met_genes else ""
        )
    )

    output_dir = Path(ctx.get("plots_dir") or "results/plots") / "timeseries"
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(output_dir / csv_filename, history)
    # Render the plot only on the final iteration — it is cumulative (the CSV holds
    # every step), so re-rendering the figure every iteration is wasted work. When
    # the loop total is unknown (e.g. a single run), render every call.
    total_iterations = ctx.get("loop_total_iterations")
    try:
        is_final = total_iterations is None or iteration >= int(total_iterations)
    except (TypeError, ValueError):
        is_final = True
    if is_final:
        wanted = [g.strip() for g in plot_genes.split(",") if g.strip()]
        plotted = [g for g in wanted if g in met_genes]
        for g in wanted:
            if g not in met_genes:
                print(f"[FATE_SUMMARY] plot_genes '{g}' is not in metabolic_genes; not plotted")
        _write_plot(output_dir / plot_filename, history, plotted)
    return True


def _write_csv(path: Path, history) -> None:
    if not history:
        return
    fieldnames = list(history[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(history)


GENE_STEPS_AXIS_LABEL = "Gene-network updates (scheduler iterations x propagation steps)"
ITERATION_AXIS_LABEL = "Scheduler iteration (propagation steps not published)"


def time_axis(history):
    """x values and axis label for a per-iteration history.

    Gene-network updates when every row carries a numeric ``gene_steps``,
    otherwise scheduler iterations, with a label that says which (R1.5).
    """
    steps = [row.get("gene_steps") for row in history]
    if steps and all(isinstance(s, int) and not isinstance(s, bool) for s in steps):
        return steps, GENE_STEPS_AXIS_LABEL
    return [row["iteration"] for row in history], ITERATION_AXIS_LABEL


def _place_end_labels(ax, entries, x_end, y_top):
    """Write each series name at its line's right end, nudged apart so labels
    never overlap (entries: list of (y_end, text, colour))."""
    if not entries:
        return
    min_gap = 0.045 * y_top
    ordered = sorted(entries, key=lambda e: e[0])
    ys = [e[0] for e in ordered]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + min_gap)
    overflow = ys[-1] - y_top
    if overflow > 0:
        ys = [y - overflow for y in ys]
    for y, (_, text, colour) in zip(ys, ordered):
        ax.annotate(
            text,
            xy=(x_end, y),
            xytext=(6, 0),
            textcoords="offset points",
            color=colour,
            fontsize=9,
            fontweight="semibold",
            va="center",
            ha="left",
            annotation_clip=False,
        )


def _style_axis(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelcolor=INK2, length=3, width=0.6)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.margins(x=0)


def _write_plot(path: Path, history, met_genes=None) -> None:
    """Two panels sharing the time axis: marked phenotypes, then total cells
    with the ON-cell count of each gene in ``met_genes``.

    Publication style: no top/right spines, hairline grid, thin lines, no
    markers, each series named directly at its right end instead of a legend
    box. Phenotypes that stay at zero for the whole run are not drawn; a
    footnote lists them so the omission is stated, not hidden.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[FATE_SUMMARY] matplotlib unavailable; wrote CSV only")
        return

    met_genes = met_genes or []
    x, xlabel = time_axis(history)
    x_end = x[-1] if x else 0

    rc = {
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "semibold",
        "axes.titlecolor": INK,
        "axes.labelcolor": INK2,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
    with plt.rc_context(rc):
        fig, (ax_pheno, ax_pop) = plt.subplots(
            2, 1, figsize=(7.2, 6.4), sharex=True, gridspec_kw={"hspace": 0.3}
        )

        drawn, always_zero, labels = [], [], []
        for name in PHENOTYPES:
            ys = [row[f"phenotype_{name}"] for row in history]
            if not any(ys):
                always_zero.append(name.replace("_", " "))
                continue
            ax_pheno.plot(x, ys, linewidth=1.8, label=name, color=COLORS.get(name))
            drawn.append(ys)
            labels.append((ys[-1], name.replace("_", " "), COLORS.get(name)))
        pheno_top = max((max(ys) for ys in drawn), default=1) * 1.1
        ax_pheno.set_ylim(0, pheno_top)
        ax_pheno.set_ylabel("Cells")
        ax_pheno.set_title("Cell phenotypes after fate gates", loc="left")
        _style_axis(ax_pheno)
        _place_end_labels(ax_pheno, labels, x_end, pheno_top)

        # Panel 2: total population and gene ON-cell counts on ONE shared axis
        # (all are cell counts, so magnitudes compare honestly; no dual axis).
        totals = [row["total_cells"] for row in history]
        ax_pop.plot(
            x, totals, linewidth=1.4, linestyle=(0, (4, 2)),
            label="total cells", color=COLORS["total_cells"],
        )
        labels = [(totals[-1], "Total cells", COLORS["total_cells"])]
        pop_top = max(totals, default=1)
        for i, name in enumerate(met_genes):
            colour = COLORS.get(name, EXTRA_GENE_COLORS[i % len(EXTRA_GENE_COLORS)])
            ys = [row.get(f"gene_{name}", 0) for row in history]
            ax_pop.plot(x, ys, linewidth=1.8, label=f"{name} (ON)", color=colour)
            labels.append((ys[-1], f"{name} ON", colour))
            pop_top = max(pop_top, max(ys, default=0))
        pop_top *= 1.1
        ax_pop.set_ylim(0, pop_top)
        ax_pop.set_xlabel(xlabel)
        ax_pop.set_ylabel("Cells")
        ax_pop.set_title("Population and metabolic genes (cells with gene ON)", loc="left")
        _style_axis(ax_pop)
        _place_end_labels(ax_pop, labels, x_end, pop_top)

        if always_zero:
            note = ", ".join(always_zero) + " phenotypes remain at 0 cells throughout."
            fig.text(0.125, 0.01, note, fontsize=8, color=MUTED)

        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
