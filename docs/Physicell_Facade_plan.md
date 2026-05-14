# PhysiCell / PhysiBoSS — Black-Box Facade Plan

Companion to `PHYSICELL_PORT.md`. **Supersedes** the earlier draft of this
document, which proposed reimplementing PhysiCell kernels in standalone
pybind11 modules. That direction is dropped.

## 1. Goal

Use the **latest upstream PhysiCell + PhysiBoSS as a black-box engine**. No
edits to PhysiCell source. `git pull` upstream stays a one-line operation.
OpenCellComms becomes the **composition, code-generation, run-orchestration
and observability layer** on top of it. Biologists design experiments in the
GUI; the engine that actually runs is the engine the upstream community ships.

## 2. Architecture

```
[ GUI ] -- workflow JSON --> [ codegen (Python) ] --> project files
                                                        |
                                                        +- config/PhysiCell_settings.xml
                                                        +- config/cell_rules.csv
                                                        +- custom_modules/custom.{h,cpp}        (small shim)
                                                        +- custom_modules/occ_observability.{h,cpp}
                                                        +- Makefile
                                                        v
                                                  make && ./project
                                                        |
                                                        +- output/output*.xml          (PhysiCell snapshots)
                                                        +- output/occ_events.jsonl     (occ::emit stream)
                                                        v
                                            [ GUI tails events + snapshots ]
```

The engine is the engine. OpenCellComms produces text files and consumes text
files. There is **one** C++ artifact OpenCellComms owns:
`custom_modules/occ_observability.{h,cpp}`. Everything else under
`custom_modules/` is generated.

## 3. Boundary

| Concern | Lives in | Owned by |
|---|---|---|
| Cell mechanics, diffusion, MaBoSS propagation | PhysiCell + PhysiBoSS | upstream |
| Hill-style phenotype rules | `rule_phenotype_function` (upstream) | upstream |
| Custom phenotype logic outside the rules grammar | Generated `custom.cpp` fragments | OpenCellComms (Phase 5) |
| Observability emission | `occ_observability` shim | OpenCellComms |
| Project scaffold (XML, Makefile, cell types) | Codegen | OpenCellComms |
| Workflow composition + GUI | OpenCellComms | OpenCellComms |
| Run driver + event consumer | OpenCellComms | OpenCellComms |

What disappears from the previous plan: `physicell_mechanics/mechanics.cpp`,
`physicell_maboss/`, `physicell_diffusion/`. Those reimplemented PhysiCell
behaviour and are obsolete under this architecture.

## 4. Phased plan

### Phase 1 — Observability runtime (~3 days)

`custom_modules/occ_observability.{h,cpp}`. The single C++ file the project
ever ships. API:

```cpp
namespace occ {
  void emit(const char* event, int cell_id, double t,
            std::initializer_list<std::pair<const char*, double>> fields);
  void rules_observe_begin(Cell* pCell);   // snapshot phenotype rates
  void rules_observe_end  (Cell* pCell);   // diff vs. begin -> emit per-rate change
  void emit_cell_snapshot (Cell* pCell);   // periodic full-state dump
  void flush();                            // called at save_interval and on exit
}
```

Implementation: per-thread buffer -> JSON-Lines file `output/occ_events.jsonl`.
Flush on `save_interval` boundary so events align with PhysiCell snapshots.
No external dependencies beyond the C++ standard library.

Validation: build a stub PhysiCell project that emits 100 events and check
the JSONL stream is well-formed and OpenMP-safe.

### Phase 2 — Project scaffold codegen (~1 week)

Workflow JSON -> complete PhysiCell project tree, runnable with `make`.
Generated files:

- `config/PhysiCell_settings.xml` — domain, substrates, cell types,
  `save_interval`, MaBoSS coupling block, treatment schedule
- `custom_modules/custom.{h,cpp}` — minimal shim. `update_phenotype` is the
  composed function shown below; no rules CSV loaded yet
- `custom_modules/occ_observability.{h,cpp}` — copied from Phase 1
- `Makefile` — derived from the upstream sample-project Makefile; the sources
  list points at the unmodified `PhysiBoSS-master/` tree

Composed function in this phase:

```cpp
void update_phenotype_composed(Cell* pCell, Phenotype& phenotype, double dt) {
    occ::rules_observe_begin(pCell);
    rule_phenotype_function(pCell, phenotype, dt);   // upstream symbol; no-op until Phase 3
    occ::rules_observe_end(pCell);
    if (occ::should_snapshot()) occ::emit_cell_snapshot(pCell);
}
```

Exit criteria: a workflow JSON describing a 2-substrate, 1-cell-type problem
generates a project that builds and runs against unmodified `PhysiBoSS-master`.

### Phase 3 — Hypothesis Rules CSV codegen + grammar (~1.5 weeks) — **MVP**

The first round of biologist-facing functionality.

- Define the **Hill-rule node** in the GUI: a workflow node with fields
  `cell_type, signal, direction, behavior, half_max, hill_power, saturation,
  use_on_dead`. DICT parameter, per `CLAUDE.md` GUI conventions.
- Codegen pass writes `config/cell_rules.csv` from every Hill-rule node.
- Project XML registers the CSV via the `<cell_rules>` block consumed by
  `parse_rules_from_pugixml` (already in `core/PhysiCell_rules.cpp`).
- A **grammar validator** in Python rejects nodes that don't fit the grammar
  at workflow-save time, with a clear error and a pointer to "Phase 5
  (fragments) is required for this rule".

Observability target for this phase: every rule-driven rate change emits a
`rule_engine_changed` event with `from`, `to`, and the values of the relevant
signals at that cell at that time. GUI renders this as a per-cell timeline.

Exit criteria: the upstream `sample_projects/rules_sample` is reproducible by
loading its CSV-equivalent workflow into the GUI and re-running through
OpenCellComms; population trajectories match native within stochastic tolerance.

### Phase 4 — Run driver + GUI integration (~1 week)

- `opencellcomms_engine` `WorkflowExecutor`: a new "physicell" backend that,
  for workflows tagged as physicell-target, runs codegen -> `make` -> spawn ->
  tail events. Existing Python-only backends untouched.
- GUI: subscribe to `output/occ_events.jsonl`, live-update a "rule fires"
  timeline and a per-cell snapshot view.
- `make validate-physicell` target wraps the Phase 3 reproduction as a
  regression test.

### Phase 5 (later) — Fragment library for non-Hill rules

Path back to running the prostate model and anything else that exceeds the
rules grammar. Not part of the MVP.

- A versioned **fragment library** of small parameterised C++ templates, one
  per "kind of behaviour" (MaBoSS-coupled drug sensitivity, custom drug
  pharmacokinetics, contact-mediated logic, BN-output -> phenotype rates).
- Codegen extends to interleave fragments with the rules engine in the
  composed function: `pre_fragments -> rule_phenotype_function -> post_fragments`.
- Each fragment template carries its own `occ::emit` call, so per-rule
  observability is explicit (vs. the diff-based observability used for the
  rules engine).
- Validation: `compare_prostate_native.py` is the regression test for this
  phase; parity should be exact since the engine being driven is identical.

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Rules grammar can't express user's intent | Validator surfaces this clearly at workflow-save time; user is told Phase 5 is needed |
| Codegen drifts from upstream Makefile conventions | Generate the Makefile from the upstream sample-project Makefile each release, not hand-written |
| Observability JSONL becomes large in long runs | Per-event filtering at emit time (configurable from the GUI); rotate per save_interval |
| OpenMP races in `occ::emit` | Per-thread buffer, single-writer flush at `save_interval` boundary |
| Build breaks after `git pull PhysiCell` | CI job: nightly codegen + build of one canonical workflow against upstream master |

## 6. Definition of done (Phases 1-4, MVP)

- A workflow built in the GUI with only Hill-rule nodes generates, builds and
  runs against unmodified `PhysiBoSS-master`.
- Rule-fire events stream to the GUI with per-rate-change granularity.
- The upstream `sample_projects/rules_sample` is reproducible end-to-end via
  OpenCellComms.
- No file in `PhysiBoSS-master/` is ever edited by OpenCellComms.

## 7. What carries over from the previous plan

- `opencellcomms_adapters/prostate/` Python scaffolding stays as the *spec*
  for Phase 5 (it documents the prostate experiment's coupling and treatment).
- `compare_prostate_native.py` stays as the validation target for Phase 5.
- Everything in `src/adapters/physicell_mechanics/` and the per-cell MaBoSS
  pool ideas from F1/F2 of the previous draft are **dropped**. No
  reimplementation of upstream kernels.
