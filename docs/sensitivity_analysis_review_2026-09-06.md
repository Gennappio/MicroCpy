# Review of the p53 sensitivity analysis — 6 September 2026

The suite is a useful starting point for exploratory, local sensitivity analysis. Its parameter wiring and workflow generation are sound in the checks performed. It is **not yet sufficient for reliable parameter rankings or strong biological robustness claims**: the propagation comparison mixes different biological durations, replication is inadequate, and several metrics and collection rules can mislead.

Scope: repository commit `355d6dc`; the five `p53_sa_*.json` workflows, generator, reporter, collector, SLURM launcher, and their active execution paths. No completed sensitivity-suite results were present in local `runs/` or `results/`. The existing `p53off_STABLEBASELINE` run is not a completed sensitivity experiment. The short runs below verify implementation behavior; they do not establish long-term effects or effect sizes.

## What is already sound

- The five committed workflows exactly match regeneration from the current p53-off baseline.
- The four non-propagation sweeps have a shared baseline, sparse overrides, and a consistent 2,000-iteration horizon. Their four baseline arms can supply a preliminary estimate of baseline variability.
- Glucose and oxygen consumption multipliers are actually consumed by the active metabolic solver and its metabolism callback. They are not inert GUI parameters.
- Glucose supply moves initial and boundary concentrations together. This is a coherent supply scenario for a converged steady-state metabolic solve, although independence from the initial guess remains something to verify.
- Changing domain size keeps the initial colony and the 50 µm solver spacing fixed. This avoids changing cell size or mesh spacing simultaneously.
- The reporter shares the actual ATP-gate law, records raw counts and denominators, and leaves some undefined ratios blank.
- All **16 focused tests passed**, including generation and workflow validation. Two three-iteration baseline runs completed; their Picard solves converged in 46/30/6 and 46/31/6 iterations.

## 1. High priority: the propagation sweep changes biological duration

[`_clock_overrides`](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_adapters/MicroC/workflows/sensitivity_analysis/build_sensitivity_workflows.py:110) fixes the nominal gene-update budget at 10,000 by changing the number of scheduler iterations. But [cell age increases by one per scheduler iteration](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_adapters/MicroC/functions/fate/advance_cell_age.py:38), the proliferation gate requires age > 2, and [necrotic clearance counts scheduler iterations](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_adapters/MicroC/functions/fate/remove_necrotic_cells.py:61), with a suite delay of 30.

| Propagation updates per iteration | Scheduler iterations | Earliest age eligibility after division, in nominal gene updates | Necrotic residence, in nominal gene updates |
|---:|---:|---:|---:|
| 1 | 10,000 | 3 | 30 |
| 5 (baseline) | 2,000 | 15 | 150 |
| 10 | 1,000 | 30 | 300 |
| 50 | 200 | 150 | 1,500 |

Eligibility is not guaranteed division: the gene, ATP, and spatial conditions must also pass. Nevertheless, the scheduling difference is real. The first and last propagation arms execute 50-fold different numbers of growth, fate, removal, and environmental update passes.

Equal gene-update budgets therefore do **not** establish comparable tumour-development time. The sweep can answer a deliberately defined question about coupling frequency at fixed nominal gene updates, but cannot isolate gene-update frequency over equal biological duration.

Recommended change: for sensitivity to gene-update rate, retain the same scheduler horizon and cell-cycle/removal rules, varying propagation steps only. If the intended study is numerical convergence at a fixed gene-network timescale, define that timescale explicitly and rescale the other biological clocks and coupling schedule consistently. Record both clocks. The current `gene_steps` also denotes a global nominal clock, not the number of updates received by every cell: newborn cells have shorter histories and necrotic networks stop updating.

## 2. High priority: replication and reproducibility are insufficient

The launcher defines 15 arms, with one run at each non-baseline setting and four baseline runs. That does not estimate outcome uncertainty separately for each perturbed setting. Baseline variance need not equal variance near hypoxia or fate-switch thresholds.

The executor [initializes a NumPy generator from the workflow seed](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_engine/src/workflow/executor.py:1459), but gene initialization and [single-gene selection use Python's separate global random generator](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_adapters/MicroC/functions/gene_network/propagate_gene_networks_single_gene.py:125).

A direct repeat confirmed the consequence:

| Same baseline configuration, iteration 3 | Run A | Run B |
|---|---:|---:|
| Logged run seed | 42 | 42 |
| Hypoxic fraction | 0.079 | 0.255 |
| Proliferating cells | 3 | 11 |
| MSI_mito | 0 | 0.03155 |

These are short verification runs, not estimates of final-run variance. They demonstrate that the recorded seed is insufficient to replay the model.

Also, standard runs derive their [output directory from workflow/tab names](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_engine/tools/run_sim.py:1353), and [CSV writing truncates the existing file](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_adapters/MicroC/functions/reporting/record_metabolic_symbiosis.py:258). Repeating the same launch does not automatically retain another replicate.

Recommended change: seed all random sources, save seed and code revision, and give each replicate a unique directory. Start with a pilot of roughly 10–20 independent seeds per distinct setting, then increase replication until confidence intervals and qualitative conclusions stabilize. That starting count is a practical proposal, not a universal adequacy threshold. The simulation run is the independent unit; cells and successive time points are not independent replicates. This distinction and output-variance assessment are discussed by [Lee et al. (2015)](https://www.jasss.org/18/4/4.html).

## 3. High priority: the metabolic indices can count dead cells as active metabolism

The [shared region census](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_adapters/MicroC/functions/reporting/record_metabolic_symbiosis.py:213) counts every remaining cell's `mitoATP`, `glycoATP`, and `MCT1` states. Necrotic cells retain frozen gene states until removal. Consequently, `R_MG` and MSI can reflect dead-cell labels.

A synthetic call to the actual reporter with two necrotic cells, one oxygenated/mitoATP-positive and one hypoxic/glycoATP-positive, returned:

```text
N_total = 2; N_viable = 0; N_necrotic = 2
R_MG = 1.0; MSI_mito = 1.0
```

Thus the maximum MSI is possible without a viable cell. This is incompatible with interpreting it as evidence of active metabolic cooperation.

There is a separate mechanistic limitation: the [metabolism explicitly excludes lactate-derived ATP](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_adapters/MicroC/functions/metabolism/calculate_cell_metabolism.py:70), and lactate uptake is gated by mitoATP rather than directly by MCT1. These indices describe spatial gene-state patterns, not demonstrated lactate-supported energetic cooperation.

Recommended change: retain any all-cell census as explicitly labeled morphology, add viable-only pathway counts and coexpression categories, and report actual lactate production/uptake when discussing exchange. Establish an energetic benefit before claiming functional symbiosis. `F_ATP` already uses a viable denominator; extend comparable care to the other metabolic summaries.

## 4. High priority: incomplete and numerically unsuccessful runs are not screened

The [collector takes the last available CSV row](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_adapters/MicroC/workflows/sensitivity_analysis/collect_sensitivity_results.py:100), regardless of whether the run reached its planned horizon. A probe with one row from a workflow planned for 2,000 iterations was accepted without a completion/validity flag. The output exposes `n_iterations` and `steps_planned`, so manual checking is possible, but it is not enforced.

Separately, the [Picard loop warns and continues after exhausting its iteration limit](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_engine/src/workflow/functions/diffusion/run_diffusion_solver_coupled.py:330). Convergence status is not carried into the sensitivity summary. The six solves in this review converged; that does not establish convergence for all levels over their full runs.

Recommended change: separate run completion from numerical validity; require the intended endpoint, check row continuity and finite values, and retain solver convergence diagnostics. Flag incomplete runs explicitly and exclude them from endpoint comparisons by default. Check mesh refinement and tighter tolerances at the baseline and demanding extremes before interpreting small parameter effects.

## 5. Interpretation: the geometry and consumption experiments need precise names

The domain sweep leaves the initial tumour radius approximately **276.6 µm** in all three arms. Domain half-widths are 600/750/900 µm, giving nominal initial gaps to a side boundary of approximately 323.4/473.4/623.4 µm. It tests **domain size and distance to nutrient supply**. It does not isolate absolute tumour size. Report absolute radius, cell number, and boundary distance alongside the relative ratio; the ratio changes mechanically when its denominator changes.

The consumption controls are **PDE source-term multipliers**. In a controlled call with fields and gene states fixed, glucose multipliers 5.6/7/8.4 changed glucose uptake from 3.96/4.95/5.94 × 10⁻¹⁶, while ATP production and lactate production stayed unchanged. This is intentional in the implementation. It is a valid perturbation of environmental depletion, but should not be described as a coherent change in intrinsic glycolytic flux or ATP yield.

## 6. Scope: useful local exploration, without a complete sensitivity analysis yet

The ±20% consumption and ±10% supply changes are reasonable exploratory perturbations. Their biological uncertainty ranges are not justified by evidence in the suite documentation. Three levels per factor can show direction and some curvature around this baseline; they cannot establish global robustness or resolve interactions.

The collector produces endpoint tables, not uncertainty estimates or sensitivity coefficients. Predefine a small set of primary outcomes and the sampling phase: the current census is after fate assignment and before division/removal. Use full trajectories to establish whether the selected horizon captures a transient or a stable regime. Do not assume that 10,000 nominal gene updates implies stationarity.

For comparison across parameters with different percentage ranges, calculate normalized local effects where baseline outcomes are nonzero, for example:

`S = (p0 / mean(Y0)) × (mean(Y+) − mean(Y−)) / (p+ − p−)`

Report uncertainty across runs. Use absolute or otherwise meaningful scales when the baseline outcome is zero; percent changes are then undefined.

Extended one-factor-at-a-time analysis is a defensible ABM starting point, as [ten Broeke et al. (2016)](https://jasss.soc.surrey.ac.uk/19/1/5.html) explain. Add targeted combinations such as glucose supply × glucose demand and oxygen demand × domain size when making claims involving those interactions. Broader importance rankings require a suitable global design; [SALib's documentation](https://salib.readthedocs.io/en/latest/user_guide/basics_with_interface.html) also cautions that Sobol analysis requires its corresponding sampling design. The current 15 arms cannot simply be passed to a Sobol estimator.

If the intended conclusion concerns the effect of p53 knockout, include a matched p53-on/intact comparison. The present suite characterizes sensitivity conditional on p53 being clamped off.

## Work performed and retained evidence

No implementation or production workflow was changed. Temporary generated copies and outputs are under [/private/tmp/microc_sa_review_20260906](/private/tmp/microc_sa_review_20260906). The short runs used the current baseline arm and the generator's documented `--steps 3` option, with outputs redirected away from existing runs.

- [Structured evidence: both smoke-run time series and the controlled consumption probe](/private/tmp/microc_sa_review_20260906/audit_evidence.json)
- [First smoke log](/private/tmp/microc_sa_review_20260906/smoke.log) and [repeat log](/private/tmp/microc_sa_review_20260906/smoke_repeat.log)
- [Synthetic all-necrotic reporter output](/private/tmp/microc_sa_review_20260906/dead_metric_probe/timeseries/sensitivity_metrics_over_time.csv)
- [One-row incomplete-run probe](/private/tmp/microc_sa_review_20260906/partial_run/sensitivity_summary/timeseries/sensitivity_metrics_over_time.csv)

Priority order: correct/define the propagation comparison; retain reproducible replicates; correct metabolic metric interpretation; enforce completion and numerical quality checks; then run and analyze the suite with uncertainty.

