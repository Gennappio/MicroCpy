# OpenCellComms evaluation harness

**Question this answers:** does the constrained authoring environment (workflow IR,
role-aware scaffolds, canonical examples, static validators, the `/occ_*` protocols)
actually let a coding agent turn a `MODEL.md` into correctly-structured, runnable ABM
code — in fewer correction rounds, with the remaining corrections about biology rather
than plumbing? The paper (`ARTICLE/`, `docs/AGENT_ASSISTED_ABM_AUTHORING.md`) claims it
does but calls the evidence *"structural and qualitative, not a controlled benchmark."*
This is that benchmark.

It **regenerates each canonical model from its `MODEL.md` in a quarantined workspace,
scores the result on four axes, and records the coding agent's full reasoning trace**
so every defect is traced back to the reasoning step that caused it.

The benchmark set is the three canonical plugins — SUGARSCAPE, TCELL_CORRAL, MicroC —
which are also the paper's three use cases.

## The four axes

| Axis | Module | What it answers | Benchmark needed? |
|---|---|---|---|
| **Conformance** | `harness/conformance.py` | Does the artifact satisfy the repo's own rules (validator + Expected Contract + AST anti-patterns)? | No |
| **Fidelity** | `harness/compare_workflow.py` | Does it encode the *same ABM* (slot-level, matched by biological role not identifier)? | Yes |
| **Behavior** | `harness/compare_results.py` | Does it run, reproduce deterministically, and satisfy the MODEL.md Observables? | Yes |
| **Reasoning** | `harness/trace.py` | *Where did the reasoning break, and why?* — defect → quoted thinking → root cause | — |

A regenerated model can be **correct but different**: function names and file paths are
free variables. So nothing here is a byte-diff. Conformance is objective and needs no
benchmark; fidelity compares *roles* not names; behavior is aggregate/trajectory-level
across implementations (only same-code/same-seed comparison is bit-exact).

## Running the comparators (standalone)

```bash
# Fidelity — semantically compare two workflow JSONs
python -m evals.harness.compare_workflow  BENCH.json  CANDIDATE.json

# Conformance — validate against the repo's rules + scan plugin code for anti-patterns
python -m evals.harness.conformance  CANDIDATE.json  --plugin-dir path/to/PLUGIN

# Behavior — run + snapshot + compare (fresh process per run; seeds the globals)
python -m evals.harness.compare_results determinism --workflow W.json --seed 123 --steps 5
python -m evals.harness.compare_results run     --workflow W.json --seed 123 --steps 5 --out DIR
python -m evals.harness.compare_results compare REF_DIR NEW_DIR [--field-rtol R --field-atol A]
```

## Design decisions (see the plan for rationale)

- **Reuse, don't reinvent.** The comparators are thin layers over machinery that
  already exists and is the same oracle the `/occ_*` skills target:
  `tools/compact_workflow.py` (semantic canonical form), `scripts/validate_workflow.py`
  (conformance), `tools/migration/microc_golden.py` (numeric diff). See `harness/_engine.py`.
- **Determinism footguns are obeyed** (from `microc_golden.py`): seed the *global* RNGs
  (not just `workflow.seed`, which only orders entities), key cells by **position** (not
  the unseedable `uuid4` daughter ids), and run each simulation in a **fresh process**.
- **Contamination is the #1 threat.** `CLAUDE.md` and `/occ_new-model` tell the agent to
  read the canonical workflows as examples — including the target's own. Each run gets a
  quarantined workspace (no `.git`) with the target stripped to `MODEL.md` + inputs, and
  the canonical-examples lists rewritten to name only the *other* models. `trace.py`
  scans every read for quarantined paths and **marks a leaked run invalid**.
- **The gates are the metric.** `/occ_new-model` has two human stop-gates (the `❓ NEEDS`
  question round and the pre-code preview approval). A **simulated biologist**
  (`prompts/biologist.md`) plays the biologist at both, answering from an answer key but
  never handing over the architecture. Each round-trip is a *correction round* — the
  paper's headline metric.

## Layout

```
cases/{sugarscape,tcell_corral,microc}.yaml   # benchmark paths, quarantine sets, seeds
conditions/{full,no_validator,no_protocol,naked}.yaml   # the experimental control
prompts/biologist.md                          # the simulated biologist (versioned)
golden/                                        # frozen benchmark copies + captured runs
harness/                                       # comparators, conformance, trace, score, report
tests/                                         # the harness's own tests (run before it is trusted)
runs/                                          # generation outputs (gitignored)
```

## The conditions

| id | CLAUDE.md | `/occ_*` | validator | examples | isolates |
|---|---|---|---|---|---|
| `full` | ✓ | ✓ | ✓ | ✓ (−target) | the system as shipped |
| `no_validator` | ✓ | ✓ | ✗ | ✓ | what the validator catches |
| `no_protocol` | ✓ | ✗ | ✓ | ✓ | what the protocol adds |
| `naked` | ✗ | ✗ | ✗ | ✗ | the generic-agent baseline |

## Two tiers, one MODEL.md

`MODEL.md` is authored so its first three sections (Provenance · Biology · Observables)
stand alone as a **biology brief**. Tier 1 (`spec2code`) feeds the whole file — slots
given, agent writes code. Tier 2 (`bio2code`) feeds only the brief — the agent must
*derive* the slots, passing both gates, and its MODEL.md becomes a scored artifact.

## Verify the harness before trusting it

```bash
cd evals && python -m pytest tests/ -q          # 54 tests (2 slow: live SUGARSCAPE run)
cd evals && python -m pytest tests/ -q -m "not slow"
```

The tests are adversarial: benchmark-vs-itself must be identical, and a benchmark with
a deliberately-injected defect (orphan, `for_each`-on-creation, double-iteration loop,
dropped scheduler node) must be **detected and classified**. A comparator that cannot
tell the benchmark from a corrupted benchmark measures nothing.

## Adding a case

1. Write `cases/<name>.yaml` (copy `sugarscape.yaml`): plugin path, benchmark workflow,
   quarantine strip/keep lists, allowed cross-model examples, run seed/steps.
2. Ensure the plugin has a layered `MODEL.md` with an `## Observables` section.
3. `python -m evals.harness.conformance <benchmark.json> --plugin-dir <plugin>` should be
   clean — if the benchmark itself violates the rules, fix that first (grading against a
   non-conformant benchmark is incoherent).
