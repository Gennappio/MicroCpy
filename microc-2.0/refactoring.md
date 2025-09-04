# MicroC 2.0 – Refactoring Blueprint (SOLID, Maintainable, Readable)

This document proposes a clean architecture for MicroC that is: testable, modular, and easy to extend. It adopts SOLID, hexagonal architecture (ports & adapters), and clear separation of concerns across simulation, diffusion, biology, I/O, and visualization.

The plan is incremental: you can phase it in area-by-area without a big bang.


## 1) Guiding Principles
- Single Responsibility: each class does one thing well (e.g., building source fields is not the solver’s job).
- Open/Closed: add new solvers, substances, or metabolism models without touching core logic.
- Liskov: interfaces define substitutable behavior (e.g., any DiffusionSolver must solve the same problem contract).
- Interface Segregation: small, focused interfaces (e.g., BoundaryConditionProvider separate from Solver).
- Dependency Inversion: high-level policies depend on abstractions, not FiPy or matplotlib.
- Ports & Adapters: core logic sits behind abstractions; concrete tech (FiPy, VTK, matplotlib) is plugged in at the edge.
- Determinism & Testability: pure functions where possible; inject time/randomness.
- Clear Units: encapsulate physical units in value objects to avoid sign/scale mistakes.


## 2) High-level Architecture

Layers (inner to outer):
- Domain (entities & value objects)
- Application (use cases/orchestrator, services)
- Infrastructure (adapters: FiPy, VTK/H5, plotting, CLI)
- Interfaces (ports/interfaces that infrastructure implements)


## 3) Proposed Package Layout

```
src/
  core/
    domain/
      geometry.py           # DomainSpec, GridSpec, IndexMapping
      units.py              # Length, Time, Concentration, Diffusivity, Rate, etc.
      cells.py              # CellId, CellState, Phenotype (value objects)
      substances.py         # SubstanceId, SubstanceConfig (immutable), Thresholds
    policies/
      scheduling.py         # UpdatePolicy, TimingStrategy (interfaces)
      metabolism.py         # MetabolismModel (Strategy)
      boundaries.py         # BoundaryConditionProvider (port)
  simulation/
    orchestrator/
      engine.py             # SimulationEngine (application service)
      scheduler.py          # MultiTimescaleScheduler (Strategy-based)
    diffusion/
      ports.py              # DiffusionSolver, EquationBuilder (ports)
      equations.py          # SteadyStateEquationSpec (value object)
      source_field.py       # SourceFieldBuilder (maps reactions→mesh)
      fipy_adapter.py       # FiPyDiffusionSolver (adapter)
    biology/
      population.py         # PopulationService (app service)
      genes.py              # GeneNetwork, GeneStates
      metabolism_service.py # Calculates reactions via MetabolismModel
    substances/
      registry.py           # SubstanceRegistry (lookup metadata/config)
  io/
    config_loader.py        # YAML→Config (Pydantic/dataclasses)
    vtk_reader.py           # VTK domain reader (port impl)
    vtk_writer.py           # VTK field/cell writer (port impl)
    h5_io.py                # H5 gene states save/load
    logging.py              # Structured logging & diagnostics
  presentation/
    plots.py                # PlotService (adapter, decoupled from sim)
    reports.py              # Text/HTML report generator
  app/
    cli.py                  # Unified CLI (run, analyze, visualize)
    presets.py              # Ready-made configs
```

Tests: `tests/unit`, `tests/integration`, `tests/golden`, `tests/perf`.


## 4) Core Domain (Entities & Value Objects)

- DomainSpec
  - size_x/y/z: Length; nx/ny/nz: int; centered: bool
  - to_grid_spec(): returns GridSpec (cell size, spacing)

- GridSpec
  - spacing_x/y/z: Length; shape: tuple[int, int, int]
  - index_of(point: (m, m, m)) → int (column-major mapping consistent everywhere)
  - Guarantees: mapping is the single source of truth for FiPy indices.

- Units (units.py)
  - Length, Time, Concentration, Diffusivity, RateMolPerCell, RateMMPerSec
  - Conversion helpers (explicit, named methods) to avoid implicit bugs.

- SubstanceConfig (immutable)
  - name, initial_conc: Concentration, boundary_value: Concentration
  - diffusion: Diffusivity, boundary_type (enum), thresholds

- CellState (immutable-ish dataclass with `with_updates`)
  - id, position (bio grid coords), phenotype, gene_states, metabolic_state

- Reaction (value object)
  - per-substance mol/s/cell map; sign convention: negative=consumption, positive=production (documented here once)


## 5) Policies (Interfaces/Strategies)

- TimingStrategy (Strategy)
  - should_update_diffusion(step, last, interval, state) → bool
  - should_update_intracellular(...), should_update_intercellular(...)
  - Provide a DefaultIntervalStrategy + CustomScriptStrategy (loads user python)

- MetabolismModel (Strategy)
  - reactions_for(cell_state, local_env) → Reaction
  - Implementations: NetLogoCompatibleModel, FixedRatesModel (for tests), HybridModel

- BoundaryConditionProvider (Port)
  - apply(var, mesh) → None (adapter decides how to set gradients/fixed faces)


## 6) Application Services

- SimulationEngine
  - run_step(): orchestration of scheduling → diffusion → genes → phenotypes → IO hooks
  - depends on: Scheduler, PopulationService, DiffusionService, SubstanceRegistry, PlotService (optional), Repositories

- MultiTimescaleScheduler
  - holds intervals; delegates to TimingStrategy; records last_update; pure logic

- PopulationService
  - holds Cells, provides: get_local_env(cell), update_gene_networks(), update_phenotypes(), remove_dead, division
  - consumes MetabolismService for reactions; exposes aggregate reactions per position

- MetabolismService
  - depends on MetabolismModel; aggregates per-cell reactions into per-position reactions

- DiffusionService
  - builds SourceField via SourceFieldBuilder; builds EquationSpec; calls DiffusionSolver
  - updates concentration fields per substance; no FiPy knowledge inside

- SourceFieldBuilder
  - maps reactions (mol/s/cell) to mesh (mM/s) via GridSpec + cell_height + 2D coefficient
  - handles 2D vs 3D; sign conventions; returns np.ndarray ready for solver


## 7) Diffusion (Ports & Adapters)

Ports (interfaces):
- DiffusionSolver
  - solve_steady_state(var_name: str, equation: SteadyStateEquationSpec) → ConcentrationField
- EquationBuilder (optional)
  - build(substance_config, boundary_provider, source_field) → SteadyStateEquationSpec

Adapters (infrastructure):
- FiPyDiffusionSolver
  - owns FiPy mesh/variables; adapts `source_field` into CellVariable
  - uses: DiffusionTerm == -source_var (or ImplicitSourceTerm when appropriate)
  - no unit logic

Value Objects:
- SteadyStateEquationSpec
  - diffusion_coeff, boundary_type/value, source_field (np.ndarray), mesh_ref


## 8) I/O & Persistence

- ConfigLoader (YAML → strongly-typed config; with validation using Pydantic or dataclasses + schema checks)
- DomainRepository (port): load/save domains (VTK reader detects format, returns positions and metadata)
- FieldRepository (port): save concentration fields to VTK/H5; load for post-processing
- Logging: structured logs with context (step, substance, min/max/range, #cells)

Adapters:
- VTKDomainReader, VTKFieldWriter, H5GeneStateWriter/Reader


## 9) Presentation (Visualization & Reports)

- PlotService (adapter)
  - draw_heatmap(field, thresholds, centered_axes, legends), write_png
  - No simulation logic; pure presentation
- ReportService
  - summary page with ranges, counts, timings


## 10) CLI Structure

`app/cli.py` provides subcommands:
- `sim run --config <yaml>`
- `sim diff --h5 <file>`
- `analyze cells --h5 <file>`
- `viz heatmaps --h5 <file>`
- `tools generate --cells N --radius R --output X`

All subcommands call application services through ports; no imports from infrastructure in core.


## 11) Class-by-Class Snapshot (with patterns)

- core/domain/geometry.py
  - class DomainSpec, class GridSpec, class IndexMapping (SRP)

- core/domain/units.py
  - class Length, Time, Concentration, Diffusivity, RateMolPerCell (SRP)

- core/domain/substances.py
  - dataclass SubstanceConfig (immutable)
  - class SubstanceRegistry (Factory + Repository)

- simulation/orchestrator/engine.py
  - class SimulationEngine (Facade over use cases; depends-on-ports) (Dependency Inversion)

- simulation/orchestrator/scheduler.py
  - class MultiTimescaleScheduler (Strategy for timing)

- simulation/biology/population.py
  - class PopulationService (coordinates cells, genes, phenotypes) (SRP)

- simulation/biology/genes.py
  - class GeneNetwork, GeneStates (SRP)

- simulation/biology/metabolism_service.py
  - class MetabolismService (uses MetabolismModel Strategy)

- simulation/diffusion/source_field.py
  - class SourceFieldBuilder (SRP; clear sign/units; testable)

- simulation/diffusion/ports.py
  - interface DiffusionSolver (ISP)

- simulation/diffusion/fipy_adapter.py
  - class FiPyDiffusionSolver (Adapter; implements DiffusionSolver)

- simulation/diffusion/equations.py
  - dataclass SteadyStateEquationSpec (value object)

- io/config_loader.py
  - class ConfigLoader (SRP)

- presentation/plots.py
  - class PlotService (Adapter)


## 12) Patterns Map per Task

- Scheduling: Strategy (timing), Template Method in SimulationEngine for step phases
- Diffusion: Adapter (FiPy), Builder (EquationSpec), Strategy (boundary conditions)
- Metabolism: Strategy (selectable models), Composite (aggregate cell reactions)
- Coordinates/Mapping: Single source of truth in GridSpec (avoid duplication)
- I/O: Ports & Adapters; Repository pattern for domain/fields
- CLI: Command pattern via subcommands
- Events (optional): Observer/EventBus for “after_step”, “after_diffusion” hooks


## 13) Data Flow per Step

1) Scheduler decides which processes to run.
2) PopulationService asks MetabolismService for reactions per cell.
3) MetabolismService aggregates to per-position reactions.
4) SourceFieldBuilder converts to mM/s and maps to FiPy indices.
5) DiffusionSolver solves steady-state and returns concentration fields.
6) PopulationService updates gene networks & phenotypes based on concentrations.
7) I/O saves VTK/H5 and PlotService generates heatmaps.


## 14) Testing Strategy

- Unit tests (pure): units conversions, SourceFieldBuilder, GridSpec index mapping, TimingStrategy
- Contract tests: DiffusionSolver port (run with FakeSolver & FiPyAdapter)
- Integration tests: full step on a tiny grid; golden PNG/VTK range checks
- Property tests: mapping bijection (grid index ↔ coords), conservation checks
- Performance tests: big grids with profiler guards


## 15) Observability & Diagnostics

- Structured logging across phases (substance, min/max/mean, non-zero terms)
- Debug toggles per subsystem (env var or CLI flags)
- Counters for calls (e.g., metabolism invocations) to catch accidental O(N²)


## 16) Migration Plan (Incremental)

1) Introduce DiffusionSolver port and FiPyDiffusionSolver adapter; move all FiPy code behind adapter.
2) Extract SourceFieldBuilder from current MultiSubstanceSimulator (preserve behavior with tests).
3) Introduce SimulationEngine + Scheduler around existing loop; delegate logic gradually.
4) Move custom metabolism to MetabolismModel Strategy; leave current functions as one implementation.
5) Establish GridSpec/IndexMapping as the only mapping authority; remove duplicates.
6) Extract PlotService; remove plotting from simulation core.
7) Replace direct file I/O with repositories; wire adapters in CLI.
8) Consolidate config loading into ConfigLoader with schema validation.
9) Flatten remaining SRP violations (e.g., remove equation building from services).


## 17) Conventions & Defaults

- Coordinates centered by default; DomainSpec knows extents; PlotService uses [-L/2, +L/2].
- Sign convention is documented once: negative=consumption, positive=production.
- 2D adjustment coefficient lives in SourceFieldBuilder; unit conversions are explicit.
- No hidden global state; all services constructed with dependencies.


## 18) Example Wiring (pseudo-code)

```python
# app/cli.py wires ports to adapters
registry = SubstanceRegistry(config.substances)
mesh = GridSpec.from_domain(config.domain)
diff_solver = FiPyDiffusionSolver(mesh, boundary_provider)
source_builder = SourceFieldBuilder(mesh, config.diffusion.twod_coeff, cell_height=config.domain.cell_height)
met_model = NetLogoCompatibleModel(config)
met_service = MetabolismService(met_model)
pop_service = PopulationService(initial_cells, registry, met_service)
scheduler = MultiTimescaleScheduler(config.time, strategy=DefaultIntervalStrategy())
engine = SimulationEngine(scheduler, pop_service, diff_solver, source_builder, registry, plot_service, repositories)
engine.run_step()
```


## 19) Benefits

- Tech-agnostic core (replace FiPy/VTK without touching core logic)
- Clear boundaries reduce bugs (sign/units live in one place)
- Easier profiling & scaling (swap solver, parallelize metabolism)
- Readable codebase with predictable responsibilities


## 20) What Stays Familiar

- Existing config semantics, substances, and the Jayatilake experiment remain usable
- FiPy still powers diffusion, just hidden behind DiffusionSolver
- Custom functions become MetabolismModel implementations and TimingStrategy scripts


---
This blueprint keeps existing scientific behavior intact while making the codebase modular, testable, and future-proof. Start with the DiffusionSolver port + SourceFieldBuilder extraction to get immediate wins with minimal risk.

