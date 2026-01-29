# Chapter 8 — Reproducibility, Results, and Data Products

## 8.1 Scientific reproducibility: what matters in practice

In simulation research, reproducibility has a few concrete requirements:

- You can rerun an experiment with the same configuration and get the same results (or the same distribution if stochastic).
- You can identify what changed between two runs: parameters, ordering, code version, inputs.
- You can export outputs into analysis tooling (Python/R/Julia) without GUI dependence.

OpenCellComms addresses these needs through:

- serialized **workflow JSON** (the protocol)
- optional **YAML configuration** usage for engine runs
- flat-file results (CSV, plots, checkpoints)
- (optionally) observability artifacts that explain node-by-node behavior

## 8.2 Workflow as an experiment artifact

Because workflows are serializable and explicit, they become experiment artifacts:

- store them in version control
- label them (metadata: author, created date, experiment notes)
- treat them like methods sections in papers

Even if the underlying code changes, the workflow documents the intent of the run.

## 8.3 Outputs: what the engine produces

From the usage guide (`docs/USAGE.md`), outputs typically include:

- **CSV files**: cell data per timestep (positions, states, phenotypes)
- **Substance CSV or field exports** (depending on configured exporters)
- **Plots**: snapshots, animations, statistics
- **Logs**
- **Checkpoints** (e.g., gene networks snapshots)

In GUI mode, results are placed under `opencellcomms_gui/results/`.
In CLI mode, results are placed under `opencellcomms_engine/results/`.

## 8.4 Overwrite semantics: a conscious tradeoff

The system favors simplicity:

- each new run clears the results directory (at least for GUI runs)
- there is no built-in run history manager

This can be presented honestly as:

- a choice to avoid building storage management UI and databases,
- in exchange for asking researchers to archive important runs themselves.

In publications or team practice, the solution is straightforward:

- copy/zip the results directory with a timestamp and a short run label,
- store the workflow JSON alongside it,
- optionally include git commit hash and environment info.

## 8.5 Recommendations for stronger reproducibility (what to do in your lab)

These are practical recommendations you can include as “best practices”:

- **Record versions**:
  - git commit hash
  - Python version
  - key dependency versions (FiPy, NumPy)
- **Record randomness**:
  - seeds used for stochastic components (migration noise, MaBoSS if stochastic)
- **Archive inputs**:
  - initial cell CSV/VTK
  - gene network files (.bnd/.cfg)
- **Archive workflows**:
  - store the workflow JSON in the same folder as results
  - label the workflow with experiment metadata

OpenCellComms already makes workflows and outputs file-based, which aligns well with these practices.

## 8.6 Data products as a bridge to analysis

An underrated strength of flat-file outputs is that they decouple:

- simulation execution
- from analysis and visualization

In an article, you can show a quick “analysis pipeline” example (conceptual):

- load CSV snapshots
- compute phenotype fractions over time
- correlate phenotype with local concentration
- produce publication plots

This positions OpenCellComms as:

> a simulation generator producing analysis-ready data products.

## 8.7 Suggested figures (for this chapter)

- **Figure 1 — Results directory anatomy**
  - A screenshot or diagram of `results/` with subfolders: CSV, plots, checkpoints, observability.

- **Figure 2 — Example heatmap**
  - Use existing assets:
    - `opencellcomms_gui/results/subworkflows/Generate_final_plots/heatmaps/*.png`

- **Figure 3 — Example phenotype/position plot**
  - Use:
    - `opencellcomms_engine/tools/cell_visualizer_results/*phenotypes*.png`
    - `opencellcomms_engine/tools/cell_visualizer_results/*positions*.png`

