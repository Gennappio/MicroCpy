"""Regression tests for the MicroC fate time-series reporter."""

import matplotlib.pyplot as plt

from src.biology.context import BiologicalContext

from opencellcomms_adapters.MicroC.functions.gene_network.gene_propagation_record import (
    gene_steps,
    publish_propagation_steps,
    published_propagation_steps,
)
from opencellcomms_adapters.MicroC.functions.reporting import (
    record_gene_fate_counts as fate_reporter,
)

plt.switch_backend("Agg")


def _row(iteration, **extra):
    row = {"iteration": iteration, "total_cells": 10, "gene_Necrosis": 0}
    row.update({f"phenotype_{name}": 0 for name in fate_reporter.PHENOTYPES})
    row["phenotype_Quiescent"] = 10
    row.update(extra)
    return row


def _capture_axes(monkeypatch):
    captured = {}
    real_subplots = plt.subplots

    def capture_subplots(*args, **kwargs):
        fig, axes = real_subplots(*args, **kwargs)
        captured["axes"] = axes
        return fig, axes

    monkeypatch.setattr(plt, "subplots", capture_subplots)
    return captured


def test_plot_x_axis_is_gene_steps_when_published(tmp_path, monkeypatch):
    captured = _capture_axes(monkeypatch)
    history = [_row(1, gene_steps=5), _row(2, gene_steps=10), _row(3, gene_steps=15)]
    fate_reporter._write_plot(tmp_path / "fate.png", history)
    ax_pheno, ax_pop = captured["axes"]
    assert list(ax_pop.get_lines()[0].get_xdata()) == [5, 10, 15]
    assert list(ax_pheno.get_lines()[0].get_xdata()) == [5, 10, 15]
    assert ax_pop.get_xlabel() == fate_reporter.GENE_STEPS_AXIS_LABEL


def test_plot_falls_back_to_iterations_without_gene_steps(tmp_path, monkeypatch):
    captured = _capture_axes(monkeypatch)
    history = [_row(1), _row(2, gene_steps="")]
    fate_reporter._write_plot(tmp_path / "fate.png", history)
    _, ax_pop = captured["axes"]
    assert list(ax_pop.get_lines()[0].get_xdata()) == [1, 2]
    assert ax_pop.get_xlabel() == fate_reporter.ITERATION_AXIS_LABEL


def test_time_axis_requires_every_row_numeric():
    assert fate_reporter.time_axis([_row(1, gene_steps=5), _row(2, gene_steps=10)])[0] == [5, 10]
    assert fate_reporter.time_axis([_row(1, gene_steps=5), _row(2)])[0] == [1, 2]
    assert fate_reporter.time_axis([])[1] == fate_reporter.ITERATION_AXIS_LABEL


def test_propagation_record_round_trip():
    env = BiologicalContext({})
    assert published_propagation_steps(env) is None
    assert gene_steps(env, 3) is None
    publish_propagation_steps(env, 7, updater="single_gene")
    assert published_propagation_steps(env) == 7
    assert gene_steps(env, 3) == 21
    env.results.store("gene_propagation", {"propagation_steps": "not a number"})
    assert gene_steps(env, 3) is None


def test_plot_uses_actual_phenotype_not_necrosis_gene(tmp_path, monkeypatch):
    """A Necrosis node is not necrosis until fate_update marks the cell."""
    captured = {}
    real_subplots = plt.subplots

    def capture_subplots(*args, **kwargs):
        fig, axes = real_subplots(*args, **kwargs)
        captured["axes"] = axes
        return fig, axes

    monkeypatch.setattr(plt, "subplots", capture_subplots)

    history = [
        {
            "iteration": 1,
            "total_cells": 10,
            "gene_Necrosis": 8,
            "phenotype_Apoptosis": 0,
            "phenotype_Growth_Arrest": 0,
            "phenotype_Proliferation": 2,
            "phenotype_Necrosis": 0,
            "phenotype_Quiescent": 8,
            "phenotype_Other": 0,
        },
        {
            "iteration": 2,
            "total_cells": 10,
            "gene_Necrosis": 1,
            "phenotype_Apoptosis": 0,
            "phenotype_Growth_Arrest": 0,
            "phenotype_Proliferation": 1,
            "phenotype_Necrosis": 2,
            "phenotype_Quiescent": 7,
            "phenotype_Other": 0,
        },
    ]
    output = tmp_path / "gene_fate_counts_over_time.png"

    fate_reporter._write_plot(output, history)

    assert output.exists()
    axes = captured["axes"]
    assert len(axes) == 2
    phenotype_lines = {line.get_label(): line for line in axes[0].get_lines()}
    assert list(phenotype_lines["Necrosis"].get_ydata()) == [0, 2]
    assert axes[0].get_title() == "Actual Cell Phenotypes After Fate Gates"
    assert all("Gene Outputs" not in axis.get_title() for axis in axes)
