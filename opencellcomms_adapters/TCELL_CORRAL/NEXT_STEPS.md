# TCELL_CORRAL — Development Roadmap & Handoff

Resumable plan for finishing the plugin. Written to be **self-sufficient**: the
PhysiCell reference values are embedded here, so you do not need the machine-local
PhysiCell tree to continue (the essential `.bnd`/`.cfg`/`cells.csv` are already
vendored in `data/`).

---

## 0. Where we are (state as of this commit)

| Piece | Status | Location |
|---|---|---|
| Engine: MaBoSS continuous-time stochastic mode | ✅ done + validated | `opencellcomms_engine/src/biology/gene_network.py` (`step_maboss`, `load_cfg`, `set_rate`) — commit `fc86aab` |
| Engine: `AND/OR/NOT` word-operator parser fix | ✅ done | same file (`BooleanExpression._compile`) — commit `fc86aab` |
| Engine: analytic + cmaboss cross-check tests | ✅ passing | `opencellcomms_engine/tests/biology/test_maboss_ctmc.py`, `test_maboss_crosscheck.py` |
| Plugin: skeleton + vendored data | ✅ done | this directory |
| Plugin: intracellular core (build + step) | ✅ done | `functions/initialization/build_tcell_networks.py`, `functions/intracellular/step_tcell_network.py` |
| Plugin: spatial layer (population, CCL21, chemotaxis, contact, fate, motility) | ⏳ **next** | see §4 |
| Plugin: behaviors + workflow JSON + reporting | ⏳ next | see §4 |
| Validation vs PhysiCell | ⏳ final | see §5 |

**Fidelity is locked.** On the real 95-node `tcell_corral` network, `step_maboss`
matches the reference engine (cmaboss) at steady state — baseline and under the
FOXP3₂ rate perturbation:

| | Treg | Th1 | Th17 |
|---|---|---|---|
| MaBoSS baseline | 0.494 | 0.261 | 0.245 |
| our engine baseline | 0.526 | 0.258 | 0.216 |
| MaBoSS `$u_FOXP3_2=0.2` | 0.314 | 0.394 | 0.291 |
| our engine `$u_FOXP3_2=0.2` | 0.316 | 0.376 | 0.308 |

---

## 1. The goal

Reproduce the PhysiCell / PhysiBoSS **FOXP3_2 Corral** T-helper differentiation
experiment in **native Python** (the `biophysics` kernel), so the model — and its
perturbations — are readable and editable from the GUI.

**Mechanism:** one endothelial cell secretes CCL21 → dendritic cells chemotax up
the gradient → DC contacts a naive T0 cell → contact switches on the T0 cell's
MaBoSS network → the network settles into a Treg / Th1 / Th17 attractor → the T0
cell commits to that fate. No birth, no death. `FOXP3_2_lower` lowers one MaBoSS
transition rate, shifting the split away from Treg.

---

## 2. Architecture (decided)

- **Native `biophysics` kernel**, on-lattice ABM (the model is mechanics-light —
  no proliferation, no volume dynamics, sparse cells — so the lattice is fine).
- **Two layers:** (1) intracellular MaBoSS — DONE and validated; (2) spatial ABM.
- **One `tcell` agent kind carrying a `fate` state field** (`naive`/`Treg`/`Th1`/
  `Th17`), rather than four kinds. Differentiation is a state change on one cell,
  which avoids remove+respawn churn on the lattice; the MaBoSS network simply
  stops being consulted once `fate` commits. (Alternative: 4 kinds + a
  `request_transform`; more GUI-explicit, more plumbing. Revisit only if the GUI
  needs each fate as a first-class Agents-tab entity.)
- **The perturbation is a GUI knob:** `build_tcell_networks`'
  `up_rate_overrides` DICT param. `FOXP3_2_lower` = `{"FOXP3_2": 0.2}`;
  `_mutant` = clamp the node OFF (use `BooleanNetwork.fix_node`, add a small
  `fix_tcell_nodes` function mirroring MicroC's `fix_gene_nodes`).

---

## 3. PhysiCell reference values (embedded — the source of truth for the port)

**Domain / time (2D):** x,y ∈ [-300, 300] µm (600×600), z ∈ [-10, 10]; substrate
mesh dx=20 → 30×30. `max_time` 5000 min (~83 h). Intracellular step = 6 min
(`intracellular_dt=6`, tcell `scaling=1.0`; dendritic `scaling=30`). Cell volume
2494 µm³ → radius ~8.4 µm, diameter ~17 µm (→ a ~35×35 bio-grid over 600 µm).

**CCL21 substrate:** D = 1000 µm²/min, decay = 0.005 /min, initial 0, Dirichlet
off, gradients on.

**Cell kinds** (all: no cycle/no death; adhesion 0.4 / repulsion 10 / max-adh-dist
1.25):

| Kind | Count | Motility | CCL21 | Intracellular |
|---|---|---|---|---|
| T0 (→Treg/Th1/Th17) | 100 | speed 0.8, no chemotaxis | — | `tcell_corral` (95 nodes) |
| Treg | (fate) | speed 0.5, bias 0.5 | — | — |
| Th1 | (fate) | disabled | — | — |
| Th17 | (fate) | speed 0.5 | **uptake 0.5** | — |
| dendritic_cell | 7 | chemotaxis→CCL21, bias 0.8 | — | `dendritic_cells` (4 nodes) |
| endothelial_cell | 1 | disabled | **secrete rate 10, target 10** | — |

**Initial positions:** in `data/cells.csv` (100 T0 clustered upper-left
x∈[-266,-118] y∈[112,290]; 7 DC; 1 endothelial).

**rules.csv (single rule):** `dendritic_cell, CCL21, decreases, migration bias,
0.0, 2, 4, 0` — high CCL21 damps DC migration bias (Hill: saturation 0, half-max
2, power 4).

**T0 network I/O:** "contact with dendritic_cell" drives **9 input nodes** ON —
`IL1_In, MHCII_b1, MHCII_b2, IL12_In, IL6_In, CD80, CD4, IL23_In, PIP2`. Output
nodes `Treg`/`Th1`/`Th17` map to PhysiCell `transform to …` (value 1e6 = commit).
`FOXP3_2 = IL1R AND NOT MINA`; it feeds Treg and represses SATB1 (the Th17 arm).

**DC network:** `Migration = Maturation & CCL21 & !Contact`; init `Maturation=1`;
outputs → chemotactic response + migration speed. (Tiny enough to inline as a
guard — "chemotax unless touching a T0" — instead of running MaBoSS for the DC.)

**Perturbation series** (each was a separate XML; here they are params):
`WT` (none) · `FOXP3_2_lower` `$u_FOXP3_2=0.2` · `FOXP3_2_mutant` FOXP3_2 clamped
OFF · `NFKB_lower` `$u_NFKB=0.1` · `NFKB_mutant` NFKB clamped OFF.

---

## 4. Next increments (sequenced)

Each: **goal → files → API/pattern to mirror → definition of done (DoD)**.

### Increment 2 — population + a first intracellular-only run *(start here)*
- **Goal:** load the 3 kinds and run the differentiation with contact faked ON, to
  prove the intracellular layer end-to-end in a workflow before adding space.
- **Files:** `functions/initialization/place_cells_from_csv.py`; a minimal
  `workflows/tcell_corral_intracellular.json`.
- **Mirror:** MicroC `functions/initialization/build_tumor_cell_abm_population.py`
  (CSV → `abm.Population` sharing the legacy `CellPopulation`); it maps µm → grid.
- **Wiring:** setup world → `place_cells_from_csv` → `build_tcell_networks` →
  scheduler `{ (temporary) set the 9 contact inputs ON → step_tcell_network }` →
  `record_fate_counts`.
- **DoD:** CLI run yields Treg/Th1/Th17 ≈ the §0 baseline (Treg ~0.5). This is the
  cheapest end-to-end checkpoint.

### Increment 3 — CCL21 diffusion + secretion/uptake
- **Files:** `functions/initialization/setup_ccl21_field.py`;
  `functions/intercellular/secrete_ccl21.py` (endothelial source);
  `functions/intercellular/uptake_ccl21.py` (Th17 sink).
- **Mirror:** MicroC `__world__.subworkflow.json` substance setup +
  `run_diffusion_solver_coupled`; secretion/uptake as per-cell reaction terms.
- **Values:** CCL21 D=1000, decay=0.005; endothelial rate 10/target 10; Th17 0.5.
- **DoD:** a CCL21 gradient forms around the endothelial cell (inspect field / plot).

### Increment 4 — DC chemotaxis + contact-gated activation
- **Files:** `functions/intercellular/chemotax_ccl21.py` (DC),
  `functions/intercellular/sense_tcell_contact.py` (DC),
  `functions/intracellular/sense_dc_contact.py` (T0 → set the 9 inputs ON).
- **Mirror:** SUGARSCAPE `functions/forager/move_to_best_sugar.py` for gradient
  climbing; `agent.neighbors()` / `agent.sense()` for contact + field.
- **Detail:** DC climbs CCL21, damped by the rules.csv Hill (half-max 2, power 4),
  stops on T0 contact. Replace increment 2's "all inputs ON" hack with real
  contact gating (only contacted T0s activate their networks).
- **DoD:** DCs migrate toward the T0 cluster; only contacted T0s differentiate.

### Increment 5 — fate commitment + differentiated motility
- **Files:** `functions/intercellular/commit_tcell_fate.py` (Treg/Th1/Th17 node ON
  → set `fate`), `functions/intercellular/differentiated_motility.py`
  (naive 0.8 / Treg 0.5 / Th1 0 / Th17 0.5 + CCL21 uptake).
- **DoD:** T0s commit spatially; fate-specific motility behaves.

### Increment 6 — behaviors + workflow JSON + reporting
- **Files:** `behaviors/*.subworkflow.json`; `workflows/tcell_corral.json`;
  `functions/reporting/record_fate_counts.py`, `plot_fate_timeseries.py`.
- **Homing rule (non-negotiable, see root `CLAUDE.md`):** every behaviour must sit
  under a real GUI tab — home in-loop behaviours to their owning agent/resource
  kind (`tcell`, `dendritic_cell`, `endothelial_cell`, `CCL21`), post-loop to
  `processing`. **Never** `environment.behavior_subworkflows`. Use
  `dictParameterNode` for DICT params (e.g. `up_rate_overrides`) so they render as
  editable tables.
- **DoD:** opens in the GUI, runs end-to-end, emits fate proportions over time.

### Increment 7 — validation vs PhysiCell
- Run `WT / FOXP3_2_lower / FOXP3_2_mutant` (+ the NFKB pair) and compare the
  Treg:Th1:Th17 proportions to PhysiCell's `scripts/Corral_analysis.ipynb`.
  Stochastic → distributional comparison, not cell-by-cell. Add `fix_tcell_nodes`
  (mirror MicroC `fix_gene_nodes`) for the `_mutant` knockouts.

### Quick win (any time) — make the cross-check portable
`tests/biology/test_maboss_crosscheck.py` currently points `_PHYSICELL_BN` at a
machine-local PhysiCell path, so its two `slow` tcell tests **skip on other
machines**. Repoint them at the now-vendored `TCELL_CORRAL/data/tcell_corral.*`
so the full cross-check runs anywhere `cmaboss` is installed.

---

## 5. Key decisions & gotchas (the "why", not in the code)

- **Rate perturbations need CTMC.** Discrete Boolean modes are blind to a
  transition rate, so the `_lower` configs are meaningless there; `_mutant`
  (knockout) *could* use discrete clamping, but `_lower` forces `step_maboss`.
- **Cross-check at steady state only.** MaBoSS's `probtraj` value at time *t* is a
  time-average over `[t, t+time_tick]`; comparing at a transient time disagrees by
  that reporting convention. Attractor/steady-state comparison is convention-free.
- **cmaboss, not a binary.** The reference engine is the pip package `cmaboss`
  (`maboss.load(..., cmaboss=True)`) — no external `MaBoSS` executable needed.
  Install via `pip install -e ".[maboss]"`.
- **On-lattice ≈ off-lattice here.** PhysiCell motility is off-lattice; the lattice
  chemotaxis approximation is acceptable because this model is contact-driven and
  sparse, not mechanically crowded.
- **`AND/OR/NOT` fix.** Before commit `fc86aab`, `BooleanExpression` only handled
  `&|!`; word-operator networks (like `tcell_corral`) silently compiled every such
  node to `False`. Fixed with `\b`-bounded regex (so `NOTCH1` etc. survive).
- **Iteration order is always random** in the executor's per-agent ask
  (`for_each.order` is intentionally ignored) — do not "fix" it.
- **RNG:** `step_tcell_network` calls `step_maboss(dt)` with the global RNG, which
  the executor seeds once per run; pass an explicit `random.Random` only if you
  need per-cell reproducibility independent of interleaving.

---

## 6. Key paths, commands, and how to resume elsewhere

**Paths**
- Engine CTMC: `opencellcomms_engine/src/biology/gene_network.py`
- Cross-check tests: `opencellcomms_engine/tests/biology/test_maboss_{ctmc,crosscheck}.py`
- This plugin: `opencellcomms_adapters/TCELL_CORRAL/` (data vendored in `data/`)
- Template to mirror: `opencellcomms_adapters/MicroC/` (population, gene-network
  init/step); `opencellcomms_adapters/SUGARSCAPE/functions/forager/` (motility)
- PhysiCell source (machine-local, not required — values captured in §3):
  `…/PhysiCell/config/differentiation/` (`*.xml`, `rules.csv`, `cells.csv`,
  `boolean_network/`, `scripts/Corral_analysis.ipynb`)

**Resume on another machine**
```bash
git checkout plugins-alignment
cd opencellcomms_engine && pip install -e ".[dev,diffusion,maboss]"
# core validation (self-contained; runs anywhere):
python -m pytest tests/biology/test_maboss_ctmc.py -q
python -m pytest tests/biology/test_maboss_crosscheck.py -q -m "slow or not slow"
#   -> the toggle cross-check runs; the two tcell cross-checks SKIP unless the
#      PhysiCell path exists (see the §4 "quick win" to make them portable).
# sanity-check the plugin registers:
python -c "import sys; sys.path[:0]=['.','..']; import opencellcomms_adapters.TCELL_CORRAL.register; import src.workflow.registry as r; g=r.get_default_registry(); print('build_tcell_networks' in g.functions, 'step_tcell_network' in g.functions)"
```

**Adding a new node function** (recap of root `CLAUDE.md`): create the file under
`functions/<category>/`, decorate with `@register_function` (typed `env`,
`requires=[...]`, `compatible_kernels=["biophysics"]`), import it in
`register.py`, restart the backend. One file = one node = one atomic function; a
behaviour is a subworkflow of atomic nodes.
