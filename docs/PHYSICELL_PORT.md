# PhysiCell/PhysiBoss → OpenCellComms Integration Plan



## 1. Objective

Port the PhysiBoss simulation framework into the OpenCellComms workflow platform so
that existing PhysiCell/PhysiBoss models (XML + BND/CFG) can be loaded, visualised,
modified, and executed as OpenCellComms workflows.

The approach is **wrap, not rewrite**: keep PhysiCell's performance-critical C++
compute kernels and compile them as a pybind11 extension module.  Replace the
orchestration layer, the PhysiBoss intracellular coupling, custom user functions,
and the main loop with Python code that integrates into the OpenCellComms workflow
engine and GUI.

---

## 2. What PhysiCell/PhysiBoss Is

### 2.1 PhysiCell (C++)

An open-source, physics-based multicellular simulator.  Each cell is an agent with:

- **Continuous-space position** — `double position[3]` in µm.
- **Phenotype** — a large struct containing:
  - `Cycle` (phase-based cell cycle with stochastic transitions)
  - `Death` (apoptosis/necrosis models with rates)
  - `Volume` (total, solid, fluid, nuclear, cytoplasmic + target volumes and ODE rates)
  - `Geometry` (radius, nuclear radius, surface area)
  - `Mechanics` (adhesion strength, repulsion strength, spring constants)
  - `Motility` (speed, persistence time, chemotaxis bias)
  - `Secretion` (per-substance uptake/secretion/export rates)
  - `Intracellular*` (pointer to intracellular model — this is the PhysiBoss hook)
- **Custom data** — key/value store for user variables.
- **Function pointers** — `update_phenotype`, `custom_cell_rule`, `contact_function`,
  `volume_update_function`, `update_velocity`, `pre/post_update_intracellular`.

The microenvironment (BioFVM) solves reaction-diffusion PDEs on a Cartesian voxel
grid.  Each voxel stores a density vector (one float per substrate).

Source files (in `PhysiBoSS-master/`):

| File | Role |
|------|------|
| `core/PhysiCell_cell.h/.cpp` | `Cell` class, `Cell_State`, `Cell_Functions`, `divide()`, `die()`, `update_position()`, `add_potentials()` |
| `core/PhysiCell_phenotype.h/.cpp` | `Phenotype`, `Cycle`, `Death`, `Volume`, `Geometry`, `Mechanics`, `Motility`, `Secretion` |
| `core/PhysiCell_cell_container.h/.cpp` | `Cell_Container`, `update_all_cells()` — the main per-timestep orchestrator |
| `core/PhysiCell_standard_models.cpp` | `standard_volume_update_function()`, `standard_update_cell_velocity()`, `standard_elastic_contact_function()` |
| `BioFVM/BioFVM_microenvironment.h/.cpp` | `Microenvironment`, `simulate_diffusion_decay()` (LOD Thomas algorithm) |
| `BioFVM/BioFVM_basic_agent.h/.cpp` | `Basic_Agent` (cell base class), `simulate_secretion_and_uptake()`, `nearest_density_vector()`, `nearest_gradient()` |

### 2.2 PhysiBoss (C++ addon)

An addon that couples MaBoSS (stochastic Boolean network simulator) to PhysiCell
cells.  Each cell gets a `MaBoSSIntracellular` object that:

1. **Reads** PhysiCell signals (substance concentrations, contact states) and
   thresholds them into MaBoSS input node states.
2. **Runs** the MaBoSS stochastic simulation engine for one intracellular timestep.
3. **Writes** MaBoSS output node probabilities back to PhysiCell phenotype
   (apoptosis rate, proliferation rate, necrosis rate, etc.).

Source files:

| File | Role |
|------|------|
| `addons/PhysiBoSS/src/maboss_intracellular.h/.cpp` | `MaBoSSIntracellular` class: `update()`, `update_inputs()`, `update_outputs()`, `inherit()`, XML parsing |
| `addons/PhysiBoSS/src/maboss_network.h/.cpp` | `MaBoSSNetwork` wrapper: `init_maboss()`, `run_simulation()`, `get/set_node_value()` |
| `addons/PhysiBoSS/src/utils.h/.cpp` | `MaBoSSInput`, `MaBoSSOutput` structs (threshold, smoothing, Hill function parameters) |

### 2.3 The Simulation Loop

```
main.cpp:
  WHILE current_time < max_time:
      treatment_function()                                   # user custom (C++)
      microenvironment.simulate_diffusion_decay(diffusion_dt) # BioFVM PDE solver
      cell_container->update_all_cells(current_time)          # all cell updates

Cell_Container::update_all_cells(t):
  1. Secretion      (every diffusion_dt)     — per cell: advance secretion/uptake
  2. Intracellular  (every diffusion_dt)     — per cell: if need_update():
                                                  pre_update_intracellular()
                                                  intracellular->update()     # PhysiBoss
                                                  post_update_intracellular()
  3. Phenotype      (every phenotype_dt)     — per cell: advance_bundled_phenotype_functions()
                                                  (volume, geometry, cycle, death, transformations)
                                              — process cells_ready_to_divide → divide()
                                              — process cells_ready_to_die → die()
  4. Mechanics      (every mechanics_dt)     — compute gradients
                                              — per cell: evaluate_interactions (contact)
                                              — per cell: custom_cell_rule
                                              — per cell: update_velocity (add_potentials)
                                              — per cell: spring attachments
                                              — per cell: update_position (Adams-Bashforth)
                                              — per cell: update_voxel_in_container
```

### 2.4 Multi-Timescale Structure

PhysiCell runs four nested timescales (from the TNF tutorial `1_Long_TNF.xml`):

| Timescale | dt (min) | What runs | Ratio to finest |
|-----------|----------|-----------|-----------------|
| `dt_diffusion` | 0.01 | Diffusion PDE, secretion/uptake | 1× |
| `dt_mechanics` | 0.1 | Cell forces, positions | 10× |
| `dt_phenotype` | 6.0 | Cycle, death, volume, geometry | 600× |
| `intracellular_dt` | 1440.0 | MaBoSS Boolean network | 144,000× |

---

## 3. Reference Example: TNF Tutorial

The simplest end-to-end PhysiBoss example. Located at
`PhysiBoSS-master/sample_projects_intracellular/boolean/tutorial/`.

### 3.1 Scenario

- ~800 tumour cells in a 1000×1000 µm 2D domain.
- One diffusing substrate: **TNF** (D=1200 µm²/min, decay=0.0275/min).
- TNF applied as Dirichlet BC (concentration=10) with periodic on/off treatment.
- Each cell has a 30-node Boolean network (`cellfate.bnd/cellfate.cfg`) modelling
  the TNF→TNFR→NFkB→Survival vs TNF→DISC→CASP8→CASP3→Apoptosis pathways.

### 3.2 Coupling Rules (from XML)

**Input mapping** (PhysiCell → MaBoSS):

| Substance | MaBoSS node | Threshold | Action |
|-----------|-------------|-----------|--------|
| TNF | TNF | 1.0 | activation |

**Output mapping** (MaBoSS → PhysiCell):

| MaBoSS node | PhysiCell behaviour | Value (ON) | Base value (OFF) |
|-------------|---------------------|------------|------------------|
| Apoptosis | apoptosis rate | 1,000,000 | 0 |
| NonACD | necrosis rate | 1,000,000 | 0 |

### 3.3 Files

| File | Purpose |
|------|---------|
| `config/simple_tnf/1_Long_TNF.xml` | Full PhysiCell config (domain, substrates, cell types, phenotype, MaBoSS coupling, treatment) |
| `config/simple_tnf/boolean_network/cellfate.bnd` | 30-node Boolean network (TNF/NFkB/Apoptosis/Survival) |
| `config/simple_tnf/boolean_network/cellfate.cfg` | MaBoSS rates, initial states, parameters |
| `config/simple_tnf/cells.csv` | Initial cell positions (x,y,z,type) |
| `custom_modules/custom.cpp` | `phenotype_function()` (empty), `treatment_function()` (toggles TNF Dirichlet BC) |
| `main.cpp` | Main simulation loop |

---

## 4. Integration Strategy: Wrap vs Replace

### 4.1 Principle

Keep every compute-hot function in compiled C++.  Replace everything else with
Python to gain GUI visibility, workflow composability, and modifiability.

### 4.2 Functions to WRAP (keep C++, expose via pybind11)

These run millions of times per simulation and would be unacceptably slow in Python.

| C++ function | Signature | Frequency | Cost | pybind11 binding |
|-------------|-----------|-----------|------|------------------|
| `Microenvironment::simulate_diffusion_decay(dt)` | `void(double)` | Every 0.01 min (1M calls for 10k min sim) | O(V×D), Thomas LOD | `env.simulate_diffusion_decay(dt)` |
| `Basic_Agent::simulate_secretion_and_uptake(pS, dt)` | `void(Microenvironment*, double)` | Every 0.01 min × N cells | O(D) per cell | `container.update_secretion_all(dt)` |
| `standard_update_cell_velocity(Cell*, Phenotype&, dt)` | `void(Cell*, Phenotype&, double)` | Every 0.1 min × N cells | O(neighbors) per cell | `container.update_velocities(dt)` |
| `Cell::add_potentials(Cell*)` | `void(Cell*)` | Every 0.1 min × N×neighbors | O(1) per pair | Called internally by `update_velocities` |
| `Cell::update_position(dt)` | `void(double)` | Every 0.1 min × N cells | O(1) per cell (Adams-Bashforth) | `container.update_positions(dt)` |
| `standard_elastic_contact_function(...)` | `void(Cell*, Phenotype&, Cell*, Phenotype&, double)` | Every 0.1 min × spring attachments | O(1) per pair | Called internally by `update_velocities` |
| `standard_volume_update_function(Cell*, Phenotype&, dt)` | `void(Cell*, Phenotype&, double)` | Every 6 min × N cells | O(1) per cell | `container.update_volumes_all(dt)` |

### 4.3 Functions to REPLACE (rewrite in Python)

These are called infrequently, are decision/mapping logic, or are orchestration code.

#### 4.3.1 PhysiBoss Coupling Layer (the core adapter)

| C++ function | Call frequency | Python replacement |
|-------------|----------------|-------------------|
| `MaBoSSIntracellular::update_inputs(cell, phenotype, dt)` | Every intracellular_dt × N cells | `@register_function("physiboss_update_inputs")` — threshold substance concentrations → set pyMaBoSS node states |
| `MaBoSSIntracellular::update_outputs(cell, phenotype, dt)` | Every intracellular_dt × N cells | `@register_function("physiboss_apply_outputs")` — read pyMaBoSS node probabilities → set death/proliferation rates |
| `MaBoSSIntracellular::update(cell, phenotype, dt)` | Orchestrates above + `run_simulation()` | Combined in `run_physiboss_step` workflow function |
| `MaBoSSIntracellular::need_update()` | Every diffusion_dt × N cells | Handled by `TimescaleOrchestrator` |
| `MaBoSSIntracellular::initialize_intracellular_from_pugixml(node)` | Once at init | Python XML parser |
| `MaBoSSIntracellular::inherit(cell)` | On division | `copy.deepcopy(mother_maboss_network)` |

**Why replace:** This is ~300 lines of XML-to-behaviour mapping called once per cell
per intracellular_dt (1440 min in the tutorial).  Speed is irrelevant.  Making it
Python gives GUI visibility and composability.

#### 4.3.2 MaBoSS Engine

| C++ function | Python equivalent |
|-------------|-------------------|
| `MaBoSSNetwork::init_maboss(bnd, cfg)` | `maboss.load(bnd_file, cfg_file)` (pyMaBoSS) |
| `MaBoSSNetwork::run_simulation()` | `sim.run()` (pyMaBoSS — still calls C++ `libMaBoSS` internally) |
| `MaBoSSNetwork::set_node_value(name, val)` | `sim.mutate(name, 'ON'/'OFF')` |
| `MaBoSSNetwork::get_node_value(name)` | `result.get_last_nodes_probtraj()` |

**No speed loss:** pyMaBoSS wraps the same C++ MaBoSS engine.

#### 4.3.3 Phenotype Decisions

| C++ function | Frequency | Python replacement |
|-------------|-----------|-------------------|
| `Cell::advance_bundled_phenotype_functions(dt)` | Every 6 min × N cells | Split into discrete workflow steps |
| `Cycle_Model::advance_model(cell, phenotype, dt)` | Every 6 min × N cells | Python stochastic phase transitions (simple random draws) |
| `Death::check_for_death(dt)` | Every 6 min × N cells | `if random() < rate * dt: mark_dead()` |
| `Cell::divide()` | Rare (~0.001/cell/min) | Python: create daughter, copy state, halve volume |
| `Cell::die()` | Rare | Python: remove from cell list |

#### 4.3.4 Custom Functions

| C++ function | Python replacement |
|-------------|-------------------|
| `phenotype_function(Cell*, Phenotype&, dt)` | `@register_function` — user-editable in GUI |
| `custom_function(Cell*, Phenotype&, dt)` | `@register_function` |
| `contact_function(Cell*, Phenotype&, Cell*, Phenotype&, dt)` | `@register_function` |
| `treatment_function()` | `@register_function("physiboss_treatment")` |

#### 4.3.5 Initialisation and I/O

| C++ function | Python replacement |
|-------------|-------------------|
| `load_PhysiCell_config_file(xml)` | Python XML parser → `PhysiBossConfig` dataclass |
| `initialize_cell_definitions_from_pugixml()` | Part of config loader |
| `load_cells_from_pugixml()` / CSV loading | Existing `load_cells_from_csv` function |
| `setup_microenvironment()` | `setup_domain()` + `setup_substances()` |
| `save_PhysiCell_to_MultiCellDS_v2()` | OpenCellComms visualisation/export functions |

#### 4.3.6 Main Loop

| C++ | Python replacement |
|-----|-------------------|
| `main.cpp` while loop | Workflow JSON + `WorkflowExecutor` |
| `Cell_Container::update_all_cells()` orchestration | Python calling wrapped C++ kernels at appropriate dt intervals |

### 4.4 Functions to SKIP (not needed)

| C++ function | Why skip |
|-------------|----------|
| `standard_cell_transformations()` | Cell type transformations — not used in basic models |
| `apply_ruleset()` | CBHG rules — disabled in tutorial XML, optional feature |
| `standard_cell_cell_interactions()` | Phagocytosis/attack/fusion — all rates=0, rare use |
| SVG plotting functions | OpenCellComms has its own visualisation |
| Legacy output functions | Replaced by OpenCellComms I/O |

---

## 5. Data Structures: The Python↔C++ Bridge

### 5.1 The Core Problem

Cell state lives in C++ structs.  Python needs to read it (for coupling, decisions,
GUI) and write it (for phenotype changes from MaBoSS outputs).  The bridge must be
zero-copy or near-zero-copy for the wrapped compute kernels.

### 5.2 Recommended Approach: NumPy SoA (Structure of Arrays)

Expose C++ cell arrays as NumPy views via pybind11 buffer protocol.

```python
# All cell state exposed as NumPy arrays (zero-copy views of C++ memory)
positions     = container.get_positions()      # np.ndarray shape (N, 3), dtype float64
velocities    = container.get_velocities()     # np.ndarray shape (N, 3)
volumes       = container.get_volumes()        # np.ndarray shape (N,)
pressures     = container.get_pressures()      # np.ndarray shape (N,)
radii         = container.get_radii()          # np.ndarray shape (N,)
cell_types    = container.get_cell_types()     # np.ndarray shape (N,), dtype int32
is_alive      = container.get_alive_mask()     # np.ndarray shape (N,), dtype bool

# Substance grid (zero-copy view of BioFVM density array)
tnf_field     = env.get_density_array(0)       # np.ndarray shape (Vx, Vy)

# Python-only objects (not in C++)
maboss_networks = {cell_id: pyMaBoSS.Simulation(...), ...}
```

### 5.3 Microenvironment Density Storage

BioFVM stores `density_vectors[voxel_idx][substrate_idx]`.  Expose as a 2D NumPy
array `(num_voxels, num_substrates)` or reshape into `(Vx, Vy, num_substrates)` for
spatial access.

### 5.4 Cell Lifecycle

When Python triggers `divide()` or `die()`, it calls back into C++ to create/remove
the cell in the `Cell_Container`.  The NumPy views then reflect the updated state.

---

## 6. Architecture

### 6.1 File Layout

```
OpenCellComms/
├── opencellcomms_engine/src/
│   ├── adapters/
│   │   └── physiboss/                            ← NEW: adapter package
│   │       ├── __init__.py
│   │       ├── config_loader.py                  ← Parse PhysiCell XML → Python config
│   │       ├── coupling.py                       ← PhysiBossSubstrateCoupling class
│   │       ├── phenotype_mapper.py               ← BN output nodes → cell fate rates
│   │       ├── cycle_model.py                    ← Python Cycle_Model (stochastic transitions)
│   │       └── README.md
│   │
│   ├── adapters/_physicell_core/                 ← NEW: pybind11 C++ extension
│   │   ├── CMakeLists.txt
│   │   ├── bindings.cpp                          ← pybind11 module definition
│   │   └── physicell_sources/                    ← symlinks or copies of PhysiCell C++ files
│   │       ├── core/PhysiCell_cell.cpp
│   │       ├── core/PhysiCell_cell_container.cpp
│   │       ├── core/PhysiCell_standard_models.cpp
│   │       ├── core/PhysiCell_phenotype.cpp
│   │       └── BioFVM/BioFVM_*.cpp
│   │
│   └── workflow/functions/
│       ├── initialization/
│       │   ├── setup_physiboss_model.py           ← NEW: loads XML + BND/CFG + coupling
│       │   └── physiboss_treatment.py             ← NEW: Dirichlet BC toggle
│       ├── intracellular/
│       │   └── run_physiboss_step.py              ← NEW: per-cell MaBoSS coupling
│       ├── intercellular/
│       │   ├── apply_physiboss_phenotype.py       ← NEW: BN → cell fate
│       │   └── physiboss_cell_division.py         ← NEW: division with BN inheritance
│       └── diffusion/
│           └── run_diffusion_solver_physicell.py  ← NEW: BioFVM wrapper (optional, replaces FiPy)
│
├── opencellcomms_gui/
│   └── server/workflows/
│       └── physiboss_tnf_tutorial.json            ← NEW: sample workflow
│
└── docs/
    └── PHYSICELL_PORT.md                          ← THIS FILE
```

### 6.2 Adapter Classes

#### `PhysiBossConfigLoader` (`config_loader.py`)

Parses a PhysiCell XML config file into Python dataclasses:

```
PhysiBossConfig
  ├── domain: DomainConfig (x/y/z min/max, dx/dy/dz, use_2D)
  ├── timing: TimingConfig (max_time, dt_diffusion, dt_mechanics, dt_phenotype)
  ├── substrates: list[SubstrateConfig] (name, D, decay, initial_condition, dirichlet)
  ├── cell_definitions: list[CellDefinitionConfig] (name, cycle, death, volume, mechanics, motility, secretion)
  ├── intracellular: IntracellularConfig (bnd_file, cfg_file, intracellular_dt, scaling, inheritance)
  ├── coupling: CouplingConfig
  │     ├── inputs: list[InputMapping] (substance_name, node_name, threshold, action, smoothing)
  │     └── outputs: list[OutputMapping] (node_name, behaviour_name, value, base_value, action, smoothing)
  ├── initial_cells: InitialCellsConfig (csv_path, or random count)
  ├── treatment: TreatmentConfig (enabled, substrate, period, duration)
  └── save: SaveConfig (folder, interval)
```

#### `PhysiBossSubstrateCoupling` (`coupling.py`)

The core adapter logic (~100 lines):

```python
class PhysiBossSubstrateCoupling:
    inputs:  list[InputMapping]     # substance → BN node threshold
    outputs: list[OutputMapping]    # BN node → phenotype rate

    def compute_bn_inputs(substance_concs: dict[str,float]) → dict[str,bool]:
        # For each input: concentration >= threshold → True
        # Supports: activation, inhibition, smoothing

    def apply_phenotype_outputs(bn_states: dict[str,float], cell) → None:
        # For each output: if node active → set rate to value, else base_value
        # Supports: activation, inhibition, smoothing
```

#### `PhysiBossCycleModel` (`cycle_model.py`)

Python reimplementation of `Cycle_Model::advance_model()`:

```python
class CycleModel:
    phases: list[Phase]
    transition_rates: list[list[float]]

    def advance(cell, dt) → None:
        # For each phase link from current phase:
        #   If fixed_duration: advance if elapsed >= 1/rate
        #   Else: advance with probability rate*dt
        #   Handle division_at_phase_exit, removal_at_phase_exit
```

### 6.3 pybind11 Module (`_physicell_core`)

```cpp
PYBIND11_MODULE(_physicell_core, m) {
    py::class_<Microenvironment>(m, "Microenvironment")
        .def("simulate_diffusion_decay", ...)
        .def("get_density_array", ...)        // → NumPy view
        .def("get_gradient_at", ...)
        .def("set_dirichlet_activation", ...)
        .def("compute_all_gradients", ...);

    py::class_<CellContainer>(m, "CellContainer")
        .def("update_mechanics", ...)         // velocity + position update
        .def("update_secretion_all", ...)
        .def("update_volumes_all", ...)
        .def("get_positions", ...)            // → NumPy (N,3) view
        .def("get_velocities", ...)
        .def("get_pressures", ...)
        .def("get_volumes", ...)
        .def("divide_cell", ...)
        .def("remove_cell", ...);

    m.def("create_microenvironment_from_xml", ...);
    m.def("create_cell_container", ...);
    m.def("create_cells_from_csv", ...);
}
```

### 6.4 Workflow JSON Structure

```json
{
  "workflow_version": "2.0",
  "name": "PhysiBoss TNF Tutorial",
  "subworkflows": [
    {
      "name": "initialization",
      "execution_order": ["setup_physiboss_model", "load_cells_from_csv"],
      "nodes": [
        {"function": "setup_physiboss_model", "parameters": {
          "xml_config": "1_Long_TNF.xml"
        }},
        {"function": "load_cells_from_csv", "parameters": {
          "csv_file": "cells.csv"
        }}
      ]
    },
    {
      "name": "macrostep",
      "iterations": "max_time / dt",
      "execution_order": [
        "physiboss_treatment",
        "run_diffusion_solver_physicell",
        "run_physiboss_step",
        "apply_physiboss_phenotype",
        "physiboss_cell_division",
        "update_mechanics_physicell"
      ]
    },
    {
      "name": "finalization",
      "execution_order": ["save_simulation_data", "generate_summary_plots"]
    }
  ]
}
```

---

## 7. Phased Action Plan

### Phase 0: Setup & Proof of Concept (Week 1)

| # | Task | Deliverable | Days |
|---|------|-------------|------|
| 0.1 | Create branch `feature/physiboss-adapter` | Clean branch | 0.5 |
| 0.2 | Create `code_description.txt` and `code_activities.txt` | Traceability docs | 0.5 |
| 0.3 | Create `opencellcomms_engine/src/adapters/physiboss/` skeleton | Package with `__init__.py` | 0.5 |
| 0.4 | Write `config_loader.py` — parse `1_Long_TNF.xml` | Produces `PhysiBossConfig` dataclass from XML | 2 |
| 0.5 | Write proof-of-concept script: load XML → load BND/CFG via pyMaBoSS → load cells from CSV → run 10 timesteps of FiPy diffusion + pyMaBoSS → print cell fates | Standalone `.py` that proves the pipeline connects | 2 |

**Exit criteria:** A Python script reads the PhysiBoss tutorial XML, runs a few
simulation steps, and prints `Cell 42: Apoptosis=True`.  No GUI, no workflow JSON,
no pybind11.

**Commit:** `feat: add PhysiBoss XML config loader + proof-of-concept pipeline`

### Phase 1: Python Adapter Layer (Weeks 2-4)

#### Phase 1A: Core Adapter Classes (Week 2)

| # | Task | File |
|---|------|------|
| 1.1 | `PhysiBossConfigLoader` — full XML parser | `adapters/physiboss/config_loader.py` |
| 1.2 | `PhysiBossSubstrateCoupling` | `adapters/physiboss/coupling.py` |
| 1.3 | `PhysiBossPhenotypeMapper` | `adapters/physiboss/phenotype_mapper.py` |
| 1.4 | `PhysiBossCycleModel` | `adapters/physiboss/cycle_model.py` |

**Commit:** `feat: PhysiBoss adapter classes (coupling, phenotype, cycle)`

#### Phase 1B: Workflow Functions (Week 3)

| # | Task | File | Category |
|---|------|------|----------|
| 1.5 | `setup_physiboss_model` | `functions/initialization/setup_physiboss_model.py` | INITIALIZATION |
| 1.6 | `run_physiboss_step` | `functions/intracellular/run_physiboss_step.py` | INTRACELLULAR |
| 1.7 | `apply_physiboss_phenotype` | `functions/intercellular/apply_physiboss_phenotype.py` | INTERCELLULAR |
| 1.8 | `physiboss_treatment` | `functions/initialization/physiboss_treatment.py` | UTILITY |
| 1.9 | `physiboss_cell_division` | `functions/intercellular/physiboss_cell_division.py` | INTERCELLULAR |
| 1.10 | Register all in `registry.py` | `workflow/registry.py` | — |

**Commit:** `feat: PhysiBoss workflow functions`

#### Phase 1C: Workflow JSON & End-to-End Test (Week 3-4)

| # | Task |
|---|------|
| 1.11 | Write `physiboss_tnf_tutorial.json` workflow (v2.0 subworkflow format) |
| 1.12 | Configure multi-timescale scheduling (0.01, 0.1, 6, 1440 min) |
| 1.13 | Integration test: `python run_workflow.py --workflow physiboss_tnf_tutorial.json` |

**Exit criteria:** TNF tutorial runs fully in Python via OpenCellComms workflow.
FiPy handles diffusion.  pyMaBoSS handles Boolean networks.  Cell fates emerge.
No C++ wrapping yet — mechanics is simplified or skipped.

**Commit:** `feat: TNF tutorial workflow JSON + integration test`

### Phase 2: pybind11 C++ Kernel Wrapping (Weeks 4-6)

#### Phase 2A: Build System (Week 4)

| # | Task |
|---|------|
| 2.1 | Add `pybind11>=2.11.0` to `pyproject.toml` build dependencies |
| 2.2 | Create `CMakeLists.txt` for `_physicell_core` extension module |
| 2.3 | Write `bindings.cpp` (pybind11 module definition) |
| 2.4 | Test: `import _physicell_core` from Python |

**Commit:** `feat: pybind11 build system for PhysiCell core`

#### Phase 2B: Wrap Diffusion (Week 4-5)

| # | Task |
|---|------|
| 2.5 | Wrap `Microenvironment::simulate_diffusion_decay(dt)` |
| 2.6 | Expose density grid as NumPy (zero-copy view) |
| 2.7 | Wrap Dirichlet BC control |
| 2.8 | Wrap gradient computation |
| 2.9 | Validation: compare FiPy vs BioFVM on same grid |

**Commit:** `feat: wrap BioFVM diffusion solver`

#### Phase 2C: Wrap Secretion + Volume (Week 5)

| # | Task |
|---|------|
| 2.10 | Wrap `Secretion::advance()` for all cells |
| 2.11 | Wrap `standard_volume_update_function()` for all cells |
| 2.12 | Expose per-cell volume/radius as NumPy |

**Commit:** `feat: wrap PhysiCell secretion and volume`

#### Phase 2D: Wrap Mechanics (Week 5-6)

| # | Task |
|---|------|
| 2.13 | Wrap `standard_update_cell_velocity()` (includes `add_potentials`) |
| 2.14 | Wrap `Cell::update_position(dt)` for all cells |
| 2.15 | Wrap `standard_elastic_contact_function()` |
| 2.16 | Expose positions, velocities, pressures as NumPy |
| 2.17 | Combined `container.update_mechanics(dt)` |

**Commit:** `feat: wrap PhysiCell mechanics`

#### Phase 2E: Wrap Cell Lifecycle (Week 6)

| # | Task |
|---|------|
| 2.18 | Wrap `Cell::divide()` |
| 2.19 | Wrap `Cell::die()` |
| 2.20 | Wrap cell creation from CSV |
| 2.21 | Wrap `Microenvironment` creation from XML |

**Commit:** `feat: wrap PhysiCell cell lifecycle`

### Phase 3: Validation & Tests (Weeks 7-8)

| # | Task |
|---|------|
| 3.1 | Create `run_diffusion_solver_physicell.py` (BioFVM wrapper, drop-in for FiPy) |
| 3.2 | Create `update_mechanics_physicell.py` (mechanics wrapper) |
| 3.3 | Update workflow JSON to use C++ kernels |
| 3.4 | Run TNF tutorial with C++ kernels (full 10,000 min) |
| 3.5 | Build PhysiCell binary separately for reference |
| 3.6 | Run native PhysiCell with same `1_Long_TNF.xml` |
| 3.7 | Compare outputs (cell count, apoptosis%, necrosis%, spatial distribution; tolerance ±10%) |
| 3.8 | Unit tests: `test_config_loader.py`, `test_coupling.py`, `test_phenotype_mapper.py`, `test_cycle_model.py` |
| 3.9 | Integration test: `test_physiboss_tnf_full.py` (100 min, basic invariants) |
| 3.10 | Performance benchmark: Python-only vs C++ kernels vs native PhysiCell |

**Exit criteria:** Results match native PhysiCell within stochastic tolerance.
Tests pass.  Performance within 5× of native.

**Commit:** `test: PhysiBoss TNF tutorial validation`

### Phase 4: GUI Integration & Documentation (Week 9)

| # | Task |
|---|------|
| 4.1 | Register functions in `functionRegistry.js` (GUI palette) |
| 4.2 | Add parameter metadata for ParameterEditor (file pickers for BND/CFG/XML) |
| 4.3 | Load sample workflow in canvas, verify rendering and execution |
| 4.4 | Write `adapters/physiboss/README.md` |
| 4.5 | Write `docs/PHYSICELL_INTEGRATION_GUIDE.md` (user-facing) |
| 4.6 | Update `CLAUDE.md` |
| 4.7 | Update `docs/CHATLOG.md` |

**Commit:** `docs: PhysiBoss integration guide + GUI registration`

---

## 8. Dependency Graph

```
Phase 0.4 (config_loader)
    │
    ├──→ Phase 1A (adapter classes)
    │        │
    │        ├──→ Phase 1B (workflow functions)
    │        │        │
    │        │        ├──→ Phase 1C (workflow JSON + test)
    │        │        │        │
    │        │        │        └──→ Phase 3 (validation)
    │        │        │                  │
    │        │        │                  └──→ Phase 4 (GUI + docs)
    │        │        │
    │        │        └──→ Phase 2 (pybind11) ──→ Phase 3
    │        │
    │        └──→ Phase 2A (build system) ──→ Phase 2B-E (wrap functions)
    │
    └──→ Phase 0.5 (proof of concept)
```

**Critical path:** 0.4 → 1A → 1B → 1C → 3.4-3.7

**Phase 2 (pybind11) is parallel** to Phase 1B-1C.  Two people can work in parallel:
one on the Python adapter, one on the C++ wrapping.

---

## 9. Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **pyMaBoSS API mismatch** — discrete-time mode, stochasticity, or sample_count=1 behaves differently than the C++ `MaBoSSNetwork` | High | Medium | Phase 0.5 tests this immediately. Fallback: wrap `libMaBoSS-static` directly via pybind11. |
| **pybind11 compilation fails** — OpenMP, macOS linker issues, PhysiCell header dependencies | Medium | Medium | Phase 2.4 is a gate. Fallback: the Python-only path (Phase 1) works without Phase 2; use FiPy for diffusion and simplified NumPy for mechanics. |
| **Multi-timescale scheduling wrong** — phenotype runs at wrong frequency, MaBoSS fires too early/late | High | Medium | Phase 3.7 comparison catches this. The 4 nested timescales are the most subtle part. |
| **Performance too slow** — Python loop over cells is bottleneck for >10k cells | Medium | Low | Phase 3.10 benchmarks. If slow: vectorise with NumPy, add Numba JIT to coupling loop, or batch pyMaBoSS calls. |
| **PhysiCell C++ API changes** — different PhysiCell versions break the pybind11 bindings | Medium | Low | Pin to a specific PhysiCell version (the one in PhysiBoSS-master). Abstract the C++ interface behind a stable Python API. |
| **Cell mechanics gap** — OpenCellComms lattice model gives qualitatively different results than PhysiCell continuous model for morphological questions | Low | High (expected) | Document as a known limitation. The Python-only fallback is sufficient for signalling/fate questions but not for morphological studies. Phase 2 resolves this. |

---

## 10. What OpenCellComms Already Has

Key existing infrastructure that this integration builds on:

| Component | Location | How it helps |
|-----------|----------|--------------|
| `setup_maboss` | `functions/initialization/setup_maboss.py` | Already loads pyMaBoSS, stores in context. Extend for PhysiBoss coupling. |
| `run_maboss_step` | `functions/intracellular/run_maboss_step.py` | Per-cell MaBoSS execution. Needs rewrite to add substrate coupling, but pattern exists. |
| `FiPy diffusion solver` | `simulation/multi_substance_simulator.py` | Already solves multi-substance PDEs. Serves as the default diffusion backend. |
| `TimescaleOrchestrator` | `simulation/orchestrator.py` | Multi-timescale scheduling. Needs configuration for the 4 PhysiCell timescales. |
| `@register_function` decorator | `workflow/decorators.py` | All new functions use this pattern. |
| `_TEMPLATE.py` | `workflow/functions/_TEMPLATE.py` | Starting point for new functions. |
| `load_cells_from_csv` | `functions/initialization/` | Already reads CSV cell positions. |
| `mark_apoptotic_cells`, `mark_necrotic_cells`, etc. | `functions/intercellular/` | Cell fate marking functions. |
| `update_cell_division` | `functions/intercellular/` | Cell division with gene network inheritance. |
| `opencellcomms_adapters/` | Project root | Experiment-specific adapters pattern. PhysiBoss adapter lives here or in `engine/src/adapters/`. |

---

## 11. Considerations and Open Questions

### 11.1 Where Should PhysiBoss Functions Live?

Two options per the existing project conventions:

- **`opencellcomms_engine/src/adapters/physiboss/`** — if we consider PhysiBoss
  support a generic, reusable engine capability (any PhysiCell model can be loaded).
- **`opencellcomms_adapters/physiboss/`** — if we consider it experiment-specific
  (like the existing `jayatilake` and `maboss` adapters).

**Recommendation:** The adapter classes (config loader, coupling, cycle model) go in
`opencellcomms_engine/src/adapters/physiboss/` because they are generic.  The
pybind11 extension also lives in the engine.  Specific experiment workflows (e.g.
the Jaya model from PhysiBoss_micro) go in `opencellcomms_adapters/physiboss_jaya/`.

### 11.2 FiPy vs BioFVM for Diffusion

Phase 1 uses FiPy (already working).  Phase 2 wraps BioFVM.  Should we keep both?

**Recommendation:** Yes.  FiPy is the default (pure Python, no compilation needed).
BioFVM is an optional high-performance backend selectable via a workflow parameter.
This keeps the system accessible to users who don't want to compile C++.

### 11.3 Cell Mechanics: When is it Worth the Effort?

The pybind11 mechanics wrapping (Phase 2D) is the hardest part.  It's needed for:
- Tumour spheroid growth where shape matters.
- Studies involving cell compression, contact inhibition via pressure.
- Any model where continuous-space cell positions and forces are essential.

It's NOT needed for:
- Pure signalling studies (like TNF tutorial — apoptosis fraction is the readout).
- Gene network validation.
- Drug screening (which substance threshold kills which cells).

**Recommendation:** Phase 2D is optional.  Deliver Phase 1 + Phase 2B (diffusion
only) first.  This already gives 80% of the value.  Add mechanics when a specific
biological question requires it.

### 11.4 pyMaBoSS vs Direct libMaBoSS Wrapping

pyMaBoSS (the Python package) wraps MaBoSS but with a different API than what
PhysiBoss uses internally.  Key differences:

- PhysiBoss calls `run_simulation()` which advances the Boolean network state
  in-place for `time_to_update/scaling` time units.
- pyMaBoSS runs a full simulation (with sample_count samples) and returns
  probability trajectories.

For per-cell, single-sample, in-place state updates (what PhysiBoss does), we may
need to use pyMaBoSS's lower-level API or wrap `libMaBoSS` directly.

**Recommendation:** Test pyMaBoSS with `sample_count=1` in Phase 0.5.  If the
single-sample mode faithfully reproduces the in-place state update, use pyMaBoSS.
If not, wrap `libMaBoSS-static` via pybind11 alongside the other C++ kernels.

### 11.5 Continuous vs Lattice Cell Positions

OpenCellComms currently uses integer grid positions.  PhysiCell uses continuous
floats.  The wrapped mechanics (Phase 2) will use continuous positions.  This means:

- Phase 1 (Python-only): cells are placed on the lattice (existing model).
  Substance concentration lookup uses grid coordinates.
- Phase 2 (with pybind11): cells have continuous positions.  Substance lookup uses
  `nearest_voxel_index(position)` (matching PhysiCell exactly).

The transition from lattice to continuous positions affects `update_cell_division`,
`update_cell_migration`, and concentration lookups.  These functions need a
`if using_physicell_core:` branch or should be refactored to support both.

### 11.6 Performance Expectations

For the TNF tutorial (~800 cells, 10,000 min, 1M diffusion steps):

| Configuration | Expected wall time |
|---------------|-------------------|
| Native PhysiCell (C++) | ~2-5 min |
| OpenCellComms + pybind11 kernels | ~10-25 min (5× overhead from Python orchestration) |
| OpenCellComms + FiPy (no pybind11) | ~30-120 min (FiPy is slower than BioFVM LOD) |

The 5× overhead is the cost of Python function call dispatch, context dict access,
and per-cell Python loops for the coupling logic.  This is acceptable because:
1. The user gains GUI visibility and workflow composability.
2. For larger models, the C++ kernels dominate (mechanics is O(N²), Python overhead
   is O(N)).

### 11.7 Version Pinning

The integration must be tested against a specific PhysiCell version.
`PhysiBoSS-master` appears to be based on PhysiCell 1.13.x (post-2023).
Document the exact version hash.  If upstream PhysiCell changes break the
pybind11 bindings, we can always fall back to the Python-only path.

### 11.8 Broader Vision

This PhysiBoss adapter is the first of potentially several simulator adapters:
- PhysiCell/PhysiBoss (this plan)
- CompuCell3D (Potts model)
- Chaste (finite element)
- Custom C++ kernels for specific biophysics

The `adapters/` package structure should be designed with this in mind.  Each
adapter exposes the same workflow function interface (`setup_*`, `run_*_step`,
`apply_*_phenotype`) so they are interchangeable in the GUI.

---

## 12. Summary

| Question | Answer |
|----------|--------|
| How feasible? | Very feasible — the biology is already 60% implemented in OpenCellComms |
| Prototype (Python-only, FiPy, no mechanics)? | **3-4 weeks** |
| Full integration (pybind11, BioFVM, mechanics)? | **7-10 weeks** |
| The hard part? | pybind11 build system + mechanics wrapping |
| The easy part? | BN loading (pyMaBoSS), config parsing (XML), coupling logic |
| Most value for least effort? | Phase 0 + Phase 1 — Python-only adapter with FiPy |
| Who can work in parallel? | Person A: Python adapter (Phase 1). Person B: pybind11 (Phase 2). |

---

*This document was generated from a detailed analysis of both codebases. It should
be kept up-to-date as the implementation progresses.  Update the status field at
the top and add notes to `docs/CHATLOG.md` after each phase completion.*
