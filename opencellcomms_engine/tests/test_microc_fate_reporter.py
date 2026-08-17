"""Regression tests for the MicroC fate time-series reporter."""

import matplotlib.pyplot as plt

from opencellcomms_adapters.MicroC.functions.reporting import (
    record_gene_fate_counts as fate_reporter,
)

plt.switch_backend("Agg")


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
