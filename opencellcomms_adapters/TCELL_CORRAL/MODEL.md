# Corral T-cell Differentiation — PhysiCell vs. TCELL_CORRAL

What the PhysiCell/PhysiBoSS model simulates, how it does it, how this
OpenCellComms plugin (`TCELL_CORRAL`) reproduces it in native Python, and where
the two differ. The short version: **the intracellular decision layer is a
faithful, validated re-implementation; the spatial/mechanical layer is a
deliberately simplified on-lattice re-expression that reproduces the same
population-level outcome distributionally.**

- **Their model:** `…/PhysiCell/sample_projects_intracellular/boolean/tutorial/` (PhysiBoSS tutorial, doi:10.1093/bib/bbae509). Boolean network from Corral et al.
- **Our model:** `opencellcomms_adapters/TCELL_CORRAL/` on the OpenCellComms `biophysics` kernel.

---

## 1. What the model wants to simulate (the biology — same on both sides)

A naïve CD4⁺ T cell (**T0**) decides whether to become a regulatory **Treg**, an
inflammatory **Th1**, or a **Th17** cell. The decision is driven by a large
intracellular signalling network, switched on by contact with an antigen-
presenting **dendritic cell (DC)**, which is itself guided into the T-cell zone
by a chemokine (**CCL21**) secreted by an **endothelial cell**.

The end-to-end mechanism:

1. One **endothelial cell** secretes **CCL21**, forming a gradient.
2. Mature **dendritic cells** chemotax up the CCL21 gradient toward the T-cell
   cluster; they stop when they touch a T0 cell.
3. **DC↔T0 contact** delivers a 9-node "antigen presentation + cytokine" signal
   into the T0 cell's ~95-node **MaBoSS Boolean network** (`tcell_corral`).
4. The network integrates that signal and settles into a **mutually exclusive
   Treg / Th1 / Th17 attractor** (winner-take-all logic).
5. The winning fate node commits the T0 cell to that T-helper identity.

**The scientific question — dose-dependent control of the Treg/Th1/Th17 mix.**
Two network nodes are the levers: **`FOXP3_2`** (`= IL1R AND NOT MINA`, a second
route to the Treg master TF; it also represses the Th17/`SATB1` arm) and
**`NFKB`** (`= IKK`, driving the inflammatory arm). The model runs five
conditions to test how weakening each — gradually (`_lower`, a rate change) or
completely (`_mutant`, a knockout) — reshapes the fate proportions:

| Condition | Perturbation | Expected effect |
|---|---|---|
| WT | none | baseline mix (Treg-dominant) |
| `FOXP3_2_lower` | `$u_FOXP3_2 = 0.2` (from 1.0) | ↓ Treg |
| `FOXP3_2_mutant` | `FOXP3_2` locked OFF | Treg → 0 |
| `NFKB_lower` | `$u_NFKB = 0.1` (from 1.0) | ↑ Treg |
| `NFKB_mutant` | `NFKB` locked OFF | strongest ↑ Treg |

These five conditions come straight from the model's own derivation notebook
(`scripts/Corral_analysis.ipynb`), which sweeps the two rates in pure MaBoSS
(FOXP3_2: 1 → **0.2** → 0.1 → 0.01; NFKB: 1 → **0.1** → 0.01) and lifts the
chosen values into the PhysiCell configs. The spatial simulation then tests
whether the **contact-gated, multicellular** system reproduces the same shifts.

### Why genetically identical cells reach different fates

Every T0 cell is identical — same 95-node network, same logic, same kinetic
rates, same naïve starting state (there is **no** per-cell parameter or
initial-state randomisation). Its only input is also identical and binary: DC
contact drives the *same* 9 nodes ON, and a T0 cell senses no gradient or
concentration into its network. So the fate spread does **not** come from cells
receiving different signals — it comes from two other sources:

- **Extrinsic (spatial/temporal):** whether, when, and for how long a given T0
  is contacted. With no input the network's stable state *is* naïve, so an
  uncontacted T0 never differentiates; in the spatial run the 7 DCs reach only a
  fraction of the 100 T0 cells.
- **Intrinsic (molecular noise):** given the identical signal, MaBoSS (and our
  `step_maboss`) is a *continuous-time stochastic* process — two identical cells
  follow different random trajectories and lock into different attractors. The
  winner-take-all mutual inhibition makes it all-or-nothing; the kinetic rates
  (`$u_Th17=100`, `$u_Th1=1`, `$u_Treg=0.1`) bias the *odds* of each outcome.

The perturbations therefore never tell an individual cell what to become — they
re-weight the whole population's odds (FOXP3_2↓ → less Treg; NFKB↓ → more Treg).
This is **stochastic cell-fate commitment**: identical cells + identical signal
→ different decisions from noise, with the proportions set by the network
kinetics. It is the behaviour reproduced most tightly — the cmaboss cross-check
in §5 matches these attractor *probabilities*, not any single cell's outcome.

---

## 2. How PhysiCell does it

PhysiCell/PhysiBoSS is a **compiled C++ engine**; the biology is **declarative**
(XML + CSV + MaBoSS network files) and the custom C++ is essentially the stock
template — `phenotype_function`, `custom_function`, `contact_function` are all
empty, and the only hand-written routine (`treatment_function`) is dormant
because no differentiation config defines a `treatment` parameter. Everything
below is data, not code.

**Domain & time.** 2D, ±300 µm (canonical), 20 µm mesh → 30×30 substrate voxels;
`max_time = 5000 min` (~83 h); `dt_diffusion 0.01`, `dt_mechanics 0.1`,
`dt_phenotype 6`; output every 30 min. *(The specific `FOXP3_2_lower.xml` in this
tree is edited to ±1000 µm — see §4, note A.)*

**CCL21 microenvironment.** One substrate: `D = 1000 µm²/min`, `decay = 0.005/min`,
`initial 0`, all Dirichlet boundaries off (no-flux), gradients tracked. Integrated
**transiently** by BioFVM at the diffusion dt.

**Cells** (108, from `cells.csv`: 100 T0 upper-left cluster, 7 DC lower-right,
1 endothelial upper-left corner). All: `live` cycle with **transition rate 0 (no
proliferation)**, **death rate 0 (no death)**, volume 2494 µm³ (~17 µm diam.),
off-lattice mechanics (adhesion 0.4 / repulsion 10 / max-adh-dist 1.25).

| Cell | Motility | CCL21 | MaBoSS network |
|---|---|---|---|
| T0 | speed 0.8, no chemotaxis | — | `tcell_corral` (95 nodes) |
| Treg | speed 0.5, bias 0.5 | — | — |
| Th1 | motility **off** | — | — |
| Th17 | speed 0.5 | **uptake 0.5** | — |
| dendritic_cell | speed 0→1 (MaBoSS-driven), **chemotaxis→CCL21, bias 0.8** | — | `dendritic_cells` (4 nodes) |
| endothelial_cell | off | **secrete 10, target 10** | — |

**Intracellular coupling (PhysiBoSS + MaBoSS).** Each MaBoSS-bearing cell
re-runs its network every `intracellular_dt = 6 min`. On each update PhysiBoSS
advances the **continuous-time stochastic MaBoSS engine** by `intracellular_dt /
scaling` MaBoSS-time units from the cell's current state:
- **T0:** `scaling = 1.0` → 6.0 units/step (reaches its attractor each step).
- **DC:** `scaling = 30.0` → 0.2 units/step (its `Migration` decision evolves slowly).

Signal wiring: `contact with dendritic_cell` → the 9 T0 input nodes
(`IL1_In, MHCII_b1, MHCII_b2, IL12_In, IL6_In, CD80, CD4, IL23_In, PIP2`); output
nodes `Treg`/`Th1`/`Th17` → `transform to <fate>` at rate 1e6/min (≈ instant, so
the T0 **physically changes cell type**). The DC network output `Migration` →
`chemotactic response to CCL21` + `migration speed`.

**Chemotaxis fine-tuning (`rules.csv`, one rule).** `dendritic_cell, CCL21,
decreases, migration bias, 0.0, 2, 4, 0` — a Hill function (half-max 2, power 4)
that drives a DC's migration bias from 0.8 toward 0 as local CCL21 rises, so DCs
settle and mingle in the CCL21-rich T-cell zone instead of over-committing to the
gradient direction.

### Motility ≠ chemotaxis, and which contacts matter

PhysiCell separates three independent knobs: **speed** (how fast), **migration
bias** (0 = pure random walk … 1 = fully directed), and **chemotaxis** (whether
the directed part actually follows a substrate gradient). A cell can be motile
yet non-chemotactic — it then simply wanders. In this model **only dendritic
cells chemotax toward CCL21** (chemotaxis on, bias 0.8); the other motile cells
have chemotaxis *off*, so they random-walk and go nowhere in particular:

| Cell | Moves? | Homes to CCL21? | Motion |
|---|---|---|---|
| T0 | yes (0.8) | no (bias 0) | fast, undirected random walk |
| Treg | yes (0.5) | no | random walk |
| Th17 | yes (0.5) | no | random walk (+ *consumes* CCL21) |
| Th1 | **no** | — | immotile (motility disabled) |
| dendritic_cell | yes (0→1) | **yes** (bias 0.8) | climbs the CCL21 gradient |
| endothelial_cell | **no** | — | immotile (fixed source) |

So the "everything jiggles a bit" you see is *undirected* motion — naïve and
effector T cells milling around the tissue while only mature DCs actively home
up the gradient. **Differentiated cells do not move toward CCL21:** Treg/Th17
keep random-walking, Th1 stops entirely, and Th17's only CCL21 interaction is
*uptake* (eating it), not movement toward it.

**Which contacts matter — only DC↔T0, and in both directions.** `contact with
dendritic_cell` drives the T0's 9 input nodes (→ it differentiates); `contact
with T0` sets the DC's `Contact` node (→ `Migration = Maturation & CCL21 &
!Contact` goes false → the DC halts). Every other contact is functionally inert:
T0↔T0, T0↔differentiated, and contact with the endothelial cell feed no network,
and there are no attack/phagocytosis/fusion interactions (all those rates are 0)
— such contacts only exclude cells mechanically. And once a T0 transforms it is
a *new* cell type, so it neither presents antigen nor registers on the DC's
`Contact` sensor: differentiated cells drop out of contact signalling entirely.
(Our port mirrors this — only `chemotax_ccl21` is gradient-directed, the rest
random-hop with Th1 arrested, and the only wired contacts are DC→T0
(`sense_dc_contact`) and T0→DC-stops (the contact check in `chemotax_ccl21`).)

---

## 3. How TCELL_CORRAL does it

Same biology, rebuilt on the OpenCellComms `biophysics` kernel following the
platform's rule that **every mechanism is a visible Python node-function on a GUI
canvas**, orchestrated by a workflow JSON. There is no compiled binary and no
external MaBoSS: the continuous-time stochastic engine is re-implemented in the
engine as `BooleanNetwork.step_maboss` (a Gillespie/SSA CTMC), and each biological
step is one `.py` node the scientist can read and edit.

**Two grids.** Agents live on a **40×40 bio-grid** (tile = 15 µm, one agent per
tile, on-lattice); CCL21 lives on a **30×30 FiPy mesh** (20 µm). Positions are
reconciled by index conversion. Domain 600×600 µm = **±300** (matches canonical
PhysiCell).

**Population** (`place_cells_from_csv` → `build_tcell_abm_population`). Reads the
same `cells.csv`, maps centered-µm → grid index, tags each cell's kind in
`metabolic_state["_kind"]` (`T0`→`tcell`, DC, endothelial), gives T0 cells
`fate="naive"`. Overlaps in the dense T0 cluster are nudged to the nearest free
tile (expanding-ring search) rather than dropped. Wrapped in an `abm.Population`
sharing the legacy cells inside a `LatticeWorld`.

**CCL21** (`setup_ccl21_field` → `diffuse_ccl21`). Same physics constants
(D 1000 µm²/min, decay 0.005/min, initial 0, no-flux) but solved to
**steady state each step**: `D·∇²c − k·c = −source` via FiPy
`DiffusionTerm − ImplicitSourceTerm == −source`, with a **direct LU solver**
(iterative GMRES diverges on the large source magnitude). Endothelial cells add a
constant per-tile source (10); Th17 cells add a first-order sink (0.5 × local).

**Intracellular MaBoSS** (`build_tcell_networks` → `sense_dc_contact` →
`step_tcell_network`, plus `fix_tcell_nodes`). One `BooleanNetwork` per T0 cell,
parsed once from `tcell_corral.bnd`/`.cfg` and `copy()`-ed per cell.
`step_maboss(6.0)` runs the Gillespie CTMC (draw exponential waiting times from
the summed node rates, flip one node per event, recompute) — the same semantics
as MaBoSS, so the `.cfg` rate asymmetry (`$u_Th17=100`, `$u_Th1=1`, `$u_Treg=0.1`)
and the FOXP3_2 rate perturbation are meaningful. **A committed cell's network is
no longer stepped** (`fate != "naive"` → skip). The two perturbation families use
two mechanisms: **`_lower` → `set_rate(node, up=…)`** (needs the CTMC);
**`_mutant` → `fix_node(node, False)`** (clamp, excluded from CTMC candidates).

**Contact & spatial behaviours.**
- **Contact** = lattice Moore-1 adjacency (`agent.neighbors(radius=1)`), checked
  on both sides.
- **`sense_dc_contact`** (per T0): while a DC is adjacent, drive the 9 input nodes
  ON (OFF otherwise) — sustained contact lets the CTMC settle.
- **`chemotax_ccl21`** (per DC): stop if touching a T0; else step one tile toward
  the highest-CCL21 tile within vision 4, with probability = bias 0.8 (else a
  random free tile). The `rules.csv` Hill damping is approximated by the
  **local-maximum stop** (a DC at a peak has no higher neighbour) plus the contact
  stop, since the lattice field's scale doesn't carry the physical half-max.
- **`commit_tcell_fate`** (per T0): when exactly one of Treg/Th1/Th17 is ON for
  `stable_steps = 3` consecutive steps, write `metabolic_state["fate"]`. Fate is a
  **state field on the single `tcell` kind**, not a cell-type switch.
- **`differentiated_motility`** (per T0): per-step hop probability = speed (naive
  0.8 / Treg 0.5 / Th1 0 / Th17 0.5); a naive cell in DC contact is held (the
  synapse).

**Workflow** (`workflows/tcell_corral.json`, 100 steps). Per step:
`diffuse_ccl21` → `dc_step`(`chemotax_ccl21`) → `tcell_step`(`sense_dc_contact` →
`step_tcell_network` → `commit_tcell_fate` → `differentiated_motility`) →
`world_reconcile` (tile arbitration) → reports. The **five PhysiCell configs
become five GUI planner tabs** on two `dictParameterNode`s (`up_rate_overrides`
for the `_lower` rates, `fixed_nodes` for the `_mutant` knockouts). Three
incremental workflows (`_intracellular`, `_ccl21`, `_spatial`) are the checkpoint
builds. Reporting: live + committed fate counts, DC-distance progress, CCL21/cell
frames, and a fate time-series plot.

---

## 4. The differences

### Side-by-side

| Dimension | PhysiCell / PhysiBoSS | TCELL_CORRAL | Impact |
|---|---|---|---|
| Language / form | Compiled C++ engine; biology in XML/CSV/`.bnd`; stock template code | Python node-functions on GUI canvases + workflow JSON | Mechanism is GUI-readable/editable; no build step |
| Cell space | **Off-lattice**, continuous positions | **On-lattice**, 40×40 grid, one agent/tile | The single biggest structural approximation |
| Cell mechanics | Adhesion/repulsion forces, volume dynamics | None — tile exclusion + move reconciliation | No physical crowding; moot here (sparse, no growth) |
| CCL21 solve | **Transient** PDE (BioFVM) at diffusion dt | **Steady-state** re-solve each step (FiPy, direct LU) | Same D/decay; field equilibrates instantly per step |
| Contact | Mechanical center-distance within adhesion range | Moore-1 lattice adjacency | Equivalent in intent; discretised |
| Intracellular engine | Real MaBoSS (PhysiBoSS C++), `intracellular_dt/scaling` per type | Our `step_maboss` Gillespie CTMC, `dt=6` | **Validated equivalent** (see §5); same 95-node network |
| DC decision network | `dendritic_cells.bnd` run in MaBoSS (scaling 30) | 4-node network **not run** — inlined as "chemotax unless touching a T0" | Simplification; DC net vendored but unused |
| `rules.csv` Hill damping | Literal Hill (half-max 2, power 4) on migration bias | Approximated by local-max stop + contact stop | Qualitatively same "settle near source", not the exact curve |
| Fate representation | 4 distinct cell types + `transform to <fate>` (rate 1e6) | `fate` **state field** on one `tcell` kind; `stable_steps=3` commit | No remove/respawn; differentiated behaviour via branch |
| Motility | Speed (µm/min) + migration-bias vector | Per-step lattice-hop probability = speed | Discretised; same relative ordering |
| Proliferation / death | Off (rate 0) | Off | Faithful — population count is static |
| Run length | 2500–5000 min | 100 steps × 6 min = 600 min (nominal) | Fewer DCs reach contact → smaller differentiated counts |
| Perturbations | 5 XML files (`$u_…` params / `mutation` blocks) | 5 GUI planner tabs on 2 dict-param nodes | Same values; editable as tables, not files |

### The differences that actually matter

**A. Off-lattice → on-lattice (the load-bearing approximation).** PhysiCell cells
have continuous positions and push each other with physical forces; ours occupy
integer tiles, one per tile, with movement arbitrated by reconciliation. This is
acceptable *for this model specifically* because it is mechanics-light: no
proliferation, no volume growth, sparse non-crowded cells. Contact and motility
become lattice-adjacency and hop-probability. *(Note A: the `FOXP3_2_lower.xml`
you have open is edited to ±1000 µm; the canonical WT and the other three configs
are ±300 µm, which is what our port matches. In the ±1000 box the DCs travel the
same absolute distance through more empty space.)*

**B. Transient → steady-state CCL21.** PhysiCell time-steps the diffusion PDE;
we re-solve the field to equilibrium every ABM step (same D and decay). For a
slowly-secreting chemokine over tens of hours this is a good approximation — the
gradient the DCs climb is essentially the equilibrium gradient either way.

**C. Transform-to-type → fate state field.** PhysiCell turns a T0 into a genuinely
different cell type (`transform to Treg`, rate 1e6); we set a `fate` field on the
same agent and branch its behaviour, stopping its network once committed. This
avoids remove-and-respawn churn on the lattice and is biologically honest (one
cell differentiating), at the cost of not having Treg/Th1/Th17 as first-class
Agents-tab entities. Our commit adds a `stable_steps=3` guard to avoid latching on
the transient Th1 pass-through a freshly-activated network shows.

**D. Real MaBoSS → our CTMC (but validated equivalent).** This is the difference
that could most affect the science, and it is the one we pinned down: our
`step_maboss` reproduces real MaBoSS's attractor probabilities (see §5). The
enabling engine fix was teaching `BooleanExpression` the word operators
(`AND/OR/NOT`) the `tcell_corral.bnd` uses — before that, those nodes silently
evaluated to `False`. We run the **real 95-node network unchanged**; we do not run
the tiny DC network (its logic is inlined).

**E. Run length / time mapping.** Ours defaults to 600 min of network time vs
PhysiCell's 2500–5000 min, and the ABM-step ↔ physical-time mapping is nominal.
Because the 7 DCs cross the domain at ≤1 tile/step, only ~8–24 T0 cells get
contacted and differentiate in a default run — so absolute counts are small and
proportions carry stochastic noise. Increasing the step count (or DC speed) closes
this gap.

---

## 5. Do the results agree?

Validated at two levels (`VALIDATION.md`):

**Intracellular (automated, vs the reference engine `cmaboss`).** On the vendored
95-node network, compared at steady state (`tests/biology/test_maboss_crosscheck.py`):

| | Treg | Th1 | Th17 |
|---|---|---|---|
| MaBoSS baseline | 0.494 | 0.261 | 0.245 |
| our engine baseline | 0.526 | 0.258 | 0.216 |
| MaBoSS `$u_FOXP3_2=0.2` | 0.314 | 0.394 | 0.291 |
| our engine `$u_FOXP3_2=0.2` | 0.316 | 0.376 | 0.308 |

Every fate is within Monte-Carlo tolerance, and the FOXP3₂ perturbation shifts the
split the same way. **The intracellular decision is a faithful reproduction.**

**Spatial (vs the actual PhysiBoSS C++ build, run to 2500 min).** Final fate
proportions among differentiated cells:

| Run | PhysiBoSS (C++) | Native Python |
|---|---|---|
| WT | Treg 0.62 / Th1 0.25 / Th17 0.12 | Treg 0.48 / Th1 0.38 / Th17 0.14 |
| FOXP3_2 knockout | **Treg 0.00** / Th1 0.73 / Th17 0.27 | **Treg 0.00** / Th1 0.56 / Th17 0.44 |

Both engines are Treg-dominant at baseline and **abolish Treg entirely under the
FOXP3_2 knockout**, redistributing to Th1/Th17 — the same qualitative and
near-quantitative result. The absolute proportions differ (small differentiated
counts + the spatial approximations above), so the comparison is **distributional,
not cell-by-cell** — which is exactly how the original notebook frames it too.

---

## 6. Summary: what to trust

- **Intracellular differentiation logic** — faithful and validated. If your
  question is "how does perturbing FOXP3_2 / NFKB reshape the Treg/Th1/Th17
  attractor," the Python port answers it with the same fidelity as PhysiBoSS.
- **Spatial/mechanical detail** — a deliberate on-lattice simplification. It
  reproduces the *aggregate* outcome (who dominates, what a knockout does) but
  should not be read for precise geometry, exact contact timing, or absolute
  cell counts.
- **The payoff of the port** — the whole model, including its perturbation series,
  is now a set of readable Python nodes and GUI-editable parameter tables (the
  five XML files became five planner tabs), rather than a compiled C++ project
  edited through XML.

### Where each mechanism lives

| Mechanism | PhysiCell | TCELL_CORRAL |
|---|---|---|
| CCL21 field | `microenvironment_setup` (XML) + BioFVM | `setup_ccl21_field.py` + `diffuse_ccl21.py` |
| Endothelial secretion | `secretion` block (XML) | `diffuse_ccl21.py` (kind-gated source) |
| DC chemotaxis | `motility`/`chemotaxis` (XML) + `dendritic_cells.bnd` + `rules.csv` | `chemotax_ccl21.py` |
| DC↔T0 contact | mechanical contact signal | `sense_dc_contact.py` / `agent.neighbors` |
| T0 network | `tcell_corral.bnd/.cfg` via PhysiBoSS | `build_tcell_networks.py` + `step_tcell_network.py` + engine `step_maboss` |
| Fate commitment | `transform to <fate>` output mapping | `commit_tcell_fate.py` |
| Motility by fate | per-type `motility` (XML) | `differentiated_motility.py` |
| FOXP3_2/NFKB `_lower` | `$u_…` parameter (XML) | `build_tcell_networks` `up_rate_overrides` tab |
| FOXP3_2/NFKB `_mutant` | `mutation` block (XML) | `fix_tcell_nodes` `fixed_nodes` tab |
