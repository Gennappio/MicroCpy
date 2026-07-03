# TCELL_CORRAL — Corral T-helper differentiation (PhysiCell/PhysiBoSS FOXP3_2)

A Python re-expression of the PhysiCell / PhysiBoSS **FOXP3_2** differentiation
experiment (`config/differentiation/PhysiCell_settings_FOXP3_2_lower.xml` in the
PhysiCell tree). The biology is small and almost entirely declarative; the hard
part is the intracellular stochastic-Boolean engine, which now lives in the
engine and is validated against real MaBoSS.

## The model in one paragraph

One **endothelial cell** secretes **CCL21**, establishing a chemokine gradient.
Mature **dendritic cells** chemotax up that gradient until they **contact** a
naive **T0** cell. Contact switches on the T0 cell's ~90-node **`tcell_corral`
MaBoSS network**, which propagates the TCR / cytokine cascade and settles into a
mutually-exclusive **Treg / Th1 / Th17** attractor — the T0 cell then commits to
that fate. No cells are born or die during the run. The `FOXP3_2_lower`
perturbation lowers one MaBoSS **transition rate** (`$u_FOXP3_2` 1.0 → 0.2),
which shifts the fate split away from Treg.

## Two layers

1. **Intracellular (MaBoSS) — the validated core.** The real `tcell_corral`
   network runs through the engine's continuous-time stochastic mode
   (`BooleanNetwork.step_maboss`, added in commit `fc86aab`). Cross-checked
   against the reference engine `cmaboss`: on the actual 95-node network the
   Treg/Th1/Th17 attractor distribution matches at baseline **and** under the
   `$u_FOXP3_2 = 0.2` perturbation
   (`opencellcomms_engine/tests/biology/test_maboss_crosscheck.py`).

2. **Spatial (ABM class layer).** CCL21 as a diffusing resource, DC chemotaxis,
   contact sensing, fate commitment, and fate-specific motility — built as
   atomic node-functions on the Agents / Resources / World / Scheduler canvases.

The `FOXP3_2_lower` / `_mutant` series that were separate XML files become, in
the GUI, an editable **node up-rate table** on the network node (`FOXP3_2` →
0.2) and node clamps (knockout) — the mechanism a scientist can read and change.

## Status

**Implemented and validated (intracellular core):**

| File | Node | What it does |
|---|---|---|
| `functions/initialization/build_tcell_networks.py` | Build T-cell MaBoSS Networks | One `BooleanNetwork` per T0 cell from `data/tcell_corral.bnd/.cfg`; applies `up_rate_overrides` (the FOXP3_2 knob). |
| `functions/intracellular/step_tcell_network.py` | Step T-cell Networks (MaBoSS) | Advances each cell's network by `intracellular_dt` via `step_maboss` (per-agent when `env.cell` is bound). |

**Vendored data (`data/`):** `tcell_corral.bnd/.cfg` (the ~90-node network),
`dendritic_cells.bnd/.cfg` (the 4-node DC network), `cells.csv` (108 cells: 100
T0, 7 dendritic_cell, 1 endothelial_cell). Copied unchanged from the PhysiCell
project.

**Not yet built (spatial layer + wiring).** The CSV population loader, CCL21
diffusion/secretion, DC chemotaxis + contact sensing, fate commitment,
fate-specific motility, and the behaviour/workflow JSON are the next increments.

➡️ See **[`NEXT_STEPS.md`](NEXT_STEPS.md)** for the full sequenced roadmap:
per-function contracts, the embedded PhysiCell reference values, the design
decisions/gotchas, and how to resume on another machine.

## Validation target

Reproduce the PhysiCell `Corral_analysis.ipynb` result: the WT → `FOXP3_2_lower`
→ `FOXP3_2_mutant` (and the NFKB pair) shift in the Treg : Th1 : Th17
proportions among the 100 T0 cells. Because it is stochastic, the comparison is
distributional, not cell-by-cell.
