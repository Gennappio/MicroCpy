# MicroC Adapter

A standalone re-expression of the jayatilake v7 tumor-microenvironment model in the new ABM workflow format.

This adapter contains its own copies of all adapter-side Python functions (gene network propagation, cell fate marking, plotting) plus the data files. It runs independently of the jayatilake adapter.

## Structure (new ABM format)

- **Agent kind**: `tumor_cell`
  - Init (seed the agents into the world): `read_checkpoint` + `initialize_netlogo_gene_networks`
  - Behaviors:
    - `gene_update`: substance→input mapping + NetLogo gene network propagation
    - `fate_update`: necrotic / growth-arrest / apoptotic / proliferating marking
    - `division`: cell division + apoptotic removal
- **Environment**:
  - Init (set up the world): `setup_simulation` + `setup_domain` + `setup_population` (empty container, bound to the domain grid) + `setup_substances` + `setup_associations`
  - Behaviors:
    - `diffusion_step`: coupled multi-substance PDE solver
    - `iteration_plots`: per-step plot generation
- **Scheduler** (30 iterations):
  `diffusion_step → gene_update → fate_update → division → iteration_plots`
- **Processing**: `final_summary` (summary plots)

## Running

```bash
python opencellcomms_engine/run_workflow.py --workflow opencellcomms_adapters/MicroC/workflows/microc.json
```

Should reproduce the same per-step cell counts and final plots as the v7 jayatilake workflow.

## Per-behavior subworkflow files

Because MicroC behaviors reference functions across multiple `.py` files
(engine + adapter), the per-behavior `.subworkflow.json` files live under
`MicroC/behaviors/` rather than next to a single `.py` file. These are in the
same format the GUI produces with **Export Behavior**, and can be re-imported
individually via **Import Subworkflow** in the palette.

## Editing the workflow

Edit `workflows/microc.json` directly, or open it in the GUI and re-export via **Export Project**.

## Conflict note

Both jayatilake and MicroC adapters register functions with the same names. When both are imported, the second registration is a benign overwrite (same code). If the engine ever raises on duplicates, comment out the jayatilake import in `opencellcomms_engine/src/workflow/registry.py`.

## Architecture notes (read before editing — these are non-obvious)

### The engine does NOT execute "agent kinds" or "environment"

`metadata.gui.agent_kinds`, `metadata.gui.environment`, `init_subworkflow`,
`behavior_subworkflows`, `main_is_synthesized` are **GUI-only** organizational
metadata. The engine never reads them (confirmed: those keys appear only under
`opencellcomms_gui/src/`, never in `opencellcomms_engine/src/`).

At runtime execution is **flat** and driven entirely by the synthesized
`main` subworkflow:

```
main → __init_sequence__ → __scheduler__ (×30) → final_summary
        │                    │
        │                    └─ diffusion_step → gene_update → fate_update → division → iteration_plots
        └─ environment_init → tumor_cell_init      (just run in execution_order, in sequence)
```

So "this belongs to the agent vs the environment" is a **conceptual/GUI
grouping only** — the engine just runs each subworkflow's `execution_order`.
Moving a function between `environment_init` and `tumor_cell_init` changes how
the GUI groups it and the order in `__init_sequence__`, but nothing about the
engine's semantics. The GUI derives the grouping via
`opencellcomms_gui/src/store/computeSubworkflowKinds.js`.

### "Create the population" is two distinct steps in two different places

Building the population is split into **container creation** (world setup) and
**cell seeding** (agent setup). This split is intentional and reflects the ABM
conceptual model (the world owns the population container; the agent kind
decides which cells seed it):

1. `setup_population` (`opencellcomms_adapters/common/functions/initialization/setup_population.py`)
   — lives in **`environment_init`**. Creates an **EMPTY** `CellPopulation`
   container + the `BooleanNetwork` infrastructure. It does **not** create any
   cells. It **requires** `config` and `mesh_manager` (produced earlier in
   `environment_init` by `setup_simulation` / `setup_domain`); the biological
   grid size is derived from `domain.size_x / domain.cell_height`. This
   dependency on the domain is exactly *why* the container belongs to the
   environment.
2. `read_checkpoint` (`opencellcomms_engine/src/workflow/functions/initialization/read_checkpoint.py`)
   — lives in **`tumor_cell_init`** (the first agent-init node). Loads the actual
   cells from the CSV (`data/initial_cells_1000_center_1500.csv`) into the
   container via `population.initialize_cells(...)`. **This is the node that
   actually produces the cells.**
3. `initialize_netlogo_gene_networks` (`functions/gene_network/`) — also in
   `tumor_cell_init`. Builds a per-cell gene network from the `.bnd` file.

History: before the env/agent split, all three lived in `tumor_cell_init`,
which meant the agent-init node literally named "Setup Cell Population" yielded
zero cells. Moving the container to `environment_init` makes the first agent
node (`read_checkpoint`) the honest cell-creation step.

Other seeding sources exist if you want to replace `read_checkpoint`:
`generate_initial_cells` (sphere/circle packing → VTK, then read it),
`load_cells_from_csv`, `load_cells_from_vtk` — all in
`opencellcomms_adapters/common/functions/initialization/`.

### BND filename

The gene model lives at `data/jaya.bnd`. Both `workflows/microc.json` and
`behaviors/tumor_cell_init.subworkflow.json` reference it as `../data/jaya.bnd`.
Keep those two references in sync with the actual filename:
`initialize_netlogo_gene_networks` returns `False` with
`[ERROR] BND file not found` (and the gene network silently does not load) if
the path doesn't resolve.
