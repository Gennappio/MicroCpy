# TCELL_CORRAL — Validation

The native-Python port is validated against the reference PhysiCell/PhysiBoSS
implementation at two levels.

## 1. Boolean level — cmaboss cross-check (automated, portable)

`opencellcomms_engine/tests/biology/test_maboss_crosscheck.py` compares the
engine's `step_maboss` against the reference MaBoSS engine (cmaboss) on the
vendored `data/tcell_corral.{bnd,cfg}`:

- `test_tcell_corral_baseline_matches_maboss` — the DC-contact Treg/Th1/Th17
  attractor split matches cmaboss (tol 0.06).
- `test_tcell_corral_foxp3_perturbation_matches_maboss` — lowering `$u_FOXP3_2`
  shifts the split the same way in both engines.

Both **pass** (run: `pytest tests/biology/test_maboss_crosscheck.py -m "slow or not slow" -k tcell`).

## 2. Spatial level — PhysiBoSS C++ simulation

The full PhysiBoSS tutorial `differentiation` project was built (brew `g++-14`,
OpenMP) and run to 2500 min for the WT and FOXP3_2-knockout configs; final cell
type counts parsed from `output/*_cells.mat` (`cell_type` label).

| Run | PhysiBoSS (C++) | Native Python |
|---|---|---|
| WT | Treg 0.62 / Th1 0.25 / Th17 0.12 | Treg 0.48 / Th1 0.38 / Th17 0.14 |
| FOXP3_2 knockout | **Treg 0.00** / Th1 0.73 / Th17 0.27 | **Treg 0.00** / Th1 0.56 / Th17 0.44 |

Both engines are Treg-dominant at baseline and **abolish Treg entirely** under the
FOXP3_2 knockout, redistributing to Th1/Th17 — the same qualitative and
near-quantitative outcome (small absolute counts: ~8–24 cells differentiate as the
7 DCs slowly reach the T0 cluster, so proportions carry stochastic noise).

**Conclusion:** the native ABM port reproduces the PhysiBoSS differentiation
outcome — the WT Treg-dominant split and the FOXP3_2 loss-of-function Treg
collapse — at both the intracellular (attractor) and spatial (cell-count) levels.
