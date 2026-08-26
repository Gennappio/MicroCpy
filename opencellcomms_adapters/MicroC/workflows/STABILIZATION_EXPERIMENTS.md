# Glucose-Loop Stabilization Experiments

Companion note for the `microc_p53_experiment_stab_*.json` workflows in this
folder. Each is a copy of `microc_p53_experiment.json` that changes **one
mechanism**; the Planner keeps only the **MCT1off** arm enabled, exactly as in
the source experiment, so runs are directly comparable.

## The problem we are trying to fix

Running the MCT1off arm (MCT1 and p53 clamped OFF), the population does not
settle into the expected pattern — a glycolytic rim outside the 4 mM
Glucose_supply line and a quiescent core inside it. Instead it oscillates as a
whole: cells go glycoATP en masse, the collective glucose drawdown drags the
4 mM threshold line across (almost) the entire colony, the cells then switch
off en masse (with a long gene-network lag), glucose refills everywhere, and
the cycle repeats. Measured on a MaBoSS + steady-fields run of the same
family: glycoATP swings between ~510 and ~150 of ~1060 cells while the
sub-threshold area sweeps between 95 % and 0 % of the spheroid interior, with
a half-period of roughly 150–250 iterations; the gene response keeps falling
for ~200 iterations *after* the field has recovered everywhere — pure
pipeline delay through the ~11-layer Boolean glycolysis chain.

## Why it happens (the mechanism)

The loop has the three classic ingredients of a **relay (thermostat) limit
cycle on a shared resource**:

1. **Infinite gain.** `Glucose_supply = (local glucose >= 4 mM)` is an
   all-or-nothing switch, and a cell whose glycoATP gene flips consumes at
   full power instantly (glycolytic consumption is ~15–20x the mitochondrial
   glucose draw). The Michaelis–Menten factor (KG = 0.5 mM) smooths the rate,
   never the switch.
2. **Delay.** Glucose_supply reaches glycoATP through ~11 Boolean layers, so
   the population reacts to the field it saw hours ago.
3. **Shared-pool coupling.** All cells draw one glucose field with only
   **1 mM of headroom** (boundary 5 mM vs threshold 4 mM) against a
   **collective drawdown of ~2–4 mM**. The instability ratio
   `Γ = drawdown / headroom ≈ 2–4`: once Γ > 1, no stationary front exists —
   mass activation must drag the line over everyone, mass shutdown must
   release everyone, and the shared field acts as a global clock that keeps
   the population in phase.

Every experiment below pushes on one of those three ingredients: the **gain**
(how far the line moves per switching cell), the **steepness** (all-or-nothing
response), or the **coherence** (everyone switching in lockstep). The delay is
real biology and is left alone.

## Supporting theory

- **Relay feedback / thermostat limit cycles** (control theory): negative
  feedback through an on–off element with lag generically produces sustained
  limit cycles; describing-function analysis (Åström & Hägglund's relay
  auto-tuning) predicts their period and amplitude. The Glucose_supply
  threshold is literally a relay on the glucose field.
- **Delayed negative feedback oscillators** (mathematical biology):
  Hutchinson's delayed logistic oscillates once gain x delay is large enough;
  the **Goodwin oscillator** (1965) — a multi-step gene cascade closing a
  negative feedback loop — oscillates when steepness and delay are large; a
  Boolean step is the infinite-steepness limit. Mackey–Glass is the same
  family.
- **Consumer–resource cycles** (ecology): Rosenzweig–MacArthur's *paradox of
  enrichment* — steep functional responses destabilize the consumer–resource
  equilibrium into limit cycles; chemostats with delayed uptake behave the
  same. Glucose is the prey, glycolytic activity the predation.
- **Dynamical quorum sensing / mean-field synchronization**: "one agent's
  behaviour makes the others behave the same" is coupling through a shared
  field. The canonical experimental system is synchronized glycolytic
  oscillations in yeast populations coupled by extracellular acetaldehyde
  (Danø, Sørensen & Hynne, *Nature* 1999; De Monte et al., *PNAS* 2007;
  Taylor et al., *Science* 2009).
- **Piecewise-smooth (Filippov) dynamics**: with no delay the front would
  "slide" along the threshold; delay converts sliding into chattering and
  finite-amplitude relaxation cycles.
- **Boundary geometry (2D)**: with a Dirichlet boundary at distance R from a
  colony of radius a, the steady drawdown scales with `1 + 2 ln(R/a)` — the
  cell-free moat is a series resistance in the supply line, and in 2D its
  effect grows logarithmically with domain size (in 3D it saturates).
  Measured with this project's solver: the current geometry (moat ~393 µm)
  carries 1.64x the drawdown of a close boundary (~93 µm).

## The experiments

| Workflow | One change | Ingredient attacked | Why it should stabilize |
|---|---|---|---|
| `..._stab_consumption.json` | MCT1off Glucose Consumption Scale **20 → 5** | Gain | Drawdown is proportional to consumption; at 4x less, the collective drawdown drops below the 1 mM headroom and the 4 mM line can no longer sweep the colony. Fastest single test of the diagnosis. |
| `..._stab_headroom.json` | Glucose boundary/initial **5 → 25 mM** (threshold stays 4; plot scale follows) | Gain margin | Headroom grows 1 → 21 mM, far above the ~2–4 mM drawdown: mass threshold crossing becomes arithmetically impossible. 25 mM is standard culture-medium glucose. |
| `..._stab_diffusion.json` | Glucose D **6.7e-11 → 2.0e-10 m²/s** | Gain (transport) | Drawdown ∝ 1/D. Also moves the glucose field's relaxation from ~1 h to ~20 min, restoring the fast-field / slow-gene timescale separation that quasi-steady solving assumes. Mid-range tissue literature value. |
| `..._stab_close_boundary.json` | **Cell Height 20 → 30 µm** with the recentered seed `initial_cells_1000_center_1500_cell30.csv` | Gain (boundary) | Cell Height is the multiplier that maps the seed's integer grid indices into physical space, and it is a GUI parameter on the World canvas. Raising it to 30 µm grows the same 1000-cell colony to ~540 µm radius in the unchanged 1500 µm domain, cutting the cell-free moat 393 → ~210 µm — with **total consumption unchanged**, isolating pure boundary geometry. Steeper near-boundary gradients pin the 4 mM line and the post-crash refill lag drops ~38 → ~12 min. (The seed's indices are shifted by −12: the rescale is anchored at the origin, so without the shift the colony would land off-centre with its far cap clamped onto the grid edge.) |
| `..._stab_hill_input.json` | `Glucose_supply` added to Hill-Activated Inputs (**hill_max 1.0, exponent 4**) | Steepness + coherence | Activation becomes `P = (c/4)⁴ / (1+(c/4)⁴)` tested against each cell's *persistent* random — every cell carries its own effective threshold spread around 4 mM (quenched heterogeneity, no per-step flicker). Cells at the front switch independently instead of in unison; the relay's infinite gain becomes finite. Same mechanism NetLogo applies to the MCT1I/GLUT1I drug inputs; zero engine changes. |

Deliberately **not** in this battery: the flux-ramp experiment (a per-cell
enzymatic capacity `dg/dt = (glycoATP − g)/τ` so cells *fade* into glycolysis
instead of switching to full power — the biologically grounded fix for the
abrupt consumption itself). It requires an engine change to
`calculate_cell_metabolism` and will be added separately.

## What success looks like

- The 4 mM isoline in the quadrant plots stops travelling: a stationary
  glycoATP rim outside it, quiescent (or starved) core inside it.
- `gene_fate_counts_over_time.csv` / `metabolic_symbiosis_over_time.csv`:
  `n_glycoATP` converges instead of swinging by hundreds of cells.
- In the MaBoSS + on-change-steady sibling of a winning configuration, the
  solve log itself becomes the stability meter: long "skipped step" streaks
  mean the field-relevant state has genuinely stopped changing.

The mechanisms compose: the expected production configuration combines
realistic D and headroom with Hill sensing (and, later, the flux ramp), at
which point the boundary and consumption scales stop being load-bearing.
These copies keep the single-gene updater of the source experiment; the same
levers apply unchanged to the `_transient` and `_maboss_steady` variants,
which share the identical field laws.
