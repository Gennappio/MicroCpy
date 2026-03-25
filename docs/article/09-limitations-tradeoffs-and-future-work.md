# Chapter 9 — Limitations, Tradeoffs, and Future Work

## 9.1 Why this chapter exists

Credible scientific software writeups include limitations. Otherwise, readers cannot:

- judge whether the tool fits their use case,
- interpret results appropriately,
- or contribute effectively.

OpenCellComms makes several explicit tradeoffs (especially around observability and run management) and has predictable constraints (performance, complexity growth).

## 9.2 Tradeoff: research-tool simplicity vs run management

The observability spec explicitly chooses:

- **no run history**
- **overwrite semantics**
- **flat-file artifacts**

Advantages:

- fewer moving parts
- fewer failure modes
- easy inspection and manual archiving

Drawbacks:

- users must archive runs they want to preserve
- harder to compare runs inside the UI without external tooling

Future work directions (optional):

- a lightweight “export run bundle” action in the GUI
- a minimal run index file (still flat-file) for local comparisons
- optional “do not overwrite” mode with timestamped result folders

## 9.3 Limitation: performance at scale

Multi-scale models are computationally expensive. Likely bottlenecks:

- diffusion solves (grid size × steps × substances)
- per-cell computations (cells × steps)
- frequent output writing
- context snapshotting if enabled for every node

What can be done:

- reduce output frequency during exploration
- add performance profiling and benchmarking workflows
- parallelize where valid (carefully; determinism matters)
- use optional acceleration packages (numba/cython) where appropriate

An honest message to readers:

> OpenCellComms is designed to make complex models easier to build and debug. Maximum throughput for massive runs requires additional optimization work.

## 9.4 Limitation: workflow complexity can become its own problem

Visual workflows reduce some complexity, but they can grow into “spaghetti graphs” if unmanaged.

Mitigations:

- use subworkflows to keep graphs modular
- adopt naming conventions for nodes and parameters
- keep “stages” or subworkflow scopes small and purposeful
- include a standard library of reusable subworkflows for common patterns

Potential future work:

- lints for workflows (anti-pattern detection)
- “collapse into subworkflow” refactor tool in the GUI
- better search and navigation across large workflows

## 9.5 Limitation: scientific validation is outside the tooling

OpenCellComms can help make runs reproducible and debuggable, but it cannot guarantee that:

- the chosen biological model is correct,
- parameters are biologically meaningful,
- coupling assumptions are valid.

What the platform can do better over time:

- stronger schema validation and domain constraints
- built-in sanity checks (mass conservation, bounds, negative concentrations)
- benchmark suites against published reference experiments

## 9.6 Naming and product identity (a practical documentation risk)

The project is called **OpenCellComms**. Legacy references to MicroCpy, MicroC, or BioComposer may still appear in older code comments or adapter-level model names. These are being consolidated over time.

## 9.7 A realistic roadmap (future work worth stating)

Depending on your audience, a realistic roadmap might include:

- **Workflow maturity**
  - better validation, linting, refactoring, modularity tools
- **Observability MVP → full loop**
  - artifacts tab: automatically associate plots/files with producing nodes
  - call-path tracing across nested subworkflows
  - richer context diff viewers for large arrays
- **Reproducibility features**
  - run bundling/export
  - manifest files with versions, seeds, and inputs
- **Performance**
  - profiling UI, benchmark workflows, targeted optimizations
- **Model library expansion**
  - more built-in functions for common biology patterns
  - curated example workflows for published experiments

## 9.8 Suggested figures (for this chapter)

- **Figure 1 — “Tradeoffs” table**
  - A table with columns: Choice / Benefit / Cost.
  - Include overwrite semantics, snapshot frequency, modular nodes.

- **Figure 2 — “Workflow complexity” illustration**
  - A before/after showing how subworkflows reduce graph clutter.

