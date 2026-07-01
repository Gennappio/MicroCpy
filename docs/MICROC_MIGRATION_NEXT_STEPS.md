# MicroC ABM Migration — Next Steps (detailed handoff)

Companion to `docs/MICROC_ABM_MIGRATION_PLAN.md`. The plan has the stage outline;
**this file is the concrete, code-level guide for resuming** — what's done, the
hard-won facts you must not relearn, and exactly what to do in Stages 4–7.

---

## Where we are

| Stage | What landed | Commit |
|---|---|---|
| 0 | MicroC made reproducible (de-ordered gene walk) + golden-reference harness | `0bb9835`, `b8afee3` |
| 1 | `DiffusingResource` wraps the FiPy solver (1:1 field) | `a741247` |
| 2 | Oxygen vertical slice — coupling/coordinates match legacy (**GO**) | `e62c057` |
| 3 | 8 substances as resources + `diffuse_substances` env behaviour | (this commit) |

Everything is **behaviour-preserving and gated on the Stage-0 golden**. Don't
break that contract.

## Hard-won facts (do NOT relearn these)

1. **Reproducibility requires four seeds.** `workflow.seed` only fixes entity
   *iteration order*. The biology uses the **global** `random` + `numpy.random`
   (seed both), and `PYTHONHASHSEED` matters because the gene walk samples a
   `set` — pin it. Daughter cells get non-seedable `uuid4` ids → **compare cells
   by position, not id**. All of this is handled in
   `tools/migration/microc_golden.py`; reuse it.
2. **Field ↔ mesh is 1:1.** `field[y, x]` is the concentration at world tile
   `(x, y)`; internally `var.value[x*ny + y]` (column-major). No interpolation.
3. **Two grids.** Cells live on a **bio-grid** of `nx = size_µm/cell_height_µm`
   (75 for MicroC); substances on the **mesh grid** (50). `cell.state.position`
   is a raw bio-grid integer index.
4. **Deposition is clean with zero conversion.** Key reactions by **raw**
   `agent.position`; the solver scales once in
   `_create_source_field_from_reactions`: `i = int(px * nx / bio_grid_nx)`,
   `fipy_idx = i*ny + j`, lands at `concentrations[j, i]`.
5. **Sensing is NOT auto-scaled — the Stage-4 trap.** `DiffusingResource.at()` /
   `values()` index the 50-grid directly. A cell at bio `(38,23)` read via
   `at((38,23))` reads mesh `[23,38]`, NOT the `[15,25]` where its own source
   landed. The legacy metabolism scales on read by hand
   (`int(cell_x*cell_size_um/grid_spacing)`). **Preserve that scaling when you
   migrate sensing to agents.**
6. **`diffuse_substances` delegates** to `run_diffusion_solver_coupled`, which
   reads `context['population']` (legacy `CellPopulation`) and runs the Picard
   loop. Its metabolism (`_recalculate_metabolism`) reads per cell:
   `state.phenotype` (skips `Necrosis`/`Growth_Arrest`), `state.position`,
   `state.gene_states['mitoATP'/'glycoATP']`; MM params default in-code
   (`oxygen_vmax=3e-17`, `KO2=0.005`, …). Reactions are
   `{position: {substance: rate}}`, negative = consumption.

## How to verify (run these constantly)

```bash
cd opencellcomms_engine
# order-independence (two runs, different hash seeds, must match):
../.venv/Scripts/python.exe tools/migration/microc_golden.py determinism --seed 123 --steps 3
# golden regression (a fresh run must still match the frozen golden):
../.venv/Scripts/python.exe -m pytest tests/migration/test_microc_golden.py    # ~75s, slow
# the ABM unit gates (fast):
../.venv/Scripts/python.exe -m pytest tests/test_abm_*.py
```
The golden is `tools/migration/golden/` (seed 123, 3 steps, 1009 cells). If you
deliberately change MicroC's trajectory again, regenerate it with
`microc_golden.py run --seed 123 --steps 3 --out tools/migration/golden`.

---

## Stage 4 — cells & metabolism onto `abm_population` — **DONE (golden MATCH)**

Implemented via option (b): `build_tumor_cell_abm_population`
(`opencellcomms_adapters/MicroC/functions/initialization/`) wraps MicroC's
existing `CellPopulation` (same cells), added as the last `tumor_cell_init` node;
`_run_for_each_entity` now binds `_current_cell = agent.cell`. **Gotcha that bit
us (relevant to Stage 5):** `_recalculate_metabolism` REPLACES `metabolic_state`
each tick, wiping the `_kind` tag → `agents_of_kind` empty. MicroC is single-kind
so its `for_each` dropped the `kind` filter. If Stage 5 stashes agent state in
`metabolic_state` (via `agent.set`), it will be wiped too — use a field metabolism
doesn't own, or make metabolism merge. The rest of the original Stage-4 notes
below are retained for reference.

**Goal:** MicroC runs on the new motor. Today `executor.py` builds **no**
`abm_population` for MicroC, so the per-agent ask falls back to
`_run_for_each_legacy_cell` over `context['population']` (executor.py ~692). Make
MicroC build an `abm_population` and run cells through it, then validate against
the golden.

**Steps:**
1. **Build the `abm_population` for MicroC.** Either (a) a MicroC init that calls
   `setup_world` (`src/workflow/functions/initialization/setup_world.py`) with a
   bio-grid `LatticeWorld` (`tile_size == cell_height == 20` → `nx=ny=75`), then
   places tumor cells as agents at their CSV bio-grid positions; or (b) wrap the
   existing `CellPopulation` MicroC already builds in an `abm.Population` (it
   already *contains* a `CellPopulation` — see `Population.__init__`, which builds
   one sized to the world). Option (b) is less invasive: construct
   `Population(world)` whose `cellpop` IS MicroC's loaded population, so
   `abm_population` and the legacy `population` are the same cells.
   - **Verify positions:** `agent.position == cell.state.position` (bio-grid).
2. **Per-agent behaviours.** `gene_update` / `fate_update` should run via the
   per-agent ask (`_run_for_each_entity`) instead of `_run_for_each_legacy_cell`.
   Once `abm_population` exists, the executor already routes there. Confirm each
   behaviour reads `env.agent` (or still `env.cell` — check
   `BiologicalContext.cell` vs `.agent`; MicroC's behaviours currently use the
   legacy per-cell binding `context['_current_cell']`).
3. **Metabolism reads agents.** `diffuse_substances` delegates to
   `run_diffusion_solver_coupled`, whose `_recalculate_metabolism` iterates
   `population.state.cells`. If `abm_population.cellpop` is the same object, this
   keeps working unchanged. If you move cells fully off `CellPopulation`, adapt
   `_recalculate_metabolism` + `_collect_reactions_from_cells` to iterate
   `env.agents` and read `agent.get(...)`/`agent.position` — **and keep the
   sensing scale-on-read** (fact #5).
4. **Validate.** Run MicroC end-to-end on the new motor and diff against the
   golden with the harness. Iterate until `compare` reports MATCH (exact). This is
   the real Stage-4 gate — fields + per-cell state + aggregates.

**Trap checklist for Stage 4:** sensing scale (#5); position is bio-grid (#3);
reactions keyed raw (#4); determinism seeds (#1); compare by position (#1).

## Stage 5 — division via reconciliation

MicroC's `division` is a World behaviour (`microc.json` `world.behavior_subworkflows`)
calling `update_cell_division`, which mutates the population directly. Move
structural change to the engine reconciliation pipeline:
- New/daughter cells via an `add_agent` intent; deaths via `remove_agent`/cull.
- The reconciliation order is canonical (see `tools/.../reconciliationSteps.js` and
  `functions/reconciliation/apply_reconciliation.py`): resource deltas → move →
  consume → add → remove → cull.
- **Gate:** cell-population trajectory (count, positions) matches the golden.
- Watch determinism: division placement already de-ordered (Stage 0); keep it
  order-independent.

## Stage 6 — substances as real per-resource inits (the "mix") — **DONE (golden MATCH)**

**Done (real, not cosmetic):** each of the 8 substances now has a **real
per-resource init canvas** on the Resources tab. Every `*_init` subworkflow runs
`setup_substances` for its one substance and is wired into `__init_sequence__`
(after `__world__`, before `tumor_cell_init`, in canonical order). The collective
`setup_substances` node was **removed** from `__world__`. Because per-substance
`setup_substances` calls append to `config.substances` and reinitialize
cumulatively (idempotent — see `initialize_substances`), the final simulator state
is identical to the old single collective call, so the golden still MATCHes
(bit-exact, 3 steps). The removal is the proof it's wired: with the collective node
gone, an unrun init would leave the fields empty and the golden would diverge.

**Coupled diffusion stays a collective World step — by design.** The diffusion is
one FiPy solve per tick over all substances together (a domain-level process, not
any single substance's step), so it remains a World/Domain step rather than a
per-resource behaviour. This is the deliberate **mix**: per-resource *init*,
collective *run*. (The GUI still auto-scopes per-resource *behaviours* to
`for_each:{type:resource}`; homing the collective solve under a resource kind would
need a "collective resource behaviour" concept in the GUI — a genuine future item,
but no longer what makes the substances real. Do NOT home `diffusion_step` under a
`resource_kind` until the GUI supports it.) Original reference items:

1. **Register `diffuse_substances`** as a usable node: import it in
   `src/workflow/functions/diffusion/__init__.py` (pulled in via
   `standard_functions.py`), so the palette/executor see it. It exists and is
   tested but is not yet in the registry.
2. **`microc.json` `metadata.gui`:** populate `resource_kinds` with the 8
   substances (init = the substance setup, behaviour = `diffuse_substances`); strip
   substance setup/run from `world`; keep only true world concerns in
   `world.behavior_subworkflows`; home `division` via reconciliation.
3. **Tab ontology (CLAUDE.md rule):** Resources tab non-empty; World = domain only;
   Agents intact; no orphan behaviours. Every behaviour reachable from a real tab.
4. **Controller labels** are auto-derived now (`controllerLabel`), so no manual
   labels needed.

## Stage 7 — full validation & sign-off

- End-to-end MicroC on the new motor vs the Stage-0 golden, within tolerance
  (baseline is exact, so aim for exact/near-exact).
- Update `docs/ABM_LAYER.md` / `ABM_GUI.md`: document the **two resource-coupling
  modes** — discrete per-agent `deposit` (Sugarscape) vs continuum reaction via
  `DiffusingResource` + the coupled solve (MicroC) — and the `DiffusingResource`
  pattern.
- Leave the legacy `CellPopulation` + `run_diffusion_solver_coupled` paths intact
  (other models may use them); MicroC simply stops using them.

---

## Key files

- Harness + golden: `opencellcomms_engine/tools/migration/microc_golden.py`,
  `tools/migration/golden/`, `tests/migration/test_microc_golden.py`
- Resource layer: `opencellcomms_engine/src/abm/resource.py`
  (`DiffusingResource`, `add_diffusing_resources`)
- Collective behaviour: `src/workflow/functions/diffusion/diffuse_substances.py`
- Legacy solver (the source of truth to match): `src/simulation/multi_substance_simulator.py`,
  `src/workflow/functions/diffusion/run_diffusion_solver_coupled.py`
- Executor motor routing: `src/workflow/executor.py` (`_run_for_each_entity` vs
  `_run_for_each_legacy_cell`; `abm_population` check)
- ABM gates: `tests/test_abm_diffusing_resource.py`, `test_abm_oxygen_slice.py`,
  `test_abm_diffuse_substances.py`
