# MicroC → ABM Library Migration Plan

**Status:** Draft for approval · **Scope:** engine + adapter + GUI metadata · **Type:** behaviour-preserving migration

Bring MicroC onto the new ABM motor (`abm_population` + `Domain`/`Resource` +
reconciliation) so that its substances become first-class **Resources** and its
structure matches the tab ontology the platform is built around. This is the
**completion of the original design**, not a redesign: `src/abm/resource.py`
already names *oxygen* as a resource and declares that *"a later
`DiffusingResource` will wrap the FiPy substance solver behind this same
interface"* — that piece was deferred and never built, which is why MicroC is
stranded on the legacy path and the Resource tab is empty.

---

## 1. Goals

- MicroC runs on the **new motor**: cells live in `abm_population`, not the
  legacy `CellPopulation`.
- The 8 substances are declared as **`resource_kinds`** and appear in the
  **Resource tab**, with their setup as resource init and their diffusion as a
  resource behaviour.
- The diffusion driver is a **new-style (`env`) behaviour**, not the old
  `context`-dict function.
- **World tab = the domain only.** Substance setup/run leaves the World;
  `division` moves to **reconciliation**.
- **The science does not change.** Numerical outputs match the pre-migration
  MicroC within an agreed tolerance.

## 2. Non-goals (explicit)

- **Not** converting MicroC's continuum uptake to Sugarscape-style discrete
  per-agent `consume_resource` reconciliation. MicroC's reaction–diffusion PDE
  with Michaelis–Menten uptake is scientifically intentional and is **kept**.
  Substance uptake stays a reaction term solved by FiPy; reconciliation is used
  only for **structural** changes (division/death).
- **Not** changing the biology, parameters, gene networks, or solver numerics.
- **Not** deleting the legacy `CellPopulation` / `simulator` paths in this work
  (other models may still use them; deprecation is a later, separate decision).

## 3. Current state (verified by reading the code)

| Aspect | MicroC today | New motor (Sugarscape) |
|---|---|---|
| Population | legacy `CellPopulation` in `context['population']` | `abm_population` built by `setup_world` |
| Substances | fields inside `context['simulator']` (FiPy mesh) | `Domain` resources (`FieldResource`) |
| Diffusion | `run_diffusion_solver_coupled(context, …)` — **old style**, reads `simulator` + `population`, Picard-couples cell metabolism ↔ PDE, mutates simulator in place | a Resource `Step` behaviour |
| `resource_kinds` | **`[]`** (empty) | the resources |
| Structural change | `division` as a **World behaviour** | reconciliation `add_agent` / `remove_agent` |
| `agent_kinds` | `tumor_cell` present in GUI metadata **but execution is legacy** | real `abm_population` agents |

Key implication: both of your targets are the *deep* version. MicroC is **fully
legacy under the hood**; the `agent_kinds` metadata is cosmetic until the motor
changes.

## 4. Target state

- `setup_world` builds `LatticeWorld` + `Domain` + `abm_population`.
- 8 `setup_resource` nodes create one `DiffusingResource` per substance
  (Oxygen, Glucose, Lactate, H, TGFA, FGF, HGF, GI).
- One **resource-collective** behaviour (`diffuse_substances`, `env`-style) runs
  the coupled FiPy solve once per tick over all substance resources.
- `tumor_cell` is a real agent; `gene_update` / `fate_update` run per-agent via
  the ask; `division` is committed by reconciliation.
- GUI: **Resources** tab lists the 8 substances; **World** tab holds only the
  domain; **Agents** tab unchanged.

## 5. Key architectural decisions

1. **Coupling → one collective behaviour.** The 8 substances are solved together
   (Picard coupling, `max_coupling_iterations`/`coupling_tolerance`). They are
   declared as 8 `resource_kinds` for visibility, but their diffusion is a
   **single once-per-step resource-collective behaviour**, not eight independent
   `Step`s. (The class layer already blesses "resource/collective behaviours run
   once".)
2. **Two resource-coupling modes are both first-class.** Discrete per-agent
   consumption via reconciliation (Sugarscape) **and** continuum reaction via a
   `DiffusingResource.Step` (MicroC). This must be documented so the empty-tab
   confusion never recurs — continuum resources are not second-class.
3. **`DiffusingResource` wraps the *existing* solver.** We do not reimplement
   diffusion; we adapt `run_diffusion_solver_coupled` behind the `Resource`
   interface so numerics are identical by construction.
4. **Keep the legacy paths intact** during migration; cut over only when the
   golden reference matches.

## 6. Risks & the prime directive

**Prime directive: behaviour preservation.** MicroC is a validated tumour model.
Motor + diffusion changes can silently shift results (FiPy-mesh ↔ lattice-grid
mapping, coupling order, uptake bookkeeping). Every stage is gated on matching a
**golden reference** (Stage 0).

| Risk | Mitigation |
|---|---|
| Mesh↔lattice mapping is lossy | Stage 2 vertical slice proves/disproves this **before** committing to the full migration (hard gate) |
| Non-determinism hides regressions | Stage 0 first establishes seeded determinism; abort if not reproducible |
| Cell uptake differs on `abm_population` | Stage 4 compares uptake fields cell-by-cell against legacy |
| Scope creep into other legacy models | Legacy paths untouched; MicroC-only cutover |

## 7. Staged plan

Each stage has a **deliverable** and an **exit gate**. Stages 0–2 are
sequential; **Stage 2 is go/no-go** for the whole approach.

### Stage 0 — Safety net (golden reference) — *prerequisite*
- Pick a representative, **seeded** MicroC config (standard `microc.json`, small
  grid, ~10–20 steps).
- Build a comparison harness that captures, per checkpoint: each substance field
  array, cell positions/phenotypes/gene states/key metabolic vars, and
  aggregates (phenotype counts, total uptake).
- **First, prove determinism:** two runs with the same seed produce identical
  output. If not, fix that before anything else.
- **Exit gate:** a committed golden-reference dataset + a `compare(run_a, run_b,
  tol)` function with an agreed tolerance (e.g. relative L2 on fields < 1e-6;
  exact match on discrete cell state). Defining "same science" tolerance is a
  decision to confirm here.

### Stage 1 — Core engine: `DiffusingResource`
- **DONE.** Implemented `DiffusingResource(Resource)` in `src/abm/resource.py` as a
  Resource-shaped VIEW over a shared `MultiSubstanceSimulator` (the existing FiPy
  solver) — numerics identical to the legacy path **by construction**, not
  reimplemented. Diffusion is a collective `simulator.update()`; `run_step` is a
  no-op (the Stage-3 behaviour drives the solve).
- **Mesh ↔ lattice resolved: strictly 1:1.** The substance field *is* the FiPy
  mesh field — `field[y, x]` ↔ `var.value[x*ny + y]` — so there is **no
  interpolation**. (The cell-*position* lattice is a different resolution, but
  that only matters when depositing reaction sources — Stage 2.)
- **Exit gate (met):** `tests/test_abm_diffusing_resource.py` — driving the solve
  through `DiffusingResource` yields a field bit-identical to the legacy solver on
  the same source; the 1:1 bridge holds for asymmetric points; the field actually
  diffuses. Fast (~0.7s), kept in the gate.

### Stage 2 — Oxygen-only vertical slice — **GATE PASSED → GO**
- `tests/test_abm_oxygen_slice.py`: a few static cells consume oxygen at a fixed
  rate; the new-motor path (abm agents → reactions from `agent.position` →
  `DiffusingResource.diffuse`) produces a field **bit-identical** to the legacy
  solver, with agent placement round-tripping and sources landing on the correct
  bio→substance-scaled mesh cells. Fast (~0.8s), in the gate.
- **Coordinate handling is clean with ZERO conversion**, provided the new motor:
  (a) places agents on the **bio-grid** — a `LatticeWorld` with
  `tile_size == cell_height` (so `nx = size_µm/cell_height_µm`, 75 for MicroC),
  and (b) keys reactions by **raw** `agent.position`. The legacy
  `_create_source_field_from_reactions` then applies the same `×nx/bio_grid_nx`
  scale and sources land on identical mesh cells.
- **Hazard carried to Stage 4 (sensing, not deposition):** `DiffusingResource.at()`
  / `values()` index the 50×50 mesh directly with no bio→substance scaling, so a
  cell sensing oxygen at a bio-coordinate would read the wrong mesh cell. The
  Picard metabolism step must scale on read (the legacy code already does, by
  hand). Deposition — Stage 2's subject — is unaffected.

### Stage 3 — Full substance set + coupled collective behaviour — **DONE**
- `add_diffusing_resources(domain, world, simulator)` (`src/abm/resource.py`) wraps
  every substance of a `MultiSubstanceSimulator` as a `DiffusingResource` on the
  domain — the 8 MicroC substances become first-class resources, each exposing its
  field 1:1, all sharing the one simulator.
- `diffuse_substances(env)` (`src/workflow/functions/diffusion/diffuse_substances.py`)
  is the env-style collective behaviour; it drives the coupled Picard solve by
  delegating to the existing `run_diffusion_solver_coupled`, so numerics are
  identical. (Stage 4 adapts the metabolism recompute inside that loop to read
  `abm_population` agents; here it reuses the legacy `population` path.)
- **Exit gate (met):** `tests/test_abm_diffuse_substances.py` — the 8 substances
  wrap 1:1; the resource-driven collective solve is bit-identical to the legacy
  simulator on the same multi-substance reactions, with cross-substance effects
  (O₂ consumed / lactate produced); `diffuse_substances` matches the legacy node on
  an identical context (slow, the Picard loop). The full Picard-with-live-cells run
  is validated end to end in Stage 4 against the golden.

### Stage 4 — Cells & metabolism onto `abm_population` — **DONE (golden MATCH)**
- `build_tumor_cell_abm_population` (a new `tumor_cell_init` node) wraps MicroC's
  **existing** `CellPopulation` in an `abm.Population` (`pop.cellpop = legacy` +
  `_rebind`), so `abm_population` and `context['population']` are the SAME cells —
  same order, same seeded shuffle. The executor now routes `gene_update` /
  `fate_update` through the per-agent ask, and `_run_for_each_entity` binds
  `_current_cell = agent.cell` (cleared after the loop) so MicroC's dual-mode
  per-cell functions run unchanged. Diffusion/metabolism keep reading
  `context['population']` (which *is* `abm_population.cellpop`).
- **Finding — `_kind` does not survive metabolism.** `_recalculate_metabolism`
  REPLACES `metabolic_state` each tick, wiping any `_kind` tag → `agents_of_kind`
  goes empty and updates stop. MicroC is single-kind, so its `for_each` drops the
  `kind` filter (iterate ALL agents). **Multi-kind models will need `_kind` to
  survive metabolism** (merge instead of replace, or a dedicated cell field).
- **Exit gate (met):** the full MicroC run on the new motor is **bit-identical** to
  the golden — 8 fields `max_abs=0`, 1009 cells, 0 state diffs, aggregates match;
  `tests/migration/test_microc_golden.py` passes (78s).

### Stage 5 — Structural changes via reconciliation
- Move `division` (and any death/removal) from the World behaviour to
  reconciliation `add_agent` / `remove_agent` / cull intents.
- **Exit gate:** cell population trajectory (count, lineage, positions) matches
  the golden reference.

### Stage 6 — Re-home & GUI metadata cutover
- `microc.json` `metadata.gui`: populate `resource_kinds` (8 substances with
  their init + the `diffuse_substances` behaviour); strip substance setup/run
  from `world`; `world.behavior_subworkflows` keeps only true world concerns;
  `division` homed via reconciliation.
- Verify tab ontology: **Resources** populated, **World** = domain only,
  **Agents** intact, no orphan behaviours (per the CLAUDE.md homing rule).
- **Exit gate:** GUI loads MicroC with a non-empty Resource tab and every
  behaviour reachable from a real tab.

### Stage 7 — Full validation & sign-off
- End-to-end MicroC run on the new motor vs the Stage-0 golden reference.
- Update `docs/ABM_LAYER.md` / `ABM_GUI.md` with the two resource-coupling modes
  (discrete vs continuum) and the `DiffusingResource` pattern.
- **Exit gate:** full run within tolerance; docs updated; legacy path still
  available but MicroC no longer uses it.

## 8. Verification strategy (applies to every stage)

- **Determinism + seed control** is the foundation (Stage 0).
- Compare at three levels: **fields** (per-substance arrays, relative-norm
  tolerance), **agents** (discrete state — ideally exact), **aggregates**
  (phenotype counts, totals).
- Keep the legacy run reproducible throughout so any stage can diff against it.
- A regression test that runs the golden comparison lands with Stage 0 and is
  kept green through Stage 7.

## 9. Open questions (to be answered by Stage 1–2)

1. **Mesh vs lattice:** does FiPy keep its own mesh inside `DiffusingResource`,
   or is the FiPy field reconciled to/from the `LatticeWorld` grid each step?
   Resolution shapes the whole engine piece.
2. **Who owns the solver:** retire the `simulator` object for MicroC, or keep a
   thin solver helper the resource delegates to?
3. **Are `tumor_cell_init` / `gene_update` / `fate_update` `env`-ready** for the
   `abm_population` (per-`env.agent`), or do they assume legacy `env.cell`?
4. **Uptake provenance:** exactly which agent state the Michaelis–Menten uptake
   reads, so it can be reproduced identically from `abm_population`.

## 10. Effort & sequencing

- **Stage 0** — small–medium, but do it first; it is the safety net.
- **Stages 1–2** — the genuinely uncertain core; treat Stage 2 as the gate
  before committing further. Largest technical risk concentrated here.
- **Stages 3–5** — medium each, mostly mechanical once Stage 2 holds, but each
  needs its own verification pass.
- **Stage 6–7** — small–medium re-homing + validation.

Overall: a **multi-day, engine-level migration with real validation work** — not
an afternoon. The de-risking order (0 → 1 → 2 gate) means we learn whether the
approach is viable cheaply, before the bulk of the work.

## 11. Rollback / safety

- All work is behind the existing legacy paths until Stage 6 cutover; reverting
  is "don't flip MicroC's metadata".
- The golden-reference regression test is the tripwire — if any stage diverges,
  it fails loudly and we fix before proceeding.

---

*Approval needed on:* (a) the tolerance definition for "same science" (Stage 0),
(b) keeping continuum uptake (Non-goal #1), and (c) green-lighting Stage 2 as the
go/no-go gate.
